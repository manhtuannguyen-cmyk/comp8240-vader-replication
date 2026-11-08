"""Run both VADER implementations on all four original text-bearing corpora."""
from __future__ import annotations
import argparse
import ast
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
from src.common import ROOT, check_unique, save_csv, save_json, environment
from src.evaluation.metrics import evaluate, scalar_metrics, vader_polarity, human_polarity, bootstrap, bootstrap_indices, attach_intervals
from src.replication.models import analyzers

FILES = {'Tweets':'tweets_GroundTruth.txt','Movie':'movieReviewSnippets_GroundTruth.txt',
         'Amazon':'amazonReviewSnippets_GroundTruth.txt','NYT':'nytEditorialSnippets_GroundTruth.txt'}
PAPER = {'Tweets':(4200,.881,.99,.94,.96),'Movie':(10605,.451,.70,.55,.61),
         'Amazon':(3708,.565,.70,.55,.63),'NYT':(5190,.492,.69,.49,.55)}


def load_original(name):
    rows = []
    with (ROOT/'data/original_vader'/FILES[name]).open(encoding='utf-8',newline='') as f:
        for line in f:
            sid,score,text = line.rstrip('\r\n').split('\t',2)
            rows.append((sid,float(score),text))
    frame = pd.DataFrame(rows,columns=['sample_id','human_raw','original_text'])
    check_unique(frame)
    if len(frame)!=PAPER[name][0] or not frame.human_raw.between(-4,4).all() or frame.original_text.str.strip().eq('').any():
        raise ValueError('Original corpus count/scale/text validation failed: '+name)
    frame['human_normalized'] = frame.human_raw/4
    frame['gold_label'] = vader_polarity(frame.human_normalized)
    return frame


def run(repetitions=2000):
    results, rows, sensitivities, audits = {}, [], [], []
    scorers = analyzers()
    for name in FILES:
        frame = load_original(name)
        indices = bootstrap_indices(len(frame),repetitions=repetitions)
        for system,scorer in scorers.items():
            frame[system+'_score'] = [scorer(t)['compound'] for t in frame.original_text]
            frame[system+'_label'] = vader_polarity(frame[system+'_score'])
            m = evaluate(frame.gold_label,frame[system+'_label'],frame.human_normalized,frame[system+'_score'])
            draws = bootstrap(frame.gold_label,frame[system+'_label'],indices,frame.human_normalized,frame[system+'_score'])
            m = attach_intervals(m,draws)
            results[name+' / '+system] = m
            paper = PAPER[name]
            rows.append({'dataset':name,'system':system,**scalar_metrics(m),'paper_r':paper[1],
                         'paper_overall_precision':paper[2],'paper_overall_recall':paper[3],'paper_overall_f1':paper[4],
                         'delta_r':m['pearson_r']-paper[1]})
            for rule,labels in [('normalized +/-0.05 primary',frame.gold_label),('raw +/-0.05 diagnostic',vader_polarity(frame.human_raw)),('human sign diagnostic',human_polarity(frame.human_raw))]:
                alt = evaluate(labels,frame[system+'_label'])
                sensitivities.append({'dataset':name,'system':system,'human_rule':rule,
                                      'neutral_count':int(np.sum(np.asarray(labels)=='neutral')),**scalar_metrics(alt)})
        save_csv(f'reports/replication/{name.lower()}_predictions.csv',frame.drop(columns='original_text'))
        rater_path = ROOT/'data/original_vader'/FILES[name].replace('GroundTruth','anonDataRatings')
        rater_rows = []
        with rater_path.open(encoding='utf-8',newline='') as f:
            for r in csv.reader(f,delimiter='\t'):
                values=ast.literal_eval(r[3]);rater_rows.append((r[0],float(r[1]),float(np.mean(values)),len(values)))
        rater=pd.DataFrame(rater_rows,columns=['sample_id','stored_mean','list_mean','ratings'])
        check_unique(rater)
        joined=frame[['sample_id','human_raw']].merge(rater,on='sample_id',validate='one_to_one')
        audits.append({'dataset':name,'text_rows':len(frame),'rater_rows':len(rater),'matched_ids':len(joined),
                       'ground_truth_mean_mismatches':int((abs(joined.human_raw-joined.stored_mean)>1e-6).sum()),
                       'list_mean_mismatches':int((abs(rater.list_mean-rater.stored_mean)>1e-6).sum()),
                       'minimum_raters':int(rater.ratings.min()),'maximum_raters':int(rater.ratings.max())})
        print(f'{name}: {len(frame):,} scored by both implementations')
    save_json('reports/replication/metrics.json',results)
    save_json('reports/replication/environment.json',environment())
    save_csv('reports/replication/metrics.csv',pd.DataFrame(rows))
    save_csv('reports/replication/threshold_sensitivity.csv',pd.DataFrame(sensitivities))
    save_csv('reports/replication/rater_artifact_audit.csv',pd.DataFrame(audits))
    return pd.DataFrame(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap',type=int,default=2000)
    args=parser.parse_args()
    run(args.bootstrap)
