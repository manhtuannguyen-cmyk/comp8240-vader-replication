"""Shared estimands. Labels are nominal; numeric score analyses require explicit scales."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import classification_report, cohen_kappa_score, confusion_matrix

from src.common import LABELS


def vader_polarity(scores):
    scores = np.asarray(scores, dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError('Nonfinite VADER scores')
    return np.where(scores >= .05, 'positive', np.where(scores <= -.05, 'negative', 'neutral'))


def human_polarity(scores):
    scores = np.asarray(scores, dtype=float)
    if not np.isfinite(scores).all():
        raise ValueError('Missing human intensity: never replace it with neutral')
    return np.where(scores > 0, 'positive', np.where(scores < 0, 'negative', 'neutral'))


def encode(labels):
    labels = np.asarray(labels)
    if not set(labels) <= set(LABELS):
        raise ValueError('Unexpected sentiment label')
    return np.array([LABELS.index(v) for v in labels], dtype=np.int64)


def ccc(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denominator = np.var(a) + np.var(b) + (a.mean()-b.mean())**2
    return float(2*np.mean((a-a.mean())*(b-b.mean())) / denominator) if denominator else np.nan


def evaluate(gold, pred, human_score=None, system_score=None):
    gold, pred = np.asarray(gold), np.asarray(pred)
    if len(gold) != len(pred) or not len(gold):
        raise ValueError('Evaluation requires nonempty aligned labels')
    encode(gold); encode(pred)
    report = classification_report(gold, pred, labels=LABELS, output_dict=True, zero_division=0)
    result = {'n': len(gold), 'accuracy': float(np.mean(gold == pred)),
              'macro_precision': report['macro avg']['precision'], 'macro_recall': report['macro avg']['recall'],
              'macro_f1': report['macro avg']['f1-score'], 'weighted_f1': report['weighted avg']['f1-score'],
              'cohen_kappa': float(cohen_kappa_score(gold, pred, labels=LABELS)) if len(set(gold)|set(pred))>1 else np.nan,
              'confusion_matrix': confusion_matrix(gold, pred, labels=LABELS).tolist(),
              'per_class': {k: report[k] for k in LABELS}}
    if human_score is not None:
        a, b = np.asarray(human_score, dtype=float), np.asarray(system_score, dtype=float)
        if len(a) != len(gold) or len(b) != len(gold) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Missing, nonfinite or misaligned intensity scores')
        variable = len(a)>1 and np.ptp(a)>0 and np.ptp(b)>0
        result.update(pearson_r=float(pearsonr(a,b).statistic) if variable else np.nan,
                      spearman_rho=float(spearmanr(a,b).statistic) if variable else np.nan,
                      mae=float(np.mean(abs(a-b))), rmse=float(np.sqrt(np.mean((a-b)**2))), ccc=ccc(a,b))
    return result


def scalar_metrics(metrics):
    return {k:v for k,v in metrics.items() if not isinstance(v,(list,dict))}


def fast_class(a, b):
    cm = np.bincount(3*a+b, minlength=9).reshape(3,3).astype(float)
    rows, cols = cm.sum(1), cm.sum(0)
    f1 = np.divide(2*np.diag(cm),rows+cols,out=np.zeros(3),where=rows+cols>0)
    accuracy = np.trace(cm)/cm.sum()
    chance = rows@cols/cm.sum()**2
    return float(accuracy), float(f1.mean()), float((accuracy-chance)/(1-chance)) if chance<1 else np.nan


def bootstrap_indices(n, groups=None, repetitions=2000, seed=8240):
    rng = np.random.default_rng(seed)
    pools = [np.arange(n)] if groups is None else [np.flatnonzero(np.asarray(groups)==g) for g in pd.unique(groups)]
    return np.concatenate([rng.choice(pool, size=(repetitions,len(pool)), replace=True) for pool in pools],axis=1)


def interval(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return (float(np.quantile(finite,.025)),float(np.quantile(finite,.975)),int(len(values)-len(finite))) if len(finite) else (np.nan,np.nan,len(values))


def bootstrap(gold, pred, indices, human_score=None, system_score=None):
    gold, pred = encode(gold), encode(pred)
    rows = []
    columns = ['accuracy','macro_f1','cohen_kappa']
    if human_score is not None:
        a,b = np.asarray(human_score,dtype=float),np.asarray(system_score,dtype=float)
        columns += ['pearson_r','ccc','mae']
    for ix in indices:
        row = list(fast_class(gold[ix],pred[ix]))
        if human_score is not None:
            aa,bb = a[ix],b[ix]
            row += [float(np.corrcoef(aa,bb)[0,1]) if np.ptp(aa)>0 and np.ptp(bb)>0 else np.nan,
                    ccc(aa,bb),float(np.mean(abs(aa-bb)))]
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def attach_intervals(point, draws):
    point = point.copy()
    for metric in draws:
        lo,hi,bad = interval(draws[metric])
        point.update({metric+'_ci_low':lo,metric+'_ci_high':hi,metric+'_degenerate_draws':bad})
    return point
