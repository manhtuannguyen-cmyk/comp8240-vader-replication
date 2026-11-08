"""Generate named PNG (300 dpi) and vector SVG figures from recomputed metrics."""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'comp8240-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from src.common import ROOT, LABELS, SYSTEMS, read_csv, require_youtube

COLORS=dict(zip(SYSTEMS,['#40576d','#7b8790','#2b7d78','#af7139','#835f93']))


def confusion(ax,cm,title,normalise=False):
    cm=np.asarray(cm)
    if normalise:cm=np.divide(cm,cm.sum(1,keepdims=True),out=np.zeros_like(cm,dtype=float),where=cm.sum(1,keepdims=True)>0)
    sns.heatmap(cm,annot=True,fmt='.2f' if normalise else 'd',cmap='Blues',cbar=False,
                xticklabels=LABELS,yticklabels=LABELS,ax=ax,vmin=0,vmax=1 if normalise else None)
    ax.set(title=title,xlabel='Prediction / comparison polarity',ylabel='Reference polarity');ax.tick_params(axis='y',rotation=0)


def run(include_youtube=True):
    sns.set_theme(style='whitegrid',font_scale=.92)
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False})
    original=read_csv('reports/replication/metrics.csv')
    public_cross=read_csv('reports/public/cross_dataset_metrics.csv')
    captions=[]
    def save(fig,stem,caption,private=True):
        folder=ROOT/('reports/youtube/figures' if private else 'reports/public/figures')
        folder.mkdir(parents=True,exist_ok=True)
        fig.tight_layout()
        for ext in ['png','svg']:fig.savefig(folder/f'{stem}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig);captions.append((folder,stem,caption))
    fig,ax=plt.subplots(figsize=(8.5,4))
    names=['Tweets','Movie','Amazon','NYT'];xx=np.arange(4)
    for shift,system in [(-.22,'VADER 2014'),(0,'VADER 3.3.2')]:
        d=original[original.system.eq(system)].set_index('dataset').loc[names]
        ax.bar(xx+shift,d.pearson_r,width=.22,color=COLORS[system],label=system)
    ax.bar(xx+.22,d.paper_r,width=.22,color='#a6aaa8',label='Published Pearson r')
    ax.set(xticks=xx,xticklabels=names,xlabel='Original evaluation corpus',ylabel='Pearson r',ylim=(0,1),title='Original VADER intensity replication')
    ax.legend(fontsize=8)
    save(fig,'figure_01_original_vader_replication_correlations','Original text-bearing release and Table 4. Partial replication; paper overall F1 is not plotted as accuracy.',private=False)
    if not include_youtube:
        fig,ax=plt.subplots(figsize=(8,4))
        for shift,system in [(-.1,'VADER 2014'),(.1,'VADER 3.3.2')]:
            d=public_cross[public_cross.system.eq(system)]
            ax.errorbar(np.arange(len(d))+shift,d.macro_f1,yerr=np.vstack([d.macro_f1-d.macro_f1_ci_low,d.macro_f1_ci_high-d.macro_f1]),fmt='o',capsize=3,label=system,color=COLORS[system])
        ax.set(xticks=np.arange(len(d)),xticklabels=d.dataset,xlabel='Dataset (differing references)',ylabel='Macro F1',ylim=(0,1),title='Public-data VADER generalisation');ax.legend(fontsize=8)
        save(fig,'public_cross_dataset_macro_f1','Pointwise 95% item-bootstrap CIs; original corpus reference labels and mapped GoEmotions targets differ.',private=False)
    else:
        require_youtube()
        frame=read_csv('reports/youtube/aligned_predictions.csv')
        master=read_csv('reports/youtube/model_metrics.csv')
        details=json.loads((ROOT/'reports/youtube/model_metrics.json').read_text())
        human=json.loads((ROOT/'reports/youtube/human_agreement.json').read_text())
        # Copy the identical public original figure into the complete private suite.
        private_folder=ROOT/'reports/youtube/figures';private_folder.mkdir(parents=True,exist_ok=True)
        import shutil
        for ext in ['png','svg']:
            shutil.copy2(ROOT/f'reports/public/figures/figure_01_original_vader_replication_correlations.{ext}',private_folder/f'figure_01_original_vader_replication_correlations.{ext}')
        captions.append((private_folder,'figure_01_original_vader_replication_correlations',
                         'Original text-bearing release and Table 4. Historical and modern implementations are distinct; partial replication.'))
        fig,axes=plt.subplots(1,2,figsize=(10,4.2))
        confusion(axes[0],human['confusion_matrix'],'Human polarity agreement, n=200')
        axes[0].set(xlabel='Annotator 2 polarity',ylabel='Annotator 1 polarity')
        axes[1].scatter(frame.human_1_raw,frame.human_2_raw,alpha=.35,color='#40576d')
        axes[1].plot([-4,4],[-4,4],linestyle='--',color='gray')
        axes[1].set(xlabel='Annotator 1 (−4 to +4)',ylabel='Annotator 2 (−4 to +4)',title='Human ordinal intensity agreement')
        save(fig,'figure_02_human_annotation_agreement','Independent-role saved exports; overlap masks point frequency. Correlation is not agreement.')
        fig,axes=plt.subplots(1,2,figsize=(11,4.5))
        for ax,metric in zip(axes,['accuracy','macro_f1']):
            d=master.set_index('system').loc[SYSTEMS];x=np.arange(5)
            ax.bar(x,d[metric],color=[COLORS[s] for s in SYSTEMS])
            ax.errorbar(x,d[metric],yerr=np.vstack([d[metric]-d[metric+'_ci_low'],d[metric+'_ci_high']-d[metric]]),fmt='none',ecolor='black',capsize=3)
            ax.set(xticks=x,xticklabels=SYSTEMS,xlabel='System',ylabel=metric.replace('_',' ').title(),ylim=(0,1),title=metric.replace('_',' ').title()+' (n=200)');ax.tick_params(axis='x',rotation=30)
        save(fig,'figure_03_youtube_model_accuracy_and_macro_f1','Common human reference; pointwise 95% video-stratified item-bootstrap CIs. No population superiority claim.')
        fig,axes=plt.subplots(2,3,figsize=(12,7.5))
        for ax,system in zip(axes.flat,SYSTEMS):confusion(ax,details[system]['confusion_matrix'],system)
        axes.flat[-1].axis('off')
        save(fig,'figure_04_youtube_all_model_confusion_matrices','Five systems compared with the same human reference, counts; the reference is averaged unless actual adjudication is supplied.')
        fig,axes=plt.subplots(1,2,figsize=(9.5,4))
        confusion(axes[0],details['VADER 2014']['confusion_matrix'],'Historical VADER: counts')
        confusion(axes[1],details['VADER 2014']['confusion_matrix'],'Historical VADER: row proportions',True)
        save(fig,'figure_05_vader_2014_confusion_counts_and_proportions','Counts show prevalence; row proportions show class recall. Historical implementation, fixed ±0.05 predictions.')
        individual=read_csv('reports/youtube/individual_human_comparison.csv')
        fig,ax=plt.subplots(figsize=(8.5,4.2))
        for i,reference in enumerate(['Human 1','Human 2']):
            d=individual[individual.reference.eq(reference)].set_index('system').loc[SYSTEMS[2:]]
            ax.errorbar(np.arange(3)+(i-.5)*.12,d.cohen_kappa,yerr=np.vstack([d.cohen_kappa-d.cohen_kappa_ci_low,d.cohen_kappa_ci_high-d.cohen_kappa]),fmt='o',capsize=3,label=reference)
        ax.axhline(human['cohen_kappa'],color='gray',linestyle='--',label='Human–human κ (different estimand)')
        ax.set(xticks=range(3),xticklabels=SYSTEMS[2:],xlabel='LLM',ylabel='Cohen κ',title='LLM versus each independent human');ax.legend(fontsize=8)
        save(fig,'figure_06_llm_agreement_with_each_human','Pointwise conditional CIs; human–human line is not an equivalence threshold.')
        pairwise=read_csv('reports/youtube/pairwise_agreement.csv');names=['Human 1','Human 2']+SYSTEMS
        matrix=pd.DataFrame(np.eye(7),index=names,columns=names)
        for row in pairwise.itertuples():matrix.loc[row.left,row.right]=matrix.loc[row.right,row.left]=row.cohen_kappa
        fig,ax=plt.subplots(figsize=(8,6));sns.heatmap(matrix,annot=True,fmt='.2f',cmap='Blues',vmin=0,vmax=1,ax=ax)
        ax.set(title='Pairwise polarity Cohen κ, n=200',xlabel='Evaluator',ylabel='Evaluator')
        save(fig,'figure_07_pairwise_evaluator_kappa_heatmap','Pairwise agreements, not pooled human/machine reliability; inter-model agreement is not proof of truth.')
        dist={'Human mean':frame.human_mean_label,'Human 1':frame.human_1_label,'Human 2':frame.human_2_label,**{s:frame[s+'_label'] for s in SYSTEMS}}
        distribution=pd.DataFrame({k:v.value_counts().reindex(LABELS,fill_value=0) for k,v in dist.items()}).T
        fig,axes=plt.subplots(1,2,figsize=(11,4.5))
        (distribution.div(distribution.sum(axis=1),axis=0)*100).plot.bar(stacked=True,ax=axes[0],color=['#8d6a61','#b6bec4','#477e78'])
        axes[0].set(xlabel='Evaluator / reference',ylabel='Label share (%)',title='YouTube sentiment prevalence');axes[0].tick_params(axis='x',rotation=40)
        pd.DataFrame(details['VADER 2014']['per_class']).T[['precision','recall','f1-score']].plot.bar(ax=axes[1])
        axes[1].set(xlabel='Reference class',ylabel='Metric value',ylim=(0,1),title='Historical VADER per-class metrics');axes[1].tick_params(axis='x',rotation=0)
        save(fig,'figure_08_youtube_label_distribution_and_vader_per_class_metrics','Prevalence and class-specific performance on the common 200-comment cohort; observed distributions are not universal model bias.')
        datasets={}
        for name in ['tweets','movie','amazon','nyt']:datasets[name.title()]=read_csv(f'reports/replication/{name}_predictions.csv').gold_label
        go=read_csv('data/goemotions/processed/all.csv');datasets['GoEmotions (all retained)']=go.mapped_sentiment;datasets['YouTube']=frame.gold_label
        fig,axes=plt.subplots(1,2,figsize=(11,4.5))
        axes[0].barh(list(datasets),[len(v) for v in datasets.values()],color='#40576d')
        axes[0].set(xscale='log',xlabel='Evaluation records (log scale)',ylabel='Dataset',title='Evaluation sample sizes')
        distribution=pd.DataFrame({k:v.value_counts().reindex(LABELS,fill_value=0) for k,v in datasets.items()}).T
        (distribution.div(distribution.sum(axis=1),axis=0)*100).plot.bar(stacked=True,ax=axes[1],color=['#8d6a61','#b6bec4','#477e78'])
        axes[1].set(xlabel='Dataset',ylabel='Reference label share (%)',title='Reference class distributions');axes[1].tick_params(axis='x',rotation=35)
        save(fig,'figure_09_dataset_sizes_and_sentiment_distributions','Actual cohorts and declared reference rules; reference constructs differ across datasets.')
        cross=read_csv('reports/youtube/cross_dataset_metrics.csv')
        fig,ax=plt.subplots(figsize=(9,4.5))
        for shift,system in [(-.12,'VADER 2014'),(.12,'VADER 3.3.2')]:
            d=cross[cross.system.eq(system)]
            ax.errorbar(np.arange(len(d))+shift,d.macro_f1,yerr=np.vstack([d.macro_f1-d.macro_f1_ci_low,d.macro_f1_ci_high-d.macro_f1]),fmt='o',capsize=3,label=system,color=COLORS[system])
        ax.set(xticks=np.arange(len(d)),xticklabels=d.dataset,xlabel='Dataset (different reference provenance)',ylabel='Macro F1',ylim=(0,1),title='VADER cross-dataset generalisation');ax.legend(fontsize=8)
        save(fig,'figure_10_vader_cross_dataset_macro_f1','Pointwise conditional CIs; performance gaps do not isolate temporal or domain drift.')
        domains=read_csv('reports/youtube/domain_metrics.csv');names=list(domains.category.unique())
        fig,ax=plt.subplots(figsize=(10,4.5))
        for i,system in enumerate(['VADER 2014']+SYSTEMS[2:]):
            d=domains[domains.system.eq(system)].set_index('category').loc[names]
            ax.errorbar(np.arange(4)+(i-1.5)*.12,d.macro_f1,yerr=np.vstack([d.macro_f1-d.macro_f1_ci_low,d.macro_f1_ci_high-d.macro_f1]),fmt='o',capsize=3,label=system,color=COLORS[system])
        ax.set(xticks=range(4),xticklabels=[s.replace(' and ',' &\n') for s in names],xlabel='Source-video category (one video each)',ylabel='Macro F1',ylim=(0,1),title='Within-video performance, n=50 per video');ax.legend(fontsize=8)
        save(fig,'figure_11_youtube_per_video_model_performance','Within-video item-bootstrap CIs. Genre, creator and audience are confounded; no population cluster inference.')
        pairs=read_csv('reports/youtube/paired_comparisons.csv').iloc[::-1].reset_index(drop=True)
        fig,ax=plt.subplots(figsize=(9,4.5))
        ax.errorbar(pairs.delta_macro_f1,np.arange(len(pairs)),xerr=np.vstack([pairs.delta_macro_f1-pairs.ci_low,pairs.ci_high-pairs.delta_macro_f1]),fmt='o',capsize=3,color='#40576d')
        ax.axvline(0,color='gray',linestyle='--')
        ax.set(yticks=np.arange(len(pairs)),yticklabels=pairs.left+' minus '+pairs.right,xlabel='Paired macro-F1 difference (left − right)',ylabel='Matched comparison',title='Pointwise conditional paired 95% CIs')
        save(fig,'figure_12_paired_model_macro_f1_differences','Matched video-stratified resamples; intervals are pointwise, not simultaneous. McNemar p-values are separately Holm adjusted.')
        h=frame.human_mean_intensity.to_numpy();v=frame['VADER 2014_score'].to_numpy()
        fig,axes=plt.subplots(1,2,figsize=(11,4.5))
        axes[0].scatter(h,v,alpha=.4,s=22,color=COLORS['VADER 2014']);axes[0].plot([-1,1],[-1,1],color='gray',linestyle='--')
        axes[0].set(xlabel='Human mean / 4 (−1 to +1)',ylabel='VADER compound (−1 to +1)',title='Historical VADER versus human intensity')
        axes[1].scatter((h+v)/2,v-h,alpha=.4,s=22,color=COLORS['VADER 2014']);axes[1].axhline(0,color='gray',linestyle='--')
        axes[1].axhline(np.mean(v-h),color='#af7139',label='Observed mean difference');axes[1].legend(fontsize=8)
        axes[1].set(xlabel='Mean of rescaled human and VADER scores',ylabel='VADER minus rescaled human',title='Descriptive intensity differences')
        save(fig,'figure_13_vader_human_intensity_and_residuals','Linear human rescaling does not make VADER compound a calibrated interval estimate. Correlation is not concordance.')
        # Causal error categories are only plotted from genuinely verified coding.
        path=ROOT/'data/youtube/annotations/error_coding.csv'
        if path.is_file():
            coding=read_csv(path,dtype=str)
            required={'sample_id','error_tags','coder_id','verification_status'}
            if not required<=set(coding):raise ValueError('Missing error-coding provenance columns')
            if not set(coding.sample_id)<=set(frame.sample_id):raise ValueError('Unknown error-coded IDs')
            verified=coding[coding.verification_status.eq('human_verified')&coding.coder_id.str.strip().ne('')]
            counts=verified.assign(tag=verified.error_tags.str.split(';')).explode('tag').query("tag!=''").tag.value_counts()
            if len(counts):
                fig,ax=plt.subplots(figsize=(8,4));counts.plot.barh(ax=ax,color='#40576d')
                ax.set(xlabel='Human-verified coded cases (multi-tag)',ylabel='Error tag',title='Verified error-type frequencies')
                save(fig,'verified_error_categories','Multi-tag human-verified codes; frequencies are not causal effects.')
        else:print('No verified error-coding records: sarcasm/slang/emoji causal-frequency chart not generated.')
    print('Figures generated:',len(captions))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-only',action='store_true')
    a=p.parse_args();run(include_youtube=not a.public_only and (ROOT/'reports/youtube/model_metrics.csv').is_file())
