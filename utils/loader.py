
import pandas as pd, json
from pathlib import Path
class DatasetLoader:
    @staticmethod
    def load_dataset(path):
        p=Path(path)
        if p.suffix.lower()=='.csv': return pd.read_csv(p)
        if p.suffix.lower() in ['.xlsx','.xls']: return pd.read_excel(p)
        if p.suffix.lower()=='.json': return pd.read_json(p)
        raise ValueError('Unsupported format')
    @staticmethod
    def load_json(path):
        with open(path,'r',encoding='utf-8') as f:
            return json.load(f)
