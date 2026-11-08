"""Optional official-API acquisition; defaults to a configuration-only dry run.

Uses the historical 10x100 recent, top-level-comment frame. New snapshots cannot
recreate deleted/edited comments or restart the old sample's retention period.
Never scrape HTML, overwrite the historical snapshot or collect author profiles.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone,timedelta
import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pandas as pd
import requests
import yaml
from src.common import ROOT, save_csv, save_json
from src.data_processing.eligibility_rules import personal_information


def run(execute=False):
    videos=yaml.safe_load((ROOT/'config/videos.yaml').read_text())['videos']
    if not execute:
        print('DRY RUN: four configured videos, up to ten pages x 100 top-level recent comments each. No requests made.')
        return
    key=os.environ.get('YOUTUBE_API_KEY','').strip()
    if not key:raise ValueError('Set YOUTUBE_API_KEY securely; no request made')
    stamp=datetime.now(timezone.utc)
    base=ROOT/'data/youtube/new_snapshots'/stamp.strftime('%Y%m%dT%H%M%S%fZ')
    base.mkdir(parents=True,exist_ok=False)
    for video in videos:
        rows=[];seen=set();token=None;pages=0;redacted_count=0
        for _ in range(10):
            params={'part':'snippet','videoId':video['video_id'],'maxResults':100,'order':'time','textFormat':'plainText','key':key,
                    'fields':'nextPageToken,items(snippet(videoId,totalReplyCount,topLevelComment(id,snippet(videoId,textOriginal,publishedAt,updatedAt,likeCount))))'}
            if token:params['pageToken']=token
            try:
                response=requests.get('https://www.googleapis.com/youtube/v3/commentThreads',params=params,timeout=45)
            except requests.RequestException:
                raise RuntimeError('YouTube network failure; request URL suppressed to protect API credentials') from None
            if response.status_code!=200:
                raise RuntimeError(f'YouTube HTTP {response.status_code}; body and credential-bearing URL not logged')
            payload=response.json();pages+=1
            for item in payload.get('items',[]):
                thread=item['snippet'];top=thread['topLevelComment'];s=top['snippet'];cid=top['id']
                if s.get('videoId',video['video_id'])!=video['video_id']:raise ValueError('Unexpected video membership')
                if 'textOriginal' not in s:raise ValueError('Missing original text; no textDisplay fallback permitted')
                if cid in seen:continue
                seen.add(cid)
                if personal_information(s['textOriginal']):redacted_count+=1;continue
                rows.append({'comment_id':cid,'video_id':video['video_id'],'comment_text_original':s['textOriginal'],
                             'published_at':s['publishedAt'],'updated_at':s['updatedAt'],'like_count':s.get('likeCount',0),
                             'reply_count':thread.get('totalReplyCount',0),'collection_timestamp':stamp.isoformat()})
            previous=token;token=payload.get('nextPageToken')
            if token and token==previous:raise ValueError('Repeated page token')
            if not token:break
        folder=base/video['folder']
        save_csv(folder/'comments_retrieved.csv',pd.DataFrame(rows))
        save_json(folder/'collection_manifest.json',{'started_at':stamp.isoformat(),'video_id':video['video_id'],'pages':pages,
                    'retained':len(rows),'prestorage_privacy_exclusions':redacted_count,'frame_truncated':bool(token),
                    'purge_or_refresh_by':(stamp+timedelta(days=29)).isoformat(),'protocol':'10 pages x 100, time order; official API'})
    print('New snapshot saved separately:',base.relative_to(ROOT))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    run(p.parse_args().execute)
