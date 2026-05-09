import gradio as gr
import pandas as pd
import os, yaml, requests

from schema import load_schemas_from_models, node_schemas_to_markdown
from loaders import (
    parse_env_text,
    load_env_to_text,
    get_excel_or_json_data
)
from graph.BFS import get_edges_for_nodes
# load schema
def load_and_display_schema(
    env_text,
    node_list
):
    print("load schema")
    env_values: dict[str, str] = {}
    env_values.update(parse_env_text(env_text))
    for k, v in env_values.items():
        os.environ[k] = v
    try:
        # env var 
        node_url = os.getenv("NODE_MODEL_URL", "")
        prop_url = os.getenv("PROP_MODEL_URL", "")

        if not node_url or not prop_url:
            raise gr.Error("Set NODE_MODEL_URL and PROP_MODEL_URL in the environment.")
        # print(node_url)
        # print(prop_url)
        node_model = yaml.safe_load(requests.get(node_url, timeout=30).text)
        prop_model = yaml.safe_load(requests.get(prop_url, timeout=30).text)
        nodes = node_model.get("Nodes", {}) or node_model.get("nodes", {}) or {}
        props = prop_model.get("PropDefinitions", {}) or prop_model.get("properties", {}) or {}
        
        whole_schema, error = load_schemas_from_models(nodes, props)
        if error:
            return [], error
        md = node_schemas_to_markdown(whole_schema)
        return md, whole_schema, ""

    except Exception as e:
        return "", [], f"error while loading schema - app\n {str(e)}"


def view_model(env_text, error_box):
    node_list_state = gr.State([])
    load_schema_btn = gr.Button("Load Schema")
    schema_state = gr.State([])

    schema_markdown = gr.Markdown(label="Schema View",  height=500)
    load_schema_btn.click(
        fn=load_and_display_schema,
        inputs=[env_text],
        outputs=[schema_markdown, schema_state, error_box],
    )

    load_relations_btn = gr.Button("View Nodes")
    graph_state = gr.State()
    # graph_df = gr.DataFrame(label="Node Tree")
    paths_out = gr.JSON(label="Paths")
    edges = gr.State([])
    edges_out = gr.DataFrame(label="Edges", interactive=False)

    load_relations_btn.click(
        fn=get_edges_for_nodes,
        inputs=[node_list_state],
        outputs=[
            graph_state,
            paths_out,
            edges,
            edges_out,
            error_box
        ]
    )

    return (
        node_list_state,
        schema_state,
        graph_state,
        paths_out,
        edges,
        edges_out,
        error_box
    )