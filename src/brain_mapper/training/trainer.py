"""Unified masked training, validation, and per-class customization engine."""

from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from brain_mapper.models.base import BaseKTModel
from brain_mapper.training.metrics import compute_kt_metrics


@dataclass
class TrainingConfig:
    """Hyperparameters governing Knowledge Tracing optimization."""

    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    epochs: int = 20
    patience: int = 4
    grad_clip: float = 1.0
    seed: int = 42
    use_amp: bool = True
    num_workers: int = 0


def set_seed(seed: int) -> None:
    """Fix RNG seeds across Python, NumPy, and PyTorch for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(requested: str | None = None) -> torch.device:
    """Select requested compute device or auto-detect CUDA GPU."""
    if requested:
        return torch.device(requested)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _masked_bce_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    mask: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute mean BCE loss over unpadded target positions."""
    loss_per_step = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
    total_valid = mask.sum().clamp(min=1.0)
    return (loss_per_step * mask).sum() / total_valid, mask.sum()


@torch.no_grad()
def evaluate_model(
    model: BaseKTModel,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, float]:
    """Evaluate a KT model without gradients across masked target interactions."""
    model.eval()
    amp_enabled = device.type == "cuda"
    all_probs: list[np.ndarray] = []
    all_targets: list[np.ndarray] = []
    loss_sum = 0.0
    weight_sum = 0.0

    for batch in loader:
        in_q = batch["in_q"].to(device, non_blocking=True)
        in_r = batch["in_r"].to(device, non_blocking=True)
        tgt_q = batch["tgt_q"].to(device, non_blocking=True)
        tgt_r = batch["tgt_r"].to(device, non_blocking=True)
        mask = batch["eval_mask"].to(device, non_blocking=True)
        student_idx = batch["student_idx"].to(device, non_blocking=True)

        with torch.amp.autocast("cuda", enabled=amp_enabled):
            logits, _ = model(in_q, in_r, tgt_q, student_idx=student_idx)
        bce, count = _masked_bce_loss(logits.float(), tgt_r.float(), mask)
        cnt_val = float(count.item())
        loss_sum += float(bce.item()) * cnt_val
        weight_sum += cnt_val

        active = mask > 0.5
        if bool(active.any()):
            probs = torch.sigmoid(logits.float()[active]).cpu().numpy()
            trues = tgt_r[active].cpu().numpy()
            all_probs.append(probs)
            all_targets.append(trues)

    if not all_targets:
        return {"loss": float("nan"), "auc": float("nan"), "accuracy": float("nan"), "rmse": float("nan"), "count": 0}

    y_true = np.concatenate(all_targets)
    y_prob = np.concatenate(all_probs)
    metrics = compute_kt_metrics(y_true, y_prob)
    metrics["loss"] = loss_sum / max(weight_sum, 1.0)
    return metrics


def _save_checkpoint(
    checkpoint_path: Path,
    state_dict: dict[str, Any],
    val_metrics: dict[str, float],
    cfg: TrainingConfig,
) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": state_dict,
            "val_metrics": val_metrics,
            "config": asdict(cfg),
        },
        checkpoint_path,
    )


def train_kt_model(
    model: BaseKTModel,
    train_loader: DataLoader,
    val_loader: DataLoader,
    cfg: TrainingConfig,
    checkpoint_path: Path | None = None,
    device: torch.device | None = None,
    verbose: bool = True,
    baseline_val_first: bool = False,
) -> dict[str, Any]:
    """Train a Knowledge Tracing model with early stopping on validation AUC."""
    set_seed(cfg.seed)
    compute_device = device or resolve_device()
    model.to(compute_device)

    amp_enabled = bool(cfg.use_amp and compute_device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
    )

    best_score = -float("inf")
    best_val_metrics: dict[str, float] = {}
    best_state = copy.deepcopy(model.state_dict())
    if baseline_val_first:
        best_val_metrics = evaluate_model(model, val_loader, compute_device)
        init_auc = best_val_metrics["auc"]
        best_score = -best_val_metrics["loss"] if math.isnan(init_auc) else init_auc
        if checkpoint_path is not None:
            _save_checkpoint(checkpoint_path, best_state, best_val_metrics, cfg)

    patience_counter = 0
    history: list[dict[str, float]] = []

    for epoch in range(1, cfg.epochs + 1):
        t0 = time.perf_counter()
        model.train()
        train_loss_sum = 0.0
        train_weight_sum = 0.0

        for batch in train_loader:
            in_q = batch["in_q"].to(compute_device, non_blocking=True)
            in_r = batch["in_r"].to(compute_device, non_blocking=True)
            tgt_q = batch["tgt_q"].to(compute_device, non_blocking=True)
            tgt_r = batch["tgt_r"].to(compute_device, non_blocking=True)
            mask = batch["eval_mask"].to(compute_device, non_blocking=True)
            student_idx = batch["student_idx"].to(compute_device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=amp_enabled):
                logits, reg_loss = model(in_q, in_r, tgt_q, student_idx=student_idx)
                bce_loss, count = _masked_bce_loss(logits, tgt_r, mask)
                loss = bce_loss + reg_loss

            scaler.scale(loss).backward()
            if cfg.grad_clip > 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            scaler.step(optimizer)
            scaler.update()

            cnt_val = float(count.item())
            train_loss_sum += float(bce_loss.item()) * cnt_val
            train_weight_sum += cnt_val

        train_loss = train_loss_sum / max(train_weight_sum, 1.0)
        val_metrics = evaluate_model(model, val_loader, compute_device)
        elapsed = time.perf_counter() - t0

        val_auc = val_metrics["auc"]
        monitor_score = -val_metrics["loss"] if math.isnan(val_auc) else val_auc

        epoch_record = {
            "epoch": epoch,
            "train_loss": round(train_loss, 5),
            "val_loss": round(val_metrics["loss"], 5),
            "val_auc": round(val_auc, 5) if not math.isnan(val_auc) else float("nan"),
            "val_accuracy": round(val_metrics["accuracy"], 5),
            "val_rmse": round(val_metrics["rmse"], 5),
            "seconds": round(elapsed, 2),
        }
        history.append(epoch_record)

        if verbose:
            print(
                f"  Epoch {epoch:02d}/{cfg.epochs:02d} | train_loss={train_loss:.4f} | "
                f"val_loss={val_metrics['loss']:.4f} | val_auc={val_auc:.4f} | "
                f"val_acc={val_metrics['accuracy']:.4f} | val_rmse={val_metrics['rmse']:.4f} ({elapsed:.1f}s)"
            )

        if monitor_score > best_score:
            best_score = monitor_score
            best_val_metrics = dict(val_metrics)
            best_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
            if checkpoint_path is not None:
                _save_checkpoint(checkpoint_path, best_state, best_val_metrics, cfg)
        else:
            patience_counter += 1
            if patience_counter >= cfg.patience:
                if verbose:
                    print(f"  Early stopping triggered at epoch {epoch} (best val_auc={best_val_metrics.get('auc', float('nan')):.4f})")
                break

    model.load_state_dict(best_state)
    return {
        "best_val_metrics": best_val_metrics,
        "history": history,
        "epochs_trained": len(history),
    }


def finetune_for_class(
    base_state_dict: dict[str, Any],
    model_factory_fn,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    cfg: TrainingConfig,
    checkpoint_path: Path | None = None,
    device: torch.device | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Customize a cloned base model exclusively on a single class's past student data."""
    compute_device = device or resolve_device()
    class_model: BaseKTModel = model_factory_fn()
    class_model.load_state_dict(copy.deepcopy(base_state_dict))
    class_model.to(compute_device)

    pre_adapt_metrics = evaluate_model(class_model, test_loader, compute_device)
    train_summary = train_kt_model(
        model=class_model,
        train_loader=train_loader,
        val_loader=val_loader,
        cfg=cfg,
        checkpoint_path=checkpoint_path,
        device=compute_device,
        verbose=verbose,
        baseline_val_first=True,
    )
    post_adapt_metrics = evaluate_model(class_model, test_loader, compute_device)

    return {
        "pre_adaptation_test": pre_adapt_metrics,
        "post_adaptation_test": post_adapt_metrics,
        "train_summary": train_summary,
    }
