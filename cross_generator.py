# cross_generator.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from util import normalize_value

EdgeKey = tuple[str, str]
NodeData = Dict[str, pd.DataFrame]
EdgeFrameMap = Dict[EdgeKey, pd.DataFrame]

CLASSIFICATION_PRIORITY = {
    "functional": 3,
    "strong": 2,
    "conditional": 1,
}

def _is_strong_enough(classification: Any) -> bool:
    text = str(classification or "").strip().lower()
    if not text:
        return False

    if "weak" in text or "independent" in text:
        return False

    return True

def _parse_node_col(spec: Any) -> tuple[str, str]:
    """
    Parse strings like:
      - "sample.sample_id"
      - "study.study_id"
      - "node.column"
    Returns: (node_name, column_name)
    """
    text = str(spec or "").strip()
    if not text:
        return "", ""
    if "." not in text:
        return "", text
    node, col = text.rsplit(".", 1)
    return node.strip(), col.strip()

def _classification_rank(classification: Any) -> int:
    """
    Rough ordering for debug filtering.

    We treat anything containing 'conditional' as the minimum accepted class,
    and stronger labels as larger ranks.
    """
    text = normalize_value(classification)

    if not text:
        return -1

    if "conditional" in text:
        return 1
    if "weak" in text:
        return 0
    if "moderate" in text:
        return 2
    if "strong" in text or "likely" in text:
        return 3
    if "very" in text or "high" in text:
        return 4
    if "certain" in text or "exact" in text or "one_to_one" in text or "one_to_many" in text:
        return 5

    return -1

def get_root_from_graph(graph):
    children = set()
    for child_list in graph.values():
        children.update(child_list)

    roots = [node for node in graph.keys() if node not in children]

    if not roots:
        raise ValueError("No root found in graph.")

    return roots[0]

def _dedupe_analysis_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    subset = [c for c in ["parent_node", "child_node", "A", "B", "classification", "feature_type"] if c in df.columns]
    if subset:
        return df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)

    return df.drop_duplicates().reset_index(drop=True)

def _prefix_df(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out.columns = [f"{prefix}__{c}" for c in out.columns]
    return out


@dataclass
class CrossNodeDebugResult:
    cross_debug_df: pd.DataFrame
    node_seed_dfs: Dict[str, pd.DataFrame] = field(default_factory=dict)
    filtered_relations_df: pd.DataFrame = field(default_factory=pd.DataFrame)

class CrossNodeDataGenerator:
    def generate_edge_frames(
        self,
        node_data_state: NodeData,
        selected_nodes: list[str],
        cross_node_analysis_dfs: pd.DataFrame,
        max_edges: int = 20,
        max_rows_per_edge: int = 100,
    ) -> EdgeFrameMap:
        if cross_node_analysis_dfs is None or cross_node_analysis_dfs.empty:
            return {}

        analysis_df = cross_node_analysis_dfs.copy()

        if "classification" in analysis_df.columns:
            analysis_df = analysis_df[
                analysis_df["classification"].apply(_is_strong_enough)
            ].copy()

        if analysis_df.empty:
            return {}

        # keep only edges touching selected nodes when possible
        selected_set = set(selected_nodes or [])

        edge_map: EdgeFrameMap = {}
        seen_edges: set[EdgeKey] = set()

        for _, rel in analysis_df.iterrows():
            if len(edge_map) >= max_edges:
                break

            parent_node = str(rel.get("parent_node", "")).strip()
            child_node = str(rel.get("child_node", "")).strip()

            if not parent_node or not child_node:
                a_node, a_col = _parse_node_col(rel.get("A"))
                b_node, b_col = _parse_node_col(rel.get("B"))
                parent_node = parent_node or a_node
                child_node = child_node or b_node

            if not parent_node or not child_node:
                continue

            if selected_set and parent_node not in selected_set and child_node not in selected_set:
                continue

            edge_key = (parent_node, child_node)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            parent_df = node_data_state.get(parent_node)
            child_df = node_data_state.get(child_node)
            if parent_df is None or child_df is None or parent_df.empty or child_df.empty:
                continue

            a_node, a_col = _parse_node_col(rel.get("A"))
            b_node, b_col = _parse_node_col(rel.get("B"))

            parent_col = a_col
            child_col = b_col

            if not parent_col or not child_col:
                continue

            if parent_col not in parent_df.columns or child_col not in child_df.columns:
                continue

            parent_cols = [c for c in parent_df.columns if c == parent_col or c in child_df.columns]
            child_cols = [c for c in child_df.columns if c == child_col or c in parent_df.columns]

            # keep it small for debug
            parent_seed = parent_df[parent_cols].drop_duplicates().head(max_rows_per_edge).copy()
            child_seed = child_df[child_cols].drop_duplicates().head(max_rows_per_edge).copy()

            # 1) try exact key overlap
            left_vals = parent_seed[parent_col].astype(str).dropna()
            right_vals = child_seed[child_col].astype(str).dropna()
            common = pd.Index(left_vals).intersection(pd.Index(right_vals))

            if len(common) > 0:
                left_sel = parent_df[parent_df[parent_col].astype(str).isin(common)].copy()
                right_sel = child_df[child_df[child_col].astype(str).isin(common)].copy()

                merged = left_sel.merge(
                    right_sel,
                    left_on=parent_col,
                    right_on=child_col,
                    how="inner",
                    suffixes=(f"__{parent_node}", f"__{child_node}"),
                )
            else:
                # 2) fallback: small cross product for debug
                left_sel = parent_seed.copy()
                right_sel = child_seed.copy()

                left_sel["_tmp"] = 1
                right_sel["_tmp"] = 1
                merged = left_sel.merge(right_sel, on="_tmp", how="inner").drop(columns="_tmp")

            if merged.empty:
                continue

            # prefix columns so parent/child properties stay clear
            parent_part = _prefix_df(
                merged[[c for c in merged.columns if c in parent_df.columns]].copy(),
                "parent",
            )
            child_part = _prefix_df(
                merged[[c for c in merged.columns if c in child_df.columns]].copy(),
                "child",
            )

            # combine prefixed frames
            edge_df = pd.concat([parent_part.reset_index(drop=True), child_part.reset_index(drop=True)], axis=1)

            edge_df["_parent_node"] = parent_node
            edge_df["_child_node"] = child_node
            edge_df["_parent_key_col"] = parent_col
            edge_df["_child_key_col"] = child_col
            edge_df["_feature_type"] = rel.get("feature_type", "")
            edge_df["_classification"] = rel.get("classification", "")
            edge_df["_strength"] = rel.get("strength", 0.0)
            edge_df["_relation_type"] = rel.get("relation_type", "")

            edge_map[edge_key] = edge_df.reset_index(drop=True)

        return edge_map


