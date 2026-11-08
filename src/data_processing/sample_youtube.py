"""Reproduce initial seed-42 sampling and the recorded seven quality replacements.

This verifies a frozen snapshot. It never overwrites the sampled or annotation
inputs. --save writes a separate reproduced sample, not new human ratings.
"""
from __future__ import annotations
import argparse
import random
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
import yaml
from src.common import ROOT, read_csv, require_youtube, save_csv, save_json


def text_key(text):return ' '.join(text.split()).casefold()
def replacement_key(text):return ' '.join(re.findall(r'\w+',text.casefold()))


def reproduce():
    require_youtube()
    videos=yaml.safe_load((ROOT/'config/videos.yaml').read_text())['videos']
    pools={};seen_ids=set();seen_text=set();initial=[]
    candidates={}
    for video in videos:
        rows=read_csv(f'data/youtube/processed/{video["folder"]}/youtube_comments_cleaned.csv',dtype=str).to_dict('records')
        candidates[video['video_id']]=rows
        raw=read_csv(f'data/youtube/raw/{video["folder"]}/comments_retrieved.csv',dtype=str).set_index('comment_id')
        pool=[]
        for row in sorted(rows,key=lambda r:r['comment_id']):
            if row['video_id']!=video['video_id'] or row['video_category']!=video['research_category']:
                raise ValueError('Source membership mismatch')
            if row['comment_text_original']!=raw.loc[row['comment_id'],'comment_text_original']:
                raise ValueError('Candidate text differs from raw source')
            key=text_key(row['comment_text_original'])
            if row['comment_id'] in seen_ids or key in seen_text:continue
            seen_ids.add(row['comment_id']);seen_text.add(key);pool.append(row)
        if len(pool)<50:raise ValueError('Insufficient unique candidates')
        pools[video['video_id']]=pool
        for index in np.random.default_rng(42).choice(len(pool),50,replace=False):
            row=pool[int(index)].copy();row['sample_id']=f'COM{len(initial)+1:03d}';initial.append(row)
    archive=read_csv('data/youtube/revisions/quality_revision_20261103/youtube_final_200.csv',dtype=str)
    initial_df=pd.DataFrame(initial)
    if initial_df.comment_id.tolist()!=archive.comment_id.tolist():raise ValueError('Initial seeded draw differs from archived original sample')
    final=[r.copy() for r in initial]
    used_ids={r['comment_id'] for r in initial};used_text={replacement_key(r['comment_text_original']) for r in initial}
    remaining={}
    for video,rows in candidates.items():
        pool=[r for r in rows if r['comment_id'] not in used_ids and replacement_key(r['comment_text_original']) not in used_text and r['processing_status']=='retained']
        pool.sort(key=lambda r:r['comment_id']);random.Random(42).shuffle(pool);remaining[video]=pool
    audit=read_csv('data/youtube/revisions/quality_revision_20261103/replacement_audit.csv',dtype=str)
    for change in audit.sort_values('old_sample_id').to_dict('records'):
        position=next(i for i,r in enumerate(final) if r['sample_id']==change['old_sample_id'])
        pool=remaining[change['video_id']]
        while pool:
            selected=pool.pop(0)
            if selected['comment_id'] not in used_ids and replacement_key(selected['comment_text_original']) not in used_text:break
        else:raise ValueError('Replacement pool exhausted')
        if selected['comment_id']!=change['new_comment_id']:raise ValueError('Seeded replacement differs from recorded audit')
        used_ids.add(selected['comment_id']);used_text.add(replacement_key(selected['comment_text_original']))
        replacement=selected.copy();replacement['sample_id']=change['new_sample_id'];final[position]=replacement
    actual=read_csv('data/youtube/sampled/youtube_final_200.csv',dtype=str)
    frame=pd.DataFrame(final)
    for column in ['sample_id','comment_id','video_id','comment_text_original']:
        if frame[column].tolist()!=actual[column].tolist():raise ValueError('Revised sample mismatch: '+column)
    if not frame.groupby('video_id').size().eq(50).all():raise ValueError('Allocation mismatch')
    return frame,initial_df


def run(save=False):
    frame,initial=reproduce()
    if save:
        save_csv('data/youtube/reproduced/initial_200.csv',initial)
        save_csv('data/youtube/reproduced/current_200.csv',frame)
    result={'initial_draw_reproduced':True,'quality_revision_reproduced':True,'n':len(frame),
            'per_video':frame.groupby('video_id').size().to_dict(),'numpy_seed':42,'replacement_python_random_seed':42,
            'sample_status':'quality-amended; not untouched SRS','saved_annotations_modified':False}
    save_json('reports/youtube/sampling_validation.json',result)
    print(result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--save',action='store_true')
    run(p.parse_args().save)
