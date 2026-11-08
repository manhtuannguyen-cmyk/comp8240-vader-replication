"""Project-defined GoEmotions polarity mapping. No sentiment model is used."""
from __future__ import annotations
from collections import Counter,defaultdict
from pathlib import Path
import argparse,csv,hashlib,json
from src.preprocessing_common import ROOT,PreprocessingError,config,check_sources,write_csv,write_json,write_report
COLUMNS=['id','text_original','original_emotion_labels','emotion_names','original_split','mapped_sentiment','processing_status','exclusion_reason','exclusion_reasons','source_file','source_row','duplicate_text_group_size','cross_split_text_duplicate']
AUDIT_COLUMNS=['id','original_split','source_file','source_row','original_emotion_labels','emotion_names','text_sha256','mapped_sentiment','processing_status','exclusion_reason','exclusion_reasons']

def map_labels(labels: list[str],mapping: dict)->tuple[str,list[str]]:
 known=set().union(*map(set,mapping.values()))
 if not labels:return '',['missing_emotion_annotations']
 if any(x not in known for x in labels):return '',['unrecognized_emotion']
 reasons=[];s=set(labels)
 if len(s)!=len(labels):reasons.append('duplicate_emotion_annotation')
 if s&set(mapping['ambiguous']):reasons.append('ambiguous_emotion_present')
 if s&set(mapping['positive']) and s&set(mapping['negative']):reasons.append('mixed_positive_negative')
 if 'neutral' in s and len(s)>1:reasons.append('neutral_with_other_emotion')
 if reasons:return '',reasons
 for polarity in ['positive','negative','neutral']:
  if s<=set(mapping[polarity]):return polarity,[]
 return '',['unrecognized_emotion']

def load_rows(root: Path):
 cfg=config(root);source=root/cfg['goemotions_root'];emotions=(source/'emotions.txt').read_text().splitlines()
 mapping=cfg['goemotions_mapping']
 if len(emotions)!=28 or len(set(emotions))!=28 or set(emotions)!=set().union(*map(set,mapping.values())):raise PreprocessingError('Emotion taxonomy does not match the explicit project mapping.')
 paths=[source/name for name in cfg['splits'].values()]+[source/'emotions.txt']
 hashes=check_sources(root,paths)
 rows=[]
 for split,name in cfg['splits'].items():
  path=source/name
  with path.open(newline='',encoding='utf-8') as f:
   for line,fields in enumerate(csv.reader(f,delimiter='\t',quoting=csv.QUOTE_NONE),1):
    reasons=[]
    if len(fields)!=3:reasons.append('invalid_record_structure')
    text=fields[0] if fields else '';raw_labels=fields[1] if len(fields)>1 else '';rid=fields[2] if len(fields)>2 else ''
    if not rid:reasons.append('missing_record_id')
    if not text.strip():reasons.append('empty_text')
    if text.strip().casefold() in {'[deleted]','[removed]'}:reasons.append('deleted_or_removed_placeholder')
    labels=[]
    try:
     if not raw_labels:raise ValueError('missing')
     indices=[int(n) for n in raw_labels.split(',')]
     if any(i<0 or i>=len(emotions) for i in indices):raise ValueError('invalid')
     labels=[emotions[i] for i in indices]
    except ValueError:reasons.append('missing_emotion_annotations' if not raw_labels else 'invalid_emotion_annotation')
    polarity,label_reasons=map_labels(labels,mapping)
    reasons+=label_reasons
    rows.append({'id':rid,'text_original':text,'original_emotion_labels':raw_labels,'emotion_names':json.dumps(labels,ensure_ascii=False),'original_split':split,'mapped_sentiment':polarity,'processing_status':'','exclusion_reason':'','exclusion_reasons':'','source_file':str(path.relative_to(root)),'source_row':line,'duplicate_text_group_size':0,'cross_split_text_duplicate':False,'_reasons':list(dict.fromkeys(reasons))})
 return rows,hashes,mapping

def process(root: Path=ROOT,replace=False):
 rows,hashes,mapping=load_rows(root)
 identities=defaultdict(list);texts=defaultdict(list)
 for i,row in enumerate(rows):
  if row['id']:identities[row['id']].append(i)
  texts[row['text_original']].append(i)
 for rid,indices in identities.items():
  if len(indices)<=1:continue
  signatures={(rows[i]['original_split'],rows[i]['text_original'],rows[i]['original_emotion_labels']) for i in indices}
  if len(signatures)>1:
   for i in indices:rows[i]['_reasons'].insert(0,'conflicting_or_cross_split_record_id')
  else:
   for i in indices[1:]:rows[i]['_reasons'].insert(0,'duplicate_record_export')
 retained=[];excluded=[];audit=[];emotion_counts=Counter()
 for row in rows:
  group=texts[row['text_original']]
  row['duplicate_text_group_size']=len(group)
  row['cross_split_text_duplicate']=len({rows[i]['original_split'] for i in group})>1
  emotion_counts.update(json.loads(row['emotion_names']))
  reasons=row.pop('_reasons')
  row['processing_status']='excluded' if reasons else 'retained'
  row['exclusion_reason']=reasons[0] if reasons else ''
  row['exclusion_reasons']=json.dumps(reasons)
  if reasons:row['mapped_sentiment']='';excluded.append(row)
  else:retained.append(row)
  record={k:row[k] for k in AUDIT_COLUMNS if k!='text_sha256'}
  record['text_sha256']=hashlib.sha256(row['text_original'].encode()).hexdigest();audit.append(record)
 write_csv(root/'data/processed/goemotions_processed.csv',retained,COLUMNS,replace)
 write_csv(root/'data/excluded/goemotions_excluded.csv',excluded,COLUMNS,replace)
 write_csv(root/'reports/goemotions_mapping_audit.csv',audit,AUDIT_COLUMNS,replace)
 counts=Counter(r['mapped_sentiment'] for r in retained)
 split_counts={s:{'original':sum(r['original_split']==s for r in rows),'retained':sum(r['original_split']==s for r in retained),'excluded':sum(r['original_split']==s for r in excluded),'classes':dict(Counter(r['mapped_sentiment'] for r in retained if r['original_split']==s))} for s in config(root)['splits']}
 summary={'original_records':len(rows),'retained':len(retained),'excluded':len(excluded),'classes':dict(counts),'class_percentages':{k:100*counts[k]/len(retained) if retained else 0 for k in ['positive','negative','neutral']},'original_emotion_distribution':dict(emotion_counts),'primary_exclusion_reasons':dict(Counter(r['exclusion_reason'] for r in excluded)),'all_exclusion_reason_occurrences':dict(Counter(reason for r in excluded for reason in json.loads(r['exclusion_reasons']))),'splits':split_counts,'duplicate_ids_beyond_first':sum(len(v)-1 for v in identities.values()),'same_text_distinct_id_groups':sum(len({rows[i]['id'] for i in g})>1 for g in texts.values()),'cross_split_text_groups':sum(len({rows[i]['original_split'] for i in g})>1 for g in texts.values()),'raw_sha256':hashes}
 write_json(root/'reports/goemotions_preprocessing_summary.json',summary,replace)
 lines=['# GoEmotions preprocessing report','','Scope: the official agreement-filtered splits (not the full per-rater release). No VADER/LLM or model evaluation was run. Original text, annotation strings, IDs and source split are preserved.','',f'Original={len(rows):,}; retained={len(retained):,}; excluded={len(excluded):,}.','', '## Project methodology','','The supplied emotion groups and multi-label rules define a project-derived three-class target. These are not direct human sentiment annotations supplied with the dataset. The release remains a multi-label emotion corpus; the official support mapping file is not treated as pre-existing three-class ground truth.','', 'Any ambiguous emotion, mixed positive/negative emotions, or neutral plus another emotion is excluded. Invalid structure/text/annotations and repeated or conflicting source IDs have precedence as the primary reason; all reasons are preserved in exclusion_reasons. No exclusions depend on text length.','', 'Duplicate policy: identical exports of the same ID and split retain their first occurrence. Conflicting or cross-split repeated IDs are all excluded for investigation. Different IDs with identical text remain distinct observations and are flagged, including cross-split overlap; the original splits are never redistributed.','', '## Classes (denominator: retained records)','','| Class | Count | Percentage |','|---|---:|---:|']
 lines += [f'| {k} | {counts[k]} | {summary["class_percentages"][k]:.4f}% |' for k in ['positive','negative','neutral']]
 lines += ['', '## Original split preservation','','| Split | Original | Retained | Excluded |','|---|---:|---:|---:|']+[f'| {s} | {c["original"]} | {c["retained"]} | {c["excluded"]} |' for s,c in split_counts.items()]
 lines += ['', '## Original emotion occurrences (multi-label records contribute more than once)','','| Emotion | Count |','|---|---:|']+[f'| {k} | {v} |' for k,v in sorted(emotion_counts.items())]
 lines += ['', '## Primary exclusion reasons','','| Reason | Count |','|---|---:|']+[f'| {k} | {v} |' for k,v in summary['primary_exclusion_reasons'].items()]
 lines += ['', '## Limitations','',f'Identical text across distinct IDs occurs in {summary["same_text_distinct_id_groups"]} groups; {summary["cross_split_text_groups"]} groups span splits. These are warnings for later training/evaluation leakage checks, not justification for silently rewriting the official partitions. The retained subset changes the original emotion distribution by design. It does not represent all Reddit users. No 60,124-record target was assumed.','', 'Raw hashes are checked before and after processing. The mapping audit has one row per source record, including excluded records. Detailed counts and provenance are in goemotions_preprocessing_summary.json.']
 write_report(root/'reports/goemotions_preprocessing_report.md',lines,replace)
 check_sources(root,[root/p for p in hashes])
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--replace-generated',action='store_true');a=p.parse_args();s=process(replace=a.replace_generated);print(json.dumps({k:s[k] for k in ['original_records','retained','excluded','classes']}))
