"""Knowledge Tracing training and evaluation package."""

from brain_mapper.training.metrics import compute_kt_metrics
from brain_mapper.training.trainer import (
    TrainingConfig,
    evaluate_model,
    finetune_for_class,
    resolve_device,
    set_seed,
    train_kt_model,
)

__all__ = [
    "TrainingConfig",
    "compute_kt_metrics",
    "evaluate_model",
    "finetune_for_class",
    "resolve_device",
    "set_seed",
    "train_kt_model",
]
