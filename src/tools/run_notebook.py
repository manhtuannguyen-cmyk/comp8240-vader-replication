"""Execute the portable analysis source in this environment; save outputs privately."""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src.common import ROOT, require_youtube


def run(output):
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client.kernelspec import KernelSpecManager
    require_youtube()
    source=ROOT/'notebooks/COMP8240_VADER_Final_Research_Evaluation.ipynb'
    output=ROOT/output
    # Executed figures and qualitative excerpts belong to the private subtree.
    if not output.resolve().is_relative_to((ROOT/'notebooks/private').resolve()):
        raise ValueError('Save executed text-bearing notebook outputs under notebooks/private/')
    output.parent.mkdir(parents=True,exist_ok=True)
    notebook=nbformat.read(source,as_version=4)
    with tempfile.TemporaryDirectory(prefix='comp8240-kernel-') as temporary:
        base=Path(temporary);kernel=base/'kernels/python3';kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                                                    'display_name':'COMP8240 project environment','language':'python'}))
        os.environ['COMP8240_ROOT']=str(ROOT)
        os.environ['JUPYTER_RUNTIME_DIR']=str(base/'runtime')
        os.environ['IPYTHONDIR']=str(base/'ipython')
        os.environ['MPLCONFIGDIR']=str(base/'matplotlib')
        client=NotebookClient(notebook,timeout=1200,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
        client.create_kernel_manager()
        client.km.kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel.parent)])
        def progress(cell,cell_index,**kwargs):
            if cell.cell_type=='code':print('Executing notebook code cell',cell_index,flush=True)
        client.on_cell_start=progress
        try:client.execute()
        finally:nbformat.write(notebook,output)
    print('Executed notebook:',output.relative_to(ROOT))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('notebooks/private/COMP8240_VADER_Final_Research_Evaluation.ipynb'))
    run(p.parse_args().output)
