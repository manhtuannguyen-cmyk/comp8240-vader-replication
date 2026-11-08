"""Fetch exact pinned upstream public benchmark files, checking SHA-256 before writing.

Does not download or reconstruct the private YouTube evaluation cohort.
Never extract an archive to the filesystem or overwrite differing local files.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import requests
from src.common import ROOT, sha


def run(dataset='all'):
    manifest=json.loads((ROOT/'config/public_sources.json').read_text())
    cache={};written=0
    for record in manifest['files']:
        if dataset!='all' and record['dataset']!=dataset:continue
        destination=ROOT/record['path']
        if destination.exists():
            if sha(destination)!=record['sha256']:raise ValueError('Existing differing source; refusing overwrite: '+record['path'])
            continue
        url,_,fragment=record['url'].partition('#')
        if url not in cache:
            response=requests.get(url,timeout=90);response.raise_for_status();cache[url]=response.content
        content=cache[url]
        if fragment:
            if not fragment.startswith('member='):raise ValueError('Unsupported archive selector')
            with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
                member=archive.getmember(fragment[len('member='):])
                if not member.isfile():raise ValueError('Archive member is not a regular file')
                extracted=archive.extractfile(member)
                if extracted is None:raise ValueError('Archive member unavailable')
                content=extracted.read()
        if hashlib.sha256(content).hexdigest()!=record['sha256']:raise ValueError('Downloaded checksum mismatch; no output written')
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(content);written+=1
    print('Verified/downloaded source files; newly written:',written)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dataset',choices=['all','original_vader','goemotions'],default='all')
    run(p.parse_args().dataset)
