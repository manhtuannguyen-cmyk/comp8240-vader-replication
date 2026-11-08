"""Repository-relative paths, deterministic file IO and private-data lifecycle checks."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['negative', 'neutral', 'positive']
SYSTEMS = ['VADER 2014', 'VADER 3.3.2', 'ChatGPT', 'Claude', 'Gemini']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return pd.read_csv(path, keep_default_na=False, **kwargs)


def save_csv(path: str | Path, frame: pd.DataFrame) -> None:
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def save_json(path: str | Path, value) -> None:
    """Strict JSON: undefined statistics become null rather than NaN literals."""
    import numpy as np
    def clean(item):
        if isinstance(item, dict):
            return {str(k): clean(v) for k, v in item.items()}
        if isinstance(item, (list, tuple, np.ndarray)):
            return [clean(v) for v in item]
        if isinstance(item, np.generic):
            return clean(item.item())
        if isinstance(item, float) and not np.isfinite(item):
            return None
        return item
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(value), indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def check_unique(frame: pd.DataFrame, key='sample_id') -> None:
    if key not in frame or frame[key].astype(str).str.strip().eq('').any() or not frame[key].is_unique:
        raise ValueError(f'Missing or duplicate {key}')


def require_youtube() -> None:
    path = ROOT / 'data/youtube/metadata/youtube_final_sampling_validation.json'
    if not path.is_file():
        raise FileNotFoundError('Private YouTube inputs unavailable; original/GoEmotions evaluation still works.')
    deadline = datetime.fromisoformat(json.loads(path.read_text())['retention_deadline'])
    if datetime.now(timezone.utc) >= deadline:
        raise ValueError('YouTube snapshot expired. Refresh/delete all source derivatives before analysis; copying does not restart retention.')


def environment() -> dict:
    import importlib.metadata
    import platform
    packages = ['numpy', 'pandas', 'scipy', 'scikit-learn', 'vaderSentiment', 'matplotlib', 'seaborn', 'statsmodels']
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'packages': {p: importlib.metadata.version(p) for p in packages},
            'execution_utc': datetime.now(timezone.utc).isoformat()}


def save_latex(path: str | Path, frame: pd.DataFrame) -> None:
    """Small plain tabular fragment, without pandas' optional template dependency."""
    import numpy as np
    def escape(value):
        if isinstance(value,(float,np.floating)):
            return f'{value:.4f}' if np.isfinite(value) else '---'
        text=str(value)
        return ''.join({'&':r'\&','%':r'\%','_':r'\_','#':r'\#','$':r'\$'}.get(c,c) for c in text)
    lines=[r'\begin{tabular}{'+'l'+'r'*(len(frame.columns)-1)+'}',
           ' & '.join(escape(c) for c in frame.columns)+r' \\',r'\hline']
    lines.extend(' & '.join(escape(v) for v in row)+r' \\' for row in frame.itertuples(index=False,name=None))
    lines.append(r'\end{tabular}')
    destination=ROOT/path;destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text('\n'.join(lines)+'\n')
