import pandas as pd

def build_status_md(node_name: str, study_id: str | None, results: pd.DataFrame) -> str:
    lines = [f"# Analysis for `{node_name}`"]
    lines.append(f"- Study: `{study_id or 'all'}`")
    lines.append(f"- Pairs analyzed: `{len(results)}`")
    if not results.empty and "classification" in results.columns:
        cls_counts = results["classification"].fillna("unknown").value_counts().to_dict()
        lines.append("\n## Relationship counts")
        for k, v in cls_counts.items():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)