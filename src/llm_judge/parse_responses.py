"""Parse and strictly validate saved CSV/JSON predictions or provider envelopes."""
from __future__ import annotations
import argparse
import json
import math
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pandas as pd
from src.common import ROOT, read_csv, save_csv, check_unique

FIELDS=['sample_id','sentiment_score','sentiment_label','confidence','uncertain','justification']


def response_text(payload):
    """Extract public output text only; never request hidden reasoning."""
    if isinstance(payload,dict) and 'output' in payload:
        return '\n'.join(part['text'] for item in payload['output'] if item.get('type')=='message'
                         for part in item.get('content',[]) if part.get('type')=='output_text')
    if isinstance(payload,dict) and 'content' in payload and isinstance(payload['content'],list):
        return '\n'.join(p['text'] for p in payload['content'] if p.get('type')=='text')
    if isinstance(payload,dict) and 'candidates' in payload:
        candidates=payload['candidates']
        return '\n'.join(p['text'] for p in candidates[0].get('content',{}).get('parts',[]) if 'text' in p) if candidates else ''
    raise ValueError('Unsupported provider envelope or missing public output text')


def parse_text(text):
    text=text.strip()
    if text.startswith('```'):
        match=re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```',text)
        if not match:raise ValueError('Malformed JSON code fence')
        text=match.group(1)
    payload=json.loads(text)
    if isinstance(payload,dict) and 'predictions' in payload:payload=payload['predictions']
    if isinstance(payload,dict) and 'sample_id' in payload:payload=[payload]
    if not isinstance(payload,list):
        return parse_text(response_text(payload))
    if not all(isinstance(p,dict) for p in payload):raise ValueError('Predictions must be JSON objects')
    return payload


def normalize(row):
    if not set(FIELDS)<=set(row):raise ValueError('Missing prediction fields')
    sid=str(row['sample_id']).strip()
    if not sid:raise ValueError('Empty sample ID')
    raw=row['sentiment_score']
    if isinstance(raw,bool):raise ValueError('Boolean is not an integer sentiment score')
    try:score=float(raw)
    except (TypeError,ValueError):raise ValueError('Non-numeric sentiment score') from None
    if not math.isfinite(score) or not score.is_integer() or not -4<=score<=4:raise ValueError('Sentiment score outside integer -4..4')
    score=int(score)
    label='positive' if score>0 else 'negative' if score<0 else 'neutral'
    if row['sentiment_label']!=label:raise ValueError('Label contradicts score')
    if isinstance(row['confidence'],bool):raise ValueError('Boolean confidence is invalid')
    confidence=float(row['confidence'])
    if not math.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Confidence outside 0..1')
    uncertain=row['uncertain']
    if isinstance(uncertain,str):
        if uncertain.lower() not in ['true','false']:raise ValueError('Invalid uncertainty flag')
        uncertain=uncertain.lower()=='true'
    if not isinstance(uncertain,bool):raise ValueError('Uncertainty flag must be boolean')
    if not isinstance(row['justification'],str) or not row['justification'].strip():raise ValueError('Missing brief justification')
    return dict(sample_id=sid,sentiment_score=score,sentiment_label=label,confidence=confidence,
                uncertain=uncertain,justification=row['justification'])


def validate_predictions(rows, expected_ids):
    frame=pd.DataFrame([normalize(r) for r in rows],columns=FIELDS)
    check_unique(frame)
    expected_ids=list(expected_ids)
    if len(set(expected_ids))!=len(expected_ids):raise ValueError('Duplicate expected IDs')
    if set(frame.sample_id)!=set(expected_ids):raise ValueError('Missing or extra prediction IDs')
    return frame.set_index('sample_id').loc[expected_ids].reset_index()


def load_predictions(path, expected_ids):
    path=Path(path)
    rows=read_csv(path,dtype=str).to_dict('records') if path.suffix=='.csv' else parse_text(path.read_text())
    return validate_predictions(rows,expected_ids)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--expected',type=Path,default=ROOT/'data/youtube/sampled/youtube_final_200.csv')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();expected=read_csv(a.expected,dtype=str)
    result=load_predictions(a.input,expected.sample_id)
    save_csv(a.output,result);print('Validated predictions:',len(result))
