import tempfile
import pandas as pd

def download_relations(df: pd.DataFrame):
    if df is None or df.empty:
        return None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(tmp.name, index=False)
    return tmp.name
