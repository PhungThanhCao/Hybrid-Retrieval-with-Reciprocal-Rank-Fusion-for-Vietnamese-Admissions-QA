import json, os, pickle
from pathlib import Path
def atomic_json(path: Path, value):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8'); os.replace(tmp,path)
def atomic_pickle(path: Path, value):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_bytes(pickle.dumps(value)); os.replace(tmp,path)
