"""Checkpointed, bounded top-level collection. Never persists commenter profiles."""
from __future__ import annotations
from pathlib import Path
from src.common import COMMENT_COLUMNS, PipelineError, load_config, now, read_json, save_json, read_csv, save_csv, sha256
from src.video_verification import verified_metadata
from src.comment_filter import personal_information

FIELDS='nextPageToken,items(snippet(videoId,totalReplyCount,topLevelComment(id,snippet(videoId,textOriginal,publishedAt,updatedAt,likeCount,parentId))))'

def collect_video(client,root: Path,candidate: dict,metadata: dict,test_only: bool=False) -> dict:
    settings,_,_=load_config(root)
    folder=root/'data'/candidate['folder']
    manifest_path=folder/'collection_manifest.json'
    raw_path=folder/'comments_retrieved.csv'
    manifest=read_json(manifest_path) if manifest_path.exists() else {'video_id':metadata['video_id'],'started_at':now(),'next_page_token':None,'pages_received':0,'received_items':0,'frame_complete':False,'duplicate_ids':[],'pre_storage_exclusions':[],'frame':{'max_pages':settings['max_pages_per_video'],'page_size':settings['page_size'],'order':'time'}}
    if manifest['video_id']!=metadata['video_id'] or manifest['frame']!={'max_pages':settings['max_pages_per_video'],'page_size':settings['page_size'],'order':'time'}:
        raise PipelineError('Existing collection does not match video/frame configuration. Start an explicitly separate project snapshot; data will not be overwritten.')
    rows=read_csv(raw_path) if raw_path.exists() else []
    if raw_path.exists() and manifest.get('snapshot_sha256')!=sha256(raw_path):
        raise PipelineError('Retrieved snapshot differs from its checkpoint; refusing an unsafe resume.')
    if manifest['frame_complete']:return manifest
    # Each page is committed with a matching hash. A crash between the CSV and manifest
    # commits fails closed on resume, instead of silently changing the sampling frame.
    while manifest['pages_received']<settings['max_pages_per_video']:
        parameters={'part':'snippet','videoId':metadata['video_id'],'maxResults':100,'textFormat':'plainText','order':'time','fields':FIELDS}
        if manifest['next_page_token']:parameters['pageToken']=manifest['next_page_token']
        response=client.request('commentThreads',**parameters)
        new=[];redacted=[];seen={r['comment_id'] for r in rows};duplicates=set(manifest['duplicate_ids'])
        for item in response.get('items',[]):
            thread=item['snippet'];top=thread['topLevelComment'];snippet=top['snippet']
            if snippet.get('parentId'):raise PipelineError('Unexpected reply in top-level response.')
            if thread.get('videoId')!=metadata['video_id'] or snippet.get('videoId',metadata['video_id'])!=metadata['video_id']:
                raise PipelineError('API returned a comment for a different video.')
            if 'textOriginal' not in snippet:
                raise PipelineError('The API did not return textOriginal. Public textDisplay may differ from original text. Approval of a revised text-field methodology is required; no fallback or fabricated original text was stored.')
            cid=top['id'];text=snippet['textOriginal']
            if cid in seen:
                duplicates.add(cid)
                continue
            seen.add(cid)
            if personal_information(text):
                redacted.append({'comment_id':cid,'video_id':metadata['video_id'],'exclusion_reason':'personal_information_not_retained'})
                continue
            new.append({'comment_id':cid,'video_id':metadata['video_id'],'comment_text_original':text,'published_at':snippet['publishedAt'],'updated_at':snippet['updatedAt'],'like_count':snippet.get('likeCount',0),'reply_count':thread.get('totalReplyCount',0),'collection_timestamp':now()})
        rows+=new
        manifest['received_items']+=len(response.get('items',[]))
        manifest['pages_received']+=1
        manifest['duplicate_ids']=sorted(duplicates)
        manifest['pre_storage_exclusions']+=redacted
        token=response.get('nextPageToken')
        if token and token==manifest['next_page_token']:raise PipelineError('Repeated pagination token; retrieval stopped.')
        manifest['next_page_token']=token
        manifest['frame_complete']=not token or manifest['pages_received']>=settings['max_pages_per_video']
        manifest['bounded_frame_truncated']=bool(token)
        manifest['retained_unique_records']=len(rows)
        if manifest['frame_complete']:manifest['completed_at']=now()
        save_csv(raw_path,rows,COMMENT_COLUMNS,replace=raw_path.exists())
        manifest['snapshot_sha256']=sha256(raw_path)
        save_json(manifest_path,manifest,replace=manifest_path.exists())
        if test_only:break
    return manifest

def collect_all(client,root: Path) -> None:
    metadata=verified_metadata(root)
    _,candidates,_=load_config(root)
    # Milestone 5: first video is tested for two pages before collecting others.
    first=collect_video(client,root,candidates[0],metadata[0],test_only=True)
    if not first['frame_complete']:
        collect_video(client,root,candidates[0],metadata[0],test_only=True)
    save_json(root/'outputs/reports/collection_test.json',{'tested_at':now(),'video_id':metadata[0]['video_id'],'pages_received':read_json(root/'data'/candidates[0]['folder']/'collection_manifest.json')['pages_received'],'pagination_exercised':read_json(root/'data'/candidates[0]['folder']/'collection_manifest.json')['pages_received']>=2,'note':'If no nextPageToken exists, pagination could not be exercised on the real frame.'},replace=True)
    for candidate,value in zip(candidates,metadata):collect_video(client,root,candidate,value)
