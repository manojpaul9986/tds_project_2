import pandas as pd

def get_numeric_stats(df):
    stats = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            stats[col] = df[col].describe().to_dict()
    return stats