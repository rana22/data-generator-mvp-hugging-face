from pathlib import Path
import os, json
import pandas as pd
import gradio as gr

def parse_env_text(env_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (env_text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def load_env_to_text(env_file):
    if env_file is None:
        return ""
    try:
        if isinstance(env_file, (str, Path)):
            path = Path(env_file)
        else:
            path = Path(env_file.name)

        return path.read_text(encoding="utf-8")
    except Exception as e:
        return f"# Failed to read file: {e}"

def _read_single_file(file_path: str) -> dict[str, pd.DataFrame]:
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)

    elif ext == ".json":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise ValueError(f"Unsupported JSON structure in {file_path}")

        df = pd.DataFrame(data)

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # normalize type column
    if "type_" in df.columns:
        df.rename(columns={"type_": "type"}, inplace=True)

    if "type" not in df.columns:
        raise ValueError(f"Missing 'type' field in {file_path}")

    # ✅ split by node type
    node_dfs = {}

    for node_type, group in df.groupby("type"):
        # drop irrelevant columns (all-null columns)
        clean_df = group.drop(columns=["type"]).dropna(axis=1, how="all")

        node_dfs[node_type] = clean_df.reset_index(drop=True)

    return node_dfs

def get_excel_or_json_data(files):
    try:
        if not files:
            return {}, gr.update(choices=[], value=None), pd.DataFrame(), ""

        if not isinstance(files, list):
            files = [files]

        grouped_data: dict[str, pd.DataFrame] = {}

        for file_path in files:
            node_dfs = _read_single_file(file_path)  # now returns dict

            for node_name, node_df in node_dfs.items():
                node_key = str(node_name)

                if node_key in grouped_data:
                    grouped_data[node_key] = pd.concat(
                        [grouped_data[node_key], node_df.copy()],
                        ignore_index=True
                    )
                else:
                    grouped_data[node_key] = node_df.copy()

        node_list = sorted(grouped_data.keys())
        first_node = node_list[0] if node_list else None
        preview_df = grouped_data[first_node] if first_node else pd.DataFrame()
        # node_check_boxes = gr.CheckboxGroup(
        #     label="Select Nodes for Cross Analysis",
        #     choices=node_list,  # ✅ must be list, not State
        #     interactive=True
        # )
        return (
            grouped_data,
            gr.update(choices=node_list, value=first_node),
            preview_df,
            node_list,
            ""
        )

    except Exception as e:
        return (
            {},
            gr.update(choices=[], value=None),
            pd.DataFrame(),
            gr.update(choices=[], value=None),
            node_list,
            f"<div style='color:red;font-weight:700'>Error: {e}</div>"
        )