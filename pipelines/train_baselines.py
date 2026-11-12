"""End-to-end training & benchmarking CLI for DKT, qDKT, and QIKT baselines on XES3G5M."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brain_mapper.data.kt_dataset import (
    DEFAULT_CACHE_DIR,
    DEFAULT_DEEPSEEK_ANNOTATIONS,
    DEFAULT_INTERACTIONS_CSV,
    SKILL_NAMES,
    XES3G5MCache,
    build_cognitive_concept_clusters,
    build_or_load_kt_cache,
    build_standard_datasets,
    build_temporal_same_student_datasets,
    sample_simulated_classes,
)
from brain_mapper.models import build_baseline_model
from brain_mapper.training import (
    TrainingConfig,
    evaluate_model,
    finetune_for_class,
    resolve_device,
    set_seed,
    train_kt_model,
)


def _make_loader(dataset, batch_size: int, shuffle: bool, pin_memory: bool) -> DataLoader:
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=pin_memory,
    )


def _run_standard_or_temporal(
    model_name: str,
    cache: XES3G5MCache,
    split_mode: str,
    cfg: TrainingConfig,
    emb_size: int,
    hidden_size: int,
    max_students: int | None,
    output_dir: Path,
    device,
    attention_window: int | None = 200,
    use_concepts: bool = True,
    use_rasch: bool = True,
    cluster_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train and test a single model on standard cross-student or global temporal split."""
    pin = device.type == "cuda"
    if split_mode == "standard":
        train_ds, val_ds, test_ds = build_standard_datasets(
            cache=cache,
            val_fold=0,
            window_len=200,
            max_train_students=max_students,
            seed=cfg.seed,
        )
    else:
        pool = np.arange(cache.num_students)
        if max_students is not None and len(pool) > max_students:
            rng = np.random.default_rng(cfg.seed)
            pool = np.sort(rng.choice(pool, size=max_students, replace=False))
        train_ds, val_ds, test_ds = build_temporal_same_student_datasets(
            cache=cache,
            student_indices=[int(x) for x in pool],
        )

    train_loader = _make_loader(train_ds, cfg.batch_size, shuffle=True, pin_memory=pin)
    val_loader = _make_loader(val_ds, cfg.batch_size, shuffle=False, pin_memory=pin)
    test_loader = _make_loader(test_ds, cfg.batch_size, shuffle=False, pin_memory=pin)

    if model_name.strip().lower() == "cakt" and cache.question_cognitive is None:
        raise ValueError("Model 'cakt' requires cognitive annotations (pass --annotations-path or --annotated-only).")

    model = build_baseline_model(
        name=model_name,
        num_questions=cache.num_questions,
        num_concepts=cache.num_concepts,
        question_concepts=cache.question_concepts,
        emb_size=emb_size,
        hidden_size=hidden_size,
        question_cognitive=cache.question_cognitive,
        attention_window=attention_window,
        use_concepts=use_concepts,
        use_rasch=use_rasch,
    )

    ckpt_path = output_dir / f"{model_name}_{split_mode}_best.pt"
    train_summary = train_kt_model(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        cfg=cfg,
        checkpoint_path=ckpt_path,
        device=device,
        verbose=True,
    )
    test_metrics = evaluate_model(model, test_loader, device)
    return {
        "model": model_name,
        "split_mode": split_mode,
        "data_counts": {
            "annotated_only": cache.annotated_only,
            "annotated_questions": int(len(cache.annotated_qids)) if cache.annotated_qids is not None else 0,
            "active_skills": list(cache.cognitive_skill_names),
            "use_concepts": use_concepts if model_name.strip().lower() == "cakt" else True,
            "use_rasch": use_rasch if model_name.strip().lower() == "cakt" else False,
            "attention_window": attention_window if model_name.strip().lower() == "cakt" else None,
            "concept_clusters": cluster_summary,
            "cache_students": cache.num_students,
            "cache_interactions": cache.num_interactions,
            "train_windows": len(train_ds),
            "val_windows": len(val_ds),
            "test_windows": len(test_ds),
        },
        "best_val": train_summary["best_val_metrics"],
        "test": test_metrics,
        "epochs_trained": train_summary["epochs_trained"],
        "checkpoint": str(ckpt_path),
    }


def _run_per_class_experiment(
    model_name: str,
    cache: XES3G5MCache,
    base_cfg: TrainingConfig,
    finetune_cfg: TrainingConfig,
    emb_size: int,
    hidden_size: int,
    num_classes: int,
    students_per_class: int,
    base_students: int | None,
    output_dir: Path,
    device,
    attention_window: int | None = 200,
    use_concepts: bool = True,
    use_rasch: bool = True,
    cluster_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Benchmark From-Scratch Per-Class vs Base vs Base+Class-Customized weights across K classes."""
    pin = device.type == "cuda"
    classes = sample_simulated_classes(
        cache=cache,
        num_classes=num_classes,
        students_per_class=students_per_class,
        seed=base_cfg.seed,
        split_filter=None,
    )
    class_student_set = {sid for cls in classes for sid in cls}

    # Background students disjoint from the 5 target classes for base pre-training
    bg_pool = np.array([i for i in range(cache.num_students) if i not in class_student_set], dtype=np.int64)
    if base_students is not None and len(bg_pool) > base_students:
        rng = np.random.default_rng(base_cfg.seed)
        bg_pool = np.sort(rng.choice(bg_pool, size=base_students, replace=False))

    print(f"\n[{model_name.upper()}] Pre-training base model on {len(bg_pool)} background students (past interactions)...")
    bg_train_ds, bg_val_ds, _ = build_temporal_same_student_datasets(
        cache=cache,
        student_indices=[int(x) for x in bg_pool],
        train_ratio=0.80,
        val_ratio=0.10,
    )
    bg_train_loader = _make_loader(bg_train_ds, base_cfg.batch_size, shuffle=True, pin_memory=pin)
    bg_val_loader = _make_loader(bg_val_ds, base_cfg.batch_size, shuffle=False, pin_memory=pin)

    if model_name.strip().lower() == "cakt" and cache.question_cognitive is None:
        raise ValueError("Model 'cakt' requires cognitive annotations (pass --annotations-path or --annotated-only).")

    def make_model():
        return build_baseline_model(
            name=model_name,
            num_questions=cache.num_questions,
            num_concepts=cache.num_concepts,
            question_concepts=cache.question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            question_cognitive=cache.question_cognitive,
            attention_window=attention_window,
            use_concepts=use_concepts,
            use_rasch=use_rasch,
        )

    base_model = make_model()
    base_ckpt = output_dir / f"{model_name}_base_pretrained.pt"
    train_kt_model(
        model=base_model,
        train_loader=bg_train_loader,
        val_loader=bg_val_loader,
        cfg=base_cfg,
        checkpoint_path=base_ckpt,
        device=device,
        verbose=True,
    )
    base_state = {k: v.cpu() for k, v in base_model.state_dict().items()}

    class_reports: list[dict[str, Any]] = []
    for cls_idx, student_list in enumerate(classes, start=1):
        c_train_ds, c_val_ds, c_test_ds = build_temporal_same_student_datasets(
            cache=cache,
            student_indices=student_list,
            train_ratio=0.70,
            val_ratio=0.10,
        )
        c_train_loader = _make_loader(c_train_ds, finetune_cfg.batch_size, shuffle=True, pin_memory=pin)
        c_val_loader = _make_loader(c_val_ds, finetune_cfg.batch_size, shuffle=False, pin_memory=pin)
        c_test_loader = _make_loader(c_test_ds, finetune_cfg.batch_size, shuffle=False, pin_memory=pin)

        # A. From-scratch per-class (only trained on this class's past sessions)
        scratch_model = make_model()
        train_kt_model(
            model=scratch_model,
            train_loader=c_train_loader,
            val_loader=c_val_loader,
            cfg=finetune_cfg,
            device=device,
            verbose=False,
        )
        scratch_test = evaluate_model(scratch_model, c_test_loader, device)

        # B & C. Uncustomized Base vs Class-Customized Fine-Tuned
        class_ckpt = output_dir / f"{model_name}_class_{cls_idx}.pt"
        ft_res = finetune_for_class(
            base_state_dict=base_state,
            model_factory_fn=make_model,
            train_loader=c_train_loader,
            val_loader=c_val_loader,
            test_loader=c_test_loader,
            cfg=finetune_cfg,
            checkpoint_path=class_ckpt,
            device=device,
            verbose=False,
        )

        class_reports.append(
            {
                "class_id": cls_idx,
                "students": len(student_list),
                "from_scratch_test": scratch_test,
                "base_uncustomized_test": ft_res["pre_adaptation_test"],
                "class_customized_test": ft_res["post_adaptation_test"],
                "checkpoint": str(class_ckpt),
            }
        )
        print(
            f"  Class {cls_idx} ({len(student_list)} students) | "
            f"Scratch AUC={scratch_test['auc']:.4f} | "
            f"Base AUC={ft_res['pre_adaptation_test']['auc']:.4f} | "
            f"Customized AUC={ft_res['post_adaptation_test']['auc']:.4f}"
        )

    def _avg_metric(key: str, metric: str) -> float:
        vals = [r[key][metric] for r in class_reports if not np.isnan(r[key][metric])]
        return float(np.mean(vals)) if vals else float("nan")

    summary = {
        "from_scratch_mean_auc": round(_avg_metric("from_scratch_test", "auc"), 4),
        "from_scratch_mean_acc": round(_avg_metric("from_scratch_test", "accuracy"), 4),
        "from_scratch_mean_rmse": round(_avg_metric("from_scratch_test", "rmse"), 4),
        "base_mean_auc": round(_avg_metric("base_uncustomized_test", "auc"), 4),
        "base_mean_acc": round(_avg_metric("base_uncustomized_test", "accuracy"), 4),
        "base_mean_rmse": round(_avg_metric("base_uncustomized_test", "rmse"), 4),
        "customized_mean_auc": round(_avg_metric("class_customized_test", "auc"), 4),
        "customized_mean_acc": round(_avg_metric("class_customized_test", "accuracy"), 4),
        "customized_mean_rmse": round(_avg_metric("class_customized_test", "rmse"), 4),
    }

    return {
        "model": model_name,
        "split_mode": "per_class",
        "data_counts": {
            "annotated_only": cache.annotated_only,
            "annotated_questions": int(len(cache.annotated_qids)) if cache.annotated_qids is not None else 0,
            "active_skills": list(cache.cognitive_skill_names),
            "use_concepts": use_concepts if model_name.strip().lower() == "cakt" else True,
            "use_rasch": use_rasch if model_name.strip().lower() == "cakt" else False,
            "attention_window": attention_window if model_name.strip().lower() == "cakt" else None,
            "concept_clusters": cluster_summary,
            "cache_students": cache.num_students,
            "cache_interactions": cache.num_interactions,
            "base_students": int(len(bg_pool)),
            "base_train_windows": len(bg_train_ds),
            "base_val_windows": len(bg_val_ds),
        },
        "num_classes": num_classes,
        "students_per_class": students_per_class,
        "summary": summary,
        "classes": class_reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train and benchmark DKT, qDKT, QIKT, and CAKT models.")
    parser.add_argument("--models", nargs="+", default=["dkt", "qdkt", "qikt"])
    parser.add_argument("--split-mode", choices=["per_class", "temporal", "standard"], default="per_class")
    parser.add_argument("--interactions-csv", type=Path, default=DEFAULT_INTERACTIONS_CSV)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--annotations-path", type=Path, default=DEFAULT_DEEPSEEK_ANNOTATIONS)
    parser.add_argument(
        "--annotated-only",
        action="store_true",
        help="Restrict training, validation, and testing strictly to DeepSeek-annotated questions.",
    )
    parser.add_argument(
        "--exclude-skills",
        nargs="+",
        default=[],
        choices=list(SKILL_NAMES),
        help="Optional cognitive skills to drop for ablation experiments (e.g. --exclude-skills metacognition).",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/baselines"))
    parser.add_argument("--num-classes", type=int, default=5)
    parser.add_argument("--students-per-class", type=int, default=40)
    parser.add_argument("--base-students", type=int, default=2000)
    parser.add_argument("--max-students", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--finetune-epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--finetune-batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--finetune-lr", type=float, default=5e-4)
    parser.add_argument("--emb-size", type=int, default=128)
    parser.add_argument("--hidden-size", type=int, default=128)
    parser.add_argument(
        "--attention-window",
        type=int,
        default=200,
        help="Max sliding causal lookback window for CAKT attention (0 disables bounding).",
    )
    parser.add_argument(
        "--no-concepts",
        action="store_true",
        help="Train CAKT without Knowledge Concept IDs (cognitive skills + item scalars only).",
    )
    parser.add_argument(
        "--no-rasch",
        action="store_true",
        help="Disable Rasch decomposition in CAKT and use full question embeddings instead.",
    )
    parser.add_argument(
        "--concept-clusters",
        type=int,
        default=0,
        help="If > 0, categorize fine-grained concepts into K cognitive clusters before training.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default=None)
    args = parser.parse_args(argv)

    set_seed(args.seed)
    device = resolve_device(args.device)
    print(f"Using compute device: {device}")

    excluded = set(args.exclude_skills)
    active_skills = tuple(s for s in SKILL_NAMES if s not in excluded)
    if not active_skills:
        raise ValueError("Cannot exclude every cognitive skill.")

    needs_annotations = args.annotated_only or args.concept_clusters > 0 or any(
        m.strip().lower() == "cakt" for m in args.models
    )
    cache = build_or_load_kt_cache(
        interactions_csv=args.interactions_csv,
        cache_dir=args.cache_dir,
        annotations_path=args.annotations_path if needs_annotations else None,
        annotated_only=args.annotated_only,
        active_skills=active_skills,
    )
    cluster_summary: dict[str, Any] | None = None
    if args.concept_clusters > 0:
        cache, cluster_summary = build_cognitive_concept_clusters(
            cache,
            num_clusters=args.concept_clusters,
            seed=args.seed,
        )
        print(
            f"Categorized concepts by cognitive profile: "
            f"{cluster_summary['original_num_concepts']} concepts -> {cluster_summary['num_clusters']} clusters "
            f"(silhouette={cluster_summary['silhouette_score']})"
        )
    ann_info = (
        f", annotated_only={cache.annotated_only} ({len(cache.annotated_qids)} questions, "
        f"{cache.num_interactions} interactions, skills={list(cache.cognitive_skill_names)})"
        if cache.annotated_qids is not None
        else f", {cache.num_interactions} interactions"
    )
    print(
        f"Loaded XES3G5M cache: {cache.num_students} students, "
        f"{cache.num_questions} questions, {cache.num_concepts} concepts{ann_info}"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []

    base_cfg = TrainingConfig(
        batch_size=args.batch_size,
        learning_rate=args.lr,
        epochs=args.epochs,
        seed=args.seed,
    )
    ft_batch = args.finetune_batch_size if args.finetune_batch_size is not None else min(32, args.batch_size)
    ft_cfg = TrainingConfig(
        batch_size=ft_batch,
        learning_rate=args.finetune_lr,
        epochs=args.finetune_epochs,
        patience=3,
        seed=args.seed,
    )

    attn_win = args.attention_window if args.attention_window > 0 else None
    use_concepts = not args.no_concepts
    use_rasch = not args.no_rasch
    for model_name in args.models:
        label = "Proposed Model" if model_name.strip().lower() == "cakt" else "Baseline"
        print(f"\n{'=' * 65}\nTraining {label}: {model_name.upper()} ({args.split_mode} mode)\n{'=' * 65}")
        if args.split_mode == "per_class":
            res = _run_per_class_experiment(
                model_name=model_name,
                cache=cache,
                base_cfg=base_cfg,
                finetune_cfg=ft_cfg,
                emb_size=args.emb_size,
                hidden_size=args.hidden_size,
                num_classes=args.num_classes,
                students_per_class=args.students_per_class,
                base_students=args.base_students,
                output_dir=args.output_dir,
                device=device,
                attention_window=attn_win,
                use_concepts=use_concepts,
                use_rasch=use_rasch,
                cluster_summary=cluster_summary,
            )
        else:
            res = _run_standard_or_temporal(
                model_name=model_name,
                cache=cache,
                split_mode=args.split_mode,
                cfg=base_cfg,
                emb_size=args.emb_size,
                hidden_size=args.hidden_size,
                max_students=args.max_students,
                output_dir=args.output_dir,
                device=device,
                attention_window=attn_win,
                use_concepts=use_concepts,
                use_rasch=use_rasch,
                cluster_summary=cluster_summary,
            )
        all_results.append(res)

    report_path = args.output_dir / f"baseline_results_{args.split_mode}.json"
    report_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"\nSaved complete benchmark results to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
