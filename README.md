# COMP8240 VADER Replication

This project reproduces VADER on the original benchmarks, evaluates both the adapted 2014 implementation and `vaderSentiment==3.3.2` on GoEmotions, and evaluates VADER and three saved LLM judges on annotated YouTube comments. The full saved evaluation runs without API keys.

## Run the project

Use Python 3.14 or later.

```sh
git clone https://github.com/manhtuannguyen-cmyk/comp8240-vader-replication.git
cd comp8240-vader-replication
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/data_processing/fetch_public_data.py --dataset original_vader
python src/evaluation/run_all_metrics.py
```

On Windows, activate the environment with `.venv\\Scripts\\activate`.

The results are written to `reports/replication/`, `reports/goemotions/`, `reports/youtube/`, and `reports/public/`.

## Pipeline

![Overall VADER replication, extension and evaluation pipeline](assets/vader-replication-pipeline.png)

The repository includes the saved YouTube comments, two independent human-annotation files, and saved ChatGPT, Claude, and Gemini predictions. The evaluation uses these saved outputs; it does not make new LLM API calls. New API calls are optional and require explicit credentials and execution.

## Main folders

- `src/` — processing, replication, and evaluation code.
- `config/` — dataset mapping and source configuration.
- `data/` — VADER, GoEmotions, YouTube comments, annotations, and saved LLM outputs.
- `prompts/` — LLM-judge prompt input.
- `reports/` — generated evaluation results.
