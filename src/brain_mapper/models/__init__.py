"""Knowledge Tracing model registry and factory."""

from __future__ import annotations

import numpy as np
import torch

from brain_mapper.models.base import BaseKTModel
from brain_mapper.models.cakt import CAKT
from brain_mapper.models.dkt import DKT
from brain_mapper.models.qdkt import qDKT
from brain_mapper.models.qikt import QIKT

MODEL_REGISTRY: dict[str, type[BaseKTModel]] = {
    "dkt": DKT,
    "qdkt": qDKT,
    "qikt": QIKT,
    "cakt": CAKT,
}


def build_baseline_model(
    name: str,
    num_questions: int,
    num_concepts: int,
    question_concepts: np.ndarray | torch.Tensor,
    emb_size: int = 128,
    hidden_size: int = 128,
    dropout: float = 0.2,
    num_students: int | None = None,
    laplacian_lambda: float = 0.05,
    question_cognitive: np.ndarray | torch.Tensor | None = None,
    attention_window: int | None = 200,
    use_concepts: bool = True,
    use_rasch: bool = True,
) -> BaseKTModel:
    """Instantiate a registered KT baseline or Cognitive-Aware model cleanly."""
    key = name.strip().lower()
    if key not in MODEL_REGISTRY:
        available = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(f"Unknown model {name!r}. Choose from: {available}")

    if key == "qdkt":
        return qDKT(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
            laplacian_lambda=laplacian_lambda,
        )
    if key == "qikt":
        return QIKT(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
            num_students=num_students,
        )
    if key == "cakt":
        num_skills = int(question_cognitive.shape[1]) if question_cognitive is not None else 6
        return CAKT(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            question_cognitive=question_cognitive,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
            num_students=num_students,
            num_cognitive_skills=num_skills,
            attention_window=attention_window,
            use_concepts=use_concepts,
            use_rasch=use_rasch,
        )
    return DKT(
        num_questions=num_questions,
        num_concepts=num_concepts,
        question_concepts=question_concepts,
        emb_size=emb_size,
        hidden_size=hidden_size,
        dropout=dropout,
    )


__all__ = ["BaseKTModel", "DKT", "qDKT", "QIKT", "CAKT", "MODEL_REGISTRY", "build_baseline_model"]
