import pandas as pd
import gradio as gr
from generator import SyntheticDataGenerator
from analyze.intra_node import (
    run_intra_node_analysis,
    PairwiseRelationshipEvaluator
)
from render.table.component import (
    render_generated_tables
)

def generate_node_data(
    weights_state,
    schema_state,
    data_state,
    selected_node,
    num_rows,
    cross_node_validation=None,
):
    try:
        if not schema_state:
            raise gr.Error("Load schema first.")

        if not selected_node:
            raise gr.Error("Select a node.")

        # get schema
        schema = next((s for s in schema_state if s.name == selected_node), None)
        if schema is None:
            raise gr.Error(f"Schema not found for node '{selected_node}'.")

        # get real data
        df = data_state.get(selected_node)
        print(f"selected node {selected_node}, data length {len(df)}")
        if df is None or df.empty:
            raise gr.Error(f"No data found for node '{selected_node}'.")

        # run relationship analysis first
        engine = PairwiseRelationshipEvaluator(schema, weights_state)
        results = engine.evaluate_all_pairs(df)
        if results.empty:
            raise gr.Error("No relationships found. Cannot generate synthetic data.")
       
        # generate synthetic data
        gen = SyntheticDataGenerator(
            real_rows=df,
            relationships=results,
            schema=schema,
            synth_df=None
        )
        synth_df = gen.generate(int(num_rows))
        valid_df, invalid_df = gen.validate_rows(synth_df)
        if cross_node_validation is not None:
            return results, valid_df, invalid_df
        
        return render_generated_tables(results, valid_df, invalid_df)

    except Exception as e:
        return [], [], [], f"error while generating data - app\n {str(e)}"