"""
RAG Quality Metrics Module

Implements standard Information Retrieval metrics:
- Recall@k: What % of relevant chunks are in top-k?
- Precision@k: What % of top-k are relevant?
- MRR (Mean Reciprocal Rank): How high is the first relevant chunk?
- NDCG@k: How well does ranking reflect graded relevance?

All metrics return float in [0.0, 1.0] range.
"""

import math


def compute_recall_at_k(retrieved: list[int], relevant: list[int], k: int) -> float:
    """
    Compute Recall@k: What percentage of relevant chunks are in top-k results?

    Args:
        retrieved: List of chunk indices ranked by similarity (0-based)
        relevant: List of ground truth relevant chunk indices
        k: Number of top results to consider

    Returns:
        Float in [0.0, 1.0]. 1.0 = all relevant chunks found in top-k.

    Example:
        retrieved = [2, 5, 8]  # Top-3 chunks by similarity
        relevant = [0, 2, 5]   # Ground truth
        recall@3 = 2/3 = 0.667 (found 2 out of 3 relevant chunks, missed chunk 0)
    """
    if not relevant:
        return 0.0

    top_k = set(retrieved[:k])
    relevant_set = set(relevant)
    hits = len(top_k & relevant_set)

    return hits / len(relevant_set)


def compute_precision_at_k(retrieved: list[int], relevant: list[int], k: int) -> float:
    """
    Compute Precision@k: What percentage of top-k results are relevant?

    Args:
        retrieved: List of chunk indices ranked by similarity
        relevant: List of ground truth relevant chunk indices
        k: Number of top results to consider

    Returns:
        Float in [0.0, 1.0]. 1.0 = all top-k are relevant (no noise).

    Example:
        retrieved = [2, 5, 8]
        relevant = [2, 5]
        precision@3 = 2/3 = 0.667 (chunk 8 is noise)
    """
    if k == 0:
        return 0.0

    top_k = set(retrieved[:k])
    relevant_set = set(relevant)
    hits = len(top_k & relevant_set)

    return hits / k


def compute_mrr(retrieved: list[int], relevant: list[int]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR): How high is the first relevant chunk ranked?

    Args:
        retrieved: List of chunk indices ranked by similarity
        relevant: List of ground truth relevant chunk indices

    Returns:
        Float in [0.0, 1.0]. 1.0 = first result is relevant.

    Example:
        retrieved = [8, 2, 5]  # Chunk 2 is first relevant at rank 2
        relevant = [2, 5]
        MRR = 1/2 = 0.5
    """
    relevant_set = set(relevant)

    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in relevant_set:
            return 1.0 / rank

    return 0.0


def compute_ndcg_at_k(
    retrieved: list[int], relevance_scores: dict[int, int], k: int
) -> float:
    """
    Compute Normalized Discounted Cumulative Gain (NDCG@k).
    Measures how well the ranking reflects graded relevance (3=highly, 2=medium, 1=marginal).

    Args:
        retrieved: List of chunk indices ranked by similarity
        relevance_scores: Dict mapping chunk_id → relevance score (3, 2, 1, or 0)
        k: Number of top results to consider

    Returns:
        Float in [0.0, 1.0]. 1.0 = perfect ranking (most relevant chunks first).

    Example:
        retrieved = [2, 5, 0]
        relevance_scores = {2: 3, 5: 2, 0: 1}
        NDCG@3 = 1.0 (perfect ranking: chunks ordered by relevance)
    """
    if not relevance_scores or k == 0:
        return 0.0

    # Compute DCG@k (Discounted Cumulative Gain)
    dcg = 0.0
    for i, chunk_id in enumerate(retrieved[:k], start=1):
        rel = relevance_scores.get(chunk_id, 0)
        dcg += rel / math.log2(i + 1)

    # Compute IDCG@k (Ideal DCG - perfect ranking)
    ideal_ranking = sorted(
        relevance_scores.items(), key=lambda x: x[1], reverse=True
    )
    idcg = 0.0
    for i, (_, score) in enumerate(ideal_ranking[:k], start=1):
        idcg += score / math.log2(i + 1)

    if idcg == 0:
        return 0.0

    return dcg / idcg


def compute_all_metrics(
    retrieved: list[int],
    relevant: list[int],
    relevance_scores: dict[int, int],
    k: int = 3,
) -> dict[str, float]:
    """
    Compute all 4 metrics at once (convenience function).

    Args:
        retrieved: Chunk indices ranked by similarity
        relevant: Ground truth relevant chunk indices
        relevance_scores: Dict mapping chunk_id → relevance score (3, 2, 1, 0)
        k: Number of top results to consider (default: 3)

    Returns:
        Dict with keys: recall@k, precision@k, mrr, ndcg@k
        All values in [0.0, 1.0] range.

    Example:
        metrics = compute_all_metrics(
            retrieved=[2, 5, 8],
            relevant=[2, 5],
            relevance_scores={2: 3, 5: 2, 8: 0},
            k=3
        )
        # Returns: {
        #   "recall@3": 1.0,      # Found all relevant chunks
        #   "precision@3": 0.667,  # 2/3 are relevant
        #   "mrr": 1.0,            # First result is relevant
        #   "ndcg@3": 0.95         # Ranking almost perfect
        # }
    """
    return {
        f"recall@{k}": compute_recall_at_k(retrieved, relevant, k),
        f"precision@{k}": compute_precision_at_k(retrieved, relevant, k),
        "mrr": compute_mrr(retrieved, relevant),
        f"ndcg@{k}": compute_ndcg_at_k(retrieved, relevance_scores, k),
    }
