"""Theme analysis using TF-IDF and clustering."""

from collections import defaultdict
from datetime import datetime
from typing import Optional
from uuid import uuid4

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from mtm.config import get_config
from mtm.models import Backlinks, Theme
from mtm.storage.db import get_db


def build_tfidf(segments: list[dict], max_features: int = 1000) -> tuple[TfidfVectorizer, np.ndarray]:
    """Build TF-IDF matrix from segments.

    Args:
        segments: List of segment dicts with 'content' field
        max_features: Maximum number of features for TF-IDF

    Returns:
        Tuple of (vectorizer, tfidf_matrix)
    """
    texts = [seg.get("content", "") for seg in segments]

    vectorizer = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),  # Unigrams and bigrams
        min_df=2,  # Term must appear in at least 2 documents
        max_df=0.95,  # Term must appear in less than 95% of documents
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # Fallback if no features found
        vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(texts)

    return vectorizer, tfidf_matrix


def cluster_themes_kmeans(
    tfidf_matrix: np.ndarray,
    k: int,
    vectorizer: TfidfVectorizer,
    segments: list[dict],
) -> list[dict]:
    """Cluster segments into themes using KMeans.

    Args:
        tfidf_matrix: TF-IDF matrix
        k: Number of clusters
        vectorizer: Fitted TF-IDF vectorizer
        segments: List of segment dicts

    Returns:
        List of theme dicts with top_terms, support_count, segment_ids
    """
    if tfidf_matrix.shape[0] < k:
        # Not enough segments for k clusters
        return []

    # Perform KMeans clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(tfidf_matrix)

    # Extract feature names
    feature_names = vectorizer.get_feature_names_out()

    themes = []
    for cluster_id in range(k):
        # Get segments in this cluster
        cluster_indices = np.where(cluster_labels == cluster_id)[0]
        cluster_segments = [segments[i] for i in cluster_indices]

        if len(cluster_segments) == 0:
            continue

        # Get top terms for this cluster
        cluster_center = kmeans.cluster_centers_[cluster_id]
        top_indices = cluster_center.argsort()[-10:][::-1]  # Top 10 terms
        top_terms = [feature_names[i] for i in top_indices]

        # Collect segment IDs
        segment_ids = [seg.get("id") for seg in cluster_segments if seg.get("id")]

        themes.append(
            {
                "cluster_id": cluster_id,
                "top_terms": top_terms,
                "support_count": len(cluster_segments),
                "segment_ids": segment_ids,
                "segments": cluster_segments,
            }
        )

    return themes


def extract_themes_cooccurrence(segments: list[dict], min_support: int = 3) -> list[dict]:
    """Extract themes using keyword co-occurrence (fallback method).

    Args:
        segments: List of segment dicts with 'content' field
        min_support: Minimum number of segments to form a theme

    Returns:
        List of theme dicts
    """
    from collections import defaultdict

    # Extract keywords from segments
    word_cooccurrence: dict[tuple[str, str], int] = defaultdict(int)
    segment_keywords: dict[str, list[str]] = {}

    for seg in segments:
        content = seg.get("content", "").lower()
        seg_id = seg.get("id")

        # Simple keyword extraction (words with length > 3)
        words = [
            w.strip(".,!?;:()[]{}")
            for w in content.split()
            if len(w.strip(".,!?;:()[]{}")) > 3
        ]

        # Remove common stop words
        stop_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "two",
            "way",
            "who",
            "boy",
            "did",
            "she",
            "use",
            "her",
            "many",
            "than",
            "them",
            "these",
        }
        keywords = [w for w in words if w not in stop_words]

        segment_keywords[seg_id] = keywords

        # Build co-occurrence matrix
        for i, word1 in enumerate(keywords):
            for word2 in keywords[i + 1 :]:
                pair = tuple(sorted([word1, word2]))
                word_cooccurrence[pair] += 1

    # Find frequent co-occurring pairs
    frequent_pairs = [
        (pair, count) for pair, count in word_cooccurrence.items() if count >= min_support
    ]
    frequent_pairs.sort(key=lambda x: x[1], reverse=True)

    # Group segments by shared keywords
    themes = []
    used_segments = set()

    for (word1, word2), count in frequent_pairs[:20]:  # Top 20 pairs
        # Find segments containing both keywords
        matching_segments = []
        for seg_id, keywords in segment_keywords.items():
            if seg_id in used_segments:
                continue
            if word1 in keywords and word2 in keywords:
                matching_segments.append(seg_id)

        if len(matching_segments) >= min_support:
            # Create theme
            themes.append(
                {
                    "top_terms": [word1, word2],
                    "support_count": len(matching_segments),
                    "segment_ids": matching_segments,
                }
            )
            used_segments.update(matching_segments)

    return themes


def analyze_themes(
    project: Optional[str] = None,
    persist: bool = True,
) -> list[Theme]:
    """Analyze themes from segments.

    Args:
        project: Project name (None for global analysis)
        persist: Whether to persist themes to database

    Returns:
        List of Theme objects
    """
    config = get_config()
    # Always need database to read segments, even if not persisting
    db = get_db()

    # Fetch segments from database
    if project:
        segments_data = list(
            db.db["segments"].rows_where("project = ?", [project], order_by="created_at")
        )
    else:
        segments_data = list(db.db["segments"].rows_where("1=1", order_by="created_at"))

    if not segments_data:
        return []

    # Convert to list of dicts with required fields
    segments = []
    for seg in segments_data:
        segments.append(
            {
                "id": seg["id"],
                "content": seg.get("content", ""),
                "note_id": seg.get("note_id"),
                "project": seg.get("project", project or "global"),
            }
        )

    # Check if we have enough segments for clustering
    min_segments_for_clustering = config.kmeans_k * 2  # Need at least 2x k segments

    if len(segments) >= min_segments_for_clustering:
        # Use KMeans clustering
        vectorizer, tfidf_matrix = build_tfidf(segments)
        themes_data = cluster_themes_kmeans(
            tfidf_matrix,
            config.kmeans_k,
            vectorizer,
            segments,
        )
    else:
        # Fallback to keyword co-occurrence
        themes_data = extract_themes_cooccurrence(segments, config.min_theme_support)

    # Filter by min_theme_support and create Theme objects
    themes: list[Theme] = []
    for theme_data in themes_data:
        if theme_data["support_count"] < config.min_theme_support:
            continue

        # Get note_id from first segment (for backlinks)
        note_id = None
        if theme_data.get("segment_ids"):
            first_seg_id = theme_data["segment_ids"][0]
            first_seg = next((s for s in segments if s["id"] == first_seg_id), None)
            if first_seg:
                note_id = first_seg.get("note_id")

        # Create Theme object
        theme = Theme(
            id=uuid4(),
            project=project or "global",
            name=", ".join(theme_data["top_terms"][:3]),  # Use top 3 terms as name
            description=f"Theme with {theme_data['support_count']} supporting segments",
            keywords=theme_data["top_terms"],
            support_count=theme_data["support_count"],
            backlinks=Backlinks(
                note_id=note_id,
                segment_ids=theme_data["segment_ids"],
            ),
        )

        themes.append(theme)

        # Persist to database
        if persist and db:
            db.upsert_theme(
                theme_id=theme.id,
                project=theme.project,
                name=theme.name,
                description=theme.description,
                keywords=theme.keywords,
                support_count=theme.support_count,
                note_id=theme.backlinks.note_id,
            )

    return themes

