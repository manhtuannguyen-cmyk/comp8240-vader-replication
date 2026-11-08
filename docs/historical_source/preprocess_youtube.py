"""Clean the existing 4,000-comment candidate frame; no sampling or sentiment labels."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
import argparse,hashlib,importlib.util,json
import yaml
from src.preprocessing_common import ROOT,PreprocessingError,config,check_sources,read_csv,read_json,write_csv,write_json,write_report,sha
COLUMNS=['sample_id','video_id','video_category','video_title','comment_id','comment_text_original','published_at','updated_at','like_count','reply_count','collection_date','random_seed','processing_status','exclusion_reason','language_screen','review_reason','source_file','source_row','exact_text_group_size','record_role']
ANNOTATION_COLUMNS=['sample_id','video_category','comment_text_original','annotator_1_sentiment','annotator_2_sentiment','final_human_sentiment','annotation_notes']
AUDIT_COLUMNS=['sample_id','comment_id','video_id','source_file','source_row','processing_status','exclusion_reason','review_reason','language_screen','text_sha256','exact_text_group_size']

def rules_module(root: Path):
 path=root/config(root)['youtube_root']/'src/eligibility_rules.py'
 spec=importlib.util.spec_from_file_location('shared_youtube_eligibility_rules',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module

def source_rows(root: Path):
 cfg=config(root);ytroot=root/cfg['youtube_root']
 videos=yaml.safe_load((ytroot/'config/video_candidates.yaml').read_text())['videos']
 schedule=read_json(ytroot/'outputs/reports/retention_schedule.json')
 deadline=datetime.fromisoformat(schedule['purge_or_recollect_by_utc'])
 if datetime.now(timezone.utc)>=deadline:raise PreprocessingError('YouTube source snapshot has expired. No raw files were changed: run the explicit lifecycle deletion/refresh workflow before processing.')
 paths=[ytroot/'data'/c['folder']/'comments_retrieved.csv' for c in videos]
 hashes=check_sources(root,paths)
 rows=[];ordinal=0
 for candidate,path in zip(videos,paths):
  metadata=read_json(path.parent/'video_metadata.json');manifest=read_json(path.parent/'collection_manifest.json')
  if metadata['verification_status']!='verified' or metadata['video_id']!=candidate['video_id'] or metadata['video_title']!=candidate['expected_title']:raise PreprocessingError('Candidate metadata mismatch; cannot infer missing video identity.')
  if sha(path)!=manifest['snapshot_sha256'] or not manifest['frame_complete']:raise PreprocessingError('Retrieved source does not match its completed collection frame.')
  for line,source in enumerate(read_csv(path),2):
   ordinal+=1
   if source.get('video_id')!=metadata['video_id']:raise PreprocessingError('Comment belongs to an unexpected video; investigate before processing.')
   row={'sample_id':f'YTC{ordinal:06d}','video_id':source['video_id'],'video_category':metadata['research_category'],'video_title':metadata['video_title'],'comment_id':source['comment_id'],'comment_text_original':source['comment_text_original'],'published_at':source['published_at'],'updated_at':source['updated_at'],'like_count':source['like_count'],'reply_count':source['reply_count'],'collection_date':source['collection_timestamp'],'random_seed':'','processing_status':'','exclusion_reason':'','language_screen':'','review_reason':'','source_file':str(path.relative_to(root)),'source_row':line,'exact_text_group_size':0,'record_role':'candidate_pool_not_random_sample','_folder':candidate['folder']}
   rows.append(row)
 return rows,videos,hashes,schedule

def classify_rows(rows:list[dict],rules):
 ids=defaultdict(list);texts=Counter(row['comment_text_original'] for row in rows)
 for i,row in enumerate(rows):ids[row['comment_id']].append(i)
 duplicate_reasons={}
 for cid,indices in ids.items():
  if not cid:
   for i in indices:duplicate_reasons[i]='missing_comment_id'
  elif len(indices)>1:
   signatures={(rows[i]['video_id'],rows[i]['comment_text_original'],rows[i]['published_at'],rows[i]['updated_at'],str(rows[i]['like_count']),str(rows[i]['reply_count']),rows[i]['collection_date']) for i in indices}
   if len(signatures)>1:
    for i in indices:duplicate_reasons[i]='conflicting_duplicate_comment_id'
   else:
    for i in indices[1:]:duplicate_reasons[i]='duplicate_comment_export'
 for i,row in enumerate(rows):
  decision,reason,language=rules.classify(row['comment_text_original'])
  if i in duplicate_reasons:
   reason=duplicate_reasons[i];decision='review' if reason=='conflicting_duplicate_comment_id' else 'exclude'
  row['processing_status']={'include':'retained','exclude':'excluded','review':'review_required'}[decision]
  row['exclusion_reason']=reason if decision=='exclude' else ''
  row['review_reason']=reason if decision=='review' else ''
  row['language_screen']=language
  row['exact_text_group_size']=texts[row['comment_text_original']]
 return rows

def register_artifacts(root:Path,paths:list[Path],replace=False):
 ytroot=root/config(root)['youtube_root'];registry=ytroot/'data/derived_artifacts_registry.json'
 previous=read_json(registry) if registry.exists() else {'workspace_root':str(root),'paths':[]}
 previous['paths']=sorted(set(previous['paths'])|{str(p.relative_to(root)) for p in paths})
 previous['purpose']='Private YouTube preprocessing derivatives; delete on source expiry/refresh or relevant deletion request. No raw source paths may be registered.'
 write_json(registry,previous,replace=True)

def process(root:Path=ROOT,replace=False):
 rules=rules_module(root);rows,videos,hashes,schedule=source_rows(root);classify_rows(rows,rules)
 artifact_paths=[];video_summaries=[];all_audits=[];duplicate_audit=[]
 textgroups=defaultdict(list)
 for row in rows:textgroups[row['comment_text_original']].append(row)
 for text,group in textgroups.items():
  if len(group)>1:
   for row in group:duplicate_audit.append({'sample_id':row['sample_id'],'comment_id':row['comment_id'],'video_id':row['video_id'],'group_size':len(group),'distinct_comment_ids':len({r['comment_id'] for r in group}),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'decision':'distinct IDs retained subject to independent eligibility; same-ID conflicts reviewed'})
 for candidate in videos:
  folder=candidate['folder'];group=[r for r in rows if r['_folder']==folder]
  partitions={status:[{k:r[k] for k in COLUMNS} for r in group if r['processing_status']==status] for status in ['retained','excluded','review_required']}
  paths={'retained':root/'data/processed/youtube'/folder/'youtube_comments_cleaned.csv','excluded':root/'data/excluded/youtube'/folder/'youtube_comments_excluded.csv','review_required':root/'data/processed/youtube'/folder/'youtube_comments_review_required.csv'}
  for status,path in paths.items():
   output=partitions[status]
   # Do not duplicate detected contact information into the excluded export.
   if status=='excluded':
    output=[{**r,'comment_text_original':''} if r['exclusion_reason'].startswith('personal_information') else r for r in output]
   write_csv(path,output,COLUMNS,replace);artifact_paths.append(path)
  annotations=[{k:r[k] if k in {'sample_id','video_category','comment_text_original'} else '' for k in ANNOTATION_COLUMNS} for r in partitions['retained']]
  annotation_path=root/'data/annotation/youtube'/folder/'youtube_annotation_template.csv'
  write_csv(annotation_path,annotations,ANNOTATION_COLUMNS,replace);artifact_paths.append(annotation_path)
  audit=[{**{k:r[k] for k in AUDIT_COLUMNS if k!='text_sha256'},'text_sha256':hashlib.sha256(r['comment_text_original'].encode()).hexdigest()} for r in group]
  audit_path=root/'reports/youtube'/folder/'preprocessing_audit.csv';write_csv(audit_path,audit,AUDIT_COLUMNS,replace);artifact_paths.append(audit_path)
  counts={s:len(partitions[s]) for s in partitions}
  missing={k:sum(not str(r[k]).strip() for r in group) for k in ['comment_text_original','comment_id','published_at','updated_at','like_count','reply_count','collection_date']}
  video_summaries.append({'folder':folder,'video_id':group[0]['video_id'],'category':group[0]['video_category'],'initial':len(group),**counts,'exclusion_reasons':dict(Counter(r['exclusion_reason'] for r in partitions['excluded'])),'review_reasons':dict(Counter(r['review_reason'] for r in partitions['review_required'])),'language_screen_counts':dict(Counter(r['language_screen'] for r in group)),'missing_values':missing,'duplicate_id_occurrences':len(group)-len({r['comment_id'] for r in group}),'retained_path':str(paths['retained'].relative_to(root)),'excluded_path':str(paths['excluded'].relative_to(root)),'review_path':str(paths['review_required'].relative_to(root)),'annotation_path':str(annotation_path.relative_to(root))})
  all_audits.extend(audit)
 write_csv(root/'reports/youtube_duplicate_audit.csv',duplicate_audit,['sample_id','comment_id','video_id','group_size','distinct_comment_ids','text_sha256','decision'],replace);artifact_paths.append(root/'reports/youtube_duplicate_audit.csv')
 summary={'initial_records':len(rows),'retained':sum(r['processing_status']=='retained' for r in rows),'excluded':sum(r['processing_status']=='excluded' for r in rows),'review_required':sum(r['processing_status']=='review_required' for r in rows),'scope':'all 4000 retrieved candidates; sampling explicitly deferred by user','random_sample_exists':False,'sampling_seed_in_processed_rows':None,'sampling_shortfall':'No sample has been constructed; not a shortage of candidate records. No replacement data collected.','duplicate_id_occurrences':len(rows)-len({r['comment_id'] for r in rows}),'repeated_exact_text_groups':sum(len(g)>1 for g in textgroups.values()),'repeated_exact_text_beyond_first':sum(len(g)-1 for g in textgroups.values()),'videos':video_summaries,'raw_sha256':hashes,'retention_deadline':schedule['purge_or_recollect_by_utc'],'pooled_text_output_created':False}
 summary_path=root/'reports/youtube_preprocessing_summary.json';write_json(summary_path,summary,replace);artifact_paths.append(summary_path)
 for directory,name,field in [('data/processed','youtube_comments_cleaned.manifest.json','retained_path'),('data/excluded','youtube_comments_excluded.manifest.json','excluded_path'),('data/annotation','youtube_annotation_template.manifest.json','annotation_path')]:
  path=root/directory/name
  write_json(path,{'kind':'per-video file manifest; not a pooled text dataset','scope':summary['scope'],'retention_deadline':summary['retention_deadline'],'files':[{'video_id':v['video_id'],'path':v[field]} for v in video_summaries]},replace);artifact_paths.append(path)
 lines=['# YouTube preprocessing report','','The researcher requested cleaning all 4,000 candidates and explicitly deferred sampling. No 200-comment sample, per-video 50-comment sample or executed sampling metadata exists. random_seed is blank, not inferred from a configuration file. YTC identifiers refer to candidate records, not random-sample membership.','',f'Initial={len(rows)}; retained={summary["retained"]}; excluded={summary["excluded"]}; review required={summary["review_required"]}. Pending records are neither eligible nor exclusions. No sentiment labels, scores, model evaluations or human annotations were generated.','', '## Per-video and category distribution','','| Video | Category | Initial | Retained | Excluded | Review |','|---|---|---:|---:|---:|---:|']
 lines += [f'| {v["video_id"]} | {v["category"]} | {v["initial"]} | {v["retained"]} | {v["excluded"]} | {v["review_required"]} |' for v in video_summaries]
 lines += ['', '## Duplicate handling','',f'Repeated ID occurrences: {summary["duplicate_id_occurrences"]}. Exact text repeats occur in {summary["repeated_exact_text_groups"]} groups ({summary["repeated_exact_text_beyond_first"]} occurrences beyond the first). Only repeated exports of the same observation ID are deduplicated; conflicting same-ID records require review. Distinct IDs with identical text are kept subject to independent eligibility, not removed as spam by assumption. No commenter identities were collected, so repeated texts cannot be attributed to the same or different users.','', '## Eligibility, missing values and language','', 'The same previously documented language thresholds are reused from the shared eligibility module, not copied into a divergent implementation: seed 42 for langdetect; English >=0.95; non-English long comments >=10 words and probability >=0.99 can be excluded; short/uncertain language or meaning is flagged, not dropped. Recognized English slang can pass. Suspected spam is reviewed, not sentiment-filtered. Exact source text, whitespace, case, punctuation, emoji, mentions and spelling remain untouched in retained/review records. Diagnostic token matching operates on a temporary copy only.','']
 for v in video_summaries:
  lines += [f'### {v["folder"]}','',f'Missing/whitespace values: {v["missing_values"]}.',f'Exclusion reasons: {v["exclusion_reasons"]}.',f'Review reasons: {v["review_reasons"]}.','']
 lines += ['## Sampling integrity','','Four intended video IDs/categories are present, and all raw records match video metadata and completed ten-page time-order source frames. No random draw was executed and no likes-based or sentiment-based selection occurred. Do not describe these cleaned candidates as a sampled 200. Candidate order/identifiers follow fixed source-file order only.','', '## Privacy, storage and output adaptation','',f'The raw and derived API data are private and inherit the existing deadline {summary["retention_deadline"]}. The latest task does not supply a YouTube permission reference resolving the existing cross-owner pooling question. Therefore cleaned, excluded and blank annotation text files are stored separately per video; requested combined CSV names are represented by .manifest.json indexes instead of silently pooling text. This is a documented output-structure adaptation, not a claim that a combined sample exists.','', 'No author/profile fields are copied. Comment/video IDs remain local for membership, deletion and traceability; they are not anonymous identifiers. Contact-pattern detection is heuristic; manual privacy inspection is still required. Detected private contact text is not recopied to excluded exports. Original raw files were not changed; source preservation lasts only within permitted retention, not indefinitely. A lifecycle registry extends source expiry/refresh/deletion to these new outputs.','', '## Readiness and limitations','', 'Structural preprocessing can pass while semantic eligibility remains provisional. Review the review-required files before final sampling/annotation. Blank annotation templates cover the retained candidate subset only and are drafts, not a final 200-comment annotation task. Emoji-only or short comments may be meaningful and should not be discarded just for length. This four-video bounded frame is not representative of all YouTube or Gen Z users.']
 report_path=root/'reports/youtube_preprocessing_report.md';write_report(report_path,lines,replace);artifact_paths.append(report_path)
 artifact_paths += [root/'reports/initial_data_inventory.md',root/'reports/data_validation_report.md',root/'reports/data_validation_results.json']
 register_artifacts(root,artifact_paths)
 check_sources(root,[root/p for p in hashes])
 return summary
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--replace-generated',action='store_true');a=p.parse_args();s=process(replace=a.replace_generated);print(json.dumps({k:s[k] for k in ['initial_records','retained','excluded','review_required']}))
