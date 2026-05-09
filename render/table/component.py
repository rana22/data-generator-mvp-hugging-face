
import html as html_lib
import pandas as pd
import re, json

from config import (
    CUSTOM_CSS,
    AG_GRID_HEAD,
    DISPLAY_COLUMNS
)

def build_sortable_table(df: pd.DataFrame, table_id: str, title: str) -> str:
    if df is None or df.empty:
        return f"""
        <div class="mb-4">
            <h4 class="text-primary">{html_lib.escape(title)}</h4>
            <p>No data</p>
        </div>
        """

def format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    def truncate_cell(x):
        if isinstance(x, (list, dict)):
            x = json.dumps(x, default=str)
        x = "" if x is None else str(x)
        return html_lib.escape(x, quote=False)

    if "evidence" in out.columns:
        out["evidence"] = out["evidence"].apply(
            lambda x: json.dumps(x, indent=2, default=str) if isinstance(x, (list, dict)) else x
        ).apply(truncate_cell)

    if "a_to_b_mapping" in out.columns and not out["a_to_b_mapping"].astype(str).eq("").all():
        out["a_to_b_mapping"] = out["a_to_b_mapping"].astype(str).apply(truncate_cell)
    return out

def _cell_html(value, max_len: int = 120) -> str:
    if value is None:
        text = ""
    elif isinstance(value, float) and pd.isna(value):
        text = ""
    elif isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)

    escaped_full = html_lib.escape(text)

    if len(text) <= max_len:
        return escaped_full

    escaped_short = html_lib.escape(text[:max_len] + "…")

    return (
        f'<span class="expandable-cell" '
        f'data-full-value="{escaped_full}" '
        f'title="Click to expand">'
        f"{escaped_short}"
        f"</span>"
    )

def get_display_df(df: pd.DataFrame, feature_type: str) -> pd.DataFrame:
    cols = DISPLAY_COLUMNS.get(feature_type, DISPLAY_COLUMNS["default"])
    cols = [c for c in cols if c in df.columns]
    return df[cols].copy()

def col_to_class(col: str) -> str:
    col = str(col).strip().lower()
    col = re.sub(r"[^a-z0-9]+", "-", col)  # replace non-alphanumeric with -
    return f"col-{col}"

def build_sortable_table(df: pd.DataFrame, table_id: str, title: str) -> str:
    if df is None or df.empty:
        return f"""
        <div class="mb-4">
            <h4 class="text-primary">{html_lib.escape(title)}</h4>
            <p>No data</p>
        </div>
        """

    df = df.round(3)
    headers = []
    for idx, col in enumerate(df.columns):
        col_class = col_to_class(col)
        headers.append(
            f'<th  class="{col_class}" onclick="sortHtmlTable(\'{table_id}\', {idx})">'
            f'{html_lib.escape(str(col))}<span class="sort-indicator"></span>'
            f'</th>'
        )

    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            cells.append(f"<td>{_cell_html(row[col])}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    return f"""
    <div class="mb-4">
        <h4 class="text-primary">{html_lib.escape(title)}</h4>
        <div class="table-wrap">
            <table id="{table_id}" class="sortable-table table table-striped table-bordered table-hover table-sm"
                   data-sort-col="" data-sort-dir="asc">
                <thead>
                    <tr>{''.join(headers)}</tr>
                </thead>
                <tbody>
                    {''.join(body_rows)}
                </tbody>
            </table>
        </div>
    </div>
    """

def render_generated_tables(analysis_df: pd.DataFrame, valid_df: pd.DataFrame, invalid_df: pd.DataFrame) -> tuple[str, str, str]:
    analysis_html = (
         build_sortable_table(format_display_df(analysis_df), "property-relation-table", "Analyze property (all features)")
        if analysis_df is not None and not analysis_df.empty
        else "<p>No Analysis data</p>"
    )

    valid_html = (
        build_sortable_table(format_display_df(valid_df), "generated-table", "Generated Data")
        if valid_df is not None and not valid_df.empty
        else "<p>No generated data</p>"
    )

    invalid_html = (
        build_sortable_table(format_display_df(invalid_df), "invalid-table", "Invalid Data")
        if invalid_df is not None and not invalid_df.empty
        else "<p>No invalid rows</p>"
    )

    return analysis_html, valid_html, invalid_html, ""

def render_tables(dfs):
    if not isinstance(dfs, dict) or not dfs:
        return "<p>No grouped tables to display.</p>"

    html_parts = []
    for i, (feature_type, df) in enumerate(dfs.items(), start=1):
        display_df = format_display_df(get_display_df(df, feature_type))
        table_id = f"feature_table_{i}"
        html_parts.append(build_sortable_table(display_df, table_id, str(feature_type)))

    return "".join(html_parts)