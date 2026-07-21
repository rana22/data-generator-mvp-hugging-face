import html

import pandas as pd
import gradio as gr
from generator import SyntheticDataGenerator
from analyze.intra_node import (
    PairwiseRelationshipEvaluator
)
from config import get_disease_generation_config
from disease_vocabulary import prepare_generation_rows
from render.table.component import (
    render_generated_tables
)


EMPTY_ANALYSIS_HTML = "<p>No analysis data</p>"
EMPTY_GENERATED_HTML = "<p>No generated data</p>"
EMPTY_INVALID_HTML = "<p>No invalid rows</p>"


def _empty_generation_output(status_message: str, error_message: str = ""):
    return (
        EMPTY_ANALYSIS_HTML,
        EMPTY_GENERATED_HTML,
        EMPTY_INVALID_HTML,
        status_message,
        error_message,
    )

def generate_node_data(
    weights_state,
    schema_state,
    data_state,
    selected_node,
    num_rows,
    generation_mode=None,
    requested_disease=None,
    selected_project=None,
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

        scope_config = get_disease_generation_config(selected_project)
        validation, df = prepare_generation_rows(
            data_state=data_state,
            selected_node=selected_node,
            generation_mode=generation_mode,
            requested_disease=requested_disease,
            scope_config=scope_config,
            project_name=selected_project,
        )
        if not validation.can_generate or df is None:
            if cross_node_validation is not None:
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
            return _empty_generation_output(validation.message)

        # Validation and row scoping must complete before either engine is constructed.
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

        analysis_html, valid_html, invalid_html, error_message = render_generated_tables(
            results,
            valid_df,
            invalid_df,
        )
        return (
            analysis_html,
            valid_html,
            invalid_html,
            validation.message,
            error_message,
        )

    except Exception as e:
        if cross_node_validation is not None:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        error_text = html.escape(str(e))
        return _empty_generation_output(
            "Generation could not be completed.",
            f"<div style='color:red;font-weight:700'>Error while generating data: {error_text}</div>",
        )
