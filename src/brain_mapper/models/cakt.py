"""Cognitive-Aware Knowledge Tracing (CA-KT) integrating 6-skill LLM annotations."""

from __future__ import annotations

import math

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from brain_mapper.models.base import BaseKTModel

NUM_COGNITIVE_SKILLS = 6


class CAKT(BaseKTModel):
    """Cognitive-Aware Knowledge Tracing combining Rasch concept-cognitive item
    decomposition, causal time-decayed attention, 6-skill cognitive mastery tracking,
    and Cognitive-IRT scoring.
    """

    def __init__(
        self,
        num_questions: int,
        num_concepts: int,
        question_concepts: np.ndarray | torch.Tensor,
        question_cognitive: np.ndarray | torch.Tensor | None = None,
        emb_size: int = 128,
        hidden_size: int = 128,
        num_layers: int = 1,
        num_heads: int = 4,
        dropout: float = 0.25,
        num_students: int | None = None,
        aux_branch_weight: float = 0.5,
        num_cognitive_skills: int = NUM_COGNITIVE_SKILLS,
        attention_window: int | None = 200,
        rasch_reg_lambda: float = 1e-4,
        use_concepts: bool = True,
        use_rasch: bool = True,
    ) -> None:
        super().__init__(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
        )
        if self.hidden_size % num_heads != 0:
            raise ValueError(f"hidden_size ({self.hidden_size}) must be divisible by num_heads ({num_heads})")
        if attention_window is not None and attention_window <= 0:
            raise ValueError(f"attention_window must be positive when set, got {attention_window}")

        self.num_heads = int(num_heads)
        self.head_dim = self.hidden_size // self.num_heads
        self.num_cognitive_skills = int(num_cognitive_skills)
        self.aux_branch_weight = float(aux_branch_weight)
        self.attention_window = int(attention_window) if attention_window is not None else None
        self.rasch_reg_lambda = float(rasch_reg_lambda)
        self.use_concepts = bool(use_concepts)
        self.use_rasch = bool(use_rasch)
        self.cog_emb_dim = max(16, self.emb_size // 2)
        self.align_dim = max(16, self.hidden_size // 4)

        cog_tensor = self.prepare_cognitive_buffer(question_cognitive, num_skills=self.num_cognitive_skills)
        self.register_buffer("question_cognitive", cog_tensor)

        # Shared concept embeddings + optional Rasch decomposition vs full question embedding
        if self.use_concepts:
            self.concept_emb = nn.Embedding(
                self.num_concepts + 1,
                self.emb_size,
                padding_idx=self.concept_pad_id,
            )
            self.concept_diff_emb = (
                nn.Embedding(
                    self.num_concepts + 1,
                    self.emb_size,
                    padding_idx=self.concept_pad_id,
                )
                if self.use_rasch
                else None
            )
        else:
            self.concept_emb = None
            self.concept_diff_emb = None

        if self.use_rasch:
            self.que_emb = None
            self.que_rasch_scalar = nn.Embedding(
                self.num_questions + 1,
                1,
                padding_idx=self.question_pad_id,
            )
            nn.init.normal_(self.que_rasch_scalar.weight, mean=0.0, std=0.05)
            with torch.no_grad():
                self.que_rasch_scalar.weight[self.question_pad_id].zero_()
        else:
            self.que_rasch_scalar = None
            self.que_emb = nn.Embedding(
                self.num_questions + 1,
                self.emb_size,
                padding_idx=self.question_pad_id,
            )

        self.resp_emb = nn.Embedding(2, self.emb_size)

        self.student_bias = nn.Embedding(num_students, 1) if num_students else None
        if self.student_bias is not None:
            nn.init.zeros_(self.student_bias.weight)

        # DeepSeek cognitive encoders & optional Rasch composition projections
        self.cog_demand_proj = nn.Sequential(
            nn.Linear(self.num_cognitive_skills, self.cog_emb_dim),
            nn.GELU(),
        )
        self.cog_inter_proj = nn.Sequential(
            nn.Linear(2 * self.num_cognitive_skills, self.cog_emb_dim),
            nn.GELU(),
        )
        if self.use_rasch:
            self.cog_diff_proj = nn.Sequential(
                nn.Linear(self.num_cognitive_skills, self.cog_emb_dim),
                nn.GELU(),
            )
            self.rasch_base_proj = nn.Linear(self.emb_size + self.cog_emb_dim, self.emb_size)
            self.rasch_var_proj = nn.Linear(self.emb_size + self.cog_emb_dim, self.emb_size)
        else:
            self.cog_diff_proj = None
            self.rasch_base_proj = None
            self.rasch_var_proj = None

        # Knowledge Acquisition Module (Rasch Item + Concept + Response + Cognitive Outcome -> LSTM)
        acq_in_dim = 3 * self.emb_size + 2 * self.cog_emb_dim
        self.acq_proj = nn.Sequential(
            nn.Linear(acq_in_dim, self.emb_size),
            nn.ReLU(),
            nn.Dropout(self.dropout_rate),
        )
        self.acq_lstm = nn.LSTM(
            input_size=self.emb_size,
            hidden_size=self.hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.drop = nn.Dropout(self.dropout_rate)

        # Monotonic time-decayed causal attention over concept & cognitive signatures (AKT-inspired)
        qk_in_dim = self.emb_size + self.cog_emb_dim
        self.q_attn_proj = nn.Linear(qk_in_dim, self.hidden_size)
        self.k_attn_proj = nn.Linear(qk_in_dim, self.hidden_size)
        self.v_attn_proj = nn.Linear(self.hidden_size + self.emb_size, self.hidden_size)
        self.attn_out_proj = nn.Linear(self.hidden_size, self.hidden_size)
        self.attn_gate = nn.Parameter(torch.full((1,), -1.5))
        self.head_decay = nn.Parameter(torch.full((self.num_heads,), 0.5))

        # Interpretable student cognitive mastery profile psi_t in (0, 1)^S
        self.cog_mastery_head = nn.Sequential(
            nn.Linear(self.hidden_size, self.hidden_size // 2),
            nn.Tanh(),
            nn.Linear(self.hidden_size // 2, self.num_cognitive_skills),
        )
        self.cog_align_proj = nn.Sequential(
            nn.Linear(2 * self.num_cognitive_skills, self.align_dim),
            nn.Tanh(),
        )
        self.cog_irt_offset = nn.Linear(self.align_dim, 1)

        # Cognitive-IRT Parameters: Ability (theta), Difficulty (beta), Discrimination (alpha)
        self.ability_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size + self.align_dim, self.hidden_size // 2),
            nn.Tanh(),
            nn.Linear(self.hidden_size // 2, 1),
        )
        self.que_difficulty = nn.Embedding(
            self.num_questions + 1,
            1,
            padding_idx=self.question_pad_id,
        )
        nn.init.zeros_(self.que_difficulty.weight)
        self.difficulty_proj = nn.Linear(self.emb_size, 1)
        self.cog_difficulty = nn.Linear(self.num_cognitive_skills, 1)

        self.que_disc = nn.Embedding(
            self.num_questions + 1,
            1,
            padding_idx=self.question_pad_id,
        )
        nn.init.zeros_(self.que_disc.weight)

        # Rasch item and Concept+Cognitive problem-solving residual heads
        self.q_solve_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(self.hidden_size // 2, 1),
        )
        self.c_cog_solve_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size + self.align_dim, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(self.hidden_size // 2, 1),
        )

    def _encode_rasch_item(
        self,
        q_ids: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compose question representation via Rasch decomposition or unconstrained que_emb."""
        base_dtype = self.resp_emb.weight.dtype
        if self.use_concepts and self.concept_emb is not None:
            e_c = self.pool_concept_embeddings(q_ids, self.concept_emb)
        else:
            e_c = torch.zeros((*q_ids.shape, self.emb_size), device=q_ids.device, dtype=base_dtype)

        cog = self.question_cognitive[q_ids].to(dtype=e_c.dtype)
        v_cog = self.cog_demand_proj(cog)

        if self.use_rasch:
            if self.use_concepts and self.concept_diff_emb is not None:
                d_c = self.pool_concept_embeddings(q_ids, self.concept_diff_emb)
            else:
                d_c = torch.zeros_like(e_c)
            v_cog_diff = self.cog_diff_proj(cog)
            mu_q = self.que_rasch_scalar(q_ids).to(dtype=e_c.dtype)
            e_base = self.rasch_base_proj(torch.cat([e_c, v_cog], dim=-1))
            d_var = self.rasch_var_proj(torch.cat([d_c, v_cog_diff], dim=-1))
            e_q = e_base + mu_q * d_var
            return e_q, e_c, v_cog, cog, mu_q

        e_q = self.que_emb(q_ids)
        mu_zero = e_q.new_zeros((*q_ids.shape, 1))
        return e_q, e_c, v_cog, cog, mu_zero

    def _build_attention_mask(
        self,
        seq_len: int,
        in_q: torch.Tensor,
        dist_mat: torch.Tensor,
    ) -> torch.Tensor:
        """Build strict causal mask optionally bounded to the local attention_window."""
        causal = dist_mat >= 0
        if self.attention_window is not None:
            causal = causal & (dist_mat < self.attention_window)
        diag_mask = dist_mat == 0
        valid_keys = (in_q != self.question_pad_id).unsqueeze(1).unsqueeze(2)
        return (causal.unsqueeze(0).unsqueeze(0) & valid_keys) | diag_mask.unsqueeze(0).unsqueeze(0)

    def _causal_cognitive_attention(
        self,
        h_drop: torch.Tensor,
        in_e_c: torch.Tensor,
        in_v_cog: torch.Tensor,
        in_e_r: torch.Tensor,
        tgt_e_c: torch.Tensor,
        tgt_v_cog: torch.Tensor,
        in_q: torch.Tensor,
    ) -> torch.Tensor:
        """Attend causally (s <= t) across concept + cognitive signatures with recency decay."""
        bsz, seq_len, _ = h_drop.shape
        q = self.q_attn_proj(torch.cat([tgt_e_c, tgt_v_cog], dim=-1))
        k = self.k_attn_proj(torch.cat([in_e_c, in_v_cog], dim=-1))
        v = self.v_attn_proj(torch.cat([h_drop, in_e_r], dim=-1))

        q = q.view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = k.view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = v.view(bsz, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)).float() / math.sqrt(self.head_dim)

        pos = torch.arange(seq_len, device=h_drop.device)
        dist_mat = pos.unsqueeze(1) - pos.unsqueeze(0)
        rel_dist = dist_mat.clamp(min=0).float()
        decay = F.softplus(self.head_decay).float().view(1, self.num_heads, 1, 1)
        scores = scores - decay * torch.log1p(rel_dist).unsqueeze(0).unsqueeze(0)

        allowed = self._build_attention_mask(seq_len=seq_len, in_q=in_q, dist_mat=dist_mat)
        scores = scores.masked_fill(~allowed, torch.finfo(torch.float32).min)
        attn = torch.softmax(scores, dim=-1).to(dtype=v.dtype)

        ctx = torch.matmul(attn, v).transpose(1, 2).contiguous().view(bsz, seq_len, self.hidden_size)
        gate = torch.sigmoid(self.attn_gate).to(dtype=h_drop.dtype)
        return h_drop + gate * self.drop(self.attn_out_proj(ctx))

    def _rasch_regularization(
        self,
        in_q: torch.Tensor,
        tgt_q: torch.Tensor,
        in_mu: torch.Tensor,
        tgt_mu: torch.Tensor,
    ) -> torch.Tensor:
        """Light L2 penalty on scalar question deviation factors when Rasch mode is enabled."""
        if not self.use_rasch or not self.training or self.rasch_reg_lambda <= 0.0:
            return in_mu.new_zeros((), dtype=torch.float32)
        in_mask = (in_q != self.question_pad_id).unsqueeze(-1).float()
        tgt_mask = (tgt_q != self.question_pad_id).unsqueeze(-1).float()
        in_l2 = (in_mu.float().pow(2) * in_mask).sum() / in_mask.sum().clamp(min=1.0)
        tgt_l2 = (tgt_mu.float().pow(2) * tgt_mask).sum() / tgt_mask.sum().clamp(min=1.0)
        return self.rasch_reg_lambda * 0.5 * (in_l2 + tgt_l2)

    def forward_detailed(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute next-step predictions alongside cognitive mastery, Rasch scalar mu, and IRT quantities."""
        in_e_q, in_e_c, in_v_cog, in_cog, in_mu = self._encode_rasch_item(in_q)
        in_e_r = self.resp_emb(in_r.long().clamp(0, 1))
        r_float = in_r.unsqueeze(-1).to(dtype=in_e_q.dtype)

        signed_cog = torch.cat([in_cog * r_float, in_cog * (1.0 - r_float)], dim=-1)
        in_v_cog_inter = self.cog_inter_proj(signed_cog)

        acq_in = self.acq_proj(torch.cat([in_e_q, in_e_c, in_e_r, in_v_cog, in_v_cog_inter], dim=-1))
        h, _ = self.acq_lstm(acq_in)
        h_drop = self.drop(h)

        tgt_e_q, tgt_e_c, tgt_v_cog, tgt_cog, tgt_mu = self._encode_rasch_item(tgt_q)

        z_t = self._causal_cognitive_attention(
            h_drop=h_drop,
            in_e_c=in_e_c,
            in_v_cog=in_v_cog,
            in_e_r=in_e_r,
            tgt_e_c=tgt_e_c,
            tgt_v_cog=tgt_v_cog,
            in_q=in_q,
        )

        # Interpretable cognitive mastery state & demand-readiness alignment
        cog_mastery = torch.sigmoid(self.cog_mastery_head(z_t))  # [B, L, S]
        met_load = cog_mastery * tgt_cog
        unmet_load = (1.0 - cog_mastery) * tgt_cog
        cog_align_emb = self.cog_align_proj(torch.cat([met_load, unmet_load], dim=-1))

        # Cognitive-IRT Parameters
        theta = self.ability_head(torch.cat([z_t, tgt_e_c, cog_align_emb], dim=-1)).squeeze(-1)
        theta = theta + self.cog_irt_offset(cog_align_emb).squeeze(-1)
        s_offset = self.lookup_student_bias(self.student_bias, student_idx, theta.dtype)
        if s_offset is not None:
            theta = theta + s_offset

        beta = (
            self.que_difficulty(tgt_q).squeeze(-1)
            + self.difficulty_proj(tgt_e_q).squeeze(-1)
            + self.cog_difficulty(tgt_cog).squeeze(-1)
        )
        alpha = F.softplus(self.que_disc(tgt_q).squeeze(-1)) + 0.1

        irt_logit = alpha * (theta - beta)
        q_logit = self.q_solve_head(torch.cat([z_t, tgt_e_q], dim=-1)).squeeze(-1)
        c_cog_logit = self.c_cog_solve_head(torch.cat([z_t, tgt_e_c, cog_align_emb], dim=-1)).squeeze(-1)
        final_logit = irt_logit + self.aux_branch_weight * 0.5 * (q_logit + c_cog_logit)

        reg_loss = self._rasch_regularization(in_q=in_q, tgt_q=tgt_q, in_mu=in_mu, tgt_mu=tgt_mu)

        return {
            "logits": final_logit,
            "reg_loss": reg_loss,
            "irt_logit": irt_logit,
            "q_logit": q_logit,
            "c_cog_logit": c_cog_logit,
            "ability_theta": theta,
            "difficulty_beta": beta,
            "discrimination_alpha": alpha,
            "rasch_scalar_mu": tgt_mu.squeeze(-1),
            "cognitive_mastery": cog_mastery,
            "cognitive_demand": tgt_cog,
            "cognitive_alignment": met_load - unmet_load,
            "prob": torch.sigmoid(final_logit),
        }

    def forward(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Standard forward interface returning (logits, rasch_reg_loss)."""
        out = self.forward_detailed(in_q, in_r, tgt_q, student_idx=student_idx)
        return out["logits"], out["reg_loss"]
