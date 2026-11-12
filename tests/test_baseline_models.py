"""Rigorous unit and causality tests for DKT, qDKT, QIKT, and temporal splits."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader

from brain_mapper.data.kt_dataset import (
    SKILL_NAMES,
    KTSequenceDataset,
    build_cognitive_concept_clusters,
    build_or_load_kt_cache,
    build_temporal_same_student_datasets,
    sample_simulated_classes,
)
from brain_mapper.models import build_baseline_model
from brain_mapper.training import (
    TrainingConfig,
    compute_kt_metrics,
    evaluate_model,
    finetune_for_class,
    train_kt_model,
)


def _synthetic_question_concepts(num_q: int = 12, num_c: int = 5) -> np.ndarray:
    qc = np.full((num_q + 1, 6), num_c, dtype=np.int32)
    for q in range(num_q):
        qc[q, 0] = q % num_c
        if q % 2 == 0:
            qc[q, 1] = (q + 1) % num_c
    return qc


def _synthetic_question_cognitive(num_q: int = 12) -> np.ndarray:
    rng = np.random.default_rng(7)
    cog = rng.integers(0, 4, size=(num_q + 1, 6)).astype(np.float32) / 3.0
    cog[num_q] = 0.0
    return cog


@pytest.mark.parametrize("model_name", ["dkt", "qdkt", "qikt", "cakt"])
def test_strict_causality_no_future_leakage(model_name: str) -> None:
    torch.manual_seed(42)
    num_q, num_c = 12, 5
    qc = _synthetic_question_concepts(num_q, num_c)
    qcog = _synthetic_question_cognitive(num_q) if model_name == "cakt" else None
    model = build_baseline_model(
        name=model_name,
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        question_cognitive=qcog,
    )
    model.eval()

    in_q = torch.tensor([[0, 1, 2, 3, 4, 5]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long)
    in_r_a = torch.tensor([[1, 0, 1, 1, 0, 1]], dtype=torch.long)
    in_r_b = torch.tensor([[1, 0, 1, 0, 1, 0]], dtype=torch.long)  # Flipped from step 3 onward!

    with torch.no_grad():
        logits_a, _ = model(in_q, in_r_a, tgt_q)
        logits_b, _ = model(in_q, in_r_b, tgt_q)

    # Predictions at steps 0, 1, 2 depend ONLY on inputs 0..2, so flipping steps 3..5 must not alter them
    assert torch.allclose(logits_a[:, :3], logits_b[:, :3], atol=1e-6)
    # Predictions after the divergence point should generally differ
    assert not torch.allclose(logits_a[:, 3:], logits_b[:, 3:], atol=1e-6)


def test_qdkt_laplacian_regularization_is_positive() -> None:
    num_q, num_c = 10, 3
    qc = _synthetic_question_concepts(num_q, num_c)
    model = build_baseline_model(
        name="qdkt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        emb_size=16,
        hidden_size=16,
        laplacian_lambda=0.1,
    )
    model.train()
    in_q = torch.tensor([[0, 1, 2]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3]], dtype=torch.long)
    logits, reg_loss = model(in_q, in_r, tgt_q)
    assert logits.shape == (1, 3)
    assert float(reg_loss.item()) > 0.0


def test_qikt_interpretable_parameters_and_student_bias() -> None:
    num_q, num_c = 10, 4
    qc = _synthetic_question_concepts(num_q, num_c)
    model = build_baseline_model(
        name="qikt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        emb_size=16,
        hidden_size=16,
        num_students=5,
    )
    model.eval()
    in_q = torch.tensor([[0, 1, 2, 10]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3, 10]], dtype=torch.long)
    student_idx = torch.tensor([2], dtype=torch.long)

    details = model.forward_detailed(in_q, in_r, tgt_q, student_idx=student_idx)
    assert details["ability_theta"].shape == (1, 4)
    assert details["difficulty_beta"].shape == (1, 4)
    assert (details["discrimination_alpha"] > 0).all()
    assert ((details["prob"] > 0) & (details["prob"] < 1)).all()


def test_temporal_same_student_split_and_cache(tmp_path: Path) -> None:
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "fold",
                "student_id",
                "student_interaction_index",
                "question_id",
                "concept_ids",
                "is_correct",
            ],
        )
        writer.writeheader()
        for s_num in range(6):
            for idx in range(20):
                q = idx % 8
                c = f"{q % 4}_{(q + 1) % 4}" if q % 2 == 0 else str(q % 4)
                writer.writerow(
                    {
                        "split": "train_valid",
                        "fold": s_num % 2,
                        "student_id": f"stu_{s_num}",
                        "student_interaction_index": idx,
                        "question_id": q,
                        "concept_ids": c,
                        "is_correct": (idx + s_num) % 2,
                    }
                )

    cache = build_or_load_kt_cache(interactions_csv=csv_path, cache_dir=tmp_path / "cache")
    assert cache.num_students == 6
    assert cache.num_questions == 8
    assert cache.num_concepts == 4

    classes = sample_simulated_classes(cache, num_classes=2, students_per_class=3, seed=7, split_filter=None)
    assert len(classes) == 2 and len(classes[0]) == 3

    tr_ds, val_ds, te_ds = build_temporal_same_student_datasets(
        cache=cache,
        student_indices=classes[0],
        train_ratio=0.7,
        val_ratio=0.1,
        train_window_len=30,
        eval_max_seq_len=30,
    )
    assert len(tr_ds) == 3
    assert len(val_ds) == 3
    assert len(te_ds) == 3

    # Sequence len = 20 -> train_end = 14, val_end = 16 -> train uses indices 0..13 (13 pred pairs),
    # val mask marks indices 14..15 (2 targets), test mask marks indices 16..19 (4 targets)
    assert int(tr_ds[0]["eval_mask"].sum().item()) == 13
    assert int(val_ds[0]["eval_mask"].sum().item()) == 2
    assert int(te_ds[0]["eval_mask"].sum().item()) == 4


def test_training_and_per_class_finetuning_pipeline(tmp_path: Path) -> None:
    torch.manual_seed(0)
    num_q, num_c = 10, 4
    qc = _synthetic_question_concepts(num_q, num_c)

    samples = []
    rng = np.random.default_rng(12)
    for s in range(12):
        q_seq = rng.integers(0, num_q, size=16, dtype=np.int32)
        # Predictable pattern: even questions easy (1), odd questions hard (0)
        r_seq = (q_seq % 2 == 0).astype(np.uint8)
        role = np.ones(16, dtype=np.uint8)
        samples.append((s, q_seq, r_seq, role))

    ds = KTSequenceDataset(samples, max_seq_len=16, question_pad_id=num_q)
    loader = DataLoader(ds, batch_size=4, shuffle=False)

    def factory():
        return build_baseline_model(
            name="qikt",
            num_questions=num_q,
            num_concepts=num_c,
            question_concepts=qc,
            emb_size=16,
            hidden_size=16,
            dropout=0.0,
        )

    model = factory()
    cfg = TrainingConfig(batch_size=4, learning_rate=5e-3, epochs=6, patience=6, use_amp=False, seed=42)
    ckpt = tmp_path / "qikt_base.pt"
    summary = train_kt_model(model, loader, loader, cfg=cfg, checkpoint_path=ckpt, device=torch.device("cpu"), verbose=False)
    assert ckpt.exists()
    assert summary["best_val_metrics"]["auc"] > 0.85

    ft_res = finetune_for_class(
        base_state_dict=model.state_dict(),
        model_factory_fn=factory,
        train_loader=loader,
        val_loader=loader,
        test_loader=loader,
        cfg=TrainingConfig(batch_size=4, learning_rate=1e-3, epochs=2, use_amp=False, seed=42),
        checkpoint_path=tmp_path / "qikt_class_1.pt",
        device=torch.device("cpu"),
        verbose=False,
    )
    assert (tmp_path / "qikt_class_1.pt").exists()
    assert ft_res["post_adaptation_test"]["auc"] > 0.85


def test_metrics_edge_cases() -> None:
    res = compute_kt_metrics(np.array([1, 0, 1, 0]), np.array([0.9, 0.1, 0.8, 0.2]))
    assert res["auc"] == 1.0
    assert res["accuracy"] == 1.0
    assert res["rmse"] < 0.2
    assert res["count"] == 4


def test_cakt_cognitive_mastery_and_feature_sensitivity() -> None:
    torch.manual_seed(11)
    num_q, num_c = 10, 4
    qc = _synthetic_question_concepts(num_q, num_c)
    cog_a = np.zeros((num_q + 1, 6), dtype=np.float32)
    cog_b = np.ones((num_q + 1, 6), dtype=np.float32)
    cog_b[num_q] = 0.0

    model_a = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        question_cognitive=cog_a,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        num_students=4,
    )
    model_b = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        question_cognitive=cog_b,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        num_students=4,
    )
    # Copy weights while keeping each model's own question_cognitive buffer
    state = model_a.state_dict()
    state["question_cognitive"] = model_b.state_dict()["question_cognitive"]
    model_b.load_state_dict(state)
    model_a.eval()
    model_b.eval()

    in_q = torch.tensor([[0, 1, 2, 10]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3, 10]], dtype=torch.long)
    s_idx = torch.tensor([1], dtype=torch.long)

    with torch.no_grad():
        det_a = model_a.forward_detailed(in_q, in_r, tgt_q, student_idx=s_idx)
        det_b = model_b.forward_detailed(in_q, in_r, tgt_q, student_idx=s_idx)

    assert det_a["cognitive_mastery"].shape == (1, 4, 6)
    assert ((det_a["cognitive_mastery"] > 0) & (det_a["cognitive_mastery"] < 1)).all()
    assert (det_a["discrimination_alpha"] > 0).all()
    assert not torch.allclose(det_a["logits"], det_b["logits"], atol=1e-6)


def test_annotated_only_filter_drops_unannotated_cleanly(tmp_path: Path) -> None:
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "fold",
                "student_id",
                "student_interaction_index",
                "question_id",
                "concept_ids",
                "is_correct",
            ],
        )
        writer.writeheader()
        # stu_keep has annotated questions (0, 1) and unannotated question (2)
        for idx, qid in enumerate([0, 2, 1, 0, 2]):
            writer.writerow(
                {
                    "split": "train_valid",
                    "fold": 0,
                    "student_id": "stu_keep",
                    "student_interaction_index": idx,
                    "question_id": qid,
                    "concept_ids": str(qid % 3),
                    "is_correct": idx % 2,
                }
            )
        # stu_drop has only unannotated question 2
        writer.writerow(
            {
                "split": "train_valid",
                "fold": 0,
                "student_id": "stu_drop",
                "student_interaction_index": 0,
                "question_id": 2,
                "concept_ids": "2",
                "is_correct": 1,
            }
        )

    ann_path = tmp_path / "deepseek.jsonl"
    with ann_path.open("w", encoding="utf-8") as f:
        # Duplicate qid 0: latest record (scores all 3 -> normalized 1.0) should win
        rec0_old = {"question_id": 0, **{s: 0 for s in SKILL_NAMES}}
        rec0_new = {"question_id": 0, **{s: 3 for s in SKILL_NAMES}}
        rec1 = {"question_id": 1, **{s: 1 for s in SKILL_NAMES}}
        f.write(json.dumps(rec0_old) + "\n")
        f.write(json.dumps(rec0_new) + "\n")
        f.write(json.dumps(rec1) + "\n")

    cache = build_or_load_kt_cache(
        interactions_csv=csv_path,
        cache_dir=tmp_path / "cache",
        annotations_path=ann_path,
        annotated_only=True,
    )
    assert cache.annotated_only is True
    assert list(cache.student_ids) == ["stu_keep"]
    assert cache.num_interactions == 3
    q_seq, _ = cache.get_student_slice(0)
    assert list(q_seq) == [0, 1, 0]
    assert np.allclose(cache.question_cognitive[0], 1.0)
    assert np.allclose(cache.question_cognitive[1], 1.0 / 3.0)
    assert np.allclose(cache.question_cognitive[cache.question_pad_id], 0.0)


def test_cakt_training_learns_cognitive_rule(tmp_path: Path) -> None:
    torch.manual_seed(42)
    num_q, num_c = 10, 4
    qc = _synthetic_question_concepts(num_q, num_c)
    # Give every question identical concept=0 so ONLY cognitive annotations distinguish hardness!
    qc_same = np.full((num_q + 1, 6), num_c, dtype=np.int32)
    qc_same[:num_q, 0] = 0
    cog = np.zeros((num_q + 1, 6), dtype=np.float32)
    for q in range(num_q):
        cog[q] = 1.0 if q % 2 == 1 else 0.0  # odd questions high cognitive load, even low load

    samples = []
    rng = np.random.default_rng(19)
    for s in range(16):
        q_seq = rng.integers(0, num_q, size=18, dtype=np.int32)
        r_seq = (q_seq % 2 == 0).astype(np.uint8)
        role = np.ones(18, dtype=np.uint8)
        samples.append((s, q_seq, r_seq, role))

    ds = KTSequenceDataset(samples, max_seq_len=18, question_pad_id=num_q)
    loader = DataLoader(ds, batch_size=4, shuffle=False)

    model = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc_same,
        question_cognitive=cog,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
    )
    cfg = TrainingConfig(batch_size=4, learning_rate=5e-3, epochs=6, patience=6, use_amp=False, seed=42)
    summary = train_kt_model(model, loader, loader, cfg=cfg, device=torch.device("cpu"), verbose=False)
    assert summary["best_val_metrics"]["auc"] > 0.90


def test_cakt_without_metacognition_skill_ablation(tmp_path: Path) -> None:
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "fold",
                "student_id",
                "student_interaction_index",
                "question_id",
                "concept_ids",
                "is_correct",
            ],
        )
        writer.writeheader()
        for idx in range(6):
            writer.writerow(
                {
                    "split": "train_valid",
                    "fold": 0,
                    "student_id": "stu_0",
                    "student_interaction_index": idx,
                    "question_id": idx % 3,
                    "concept_ids": str(idx % 2),
                    "is_correct": idx % 2,
                }
            )

    ann_path = tmp_path / "deepseek.jsonl"
    with ann_path.open("w", encoding="utf-8") as f:
        for qid in range(3):
            rec = {
                "question_id": qid,
                "attention": 1,
                "working_memory": 2,
                "logical_reasoning": 3,
                "language_processing": 1,
                "critical_thinking": 2,
                "metacognition": 0,
            }
            f.write(json.dumps(rec) + "\n")

    active_5 = tuple(s for s in SKILL_NAMES if s != "metacognition")
    cache = build_or_load_kt_cache(
        interactions_csv=csv_path,
        cache_dir=tmp_path / "cache",
        annotations_path=ann_path,
        annotated_only=True,
        active_skills=active_5,
    )
    assert cache.cognitive_skill_names == active_5
    assert cache.question_cognitive.shape == (4, 5)

    model = build_baseline_model(
        name="cakt",
        num_questions=cache.num_questions,
        num_concepts=cache.num_concepts,
        question_concepts=cache.question_concepts,
        question_cognitive=cache.question_cognitive,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
    )
    assert model.num_cognitive_skills == 5
    in_q = torch.tensor([[0, 1, 2]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 0]], dtype=torch.long)
    det = model.forward_detailed(in_q, in_r, tgt_q)
    assert det["cognitive_mastery"].shape == (1, 3, 5)
    assert det["cognitive_demand"].shape == (1, 3, 5)
    loss = det["logits"].sum()
    loss.backward()


def test_cakt_sliding_attention_window_mask() -> None:
    num_q, num_c = 10, 4
    qc = _synthetic_question_concepts(num_q, num_c)
    model = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        attention_window=3,
    )
    in_q = torch.tensor([[0, 1, 2, 3, 4, num_q]], dtype=torch.long)
    pos = torch.arange(6)
    dist_mat = pos.unsqueeze(1) - pos.unsqueeze(0)
    mask = model._build_attention_mask(seq_len=6, in_q=in_q, dist_mat=dist_mat)[0, 0]

    # Row 4 may attend only to steps 2, 3, 4 (window=3); step 0, 1 and future step 5 must be masked
    assert mask[4].tolist() == [False, False, True, True, True, False]
    # Padded key at column 5 is excluded for earlier rows, while diag stays True for row 5 itself
    assert bool(mask[5, 5]) is True
    assert mask[5, :3].tolist() == [False, False, False]


def test_cakt_rasch_item_decomposition() -> None:
    num_q, num_c = 500, 20
    qc = _synthetic_question_concepts(num_q, num_c)
    qcog = _synthetic_question_cognitive(num_q)
    cakt = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        question_cognitive=qcog,
        emb_size=64,
        hidden_size=64,
        dropout=0.0,
    )
    assert float(cakt.que_rasch_scalar.weight[num_q].item()) == 0.0

    in_q = torch.tensor([[0, 1, 2]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3]], dtype=torch.long)

    cakt.train()
    logits_tr, reg_tr = cakt(in_q, in_r, tgt_q)
    assert logits_tr.shape == (1, 3)
    assert float(reg_tr.item()) > 0.0

    cakt.eval()
    _, reg_ev = cakt(in_q, in_r, tgt_q)
    assert float(reg_ev.item()) == 0.0


def test_cakt_without_concepts_uses_only_cognitive_and_item_signals() -> None:
    torch.manual_seed(5)
    num_q, num_c = 12, 5
    qc_a = _synthetic_question_concepts(num_q, num_c)
    qc_b = np.full((num_q + 1, 6), num_c, dtype=np.int32)
    qcog = _synthetic_question_cognitive(num_q)

    model_a = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc_a,
        question_cognitive=qcog,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        use_concepts=False,
    )
    model_b = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc_b,
        question_cognitive=qcog,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        use_concepts=False,
    )
    assert model_a.concept_emb is None
    assert model_a.concept_diff_emb is None

    state = model_a.state_dict()
    state["question_concepts"] = model_b.state_dict()["question_concepts"]
    model_b.load_state_dict(state)
    model_a.eval()
    model_b.eval()

    in_q = torch.tensor([[0, 1, 2, 3, 4]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1, 0, 1]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)

    with torch.no_grad():
        logits_a, _ = model_a(in_q, in_r, tgt_q)
        logits_b, _ = model_b(in_q, in_r, tgt_q)
    # Changing Knowledge Concepts has zero effect when use_concepts=False
    assert torch.allclose(logits_a, logits_b, atol=1e-6)

    model_a.train()
    out, reg = model_a(in_q, in_r, tgt_q)
    (out.sum() + reg).backward()


def test_cognitive_concept_clustering_groups_similar_concepts(tmp_path: Path) -> None:
    csv_path = tmp_path / "interactions.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "split",
                "fold",
                "student_id",
                "student_interaction_index",
                "question_id",
                "concept_ids",
                "is_correct",
            ],
        )
        writer.writeheader()
        # Q0 uses concept 0 & 1 (both low cognitive load), Q1 uses concept 2 (high load),
        # Q2 uses concept 3 (high load) -> 4 original concepts should cluster cleanly into 2 groups.
        for idx, (qid, c_str) in enumerate([(0, "0_1"), (1, "2"), (2, "3"), (0, "0_1")]):
            writer.writerow(
                {
                    "split": "train_valid",
                    "fold": 0,
                    "student_id": "stu_0",
                    "student_interaction_index": idx,
                    "question_id": qid,
                    "concept_ids": c_str,
                    "is_correct": idx % 2,
                }
            )

    ann_path = tmp_path / "deepseek.jsonl"
    with ann_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"question_id": 0, **{s: 0 for s in SKILL_NAMES}}) + "\n")
        f.write(json.dumps({"question_id": 1, **{s: 3 for s in SKILL_NAMES}}) + "\n")
        f.write(json.dumps({"question_id": 2, **{s: 3 for s in SKILL_NAMES}}) + "\n")

    cache = build_or_load_kt_cache(
        interactions_csv=csv_path,
        cache_dir=tmp_path / "cache",
        annotations_path=ann_path,
        annotated_only=True,
    )
    clustered, summary = build_cognitive_concept_clusters(cache, num_clusters=2, seed=42)
    assert summary["original_num_concepts"] == 4
    assert summary["num_clusters"] == 2
    assert clustered.num_concepts == 2
    assert clustered.concept_pad_id == 2
    # Q0 originally had concepts (0, 1) which share the same cognitive cluster -> deduplicated to 1 entry + pad
    assert int(clustered.question_concepts[0, 1]) == 2
    # Q1 and Q2 have identical high cognitive load, so they map to the exact same cluster and differ from Q0
    assert int(clustered.question_concepts[1, 0]) == int(clustered.question_concepts[2, 0])
    assert int(clustered.question_concepts[0, 0]) != int(clustered.question_concepts[1, 0])

    model = build_baseline_model(
        name="cakt",
        num_questions=clustered.num_questions,
        num_concepts=clustered.num_concepts,
        question_concepts=clustered.question_concepts,
        question_cognitive=clustered.question_cognitive,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
    )
    in_q = torch.tensor([[0, 1]], dtype=torch.long)
    in_r = torch.tensor([[1, 0]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2]], dtype=torch.long)
    out, reg = model(in_q, in_r, tgt_q)
    (out.sum() + reg).backward()


def test_cakt_no_rasch_mode_uses_full_question_emb_and_zero_reg() -> None:
    num_q, num_c = 12, 5
    qc = _synthetic_question_concepts(num_q, num_c)
    qcog = _synthetic_question_cognitive(num_q)
    model = build_baseline_model(
        name="cakt",
        num_questions=num_q,
        num_concepts=num_c,
        question_concepts=qc,
        question_cognitive=qcog,
        emb_size=16,
        hidden_size=16,
        dropout=0.0,
        attention_window=None,
        use_rasch=False,
    )
    assert model.que_emb is not None
    assert model.que_rasch_scalar is None
    assert model.attention_window is None

    in_q = torch.tensor([[0, 1, 2, 3]], dtype=torch.long)
    in_r = torch.tensor([[1, 0, 1, 0]], dtype=torch.long)
    tgt_q = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
    model.train()
    logits, reg = model(in_q, in_r, tgt_q)
    assert logits.shape == (1, 4)
    assert float(reg.item()) == 0.0
    logits.sum().backward()
