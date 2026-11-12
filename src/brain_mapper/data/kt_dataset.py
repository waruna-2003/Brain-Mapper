"""Sequence dataset builders and fast caching for XES3G5M Knowledge Tracing."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

DEFAULT_INTERACTIONS_CSV = Path("data/processed/xes3g5m/interactions.csv")
DEFAULT_CACHE_DIR = Path("data/processed/xes3g5m/kt_cache")
DEFAULT_DEEPSEEK_ANNOTATIONS = Path("data/annotations/xes3g5m/deepseek_annotations.jsonl")

SKILL_NAMES: tuple[str, ...] = (
    "attention",
    "working_memory",
    "logical_reasoning",
    "language_processing",
    "critical_thinking",
    "metacognition",
)
NUM_COGNITIVE_SKILLS = len(SKILL_NAMES)
MAX_CONCEPTS_PER_QUESTION = 6


@dataclass(frozen=True)
class XES3G5MCache:
    """In-memory handle to cached packed XES3G5M student interaction sequences."""

    num_questions: int
    num_concepts: int
    question_pad_id: int
    concept_pad_id: int
    max_concepts_per_question: int
    question_concepts: np.ndarray  # [num_questions + 1, 6] int32
    flat_q: np.ndarray  # [total_interactions] int32
    flat_r: np.ndarray  # [total_interactions] uint8
    student_ids: np.ndarray  # [num_students] str
    student_splits: np.ndarray  # [num_students] str ('train_valid' or 'test')
    student_folds: np.ndarray  # [num_students] int16
    student_offsets: np.ndarray  # [num_students + 1] int64
    question_cognitive: np.ndarray | None = None  # [num_questions + 1, num_skills] float32 in [0, 1]
    annotated_qids: np.ndarray | None = None  # sorted unique annotated question IDs
    annotated_only: bool = False
    cognitive_skill_names: tuple[str, ...] = SKILL_NAMES

    @property
    def num_students(self) -> int:
        return len(self.student_ids)

    @property
    def num_interactions(self) -> int:
        return int(len(self.flat_q))

    def get_student_slice(self, student_idx: int) -> tuple[np.ndarray, np.ndarray]:
        """Return (questions, responses) arrays for a single student index."""
        start = int(self.student_offsets[student_idx])
        end = int(self.student_offsets[student_idx + 1])
        return self.flat_q[start:end], self.flat_r[start:end]


def _resolve_active_skills(active_skills: Sequence[str] | None) -> tuple[str, ...]:
    """Validate requested cognitive skill subset while preserving canonical order."""
    skills = tuple(SKILL_NAMES if active_skills is None else active_skills)
    if not skills:
        raise ValueError("At least one cognitive skill must remain active.")
    invalid = [s for s in skills if s not in SKILL_NAMES]
    if invalid:
        raise ValueError(f"Unknown cognitive skills: {invalid}. Valid skills: {SKILL_NAMES}")
    return skills


def load_deepseek_cognitive_table(
    annotations_path: Path,
    num_questions: int,
    active_skills: Sequence[str] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Load DeepSeek skill annotations into a normalized [num_questions + 1, S] matrix.

    Supports both raw `.jsonl` bridge output and exported `.csv` files.
    Duplicate `question_id` rows keep the latest valid annotation (matching exporter policy).
    Scores in `[0, 3]` are normalized by `3.0` into `[0.0, 1.0]`.
    """
    if not annotations_path.exists():
        raise FileNotFoundError(f"Cognitive annotations file not found at {annotations_path}")

    skills = _resolve_active_skills(active_skills)
    records_by_qid: dict[int, tuple[float, ...]] = {}
    if annotations_path.suffix.lower() == ".csv":
        with annotations_path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                qid = int(row["question_id"])
                if not (0 <= qid < num_questions):
                    continue
                vec = tuple(float(int(row[s])) / 3.0 for s in skills)
                if any(v < 0.0 or v > 1.0 for v in vec):
                    raise ValueError(f"Question {qid} has out-of-range skill score in {annotations_path}")
                records_by_qid[qid] = vec
    else:
        with annotations_path.open("r", encoding="utf-8") as handle:
            for line_num, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                qid = int(rec["question_id"])
                if not (0 <= qid < num_questions):
                    continue
                try:
                    scores = [int(rec[s]) for s in skills]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid skill fields at {annotations_path}:{line_num}") from exc
                if any(score < 0 or score > 3 for score in scores):
                    raise ValueError(f"Out-of-bounds score {scores} at {annotations_path}:{line_num}")
                records_by_qid[qid] = tuple(score / 3.0 for score in scores)

    table = np.zeros((num_questions + 1, len(skills)), dtype=np.float32)
    annotated_qids = np.array(sorted(records_by_qid.keys()), dtype=np.int32)
    for qid in annotated_qids:
        table[int(qid)] = records_by_qid[int(qid)]
    return table, annotated_qids


def filter_cache_to_annotated(
    cache: XES3G5MCache,
    annotations_path: Path,
    active_skills: Sequence[str] | None = None,
) -> XES3G5MCache:
    """Attach DeepSeek cognitive vectors and restrict interactions strictly to annotated questions."""
    skills = _resolve_active_skills(active_skills)
    cog_table, annotated_qids = load_deepseek_cognitive_table(
        annotations_path,
        cache.num_questions,
        active_skills=skills,
    )
    keep_mask = np.isin(cache.flat_q, annotated_qids)

    cum = np.empty(len(keep_mask) + 1, dtype=np.int64)
    cum[0] = 0
    np.cumsum(keep_mask, dtype=np.int64, out=cum[1:])
    per_student_counts = cum[cache.student_offsets[1:]] - cum[cache.student_offsets[:-1]]
    keep_students = per_student_counts > 0

    kept_counts = per_student_counts[keep_students]
    new_offsets = np.empty(len(kept_counts) + 1, dtype=np.int64)
    new_offsets[0] = 0
    np.cumsum(kept_counts, dtype=np.int64, out=new_offsets[1:])

    return XES3G5MCache(
        num_questions=cache.num_questions,
        num_concepts=cache.num_concepts,
        question_pad_id=cache.question_pad_id,
        concept_pad_id=cache.concept_pad_id,
        max_concepts_per_question=cache.max_concepts_per_question,
        question_concepts=cache.question_concepts,
        flat_q=cache.flat_q[keep_mask],
        flat_r=cache.flat_r[keep_mask],
        student_ids=cache.student_ids[keep_students],
        student_splits=cache.student_splits[keep_students],
        student_folds=cache.student_folds[keep_students],
        student_offsets=new_offsets,
        question_cognitive=cog_table,
        annotated_qids=annotated_qids,
        annotated_only=True,
        cognitive_skill_names=skills,
    )


def build_cognitive_concept_clusters(
    cache: XES3G5MCache,
    num_clusters: int = 64,
    seed: int = 42,
) -> tuple[XES3G5MCache, dict[str, Any]]:
    """Group fine-grained Knowledge Concepts into K categories by DeepSeek cognitive profiles."""
    if cache.question_cognitive is None:
        raise ValueError("Cognitive annotations must be loaded before clustering Knowledge Concepts.")
    if num_clusters < 1:
        raise ValueError(f"num_clusters must be >= 1, got {num_clusters}")

    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    num_skills = cache.question_cognitive.shape[1]
    c_sum = np.zeros((cache.num_concepts, num_skills), dtype=np.float64)
    c_cnt = np.zeros(cache.num_concepts, dtype=np.int32)

    qids = (
        cache.annotated_qids
        if cache.annotated_qids is not None
        else np.arange(cache.num_questions, dtype=np.int32)
    )
    for qid_raw in qids:
        qid = int(qid_raw)
        cog_vec = cache.question_cognitive[qid]
        for cid_raw in cache.question_concepts[qid]:
            cid = int(cid_raw)
            if cid != cache.concept_pad_id and 0 <= cid < cache.num_concepts:
                c_sum[cid] += cog_vec
                c_cnt[cid] += 1

    mean_profiles = np.zeros((cache.num_concepts, num_skills), dtype=np.float32)
    covered_mask = c_cnt > 0
    if bool(covered_mask.any()):
        mean_profiles[covered_mask] = (c_sum[covered_mask] / c_cnt[covered_mask, None]).astype(np.float32)
        global_mean = mean_profiles[covered_mask].mean(axis=0)
        mean_profiles[~covered_mask] = global_mean

    unique_cnt = len(np.unique(np.round(mean_profiles, 6), axis=0))
    k_eff = min(int(num_clusters), max(1, unique_cnt))

    km = KMeans(n_clusters=k_eff, random_state=seed, n_init=20)
    labels = km.fit_predict(mean_profiles).astype(np.int32)

    clustered_qc = np.full_like(cache.question_concepts, k_eff)
    for qid in range(cache.num_questions):
        seen: list[int] = []
        for cid_raw in cache.question_concepts[qid]:
            cid = int(cid_raw)
            if cid == cache.concept_pad_id or not (0 <= cid < cache.num_concepts):
                continue
            cluster_id = int(labels[cid])
            if cluster_id not in seen:
                seen.append(cluster_id)
        for pos, cluster_id in enumerate(seen[: cache.max_concepts_per_question]):
            clustered_qc[qid, pos] = cluster_id

    cluster_counts = np.bincount(labels, minlength=k_eff)
    sil = float(silhouette_score(mean_profiles, labels)) if 1 < k_eff < cache.num_concepts else float("nan")
    summary: dict[str, Any] = {
        "original_num_concepts": int(cache.num_concepts),
        "covered_concepts": int(covered_mask.sum()),
        "num_clusters": int(k_eff),
        "min_cluster_size": int(cluster_counts.min()),
        "median_cluster_size": float(np.median(cluster_counts)),
        "max_cluster_size": int(cluster_counts.max()),
        "silhouette_score": round(sil, 4) if not np.isnan(sil) else None,
    }
    clustered_cache = replace(
        cache,
        num_concepts=k_eff,
        concept_pad_id=k_eff,
        question_concepts=clustered_qc,
    )
    return clustered_cache, summary


def _parse_question_concepts(
    unique_q_concepts: pd.DataFrame,
    num_questions: int,
    num_concepts: int,
    max_k: int = MAX_CONCEPTS_PER_QUESTION,
) -> np.ndarray:
    """Build static [num_questions + 1, max_k] concept matrix padded with concept_pad_id."""
    concept_pad_id = num_concepts
    table = np.full((num_questions + 1, max_k), concept_pad_id, dtype=np.int32)
    for row in unique_q_concepts.itertuples(index=False):
        qid = int(row.question_id)
        parts = [int(p) for p in str(row.concept_ids).split("_") if p.strip()]
        for k_idx, cid in enumerate(parts[:max_k]):
            table[qid, k_idx] = cid
    return table


def _attach_annotations(
    cache: XES3G5MCache,
    annotations_path: Path | None,
    annotated_only: bool,
    active_skills: Sequence[str] | None = None,
) -> XES3G5MCache:
    """Attach cognitive vectors (and optionally filter interactions to annotated questions)."""
    skills = _resolve_active_skills(active_skills)
    if annotated_only:
        if annotations_path is None:
            raise ValueError("annotations_path must be provided when annotated_only=True")
        return filter_cache_to_annotated(cache, annotations_path, active_skills=skills)
    if annotations_path is not None:
        cog_table, annotated_qids = load_deepseek_cognitive_table(
            annotations_path,
            cache.num_questions,
            active_skills=skills,
        )
        return XES3G5MCache(
            num_questions=cache.num_questions,
            num_concepts=cache.num_concepts,
            question_pad_id=cache.question_pad_id,
            concept_pad_id=cache.concept_pad_id,
            max_concepts_per_question=cache.max_concepts_per_question,
            question_concepts=cache.question_concepts,
            flat_q=cache.flat_q,
            flat_r=cache.flat_r,
            student_ids=cache.student_ids,
            student_splits=cache.student_splits,
            student_folds=cache.student_folds,
            student_offsets=cache.student_offsets,
            question_cognitive=cog_table,
            annotated_qids=annotated_qids,
            annotated_only=False,
            cognitive_skill_names=skills,
        )
    return cache


def build_or_load_kt_cache(
    interactions_csv: Path = DEFAULT_INTERACTIONS_CSV,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    rebuild: bool = False,
    annotations_path: Path | None = None,
    annotated_only: bool = False,
    active_skills: Sequence[str] | None = None,
) -> XES3G5MCache:
    """Parse interactions.csv once into a compact compressed sequence cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "xes3g5m_sequences.npz"

    if cache_file.exists() and not rebuild:
        data = np.load(cache_file, allow_pickle=False)
        cache = XES3G5MCache(
            num_questions=int(data["num_questions"]),
            num_concepts=int(data["num_concepts"]),
            question_pad_id=int(data["question_pad_id"]),
            concept_pad_id=int(data["concept_pad_id"]),
            max_concepts_per_question=int(data["max_concepts_per_question"]),
            question_concepts=data["question_concepts"],
            flat_q=data["flat_q"],
            flat_r=data["flat_r"],
            student_ids=data["student_ids"],
            student_splits=data["student_splits"],
            student_folds=data["student_folds"],
            student_offsets=data["student_offsets"],
        )
        return _attach_annotations(cache, annotations_path, annotated_only, active_skills=active_skills)

    if not interactions_csv.exists():
        raise FileNotFoundError(f"Interactions CSV not found at {interactions_csv}")

    df = pd.read_csv(
        interactions_csv,
        usecols=[
            "split",
            "fold",
            "student_id",
            "student_interaction_index",
            "question_id",
            "concept_ids",
            "is_correct",
        ],
        dtype={
            "split": str,
            "fold": np.int16,
            "student_id": str,
            "student_interaction_index": np.int32,
            "question_id": np.int32,
            "concept_ids": str,
            "is_correct": np.uint8,
        },
    )

    df.sort_values(["student_id", "student_interaction_index"], kind="mergesort", inplace=True)

    num_questions = int(df["question_id"].max()) + 1
    unique_q_concepts = df[["question_id", "concept_ids"]].drop_duplicates("question_id")
    max_concept_id = 0
    for c_str in unique_q_concepts["concept_ids"]:
        for p in str(c_str).split("_"):
            if p.strip():
                max_concept_id = max(max_concept_id, int(p))
    num_concepts = max_concept_id + 1

    question_concepts = _parse_question_concepts(
        unique_q_concepts=unique_q_concepts,
        num_questions=num_questions,
        num_concepts=num_concepts,
        max_k=MAX_CONCEPTS_PER_QUESTION,
    )

    flat_q = df["question_id"].to_numpy(dtype=np.int32)
    flat_r = df["is_correct"].to_numpy(dtype=np.uint8)

    # Compute contiguous student boundaries via first-occurrence index
    s_vals = df["student_id"].to_numpy()
    split_vals = df["split"].to_numpy()
    fold_vals = df["fold"].to_numpy()

    change_mask = np.empty(len(s_vals), dtype=bool)
    change_mask[0] = True
    change_mask[1:] = s_vals[1:] != s_vals[:-1]
    starts = np.flatnonzero(change_mask)

    student_ids = s_vals[starts].astype(str)
    student_splits = split_vals[starts].astype(str)
    student_folds = fold_vals[starts].astype(np.int16)
    student_offsets = np.empty(len(starts) + 1, dtype=np.int64)
    student_offsets[:-1] = starts
    student_offsets[-1] = len(s_vals)

    tmp_file = cache_file.with_suffix(".tmp.npz")
    np.savez(
        tmp_file,
        num_questions=np.array(num_questions, dtype=np.int32),
        num_concepts=np.array(num_concepts, dtype=np.int32),
        question_pad_id=np.array(num_questions, dtype=np.int32),
        concept_pad_id=np.array(num_concepts, dtype=np.int32),
        max_concepts_per_question=np.array(MAX_CONCEPTS_PER_QUESTION, dtype=np.int32),
        question_concepts=question_concepts,
        flat_q=flat_q,
        flat_r=flat_r,
        student_ids=student_ids,
        student_splits=student_splits,
        student_folds=student_folds,
        student_offsets=student_offsets,
    )
    tmp_file.replace(cache_file)

    cache = XES3G5MCache(
        num_questions=num_questions,
        num_concepts=num_concepts,
        question_pad_id=num_questions,
        concept_pad_id=num_concepts,
        max_concepts_per_question=MAX_CONCEPTS_PER_QUESTION,
        question_concepts=question_concepts,
        flat_q=flat_q,
        flat_r=flat_r,
        student_ids=student_ids,
        student_splits=student_splits,
        student_folds=student_folds,
        student_offsets=student_offsets,
    )
    return _attach_annotations(cache, annotations_path, annotated_only, active_skills=active_skills)


class KTSequenceDataset(Dataset):
    """PyTorch Dataset providing causally shifted and masked student interaction windows."""

    def __init__(
        self,
        samples: Sequence[tuple[int, np.ndarray, np.ndarray, np.ndarray]],
        max_seq_len: int,
        question_pad_id: int,
    ) -> None:
        self.samples = list(samples)
        self.max_seq_len = max_seq_len
        self.question_pad_id = question_pad_id

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        student_idx, q_seq, r_seq, eval_role_mask = self.samples[idx]
        seq_len = len(q_seq)
        target_steps = self.max_seq_len - 1

        in_q = np.full(target_steps, self.question_pad_id, dtype=np.int64)
        in_r = np.zeros(target_steps, dtype=np.int64)
        tgt_q = np.full(target_steps, self.question_pad_id, dtype=np.int64)
        tgt_r = np.zeros(target_steps, dtype=np.float32)
        eval_mask = np.zeros(target_steps, dtype=np.float32)

        valid_pairs = min(seq_len - 1, target_steps)
        if valid_pairs > 0:
            in_q[:valid_pairs] = q_seq[:valid_pairs]
            in_r[:valid_pairs] = r_seq[:valid_pairs]
            tgt_q[:valid_pairs] = q_seq[1 : valid_pairs + 1]
            tgt_r[:valid_pairs] = r_seq[1 : valid_pairs + 1].astype(np.float32)
            eval_mask[:valid_pairs] = eval_role_mask[1 : valid_pairs + 1].astype(np.float32)

        return {
            "student_idx": torch.tensor(student_idx, dtype=torch.long),
            "in_q": torch.from_numpy(in_q),
            "in_r": torch.from_numpy(in_r),
            "tgt_q": torch.from_numpy(tgt_q),
            "tgt_r": torch.from_numpy(tgt_r),
            "eval_mask": torch.from_numpy(eval_mask),
        }


def _chunk_sequence(
    student_idx: int,
    q_seq: np.ndarray,
    r_seq: np.ndarray,
    role_mask: np.ndarray,
    window_len: int,
) -> list[tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
    """Split a long student history into non-overlapping fixed windows of at least 2 steps."""
    chunks = []
    n = len(q_seq)
    for start in range(0, n, window_len):
        end = min(n, start + window_len)
        if end - start >= 2:
            chunks.append((student_idx, q_seq[start:end], r_seq[start:end], role_mask[start:end]))
    return chunks


def build_standard_datasets(
    cache: XES3G5MCache,
    val_fold: int = 0,
    window_len: int = 200,
    max_train_students: int | None = None,
    seed: int = 42,
) -> tuple[KTSequenceDataset, KTSequenceDataset, KTSequenceDataset]:
    """Create standard cross-student splits matching XES3G5M (train_valid folds vs test)."""
    train_indices = np.flatnonzero((cache.student_splits == "train_valid") & (cache.student_folds != val_fold))
    val_indices = np.flatnonzero((cache.student_splits == "train_valid") & (cache.student_folds == val_fold))
    test_indices = np.flatnonzero(cache.student_splits == "test")

    if max_train_students is not None and len(train_indices) > max_train_students:
        rng = np.random.default_rng(seed)
        train_indices = np.sort(rng.choice(train_indices, size=max_train_students, replace=False))

    def collect(indices: np.ndarray) -> list[tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
        samples = []
        for s_idx in indices:
            q_seq, r_seq = cache.get_student_slice(int(s_idx))
            role = np.ones(len(q_seq), dtype=np.uint8)
            samples.extend(_chunk_sequence(int(s_idx), q_seq, r_seq, role, window_len))
        return samples

    return (
        KTSequenceDataset(collect(train_indices), max_seq_len=window_len, question_pad_id=cache.question_pad_id),
        KTSequenceDataset(collect(val_indices), max_seq_len=window_len, question_pad_id=cache.question_pad_id),
        KTSequenceDataset(collect(test_indices), max_seq_len=window_len, question_pad_id=cache.question_pad_id),
    )


def build_temporal_same_student_datasets(
    cache: XES3G5MCache,
    student_indices: Sequence[int],
    train_ratio: float = 0.70,
    val_ratio: float = 0.10,
    train_window_len: int = 200,
    eval_max_seq_len: int = 512,
) -> tuple[KTSequenceDataset, KTSequenceDataset, KTSequenceDataset]:
    """Split each student chronologically into past (train), mid (val), and future (test).

    Strict causality & leak prevention:
    - Train chunks never see any interaction >= train_end.
    - Validation sequences truncate strictly at val_end and score ONLY [train_end, val_end).
    - Test sequences warm up hidden state on [0, val_end) and score ONLY [val_end, len).
    """
    train_samples: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]] = []
    val_samples: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]] = []
    test_samples: list[tuple[int, np.ndarray, np.ndarray, np.ndarray]] = []

    for s_idx in student_indices:
        q_seq, r_seq = cache.get_student_slice(int(s_idx))
        n = len(q_seq)
        if n < 10:
            continue

        train_end = max(2, int(round(n * train_ratio)))
        val_end = max(train_end + 1, int(round(n * (train_ratio + val_ratio))))
        if val_end >= n:
            val_end = n - 1

        # 1. Train: strict past [0 : train_end]
        tr_role = np.ones(train_end, dtype=np.uint8)
        train_samples.extend(
            _chunk_sequence(int(s_idx), q_seq[:train_end], r_seq[:train_end], tr_role, train_window_len)
        )

        # 2. Validation: history up to val_end, evaluated strictly on [train_end : val_end]
        val_start_ctx = max(0, val_end - eval_max_seq_len)
        val_q = q_seq[val_start_ctx:val_end]
        val_r = r_seq[val_start_ctx:val_end]
        val_role = np.zeros(len(val_q), dtype=np.uint8)
        val_offset = train_end - val_start_ctx
        if val_offset < len(val_q):
            val_role[val_offset:] = 1
            val_samples.append((int(s_idx), val_q, val_r, val_role))

        # 3. Test: history up to n, evaluated strictly on future [val_end : n]
        test_start_ctx = max(0, n - eval_max_seq_len)
        te_q = q_seq[test_start_ctx:n]
        te_r = r_seq[test_start_ctx:n]
        te_role = np.zeros(len(te_q), dtype=np.uint8)
        te_offset = val_end - test_start_ctx
        if te_offset < len(te_q):
            te_role[te_offset:] = 1
            test_samples.append((int(s_idx), te_q, te_r, te_role))

    return (
        KTSequenceDataset(train_samples, max_seq_len=train_window_len, question_pad_id=cache.question_pad_id),
        KTSequenceDataset(val_samples, max_seq_len=eval_max_seq_len, question_pad_id=cache.question_pad_id),
        KTSequenceDataset(test_samples, max_seq_len=eval_max_seq_len, question_pad_id=cache.question_pad_id),
    )


def sample_simulated_classes(
    cache: XES3G5MCache,
    num_classes: int = 5,
    students_per_class: int = 40,
    seed: int = 42,
    split_filter: str | None = "train_valid",
) -> list[list[int]]:
    """Deterministically partition XES3G5M students into disjoint simulated classrooms."""
    if split_filter is not None:
        pool = np.flatnonzero(cache.student_splits == split_filter)
    else:
        pool = np.arange(cache.num_students)

    needed = num_classes * students_per_class
    if len(pool) < needed:
        raise ValueError(f"Requested {needed} students across {num_classes} classes, only {len(pool)} available.")

    rng = np.random.default_rng(seed)
    chosen = rng.choice(pool, size=needed, replace=False)
    classes: list[list[int]] = []
    for c in range(num_classes):
        slice_idx = chosen[c * students_per_class : (c + 1) * students_per_class]
        classes.append([int(x) for x in np.sort(slice_idx)])
    return classes
