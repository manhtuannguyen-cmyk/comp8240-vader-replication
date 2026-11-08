"""User-authorized random sample: 50 per video, globally unique IDs and texts."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import sys,json,hashlib,platform
import numpy as np
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.preprocessing_common import read_csv,read_json,write_csv,write_json,write_report,sha

def text_key(text):return ' '.join(text.split()).casefold()

def select():
 videos=yaml.safe_load((ROOT/'youtube_comment_dataset/config/video_candidates.yaml').read_text())['videos']
 schedule=read_json(ROOT/'youtube_comment_dataset/outputs/reports/retention_schedule.json')
 assert datetime.now(timezone.utc)<datetime.fromisoformat(schedule['purge_or_recollect_by_utc']),'Source retention expired'
 stamp=datetime.now(timezone.utc).isoformat()
 inputs={};seen_ids=set();seen_text=set();pools=[];counts=[]
 # Fixed video order assigns shared normalized texts to their first video.
 # Stable ID ordering chooses the representative among repeated texts.
 for video in videos:
  path=ROOT/'data/processed/youtube'/video['folder']/'youtube_comments_cleaned.csv'
  rows=read_csv(path);inputs[str(path.relative_to(ROOT))]=sha(path)
  rawpath=ROOT/'youtube_comment_dataset/data'/video['folder']/'comments_retrieved.csv'
  manifest=read_json(rawpath.parent/'collection_manifest.json');assert sha(rawpath)==manifest['snapshot_sha256']
  raw={r['comment_id']:r for r in read_csv(rawpath)}
  pool=[]
  for row in sorted(rows,key=lambda r:r['comment_id']):
   assert row['video_id']==video['video_id'] and row['video_category']==video['research_category']
   assert row['processing_status']=='retained' and row['comment_text_original'].strip()
   assert row['comment_text_original']==raw[row['comment_id']]['comment_text_original']
   key=text_key(row['comment_text_original'])
   if row['comment_id'] in seen_ids or key in seen_text:continue
   seen_ids.add(row['comment_id']);seen_text.add(key);pool.append(row)
  assert len(pool)>=50,f'Unique-pool shortfall for {video["folder"]}'
  pools.append(pool);counts.append({'video_id':video['video_id'],'category':video['research_category'],'initially_retained':len(rows),'unique_sampling_pool':len(pool),'selected':50,'source_sha256':inputs[str(path.relative_to(ROOT))]})
 final=[];log=[]
 for video,pool in zip(videos,pools):
  rng=np.random.default_rng(42)
  selected=[pool[int(i)] for i in rng.choice(len(pool),50,replace=False)]
  for row in selected:
   sid=f'COM{len(final)+1:03d}'
   record={k:row[k] for k in ['video_id','video_category','video_title','comment_id','comment_text_original','published_at','updated_at','like_count','reply_count','collection_date']}
   record={'sample_id':sid,**record,'random_seed':42,'source_candidate_id':row['sample_id']}
   final.append(record)
   log.append({'sample_id':sid,'video_id':row['video_id'],'video_category':row['video_category'],'comment_id':row['comment_id'],'selected':True,'random_seed':42,'sampling_method':'SRS without replacement from stable globally deduplicated retained-text pool','sampling_date':stamp})
 assert len(final)==200 and len({r['sample_id'] for r in final})==200
 assert len({r['comment_id'] for r in final})==200
 assert len({text_key(r['comment_text_original']) for r in final})==200
 assert Counter(r['video_id'] for r in final)==Counter({v['video_id']:50 for v in videos})
 # Independently repeat the draws to verify deterministic selection.
 offset=0
 for pool in pools:
  expected=[pool[int(i)]['comment_id'] for i in np.random.default_rng(42).choice(len(pool),50,replace=False)]
  assert expected==[r['comment_id'] for r in final[offset:offset+50]];offset+=50
 annotation_columns=['sample_id','video_category','comment_text_original','annotator_1_sentiment','annotator_2_sentiment','final_human_sentiment','annotation_notes']
 annotation=[{k:r.get(k,'') if k in annotation_columns[:3] else '' for k in annotation_columns} for r in final]
 assert all(all(not r[k] for k in annotation_columns[3:]) for r in annotation)
 outputs=[ROOT/'data/processed/youtube_final_200.csv',ROOT/'data/processed/youtube_sampling_log.csv',ROOT/'data/annotation/youtube_annotation_template.csv']
 for p in outputs:assert not p.exists(),f'Refusing to overwrite {p}'
 write_csv(outputs[0],final,list(final[0]));write_csv(outputs[1],log,list(log[0]));write_csv(outputs[2],annotation,annotation_columns)
 result={'status':'passed','total':200,'unique_sample_ids':200,'unique_comment_ids':200,'unique_normalized_texts':200,'per_video':counts,'random_seed':42,'numpy_version':np.__version__,'python_version':platform.python_version(),'sampling_timestamp':stamp,'approval_basis':'User explicitly instructed random selection from initially retained candidates, superseding the earlier individual-review requirement; unreviewed flagged candidates remain outside the pool. This is pool-level sampling authorization, not a claim of per-record manual review.','unique_text_rule':'Whitespace collapse and casefold used solely for duplicate comparison; source text unchanged. Fixed video order and ascending comment_id choose one global representative per text.','retention_deadline':schedule['purge_or_recollect_by_utc'],'input_sha256':inputs,'output_sha256':{str(p.relative_to(ROOT)):sha(p) for p in outputs},'annotation_fields_blank':True,'sentiment_analysis_performed':False}
 # Verify persisted files rather than only in-memory records.
 persisted=read_csv(outputs[0]);assert len(persisted)==200
 assert [r['comment_text_original'] for r in persisted]==[r['comment_text_original'] for r in final]
 assert len(read_csv(outputs[1]))==200 and len(read_csv(outputs[2]))==200
 for name,digest in inputs.items():assert sha(ROOT/name)==digest
 write_json(ROOT/'reports/youtube_final_sampling_validation.json',result)
 lines=['# Final YouTube sampling report','',f'Selected {stamp}. Exactly 200 comments: 50 from each intended video. Seed 42; NumPy default_rng, simple random sampling without replacement from each deduplicated retained-candidate pool.','', '## Authorization and eligibility','','The user explicitly requested random selection from the initially retained candidate pools, superseding the earlier individual researcher-review gate. This is authorization to sample these pools, not evidence that every comment was manually reviewed. Flagged and excluded records remain outside this sample.','', '| Category | Initially retained | Unique pool | Selected |','|---|---:|---:|---:|']
 lines += [f'| {r["category"]} | {r["initially_retained"]} | {r["unique_sampling_pool"]} | 50 |' for r in counts]
 lines += ['', '## Unique-text rule and reproducibility','','No comment ID or normalized text occurs more than once across all 200. Duplicate comparisons collapse whitespace and ignore capitalization; original text is never rewritten. Stable ascending comment_id picks a representative for repeated texts. The configured video order assigns text shared between videos to the first video before sampling, so no after-the-fact replacement occurs. Sampling is uniform over these unique-text pools, rather than over all original comments; this requested uniqueness constraint changes the sampling population.','',f'Python {platform.python_version()}; NumPy {np.__version__}; seed 42 independently initialized per video. Source hashes, output hashes and exact counts are in youtube_final_sampling_validation.json. Sampling was reproduced before writing and persisted CSVs were checked. No sentiment, like-count or engagement ranking was used.','', '## Validation','','PASS: 200 rows; 50 per video; 200 unique COM IDs; 200 unique source comment IDs; 200 unique normalized texts; correct video/category membership; original text identical to raw sources; seed recorded; deterministic redraw identical; all annotation fields blank. No VADER, sentiment labels, annotation or model performance analysis was performed. Source candidate files and GoEmotions were not modified.','', '## Unresolved review and limitations','','The 1,547 previously flagged candidates remain unreviewed and were not sampled. The 77 prior exclusions remain excluded. Automatic eligibility screening can introduce selection bias. Distinct-ID comments with identical text were collapsed only for this final sample at the user’s explicit request; candidate data were preserved. Four selected videos do not represent YouTube; equal allocation differs from population comment frequencies. Each category has one video, so video, creator and audience confound category comparisons. Commenter ages are unverified; no Gen Z claim is supported. Random sampling cannot remove initial eligibility or unique-text selection bias.','',f'Outputs remain local and private; existing refresh/delete deadline: {schedule["purge_or_recollect_by_utc"]}. Pool-level user authorization is not a declaration of platform permission for public redistribution. Do not publish API text or retain it indefinitely.']
 write_report(ROOT/'reports/youtube_final_sampling_report.md',lines,replace=True)
 # The old blocked audit remains as historical evidence, with the newer authorization documented above.
 registry_path=ROOT/'youtube_comment_dataset/data/derived_artifacts_registry.json';registry=read_json(registry_path)
 registry['paths']=sorted(set(registry['paths'])|{str(p.relative_to(ROOT)) for p in outputs}|{'reports/youtube_final_sampling_report.md','reports/youtube_final_sampling_validation.json'})
 write_json(registry_path,registry,replace=True)
 print(json.dumps({'total':200,'unique_ids':200,'unique_texts':200,'per_video':counts,'validation':'passed'}))
if __name__=='__main__':select()
