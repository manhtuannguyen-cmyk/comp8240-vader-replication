"""Reproduce all offline experiments. No collection or paid model calls are made.

Without private YouTube inputs, reproduce original corpora and GoEmotions and
report the missing private stream explicitly. --public-only chooses that scope.
"""
from __future__ import annotations
import argparse
import itertools
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from statsmodels.stats.multitest import multipletests
from src.common import ROOT, LABELS, SYSTEMS, read_csv, save_csv, save_json, save_latex, environment, sha, check_unique
from src.evaluation.metrics import evaluate, scalar_metrics, vader_polarity, bootstrap_indices, bootstrap, interval, attach_intervals
from src.replication.models import analyzers
from src.replication.run_replication import run as replicate
from src.annotation.agreement import run as human_agreement
from src.llm_judge.parse_responses import load_predictions


def goemotions(repetitions):
    frame=read_csv('data/goemotions/processed/all.csv',dtype={'id':str})
    check_unique(frame,'id')
    rows=[];details={}
    for system,scorer in analyzers().items():
        frame[system+'_score']=[scorer(t)['compound'] for t in frame.text_original]
        frame[system+'_label']=vader_polarity(frame[system+'_score'])
    # The complete retained cohort is the primary extension estimate. Official
    # split-level results remain available as descriptive diagnostics.
    for split in ['all','train','validation','test']:
        sub=frame if split=='all' else frame[frame.original_split.eq(split)]
        ix=bootstrap_indices(len(sub),repetitions=repetitions) if split=='all' else None
        for system in SYSTEMS[:2]:
            m=evaluate(sub.mapped_sentiment,sub[system+'_label'])
            if split=='all':m=attach_intervals(m,bootstrap(sub.mapped_sentiment,sub[system+'_label'],ix))
            rows.append({'split':split,'system':system,**scalar_metrics(m)})
            details[split+' / '+system]=m
    save_csv('reports/goemotions/predictions.csv',frame.drop(columns='text_original'))
    save_csv('reports/goemotions/metrics.csv',pd.DataFrame(rows));save_json('reports/goemotions/metrics.json',details)
    print('GoEmotions: 45,258 retained records are the primary cohort; split results are descriptive; no continuous target invented.')
    return pd.DataFrame(rows)


def youtube(repetitions):
    frame,hh=human_agreement(repetitions)
    for system,scorer in analyzers().items():
        frame[system+'_score']=[scorer(t)['compound'] for t in frame.comment_text_original]
        frame[system+'_label']=vader_polarity(frame[system+'_score'])
    for system in SYSTEMS[2:]:
        pred=load_predictions(ROOT/f'data/youtube/llm/predictions/{system.lower()}.csv',frame.sample_id)
        pred=pred[['sample_id','sentiment_score','sentiment_label','confidence','uncertain']].rename(columns={
            'sentiment_score':system+'_raw','sentiment_label':system+'_label','confidence':system+'_confidence','uncertain':system+'_uncertain'})
        frame=frame.merge(pred,on='sample_id',validate='one_to_one')
        frame[system+'_score']=frame[system+'_raw']/4
    ix=bootstrap_indices(len(frame),frame.video_id,repetitions=repetitions)
    rows=[];details={};draws={};per_class=[];individual=[];domain=[]
    for system in SYSTEMS:
        m=evaluate(frame.gold_label,frame[system+'_label'],frame.human_mean_intensity,frame[system+'_score'])
        draws[system]=bootstrap(frame.gold_label,frame[system+'_label'],ix,frame.human_mean_intensity,frame[system+'_score'])
        m=attach_intervals(m,draws[system]);details[system]=m
        rows.append({'system':system,'reference':frame.gold_label_source.iloc[0],**scalar_metrics(m)})
        per_class.extend({'system':system,'class':label,**values} for label,values in m['per_class'].items())
        for n in [1,2]:
            m_ind=evaluate(frame[f'human_{n}_label'],frame[system+'_label'],frame[f'human_{n}_raw']/4,frame[system+'_score'])
            d=bootstrap(frame[f'human_{n}_label'],frame[system+'_label'],ix)
            individual.append(attach_intervals({'system':system,'reference':f'Human {n}',**scalar_metrics(m_ind)},d))
    for category,sub in frame.groupby('video_category',sort=True):
        indices=bootstrap_indices(len(sub),repetitions=repetitions)
        for system in SYSTEMS:
            m=evaluate(sub.gold_label,sub[system+'_label'],sub.human_mean_intensity,sub[system+'_score'])
            d=bootstrap(sub.gold_label,sub[system+'_label'],indices)
            domain.append(attach_intervals({'category':category,'system':system,**scalar_metrics(m)},d))
    pairs=[]
    primary=['VADER 2014','ChatGPT','Claude','Gemini']
    for left,right in itertools.combinations(primary,2):
        lc=frame[left+'_label'].eq(frame.gold_label);rc=frame[right+'_label'].eq(frame.gold_label)
        left_only=int((lc&~rc).sum());right_only=int((~lc&rc).sum())
        p=float(binomtest(left_only,left_only+right_only,.5).pvalue) if left_only+right_only else 1.
        lo,hi,bad=interval(draws[left].macro_f1-draws[right].macro_f1)
        pairs.append({'left':left,'right':right,'n':len(frame),'delta_accuracy':float(lc.mean()-rc.mean()),
            'delta_macro_f1':details[left]['macro_f1']-details[right]['macro_f1'],
            'ci_low':lo,'ci_high':hi,'left_only_correct':left_only,'right_only_correct':right_only,
            'mcnemar_exact_p':p,'degenerate_draws':bad})
    paired=pd.DataFrame(pairs);paired['mcnemar_holm_p']=multipletests(paired.mcnemar_exact_p,method='holm')[1]
    evaluators={'Human 1':frame.human_1_label,'Human 2':frame.human_2_label,
                **{s:frame[s+'_label'] for s in SYSTEMS}}
    agreements=[]
    for left,right in itertools.combinations(evaluators,2):
        m=evaluate(evaluators[left],evaluators[right])
        agreements.append({'left':left,'right':right,'n':len(frame),'exact_agreement':m['accuracy'],
                           'cohen_kappa':m['cohen_kappa'],'macro_f1_directional':m['macro_f1']})
    audit=frame[['sample_id','video_category','human_1_label','human_2_label','gold_label']+[s+'_label' for s in SYSTEMS]].copy()
    audit['humans_disagree']=audit.human_1_label.ne(audit.human_2_label)
    for system in SYSTEMS:audit[system+'_correct']=audit[system+'_label'].eq(audit.gold_label)
    primary_columns=[s+'_label' for s in primary]
    audit['all_primary_models_agree_against_reference']=audit[primary_columns].nunique(axis=1).eq(1)&audit['VADER 2014_label'].ne(audit.gold_label)
    patterns=[]
    for llm in SYSTEMS[2:]:
        v,l=audit['VADER 2014_correct'],audit[llm+'_correct']
        for name,mask in [('VADER wrong; LLM correct',~v&l),('VADER correct; LLM wrong',v&~l),('both wrong',~v&~l)]:
            patterns.append({'LLM':llm,'pattern':name,'count':int(mask.sum())})
    save_csv('reports/youtube/error_patterns.csv',pd.DataFrame(patterns))
    save_csv('reports/youtube/error_audit.csv',audit)
    save_csv('reports/youtube/aligned_predictions.csv',frame.drop(columns='comment_text_original'))
    save_csv('reports/youtube/model_metrics.csv',pd.DataFrame(rows))
    save_json('reports/youtube/model_metrics.json',details)
    save_csv('reports/youtube/per_class_metrics.csv',pd.DataFrame(per_class))
    save_csv('reports/youtube/individual_human_comparison.csv',pd.DataFrame(individual))
    save_csv('reports/youtube/domain_metrics.csv',pd.DataFrame(domain))
    save_csv('reports/youtube/paired_comparisons.csv',paired)
    save_csv('reports/youtube/pairwise_agreement.csv',pd.DataFrame(agreements))
    sensitivity=[]
    consensus=frame[frame.human_1_label.eq(frame.human_2_label)]
    for system in SYSTEMS:
        for reference,sub,gold in [('mean full cohort',frame,frame.human_mean_label),('human polarity agreement only',consensus,consensus.human_1_label)]:
            sensitivity.append({'system':system,'reference':reference,**scalar_metrics(evaluate(gold,sub[system+'_label']))})
    save_csv('reports/youtube/reference_sensitivity.csv',pd.DataFrame(sensitivity))
    print(pd.DataFrame(rows)[['system','n','accuracy','macro_f1','pearson_r']].round(4).to_string(index=False))
    return pd.DataFrame(rows)


def run(public_only=False,repetitions=2000,figures=True):
    from src.data_processing.map_goemotions import run as verify_mapping
    from src.tools.validate_inputs import run as validate_inputs
    validate_inputs(public_only=public_only)
    verify_mapping()
    original=replicate(repetitions)
    go=goemotions(repetitions)
    sample_path=ROOT/'data/youtube/sampled/youtube_final_200.csv'
    include_youtube=not public_only and sample_path.is_file()
    if include_youtube:
        from src.data_processing.sample_youtube import run as verify_sample
        verify_sample()
        youtube_results=youtube(repetitions)
    else:
        youtube_results=None
        print('YouTube / human / LLM stream NOT RUN: public-only scope or private inputs missing. See data/youtube/README.md.')
    cross=original[['dataset','system','n','accuracy','macro_f1','weighted_f1','pearson_r','macro_f1_ci_low','macro_f1_ci_high']].copy()
    go_all=go[go.split.eq('all')].copy();go_all['dataset']='GoEmotions (all retained)';go_all['pearson_r']=np.nan
    cross=pd.concat([cross,go_all.reindex(columns=cross.columns)],ignore_index=True)
    public_cross=cross.copy()
    save_csv('reports/public/cross_dataset_metrics.csv',public_cross)
    if youtube_results is not None:
        sub=youtube_results[youtube_results.system.isin(SYSTEMS[:2])].copy();sub['dataset']='YouTube'
        cross=pd.concat([cross,sub.reindex(columns=cross.columns)],ignore_index=True)
        save_csv('reports/youtube/cross_dataset_metrics.csv',cross)
        table=youtube_results[['system','n','accuracy','macro_f1','weighted_f1','cohen_kappa','pearson_r']]
        save_latex('reports/youtube/model_results.tex',table)
    save_latex('reports/public/cross_dataset_results.tex',public_cross)
    scope='full private snapshot' if include_youtube else 'original corpora and GoEmotions only'
    location='reports/youtube/run_manifest.json' if include_youtube else 'reports/public/run_manifest.json'
    save_json(location,{'scope':scope,'bootstrap_repetitions':repetitions,'seed':8240,'environment':environment(),
                        'main_script_sha256':sha(Path(__file__)),'youtube_evaluated':include_youtube,
                        'interpretation':'pointwise percentile intervals; fixed-corpus conditional inference; paired McNemar family Holm adjusted'})
    if figures:
        from src.evaluation.generate_figures import run as plot
        plot(include_youtube=include_youtube)
    print('Offline analysis complete:',scope)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-only',action='store_true')
    p.add_argument('--bootstrap',type=int,default=2000);p.add_argument('--no-figures',action='store_true')
    a=p.parse_args();run(a.public_only,a.bootstrap,not a.no_figures)
