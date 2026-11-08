# COMP8240 VADER Replication

This project reproduces VADER on the original benchmarks and evaluates both the adapted 2014 implementation and `vaderSentiment==3.3.2` on GoEmotions. The public workflow runs without API keys.

## Run the project

Use Python 3.14 or later.

```sh
git clone https://github.com/manhtuannguyen-cmyk/comp8240-vader-replication.git
cd comp8240-vader-replication
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/data_processing/fetch_public_data.py --dataset original_vader
python src/evaluation/run_all_metrics.py --public-only
```

On Windows, activate the environment with `.venv\\Scripts\\activate`.

The results are written to `reports/replication/`, `reports/goemotions/`, and `reports/public/`.

## Pipeline

```text
Original VADER benchmarks ─┐
                           ├─> VADER 2014 and VADER 3.3.2 ─> evaluation metrics ─> reports
GoEmotions data ─ mapping ─┘
```

The optional YouTube and LLM-judge workflow requires private research inputs and is not included in the public run.

## Main folders

- `src/` — processing, replication, and evaluation code.
- `config/` — dataset mapping and source configuration.
- `data/` — public VADER and GoEmotions inputs.
- `prompts/` — LLM-judge prompt input.
- `reports/` — generated evaluation results.
