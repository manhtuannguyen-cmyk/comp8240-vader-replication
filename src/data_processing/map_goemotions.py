"""Rebuild the documented emotion-to-polarity mapping from 54,263 raw rows.

Default verifies the supplied 45,258 retained records; --write rebuilds processed
split files. Raw text, annotations and official split membership never change.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pandas as pd
import yaml
from src.common import ROOT, read_csv, save_csv, save_json


def map_emotions(names, mapping):
    values=set(names)
    known=set().union(*map(set,mapping.values()))
    reasons=[]
    if not names or not values<=known:
        return '',['missing_or_unknown_emotions']
    if len(values)!=len(names): reasons.append('duplicate_emotion_annotation')
    if values&set(mapping['ambiguous']): reasons.append('ambiguous_emotion_present')
    if values&set(mapping['positive']) and values&set(mapping['negative']): reasons.append('mixed_positive_negative')
    if 'neutral' in values and len(values)>1: reasons.append('neutral_with_other_emotion')
    if reasons:return '',reasons
    for label in ['positive','negative','neutral']:
        if values<=set(mapping[label]):return label,[]
    return '',['unmapped_emotion_combination']


def build():
    config=yaml.safe_load((ROOT/'config/preprocessing.yaml').read_text())
    base=ROOT/config['goemotions_root']
    emotions=(base/'emotions.txt').read_text().splitlines()
    mapping=config['goemotions_mapping']
    rows=[]
    for split,filename in config['splits'].items():
        with (base/filename).open(encoding='utf-8',newline='') as f:
            for position,fields in enumerate(csv.reader(f,delimiter='\t',quoting=csv.QUOTE_NONE),1):
                if len(fields)!=3:raise ValueError(f'Malformed source structure: {split} row {position}')
                text,raw_labels,sid=fields
                names=[emotions[int(i)] for i in raw_labels.split(',')]
                label,reasons=map_emotions(names,mapping)
                if not text.strip():reasons.insert(0,'empty_text')
                if text.strip().casefold() in {'[removed]','[deleted]'}:reasons.insert(0,'deleted_or_removed_placeholder')
                if not sid:reasons.insert(0,'missing_record_id')
                rows.append({'id':sid,'text_original':text,'original_emotion_labels':raw_labels,
                             'emotion_names':json.dumps(names,ensure_ascii=False),'original_split':split,
                             'mapped_sentiment':label if not reasons else '',
                             'processing_status':'excluded' if reasons else 'retained',
                             'exclusion_reason':reasons[0] if reasons else '',
                             'exclusion_reasons':json.dumps(reasons),
                             'source_file':str((base/filename).relative_to(ROOT)),'source_row':position})
    frame=pd.DataFrame(rows)
    # This released snapshot has unique source IDs. Stop on changed identity
    # semantics rather than inventing a resolution for a new release.
    if not frame.id.is_unique:raise ValueError('Repeated raw IDs: inspect release conflicts before remapping')
    groups=frame.groupby('text_original',sort=False)
    frame['duplicate_text_group_size']=groups.id.transform('size')
    frame['cross_split_text_duplicate']=groups.original_split.transform('nunique').gt(1)
    retained=frame[frame.processing_status.eq('retained')].copy()
    excluded=frame[frame.processing_status.eq('excluded')].copy()
    return retained,excluded


def run(write=False):
    retained,excluded=build()
    compare=['id','text_original','original_emotion_labels','original_split','mapped_sentiment']
    expected=read_csv('data/goemotions/processed/all.csv',dtype=str)
    left=retained[compare].astype(str).reset_index(drop=True)
    right=expected[compare].astype(str).reset_index(drop=True)
    if not left.equals(right):raise ValueError('Recomputed retained mapping differs from supplied processed records')
    if len(retained)!=45258 or len(excluded)!=9005:raise ValueError('Unexpected snapshot counts')
    if write:
        save_csv('data/goemotions/processed/all.csv',retained)
        save_csv('data/goemotions/processed/excluded.csv',excluded)
        for split in ['train','validation','test']:
            save_csv(f'data/goemotions/processed/{split}.csv',retained[retained.original_split.eq(split)])
    summary={'raw_records':len(retained)+len(excluded),'retained':len(retained),'excluded':len(excluded),
             'retained_classes':dict(Counter(retained.mapped_sentiment)),
             'exclusion_primary_reasons':dict(Counter(excluded.exclusion_reason)),
             'verified_against_supplied_processed_file':True,'processed_files_rebuilt':write}
    save_json('reports/data_processing/goemotions_mapping_validation.json',summary)
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true')
    run(p.parse_args().write)
