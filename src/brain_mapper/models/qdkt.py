"""Question-centric Deep Knowledge Tracing (qDKT) baseline (Sonkar et al., EDM 2020)."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from brain_mapper.models.base import BaseKTModel


def _build_concept_graph_edges(
    question_concepts: np.ndarray | torch.Tensor,
    num_questions: int,
    concept_pad_id: int,
    max_edges: int = 50000,
    seed: int = 42,
) -> torch.Tensor:
    """Build undirected edges between questions sharing at least one Knowledge Concept."""
    qc_np = np.asarray(question_concepts)
    concept_to_qs: dict[int, list[int]] = defaultdict(list)
    for qid in range(num_questions):
        for cid in qc_np[qid]:
            c_int = int(cid)
            if c_int != concept_pad_id:
                concept_to_qs[c_int].append(qid)

    edges: list[tuple[int, int]] = []
    rng = np.random.default_rng(seed)
    for q_list in concept_to_qs.values():
        k = len(q_list)
        if k < 2:
            continue
        arr = np.asarray(q_list, dtype=np.int64)
        # Connect each question to a sparse set of neighbors sharing this concept
        shuffled = rng.permutation(arr)
        for i in range(k):
            u = int(arr[i])
            v = int(shuffled[(i + 1) % k])
            if u != v:
                edges.append((u, v))
            if k > 4:
                v2 = int(shuffled[(i + 2) % k])
                if u != v2:
                    edges.append((u, v2))

    if not edges:
        return torch.zeros((0, 2), dtype=torch.long)

    edge_arr = np.asarray(edges, dtype=np.int64)
    if len(edge_arr) > max_edges:
        chosen = rng.choice(len(edge_arr), size=max_edges, replace=False)
        edge_arr = edge_arr[chosen]
    return torch.from_numpy(edge_arr)


class qDKT(BaseKTModel):
    """Question-centric DKT with Concept-Graph Laplacian Regularization."""

    def __init__(
        self,
        num_questions: int,
        num_concepts: int,
        question_concepts: np.ndarray | torch.Tensor,
        emb_size: int = 128,
        hidden_size: int = 128,
        num_layers: int = 1,
        dropout: float = 0.2,
        laplacian_lambda: float = 0.05,
        edge_sample_size: int = 1024,
    ) -> None:
        super().__init__(
            num_questions=num_questions,
            num_concepts=num_concepts,
            question_concepts=question_concepts,
            emb_size=emb_size,
            hidden_size=hidden_size,
            dropout=dropout,
        )
        self.laplacian_lambda = float(laplacian_lambda)
        self.edge_sample_size = int(edge_sample_size)
        self.inter_pad_id = 2 * self.num_questions

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
        self.out_proj = nn.Linear(self.hidden_size, self.num_questions + 1)

        edges = _build_concept_graph_edges(
            question_concepts=question_concepts,
            num_questions=self.num_questions,
            concept_pad_id=self.concept_pad_id,
        )
        self.register_buffer("laplacian_edges", edges)

    def laplacian_loss(self) -> torch.Tensor:
        """Stochastic Graph Laplacian smoothness penalty across shared-concept questions."""
        if self.laplacian_lambda <= 0.0 or self.laplacian_edges.shape[0] == 0:
            return self.out_proj.weight.new_zeros(())

        total_edges = self.laplacian_edges.shape[0]
        if total_edges <= self.edge_sample_size:
            sampled = self.laplacian_edges
        else:
            idx = torch.randint(0, total_edges, (self.edge_sample_size,), device=self.laplacian_edges.device)
            sampled = self.laplacian_edges[idx]

        u_idx = sampled[:, 0]
        v_idx = sampled[:, 1]
        # Regularize both readout vectors and question interaction embeddings
        w_diff = F.mse_loss(self.out_proj.weight[u_idx], self.out_proj.weight[v_idx])
        return self.laplacian_lambda * w_diff

    def forward(
        self,
        in_q: torch.Tensor,
        in_r: torch.Tensor,
        tgt_q: torch.Tensor,
        student_idx: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Predict next-step logits per target question ID with Laplacian regularization."""
        inter_idx = self.encode_binary_interactions(
            in_q,
            in_r,
            vocab_size=self.num_questions,
            pad_id=self.question_pad_id,
        )
        x = self.interaction_emb(inter_idx)
        h, _ = self.lstm(x)
        all_q_logits = self.out_proj(self.drop(h))  # [B, L, num_questions + 1]
        pred_logits = torch.gather(all_q_logits, dim=-1, index=tgt_q.unsqueeze(-1)).squeeze(-1)

        reg_loss = self.laplacian_loss() if self.training else pred_logits.new_zeros(())
        return pred_logits, reg_loss
