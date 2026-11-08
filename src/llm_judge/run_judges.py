"""Optional new-run API caller. Default is offline dry run; historical outputs stay intact.

One request per comment; only sample ID and original text enter the request.
The supplied researcher prompt is preserved. This prospective per-item wrapper
does not claim to reconstruct an undocumented historical batch/API protocol.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src.common import ROOT, read_csv, require_youtube, save_csv, save_json, sha, check_unique
from src.llm_judge.parse_responses import parse_text, validate_predictions


def call_provider(provider,model,prompt,system_prompt,temperature,max_tokens):
    """Provider SDK imports are optional for the fully offline reproduction path."""
    if provider=='openai':
        from openai import OpenAI
        client=OpenAI(api_key=os.environ['OPENAI_API_KEY'],max_retries=0,timeout=90)
        kwargs={'model':model,'input':prompt,'max_output_tokens':max_tokens,'store':False}
        if system_prompt:kwargs['instructions']=system_prompt
        if temperature is not None:kwargs['temperature']=temperature
        response=client.responses.create(**kwargs)
        return response.model_dump(mode='json'),response.output_text
    if provider=='anthropic':
        from anthropic import Anthropic
        client=Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'],max_retries=0,timeout=90)
        kwargs={'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':max_tokens}
        if system_prompt:kwargs['system']=system_prompt
        if temperature is not None:kwargs['temperature']=temperature
        response=client.messages.create(**kwargs)
        return response.model_dump(mode='json'),'\n'.join(p.text for p in response.content if getattr(p,'type','')=='text')
    if provider=='google':
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=os.environ['GEMINI_API_KEY'],
                            http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1)))
        config={'response_mime_type':'application/json','max_output_tokens':max_tokens}
        if system_prompt:config['system_instruction']=system_prompt
        if temperature is not None:config['temperature']=temperature
        response=client.models.generate_content(model=model,contents=prompt,config=types.GenerateContentConfig(**config))
        return response.model_dump(mode='json'),response.text or ''
    raise ValueError('Unsupported provider')


def run(args):
    require_youtube()
    # Never read annotations, previous model scores, credentials files or .env.
    source=args.input if args.input.is_absolute() else ROOT/args.input
    if args.limit is not None and args.limit<1:raise ValueError('--limit must be positive')
    if args.max_tokens<1:raise ValueError('--max-tokens must be positive')
    frame=read_csv(source,dtype=str)[['sample_id','comment_text_original']]
    check_unique(frame)
    if args.limit:frame=frame.head(args.limit)
    prompt_path=ROOT/'prompts/supplied_judge_prompt.md'
    rubric=prompt_path.read_text()
    system_prompt=args.system_prompt.read_text() if args.system_prompt else None
    print(f'{"EXECUTE" if args.execute else "DRY RUN"}: provider={args.provider}, model={args.model}, records={len(frame)}')
    if not args.execute:
        print('No API call made. No historical model ID or system prompt has been guessed.')
        return
    environment_key={'openai':'OPENAI_API_KEY','anthropic':'ANTHROPIC_API_KEY','google':'GEMINI_API_KEY'}[args.provider]
    if not os.environ.get(environment_key):raise ValueError('Missing '+environment_key+'; no API request made')
    now=datetime.now(timezone.utc)
    folder=ROOT/'data/youtube/llm/new_runs'/f'{now.strftime("%Y%m%dT%H%M%S%fZ")}_{args.provider}'
    folder.mkdir(parents=True,exist_ok=False)
    manifest={'run_kind':'new prospective per-comment run; not historical regeneration',
              'provider':args.provider,'requested_model':args.model,'started_at_utc':now.isoformat(),
              'prompt_sha256':sha(prompt_path),'system_prompt_sha256':hashlib.sha256(system_prompt.encode()).hexdigest() if system_prompt else None,
              'temperature':args.temperature,'max_output_tokens':args.max_tokens,'input_file_sha256':sha(source),
              'sdk_retries':'disabled; Google one attempt, OpenAI/Anthropic max_retries=0',
              'records':len(frame),'independence':'only sample_id and comment_text_original are sent','attempts':[]}
    predictions=[]
    for row in frame.to_dict('records'):
        sid=row['sample_id']
        # IDs must be safe filenames for immutable response artifacts.
        import re
        if not re.fullmatch(r'[A-Za-z0-9_-]+',sid):raise ValueError('Unsafe sample ID filename')
        record_folder=folder/sid;record_folder.mkdir()
        prompt=rubric+'\n\nCURRENT INPUT RECORD (one record; return one JSON object):\n'+json.dumps(row,ensure_ascii=False)
        request_log={'provider':args.provider,'model':args.model,'user_prompt':prompt,'system_prompt':system_prompt,
                     'temperature':args.temperature,'max_output_tokens':args.max_tokens}
        save_json(record_folder/'request.json',request_log)
        try:
            raw,text=call_provider(args.provider,args.model,prompt,system_prompt,args.temperature,args.max_tokens)
            save_json(record_folder/'raw_response.json',raw)
            (record_folder/'response_text.txt').write_text(text)
            parsed=validate_predictions(parse_text(text),[sid])
            predictions.extend(parsed.to_dict('records'))
            manifest['attempts'].append({'sample_id':sid,'status':'parsed','raw_response_sha256':sha(record_folder/'raw_response.json')})
        except Exception as exc:
            # Error text can expose credentials/request bodies; preserve safe type/status only.
            manifest['attempts'].append({'sample_id':sid,'status':'failed','error_type':type(exc).__name__,
                                         'http_status':getattr(exc,'status_code',None)})
        save_json(folder/'run_manifest.json',manifest)
    if len(predictions)!=len(frame):
        raise RuntimeError(f'Only {len(predictions)}/{len(frame)} records succeeded; raw artifacts preserved. No complete predictions file produced.')
    final=validate_predictions(predictions,frame.sample_id)
    save_csv(folder/'predictions.csv',final)
    manifest['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    save_json(folder/'run_manifest.json',manifest)
    print('New run saved separately:',folder.relative_to(ROOT))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--provider',choices=['openai','anthropic','google'],required=True)
    p.add_argument('--model',required=True,help='Exact model identifier chosen by researcher; no provider-family alias is invented')
    p.add_argument('--input',type=Path,default=ROOT/'data/youtube/sampled/youtube_final_200.csv')
    p.add_argument('--system-prompt',type=Path);p.add_argument('--temperature',type=float)
    p.add_argument('--max-tokens',type=int,default=1500);p.add_argument('--limit',type=int)
    p.add_argument('--execute',action='store_true')
    run(p.parse_args())
