"""Deep Knowledge Tracing (DKT) baseline (Piech et al., NeurIPS 2015)."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

from brain_mapper.models.base import BaseKTModel


class DKT(BaseKTModel):
    """Concept-level Deep Knowledge Tracing using an LSTM backbone with multi-KC pooling."""

    def __init__(
        self,
        num_questions: int,
        num_concepts: int,
        question_concepts: np.ndarray | torch.Tensor,
        emb_size: int = 128,
        hidden_size: int = 128,
        num_layers: int = 1,
        dropout: float = 0.2,
    ) -> None:
        super().__init__(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
        )
        self.inter_pad_id = 2 * self.num_concepts
        self.interaction_emb = nn.Embedding(
            self.inter_pad_id + 1,
            self.emb_size,
            padding_idx=self.inter_pad_id,
        )
        self.lstm = nn.LSTM(
            input_size=self.emb_size,
            hidden_size=self.hidden_size,
            num_layers=num_layers,
            batch_first=True,
        )
        self.drop = nn.Dropout(self.dropout_rate)
        self.out_proj = nn.Linear(self.hidden_size, self.num_concepts + 1)

    def forward(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Predict next-step logits for each target question averaged over its concepts."""
        in_c = self.question_concepts[in_q]  # [B, L, K]
        valid = in_c != self.concept_pad_id
        raw_inter = in_c + in_r.unsqueeze(-1).long() * self.num_concepts
        inter_idx = torch.where(valid, raw_inter, torch.full_like(raw_inter, self.inter_pad_id))

        valid_f = valid.unsqueeze(-1).to(dtype=self.interaction_emb.weight.dtype)
        x_sum = (self.interaction_emb(inter_idx) * valid_f).sum(dim=2)
        x = x_sum / valid_f.sum(dim=2).clamp(min=1.0)

        h, _ = self.lstm(x)
        all_concept_logits = self.out_proj(self.drop(h))  # [B, L, num_concepts + 1]

        tgt_c = self.question_concepts[tgt_q]  # [B, L, K]
        tgt_valid = (tgt_c != self.concept_pad_id).to(dtype=all_concept_logits.dtype)
        gathered = torch.gather(all_concept_logits, dim=-1, index=tgt_c) * tgt_valid
        pred_logits = gathered.sum(dim=-1) / tgt_valid.sum(dim=-1).clamp(min=1.0)

        zero_reg = pred_logits.new_zeros(())
        return pred_logits, zero_reg
