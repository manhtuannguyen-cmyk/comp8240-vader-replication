"""Audit or explicitly purge this repository's expired private snapshot only."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src.common import ROOT


def run(purge=False):
    source=ROOT/'data/youtube/metadata/youtube_final_sampling_validation.json'
    if not source.is_file():
        print('No current private snapshot metadata; no deletion performed.');return
    deadline=datetime.fromisoformat(json.loads(source.read_text())['retention_deadline'])
    expired=datetime.now(timezone.utc)>=deadline
    scopes=[ROOT/'data/youtube',ROOT/'reports/youtube',ROOT/'notebooks/private']
    files=[]
    for scope in scopes:
        if not scope.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('Private-data scope resolves outside this repository')
        for path in scope.rglob('*') if scope.exists() else []:
            if not path.is_file():continue
            if path==ROOT/'data/youtube/README.md':continue
            if not path.resolve().is_relative_to(scope.resolve()):raise ValueError('Refusing to follow a private-data symlink outside its scope')
            files.append(path)
    print('Deadline UTC:',deadline.isoformat(),'| expired:',expired,'| private files:',len(files))
    if not purge:
        print('Audit only. --purge-expired explicitly deletes this entire private snapshot after expiry.');return
    if not expired:
        print('Not expired; no files deleted.');return
    for path in files:path.unlink()
    print('Deleted private snapshot files:',len(files),'. Original VADER, GoEmotions, source code and documentation were not deleted.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--purge-expired',action='store_true')
    run(p.parse_args().purge_expired)
