import pandas as pd
from util import (
    build_level_map,
    _json_safe
)

def df_to_html(curr_node_relations: pd.DataFrame):

    if curr_node_relations is None or curr_node_relations.empty:
        row_data = [["Alice", 25, "true"], ["Bob", 30, "false"]]
        col_defs = [{"field":"Name"}, {"field":"Age"}, {"field":"Active"}]
    else:
        display_df = curr_node_relations.copy()

        # Optional: hide or simplify huge text columns
        for col in ["evidence", "a_to_b_mapping"]:
            if col in display_df.columns:
                display_df[col] = display_df[col].astype(str)

        display_df = display_df.reset_index(drop=False)
        display_df.columns = [str(c) for c in display_df.columns]

        curr_row_data = display_df.fillna("").to_dict(orient="records")
        col_defs = [{"field": str(col)} for col in display_df.columns]
        
        row_data =[["Alice", 24, "true"]]
        return f"""
            <div id="table-root"
                style="height: 300px; width: 100%;"
                data-row-data='{_json_safe(curr_row_data)}'
                data-col-defs='{_json_safe(col_defs)}'>
                {_json_safe(col_defs)}
                </div>
            """

    data = _json_safe(row_data)
    cols = _json_safe(col_defs)

    return f"""
    <div id="table-root"
        style="height: 300px; width: 100%;"
        data-row-data='{data}'
        data-col-defs='{cols}'>
    </div>
    """
