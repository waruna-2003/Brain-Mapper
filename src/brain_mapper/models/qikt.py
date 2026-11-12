"""Question-centric Interpretable Knowledge Tracing (QIKT) baseline (Chen et al., AAAI 2023)."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from brain_mapper.models.base import BaseKTModel


class QIKT(BaseKTModel):
    """Interpretable KT decoupling student ability (theta), question difficulty (beta),
    and question/concept problem-solving modules under an IRT scoring head.
    """

    def __init__(
        self,
        num_questions: int,
        num_concepts: int,
        question_concepts: np.ndarray | torch.Tensor,
        emb_size: int = 128,
        hidden_size: int = 128,
        num_layers: int = 1,
        dropout: float = 0.2,
        num_students: int | None = None,
        aux_branch_weight: float = 0.5,
    ) -> None:
        super().__init__(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
        )
        self.aux_branch_weight = float(aux_branch_weight)

        self.que_emb = nn.Embedding(
            self.num_questions + 1,
            self.emb_size,
            padding_idx=self.question_pad_id,
        )
        self.concept_emb = nn.Embedding(
            self.num_concepts + 1,
            self.emb_size,
            padding_idx=self.concept_pad_id,
        )
        self.resp_emb = nn.Embedding(2, self.emb_size)

        # Optional per-student bias for personalized / class-customized cohorts
        self.student_bias = nn.Embedding(num_students, 1) if num_students else None
        if self.student_bias is not None:
            nn.init.zeros_(self.student_bias.weight)

        # Knowledge Acquisition Module (Question + Concept + Response -> LSTM state)
        self.acq_proj = nn.Sequential(
            nn.Linear(3 * self.emb_size, self.emb_size),
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

        # IRT Interpretable Parameters: Student Ability (theta), Difficulty (beta), Discrimination (alpha)
        self.ability_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size, self.hidden_size // 2),
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

        self.que_disc = nn.Embedding(
            self.num_questions + 1,
            1,
            padding_idx=self.question_pad_id,
        )
        nn.init.zeros_(self.que_disc.weight)

        # Question-centric & Concept-centric problem-solving heads
        self.q_solve_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(self.hidden_size // 2, 1),
        )
        self.c_solve_head = nn.Sequential(
            nn.Linear(self.hidden_size + self.emb_size, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(self.dropout_rate),
            nn.Linear(self.hidden_size // 2, 1),
        )

    def forward_detailed(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute predictions alongside interpretable IRT quantities (theta, beta, alpha)."""
        in_e_q = self.que_emb(in_q)
        in_e_c = self.pool_concept_embeddings(in_q, self.concept_emb)
        in_e_r = self.resp_emb(in_r.long().clamp(0, 1))

        acq_in = self.acq_proj(torch.cat([in_e_q, in_e_c, in_e_r], dim=-1))
        h, _ = self.acq_lstm(acq_in)
        h_drop = self.drop(h)

        tgt_e_q = self.que_emb(tgt_q)
        tgt_e_c = self.pool_concept_embeddings(tgt_q, self.concept_emb)

        # Student latent ability theta_t conditioned on target concept profile
        theta = self.ability_head(torch.cat([h_drop, tgt_e_c], dim=-1)).squeeze(-1)
        s_offset = self.lookup_student_bias(self.student_bias, student_idx, theta.dtype)
        if s_offset is not None:
            theta = theta + s_offset

        # Question difficulty beta & discrimination alpha
        beta = self.que_difficulty(tgt_q).squeeze(-1) + self.difficulty_proj(tgt_e_q).squeeze(-1)
        alpha = F.softplus(self.que_disc(tgt_q).squeeze(-1)) + 0.1

        irt_logit = alpha * (theta - beta)
        q_logit = self.q_solve_head(torch.cat([h_drop, tgt_e_q], dim=-1)).squeeze(-1)
        c_logit = self.c_solve_head(torch.cat([h_drop, tgt_e_c], dim=-1)).squeeze(-1)

        final_logit = irt_logit + self.aux_branch_weight * 0.5 * (q_logit + c_logit)

        return {
            "logits": final_logit,
            "irt_logit": irt_logit,
            "q_logit": q_logit,
            "c_logit": c_logit,
            "ability_theta": theta,
            "difficulty_beta": beta,
            "discrimination_alpha": alpha,
            "prob": torch.sigmoid(final_logit),
        }

    def forward(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Standard forward interface returning (logits, zero_reg_loss)."""
        out = self.forward_detailed(in_q, in_r, tgt_q, student_idx=student_idx)
        logits = out["logits"]
        return logits, logits.new_zeros(())
