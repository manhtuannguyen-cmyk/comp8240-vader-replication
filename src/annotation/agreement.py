"""Independent human agreement and averaged reference; never invent adjudication."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score
from src.common import ROOT, read_csv, save_csv, save_json, check_unique, require_youtube
from src.evaluation.metrics import evaluate, human_polarity, bootstrap_indices, bootstrap, attach_intervals


def aligned_annotations():
    require_youtube()
    sample=read_csv('data/youtube/sampled/youtube_final_200.csv',dtype={'sample_id':str})
    check_unique(sample)
    for n in [1,2]:
        annotations=read_csv(f'data/youtube/annotations/annotator_{n}_annotations.csv',dtype=str)
        check_unique(annotations)
        if set(annotations.sample_id)!=set(sample.sample_id):raise ValueError('Annotation IDs do not match sample')
        indexed=annotations.set_index('sample_id').loc[sample.sample_id]
        if not np.array_equal(indexed.comment_text_original.to_numpy(),sample.comment_text_original.to_numpy()):
            raise ValueError('Annotation text differs from current sample; no retired-rating transfer permitted')
        scores=pd.to_numeric(indexed.intensity_score,errors='coerce')
        if not indexed.annotation_status.eq('completed').all() or scores.isna().any() or not scores.between(-4,4).all() or not scores.eq(scores.round()).all():
            raise ValueError('Incomplete or invalid annotation; missing is not zero')
        sample[f'human_{n}_raw']=scores.to_numpy()
        sample[f'human_{n}_label']=human_polarity(scores)
    combined=read_csv('data/youtube/annotations/combined_human_annotations.csv',dtype=str).set_index('sample_id')
    if not combined.index.is_unique or set(combined.index)!=set(sample.sample_id):raise ValueError('Combined annotation identity mismatch')
    for n in [1,2]:
        if not np.array_equal(pd.to_numeric(combined.loc[sample.sample_id,f'annotator_{n}_intensity']).to_numpy(),sample[f'human_{n}_raw'].to_numpy()):
            raise ValueError('Combined export differs from individual annotations')
    sample['human_mean_raw']=sample[['human_1_raw','human_2_raw']].mean(axis=1)
    sample['human_mean_intensity']=sample.human_mean_raw/4
    sample['human_mean_label']=human_polarity(sample.human_mean_raw)
    sample['gold_label']=sample.human_mean_label
    sample['gold_label_source']='averaged independent-role intensity; sign polarity; not adjudicated'
    path=ROOT/'data/youtube/annotations/adjudicated_labels.csv'
    if path.is_file():
        actual=read_csv(path,dtype=str);check_unique(actual)
        required={'sample_id','human_gold_label','adjudicator_id','adjudication_timestamp','adjudication_status'}
        if not required<=set(actual.columns) or set(actual.sample_id)!=set(sample.sample_id):
            raise ValueError('Actual adjudication must cover the whole cohort with provenance; partial records cannot silently mix references')
        if not actual.human_gold_label.isin(['negative','neutral','positive']).all() or not actual.adjudication_status.eq('adjudicated').all():
            raise ValueError('Invalid adjudication labels or status')
        if actual.adjudicator_id.str.strip().eq('').any() or pd.to_datetime(actual.adjudication_timestamp,errors='coerce',utc=True).isna().any():
            raise ValueError('Adjudicator identity and actual timestamp required')
        sample['gold_label']=actual.set_index('sample_id').loc[sample.sample_id,'human_gold_label'].to_numpy()
        sample['gold_label_source']='actual supplied adjudicated labels; structural provenance checked'
    return sample


def weighted_kappa(a,b):
    cm=np.bincount(9*(a.astype(int)+4)+(b.astype(int)+4),minlength=81).reshape(9,9)
    distances=(np.arange(9)[:,None]-np.arange(9)[None,:])**2
    expected=np.outer(cm.sum(1),cm.sum(0))/cm.sum()
    denominator=(expected*distances).sum()
    return float(1-(cm*distances).sum()/denominator) if denominator else np.nan


def run(repetitions=2000):
    frame=aligned_annotations()
    a,b=frame.human_1_raw.to_numpy(),frame.human_2_raw.to_numpy()
    m=evaluate(frame.human_1_label,frame.human_2_label,a/4,b/4)
    m.update(quadratic_weighted_kappa=float(cohen_kappa_score(a,b,labels=list(range(-4,5)),weights='quadratic')),
             linear_weighted_kappa=float(cohen_kappa_score(a,b,labels=list(range(-4,5)),weights='linear')),
             exact_intensity_agreement=float(np.mean(a==b)),raw_intensity_mae=float(np.mean(abs(a-b))),
             polarity_disagreements=int(np.sum(frame.human_1_label!=frame.human_2_label)))
    ix=bootstrap_indices(len(frame),frame.video_id,repetitions=repetitions)
    draws=bootstrap(frame.human_1_label,frame.human_2_label,ix,a/4,b/4)
    draws['quadratic_weighted_kappa']=[weighted_kappa(a[i],b[i]) for i in ix]
    m=attach_intervals(m,draws)
    save_json('reports/youtube/human_agreement.json',m)
    # No automatic adjudicated file is created. This filename explicitly names the mean reference.
    save_csv('data/youtube/generated/human_mean_reference.csv',frame.drop(columns='comment_text_original'))
    audit=frame[['sample_id','video_category','human_1_raw','human_2_raw','human_1_label','human_2_label']].copy()
    audit['absolute_gap']=abs(audit.human_1_raw-audit.human_2_raw)
    audit['polarity_disagreement']=audit.human_1_label!=audit.human_2_label
    save_csv('reports/youtube/human_disagreements.csv',audit[audit.absolute_gap.gt(0)].sort_values('absolute_gap',ascending=False))
    print(f'Human agreement: {m["accuracy"]:.1%}; polarity kappa={m["cohen_kappa"]:.6f}; quadratic intensity kappa={m["quadratic_weighted_kappa"]:.6f}')
    return frame,m


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bootstrap',type=int,default=2000)
    run(p.parse_args().bootstrap)
