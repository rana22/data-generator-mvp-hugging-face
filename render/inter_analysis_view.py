import gradio as gr
from typing import Any, Dict
import pandas as pd

from analyze.inter_nodes import (
    run_cross_analysis
)
from loaders import (
    get_excel_or_json_data
)
from analyze.intra_node import (
    PairwiseRelationshipEvaluator
)
# from cross_evaluator import CrossNodeRelationshipEvaluator, find_selected_path
from cross_generator import CrossNodeDataGenerator
from generator import SyntheticDataGenerator

def select_all_nodes(nodes):
    return nodes

def update_node_selector(node_list):
    return gr.update(choices=node_list)

def show_selected_edge(edge_name: str, edge_frames_state: dict[str, pd.DataFrame]):
    if not edge_name or not edge_frames_state:
        return pd.DataFrame()

    df = edge_frames_state.get(edge_name)
    if df is None:
        return pd.DataFrame()

    return df

def view_selected_node_analysis(selected_node, all_node_analysis):
    if not selected_node:
        return pd.DataFrame()
    if all_node_analysis and all_node_analysis is not None:
        df = all_node_analysis.get(selected_node)
        if df is None:
            return pd.DataFrame()

        return df
    return pd.DataFrame()

def generate_cross_node_data(
    node_data_state: Dict[str, pd.DataFrame],
    cross_node_analysis_dfs: pd.DataFrame,
    selected_nodes: list[str],
):
    try:
        cross_gen = CrossNodeDataGenerator()

        edge_frames = cross_gen.generate_edge_frames(
            node_data_state=node_data_state,
            selected_nodes=selected_nodes,
            cross_node_analysis_dfs=cross_node_analysis_dfs,
            max_edges=20,
            max_rows_per_edge=50,
        )

        if not edge_frames:
            return {}, gr.update(choices=[], value=None), pd.DataFrame(), ""

        # Convert tuple keys to readable labels for the dropdown
        edge_map: dict[str, pd.DataFrame] = {}
        edge_choices: list[str] = []

        for (parent_node, child_node), edge_df in edge_frames.items():
            edge_name = f"{parent_node} -> {child_node}"
            edge_map[edge_name] = edge_df
            edge_choices.append(edge_name)

        first_edge = edge_choices[0] if edge_choices else None
        first_df = edge_map[first_edge] if first_edge else pd.DataFrame()

        return (
            edge_map,
            gr.update(choices=edge_choices, value=first_edge),
            first_df,
            "",
        )

    except Exception as e:
        print(f"[CROSS GENERATION ERROR] {e}")
        return {}, gr.update(choices=[], value=None), pd.DataFrame(), f"<div style='color:red;font-weight:700'>error while generating data - app<br>{str(e)}</div>"


def compute_cross_node_analysis(
    schema_state,
    selected_nodes,
    node_data_state,
    cross_node_analysis_dfs,
    edges_out
):
    print("compute_node_analysis")
    print(selected_nodes)
    try:
        full_analysis: dict[str, pd.DataFrame] = {}
        gr_selector = gr.update(choices=selected_nodes, value=selected_nodes[0] if selected_nodes else None)
        filtered_analysis_df = cross_node_analysis_dfs[
            cross_node_analysis_dfs["classification"].str.lower().isin(
                ["functional", "strong", "conditional"]
            )
        ]
        print(f"edges_out -> {edges_out}")
        
        print("engine")
        for _, row in edges_out.iterrows():
            parent = row["parent"]
            child = row["child"]
            print(parent, "->", child)
            try:
                df = node_data_state.get(child)
                if df is None or df.empty:
                    continue
                schema = next((s for s in schema_state if s.name == child), None)
                engine = PairwiseRelationshipEvaluator(schema)
                results = engine.evaluate_all_pairs(df)

                mask = filtered_analysis_df["B"].astype(str).str.lower().str.startswith(child.lower() + ".")
                cross_node_validation = filtered_analysis_df[mask].copy().reset_index(drop=True)

                combined = pd.concat([results, cross_node_validation], ignore_index=True, sort=False)
                full_analysis[child] = combined
            except Exception as e:
                print( f"[compute_node_analysis] {child} - {str(e)}")
                continue
        return filtered_analysis_df, gr_selector, full_analysis, ""
    except Exception as e:
        return None, gr_selector, None, f"[compute_node_analysis] {str(e)}"

def create_cross_node_data(
    schema_state,
    node_data_state,
    all_node_analysis,
    selected_nodes,
    edges_out,
    num_rows = 50
):
    full_data: dict[str, pd.DataFrame] = {}
    gr_selector = gr.update(choices=selected_nodes, value=selected_nodes[0] if selected_nodes else None)

    try:

        for _, row in edges_out.iterrows():
            parent = row["parent"]
            child = row["child"]
            schema = next((s for s in schema_state if s.name == child), None)
            # print(f"schema {schema}")
            df = node_data_state.get(child)
            node_analysis = all_node_analysis.get(child)
            # generate synthetic data
            gen = SyntheticDataGenerator(
                real_rows=df,
                relationships=node_analysis,
                schema=schema,
            )
            synth_df = gen.generate(int(num_rows))
            full_data[child] = synth_df
        return full_data, gr_selector, ""
    except Exception as e:
        return None, [], f"[generate_cross_node_data] {str(e)}"

def view_inter_nodes_analysis(
    data_upload,
    selected_node_table,
    selected_node_dataframe,
    schema_state,
    node_list_state,
    full_node_data_state,
    edges,
    edges_out,
    error_box
):
    print("view_inter_nodes_analysis")
    # cross node validation
    gr.Markdown("## Cross Node Analysis")
    with gr.Row():
        select_all_btn = gr.Button("Select All Nodes")
        uncheck_all_btn = gr.Button("Uncheck All Nodes")

    node_selector = gr.CheckboxGroup(
        label="Select Nodes for Cross Analysis",
        choices=[],   # ✅ must be list, not State
    )
    cross_btn = gr.Button("Run Cross Node Analysis")

    select_all_btn.click(
        fn=select_all_nodes,
        inputs=[node_list_state],
        outputs=node_selector,
    )

    uncheck_all_btn.click(
        fn=select_all_nodes,
        inputs=[],
        outputs=node_selector,
    )

    gr.Markdown("### View Node Analysis")
    cross_node_analysis_state = gr.State({})
    cross_node_relationship_state = gr.State({})
    cross_node_analysis_summary = gr.Markdown()
    feature_table = gr.Dataframe()
    cross_node_analysis_dfs = gr.Dataframe(label="Cross Node Relation", interactive=False)
    cross_node_analysis_html_table = gr.HTML()

    gr.Markdown("### Generate Cross Node Data")
    gen_cross_node_btn = gr.Button("Gen Selected Node Data")
    # cross_gen_html = gr.HTML()
    edge_selector = gr.Dropdown(
        label="Select Edge",
        choices=[],
        interactive=True,
    )
    cross_gen_table = gr.Dataframe(
        label="Cross Node Generated Table",
        interactive=False,
    )
    cross_gen_error = gr.HTML()
    edge_frames_state = gr.State({})

    cross_btn.click(
        fn=run_cross_analysis,
        inputs=[
            schema_state,
            full_node_data_state,
            edges,
            node_selector
        ],
        outputs=[
            cross_node_analysis_state, 
            cross_node_relationship_state, 
            cross_node_analysis_summary, 
            feature_table,
            cross_node_analysis_dfs,
            cross_node_analysis_html_table
        ]
    )


    # data upload
    data_upload.change(
        fn=get_excel_or_json_data,
        inputs=[data_upload],
        outputs=[
            full_node_data_state,
            selected_node_table,
            selected_node_dataframe,
            node_list_state,
            error_box
        ],
    ).then(
        fn=update_node_selector,
        inputs=node_list_state,
        outputs=node_selector
    )

    gen_cross_node_btn.click(
        fn=generate_cross_node_data,
        inputs=[
            full_node_data_state,
            cross_node_analysis_dfs,
            node_selector,
        ],
        outputs=[
            edge_frames_state,
            edge_selector,
            cross_gen_table,
            cross_gen_error,
        ],
    )

    edge_selector.change(
        fn=show_selected_edge,
        inputs=[
            edge_selector,
            edge_frames_state,
        ],
        outputs=[
            cross_gen_table,
        ],
    )


    # combine individual node and cross node data
    gr.Markdown("### combine individual node and cross node data")

    all_node_analysis_btn = gr.Button("Node Analyse Selected Nodes")
    cross_node_analysis_selector = gr.Dropdown(
        label="Select Node",
        choices=[],
        interactive=True,
    )
    nodes_analysis = gr.DataFrame()
    all_node_analysis = gr.State({})

    all_node_analysis_btn.click(
        fn=compute_cross_node_analysis,
        inputs=[
            schema_state,
            node_selector,
            full_node_data_state,
            cross_node_analysis_dfs,
            edges_out
        ],
        outputs=[
            nodes_analysis,
            cross_node_analysis_selector,
            all_node_analysis,
            error_box
        ]
    )

    cross_node_analysis_selector.change(
        fn=view_selected_node_analysis,
        inputs=[
            cross_node_analysis_selector,
            all_node_analysis,
        ],
        outputs=[
            nodes_analysis,
        ]
    )

    # edge_frames_state - cross node data (edge)
    gen_all_data_btn = gr.Button("Gen Data for Selected Nodes")
    cross_node_data_selector = gr.Dropdown(
        label="Select Node Data",
        choices=[],
        interactive=True,
    )
    all_node_data = gr.State({})
    view_node_data = gr.DataFrame()
    gen_all_data_btn.click(
        fn=create_cross_node_data,
        inputs=[
            schema_state,
            full_node_data_state,
            all_node_analysis,
            node_selector,
            edges_out
        ],
        outputs=[
            all_node_data,
            cross_node_data_selector,
            error_box
        ]
    )

    cross_node_data_selector.change(
        fn=view_selected_node_analysis,
        inputs=[
            cross_node_data_selector,
            all_node_data,
        ],
        outputs=[
            view_node_data,
        ]
    )
