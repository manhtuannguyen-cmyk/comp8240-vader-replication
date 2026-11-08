"""Validate frozen input hashes; private inputs are not assumed publicly distributable."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src.common import ROOT, sha


def run(public_only=False):
    manifest=json.loads((ROOT/'data/provenance/input_manifest.json').read_text())
    include_private=not public_only and (ROOT/'data/youtube/sampled/youtube_final_200.csv').is_file()
    checked=0
    for record in manifest['files']:
        if record['private'] and not include_private:continue
        path=(ROOT/record['path']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Manifest path escapes repository')
        if not path.is_file():raise FileNotFoundError(f'Missing {record["path"]}. Use src/data_processing/fetch_public_data.py for public upstream inputs, or obtain the permitted private marker bundle.')
        if sha(path)!=record['sha256']:raise ValueError('Input hash mismatch: '+record['path'])
        checked+=1
    print(f'Input hashes verified: {checked}; private snapshot checked: {include_private}')
    return checked


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-only',action='store_true')
    run(p.parse_args().public_only)
