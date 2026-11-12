"""Shared base abstractions and multi-concept pooling utilities for KT models."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


class BaseKTModel(nn.Module):
    """Base PyTorch Knowledge Tracing module supporting multi-concept questions."""

    def __init__(
        self,
        num_questions: int,
        num_concepts: int,
        question_concepts: np.ndarray | torch.Tensor,
        emb_size: int = 128,
        hidden_size: int = 128,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.num_questions = int(num_questions)
        self.num_concepts = int(num_concepts)
        self.question_pad_id = int(num_questions)
        self.concept_pad_id = int(num_concepts)
        self.emb_size = int(emb_size)
        self.hidden_size = int(hidden_size)
        self.dropout_rate = float(dropout)

        qc_tensor = torch.as_tensor(question_concepts, dtype=torch.long)
        if qc_tensor.shape[0] != self.num_questions + 1:
            raise ValueError(
                f"Expected question_concepts rows={self.num_questions + 1}, got {qc_tensor.shape[0]}"
            )
        self.register_buffer("question_concepts", qc_tensor)

    def pool_concept_embeddings(
        self,
        q_ids: torch.Tensor,
        concept_emb: nn.Embedding,
    ) -> torch.Tensor:
        """Mean-pool embeddings for the 1..K concepts linked to each question ID."""
        c_ids = self.question_concepts[q_ids]  # [B, L, K]
        valid = (c_ids != self.concept_pad_id).unsqueeze(-1).to(dtype=concept_emb.weight.dtype)
        c_vecs = concept_emb(c_ids) * valid  # [B, L, K, D]
        counts = valid.sum(dim=2).clamp(min=1.0)  # [B, L, 1]
        return c_vecs.sum(dim=2) / counts

    @staticmethod
    def encode_binary_interactions(
        item_ids: torch.Tensor,
        responses: torch.Tensor,
        vocab_size: int,
        pad_id: int,
    ) -> torch.Tensor:
        """Map (item_id, is_correct) to [0 .. 2*vocab_size-1], reserving 2*vocab_size for padding."""
        pad_mask = item_ids == pad_id
        encoded = item_ids + responses.long() * vocab_size
        return torch.where(pad_mask, torch.full_like(encoded, 2 * vocab_size), encoded)

    @staticmethod
    def lookup_student_bias(
        student_bias: nn.Embedding | None,
        student_idx: torch.Tensor | None,
        dtype: torch.dtype,
    ) -> torch.Tensor | None:
        """Look up per-student baseline ability offset while masking out-of-range indices."""
        if student_bias is None or student_idx is None:
            return None
        valid_s = (student_idx >= 0) & (student_idx < student_bias.num_embeddings)
        safe_s = torch.where(valid_s, student_idx, torch.zeros_like(student_idx))
        return student_bias(safe_s).to(dtype) * valid_s.unsqueeze(-1).to(dtype)

    def prepare_cognitive_buffer(
        self,
        question_cognitive: np.ndarray | torch.Tensor | None,
        num_skills: int = 6,
    ) -> torch.Tensor:
        """Validate or zero-initialize static [num_questions + 1, num_skills] cognitive vectors."""
        if question_cognitive is None:
            return torch.zeros((self.num_questions + 1, num_skills), dtype=torch.float32)
        cog_tensor = torch.as_tensor(question_cognitive, dtype=torch.float32)
        expected_shape = (self.num_questions + 1, num_skills)
        if tuple(cog_tensor.shape) != expected_shape:
            raise ValueError(
                f"Expected question_cognitive shape {expected_shape}, got {tuple(cog_tensor.shape)}"
            )
        return cog_tensor
