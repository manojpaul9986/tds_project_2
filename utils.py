import pandas as pd

def load_dataset(path):
    try:
        df = pd.read_csv(path, encoding="latin-1")
        print(f"Loaded dataset: {df.shape}")
        return df
    except Exception as e:
        raise ValueError(f"Error loading dataset: {e}")