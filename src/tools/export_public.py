"""Create a publication-review folder using an explicit allowlist, never git add -f.

No GitHub upload occurs. Private YouTube inputs, response logs and source-specific
reports are excluded, even if .gitignore changes.
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src.common import ROOT

FILES=['README.md','requirements.txt','.gitignore']


def run(destination):
    destination=Path(destination).resolve()
    if destination.exists():raise FileExistsError('Use a new empty destination; existing folders are never replaced')
    if ROOT==destination or destination in ROOT.parents or destination.is_relative_to(ROOT):
        raise ValueError('Public export must be a separate sibling/output folder, not inside or above the source repository')
    destination.mkdir(parents=True)
    for name in FILES:
        source=ROOT/name
        if source.is_file():shutil.copy2(source,destination/name)
    for directory in ['src','config','prompts','data/goemotions','data/provenance','reports/public']:
        source=ROOT/directory
        if source.is_dir():shutil.copytree(source,destination/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    original=destination/'data/original_vader';original.mkdir(parents=True)
    for name in ['LICENSE.txt','vaderSentiment.py','vader_sentiment_lexicon.txt']:
        p=ROOT/'data/original_vader'/name
        if p.is_file():shutil.copy2(p,original/name)
    paths=list(destination.rglob('*'))
    forbidden=['.env','local_credentials.json','annotations.db']
    if any(p.is_file() and p.name in forbidden for p in paths):raise AssertionError('Forbidden file in public export')
    print('Public review folder created:',destination)
    print('Original text corpora are fetched from pinned upstream sources; private YouTube evaluation needs permitted access separately.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
