"""One-time researcher-authorized revision, preserving identities and unchanged ratings."""
from pathlib import Path
import csv,hashlib,json,random,re,sqlite3,os
from datetime import datetime,timezone
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
REASONS={'COM015':'Near-repeated Sara legend reaction; retain COM001','COM055':'Researcher flagged unclear technical token','COM093':'Repeated long-story joke; retain COM083','COM127':'Researcher identified unrelated fashion promotion','COM134':'Researcher identified channel promotion','COM165':'Repeated DoorDash question; retain COM152','COM195':'Near-identical DoorDash question; retain COM152'}
def read(p):
 with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write(p,rows,fields):
 tmp=p.with_suffix(p.suffix+'.revision-tmp')
 with tmp.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 os.chmod(tmp,0o600);tmp.replace(p)
def key(t):return ' '.join(re.findall(r'\w+',t.casefold()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 os.umask(0o077);stamp=datetime.now(timezone.utc).isoformat();revision='quality_revision_20261103'
 source=ROOT/'data/processed/youtube_final_200.csv';rows=read(source);old_by={r['sample_id']:r for r in rows}
 assert set(REASONS)<=old_by.keys(),'Revision already applied or source differs'
 assert len(rows)==200
 dbpath=ROOT/'annotation-app/database/annotations.db';db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
 assert db.execute("select value from settings where key='source_sha256'").fetchone()[0]==sha(source)
 before_annotations=[dict(r) for r in db.execute('select * from annotations')]
 before_users=[dict(r) for r in db.execute('select role,cursor,finalized_at,submission_complete from users')]
 old_order=[r[0] for r in db.execute('select sample_id from annotation_order order by position')]
 folder=ROOT/'data/annotation/youtube/revisions'/revision;folder.mkdir(parents=True,exist_ok=False)
 backup=sqlite3.connect(folder/'annotations_before_revision.db');db.backup(backup);backup.close()
 backup_paths=[source,ROOT/'data/processed/youtube_sampling_log.csv',ROOT/'data/annotation/youtube_annotation_template.csv',ROOT/'reports/youtube_final_sampling_report.md',ROOT/'reports/youtube_final_sampling_validation.json']
 backup_paths += list((ROOT/'data/annotation').glob('*annotations.csv'))
 for p in backup_paths:(folder/p.name).write_bytes(p.read_bytes())
 ids={r['comment_id'] for r in rows};texts={key(r['comment_text_original']) for r in rows};pools={};replacements=[];mapping={}
 folders={'XLabFiVil58':'video_01_comedy','bHxLy6Qza3M':'video_02_gaming','Q-7yjWQ11kQ':'video_03_lifestyle','uiPMONFMbrg':'video_04_pop_culture'}
 for video,sub in folders.items():
  pool=[r for r in read(ROOT/'data/processed/youtube'/sub/'youtube_comments_cleaned.csv') if r['comment_id'] not in ids and key(r['comment_text_original']) not in texts and r['processing_status']=='retained']
  pool.sort(key=lambda r:r['comment_id']);random.Random(42).shuffle(pool);pools[video]=pool
 for old_id in sorted(REASONS):
  old=old_by[old_id];pool=pools[old['video_id']]
  while True:
   r=pool.pop(0)
   if r['comment_id'] not in ids and key(r['comment_text_original']) not in texts:break
  ids.add(r['comment_id']);texts.add(key(r['comment_text_original']))
  new_id=f'COM{201+len(replacements):03d}'
  new={k:r.get(k,'') for k in rows[0]};new.update(sample_id=new_id,random_seed='42',source_candidate_id=r['sample_id'])
  raw={x['comment_id']:x for x in read(ROOT/'youtube_comment_dataset/data'/folders[r['video_id']]/'comments_retrieved.csv')}
  assert new['comment_text_original']==raw[new['comment_id']]['comment_text_original']
  rows[next(i for i,x in enumerate(rows) if x['sample_id']==old_id)]=new;mapping[old_id]=new_id
  replacements.append({'old_sample_id':old_id,'new_sample_id':new_id,'video_id':old['video_id'],'old_comment_id':old['comment_id'],'new_comment_id':new['comment_id'],'reason':REASONS[old_id],'revision_timestamp':stamp,'random_seed':42,'old_annotation_position':old_order.index(old_id)+1})
 assert len({r['comment_id'] for r in rows})==200 and len({key(r['comment_text_original']) for r in rows})==200
 assert sorted(Counter(r['video_id'] for r in rows).values())==[50]*4
 write(source,rows,list(rows[0]))
 order=[mapping.get(s,s) for s in old_order]
 try:
  db.execute('pragma foreign_keys=on');db.execute('begin immediate')
  db.execute('create table if not exists retired_samples(revision TEXT,sample_id TEXT,source_metadata TEXT,annotations_json TEXT,retired_at TEXT,reason TEXT,primary key(revision,sample_id))')
  for change in replacements:
   old=change['old_sample_id'];new=next(r for r in rows if r['sample_id']==change['new_sample_id'])
   archive=[a for a in before_annotations if a['sample_id']==old]
   db.execute('insert into retired_samples values(?,?,?,?,?,?)',(revision,old,json.dumps(old_by[old],ensure_ascii=False),json.dumps(archive,ensure_ascii=False),stamp,change['reason']))
   db.execute('insert into samples values(?,?,?)',(new['sample_id'],new['comment_text_original'],json.dumps(new,ensure_ascii=False)))
   db.execute('update annotation_order set sample_id=? where sample_id=?',(new['sample_id'],old))
   db.execute('delete from annotations where sample_id=?',(old,));db.execute('delete from samples where sample_id=?',(old,))
  db.execute("update settings set value=? where key='source_sha256'",(sha(source),))
  db.execute("insert or replace into settings values('revision_order_json',?)",(json.dumps(order),))
  db.execute("insert or replace into settings values('quality_revision',?)",(revision,))
  for role in ['annotator_1','annotator_2']:
   had_work=any(a['annotator_id']==role for a in before_annotations)
   if had_work:db.execute('update users set cursor=?,finalized_at=NULL,submission_complete=0 where role=?',(min(x['old_annotation_position'] for x in replacements),role))
  db.execute('delete from sessions')
  db.commit()
 except Exception:
  db.rollback();source.write_bytes((folder/source.name).read_bytes());raise
 remaining=[dict(r) for r in db.execute('select * from annotations')]
 assert remaining==[a for a in before_annotations if a['sample_id'] not in REASONS]
 assert db.execute('pragma integrity_check').fetchone()[0]=='ok';assert not db.execute('pragma foreign_key_check').fetchall()
 assert [r[0] for r in db.execute('select sample_id from annotation_order order by position')]==order
 db.close()
 logs=read(ROOT/'data/processed/youtube_sampling_log.csv');newby={r['sample_id']:r for r in rows}
 for l in logs:
  if l['sample_id'] in mapping:
   r=newby[mapping[l['sample_id']]];l.update(sample_id=r['sample_id'],comment_id=r['comment_id'],sampling_date=stamp,sampling_method='Seed-42 replacement draw without replacement from remaining retained candidates after researcher quality exclusions')
 write(ROOT/'data/processed/youtube_sampling_log.csv',logs,list(logs[0]))
 ac=['sample_id','video_category','comment_text_original','annotator_1_sentiment','annotator_2_sentiment','final_human_sentiment','annotation_notes']
 write(ROOT/'data/annotation/youtube_annotation_template.csv',[{k:r.get(k,'') if k in ac[:3] else '' for k in ac} for r in rows],ac)
 out=folder/'replacement_audit.csv';write(out,replacements,list(replacements[0]))
 info={'revision':revision,'timestamp':stamp,'source_sha256':sha(source),'total':200,'unique_comment_ids':200,'unique_word_normalized_texts':200,'per_video':dict(Counter(r['video_id'] for r in rows)),'replacement_count':len(replacements),'unchanged_annotations_preserved':len(remaining),'old_annotations_archived':len(before_annotations)-len(remaining),'new_comments_unrated':True,'positions_preserved':True,'random_seed':42,'sampling_method':'Python random.Random(42).shuffle of stable comment-ID ordered remaining retained pools per video; first unique candidates taken. Revised sample is a quality-amended sample, not an untouched original SRS.','previous_user_states':before_users,'retention_deadline':json.loads((ROOT/'youtube_comment_dataset/outputs/reports/retention_schedule.json').read_text())['purge_or_recollect_by_utc']}
 (folder/'revision_manifest.json').write_text(json.dumps(info,indent=2)+'\n')
 p=ROOT/'reports/youtube_final_sampling_validation.json';v=json.loads(p.read_text());v.update(current_revision=revision,replacement_count=len(replacements),sampling_design_after_revision=info['sampling_method'],current_revision_validation=info,annotation_fields_blank='Template blank; actual human ratings exist in SQLite')
 v['output_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [source,ROOT/'data/processed/youtube_sampling_log.csv',ROOT/'data/annotation/youtube_annotation_template.csv']};p.write_text(json.dumps(v,indent=2)+'\n')
 report=ROOT/'reports/youtube_final_sampling_report.md';report.write_text(report.read_text()+'\n## Researcher-authorized quality revision — '+stamp+'\n\nSeven records replaced after researcher feedback: two promotional comments, one unclear technical comment, and four repeated/paraphrased reactions or questions. Same-video replacement draws use seed 42 from remaining retained candidates; no sentiment/engagement values were used. The current sample is quality-amended, not the unmodified original SRS. Unchanged sample IDs and annotation positions are preserved; new comments use COM201–COM207 and start unrated. Old ratings remain in the private revision archive, never transferred to replacement text. Existing sessions were invalidated and annotators with saved work reopened. Full audit: data/annotation/youtube/revisions/'+revision+'/replacement_audit.csv. Matching normalized text is absent; common topics or distinct opinions are not automatically duplicates. Automated wording checks cannot guarantee absence of every semantic paraphrase.\n')
 registry_path=ROOT/'youtube_comment_dataset/data/derived_artifacts_registry.json';registry=json.loads(registry_path.read_text());registry['paths']=sorted(set(registry['paths'])|{str(p.relative_to(ROOT)) for p in folder.iterdir()});registry_path.write_text(json.dumps(registry,indent=2)+'\n')
 print(json.dumps({k:v for k,v in info.items() if k not in ['previous_user_states','source_sha256']},indent=2))
if __name__=='__main__':main()
