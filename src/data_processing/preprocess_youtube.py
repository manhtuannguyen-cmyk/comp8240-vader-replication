"""Verify the historical eligibility partitions with the reused language/privacy rules."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pandas as pd
import yaml
from src.common import ROOT, read_csv, require_youtube, save_csv, save_json
from src.data_processing.eligibility_rules import classify


def run(save=False):
    require_youtube()
    videos=yaml.safe_load((ROOT/'config/videos.yaml').read_text())['videos']
    ordinal=0;summary=[]
    for video in videos:
        raw=read_csv(f'data/youtube/raw/{video["folder"]}/comments_retrieved.csv',dtype=str)
        if not raw.comment_id.is_unique:raise ValueError('Repeated raw IDs require explicit identity review')
        records=[]
        for row in raw.to_dict('records'):
            ordinal+=1
            decision,reason,language=classify(row['comment_text_original'])
            status={'include':'retained','exclude':'excluded','review':'review_required'}[decision]
            records.append({'sample_id':f'YTC{ordinal:06d}','comment_id':row['comment_id'],'processing_status':status,
                            'exclusion_reason':reason if decision=='exclude' else '',
                            'review_reason':reason if decision=='review' else '', 'language_screen':language})
        calculated=pd.DataFrame(records)
        expected=pd.concat([
            read_csv(f'data/youtube/processed/{video["folder"]}/youtube_comments_cleaned.csv',dtype=str),
            read_csv(f'data/youtube/processed/{video["folder"]}/youtube_comments_review_required.csv',dtype=str),
            read_csv(f'data/youtube/excluded/{video["folder"]}/youtube_comments_excluded.csv',dtype=str)])
        if not expected.comment_id.is_unique:raise ValueError('Repeated IDs in saved partitions')
        fields=list(calculated.columns)
        a=calculated.sort_values('comment_id')[fields].reset_index(drop=True)
        b=expected.sort_values('comment_id')[fields].reset_index(drop=True)
        if not a.equals(b):raise ValueError('Eligibility decisions changed: '+video['folder']+'; inspect pinned langdetect/environment')
        if save:save_csv(f'data/youtube/reproduced/{video["folder"]}_eligibility.csv',calculated)
        summary.append({'video_folder':video['folder'],'raw':len(raw),**calculated.processing_status.value_counts().to_dict()})
    save_json('reports/youtube/eligibility_validation.json',summary)
    print(pd.DataFrame(summary).to_string(index=False))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--save',action='store_true')
    run(p.parse_args().save)
