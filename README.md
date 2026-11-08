# COMP8240 — VADER Replication and Sentiment Evaluation

This project reproduces VADER on its four original benchmark datasets and evaluates it on GoEmotions and a newly constructed YouTube dataset. It also compares three saved LLM sentiment annotators with two completed human annotations.

**Start here:** use the quick-start commands below. The normal analysis is offline: it does not collect comments, request new LLM predictions or need API keys.

The **adapted 2014 implementation** is the primary replicated model. `vaderSentiment==3.3.2` is a separately named version comparison. They are never silently substituted for one another.

## 1. What is in this folder?

Use these links to navigate the repository:

- [Project overview and setup](README.md) — installation, reproduction commands, scope, and results.
- [Requirements](requirements.txt) — all Python dependencies needed to run the project.
- [Configuration](config/) — GoEmotions mapping rules, selected-video metadata, and pinned public source locations.
- [Data](data/) — public VADER and GoEmotions inputs, processed public data, and provenance manifests. The [original VADER materials](data/original_vader/), [GoEmotions data](data/goemotions/), and [provenance records](data/provenance/) are included for reproducibility.
- [Prompts](prompts/) — the supplied LLM-judge rubric and documentation of known historical-protocol gaps.
- [Source code](src/) — implementation organised into [replication](src/replication/), [data processing](src/data_processing/), [annotation](src/annotation/), [LLM judging](src/llm_judge/), [evaluation](src/evaluation/), and [tools](src/tools/).
- [Public reports](reports/public/) — generated public metrics, LaTeX table fragments, and figures. Other report folders contain local/generated material and may not be included in a public clone.

This working folder also contains local private research material. **Do not upload the entire folder indiscriminately.** The repository excludes private YouTube inputs and annotations, LLM outputs, notebooks, tests, and internal documentation. A public download can reproduce the VADER and GoEmotions workflow without the private YouTube snapshot.


## 2. Quick start — reproduce the current local project

Tested with **Python 3.14.5 on macOS ARM64**. The dependency versions are pinned in `requirements.txt`. NLTK and HTML scraping libraries are not required: this project uses the author's VADER implementation/package and the official YouTube API.

From a terminal, enter this folder:

```sh
cd comp8240-vader-replication
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/data_processing/fetch_public_data.py --dataset original_vader
python src/evaluation/run_all_metrics.py --public-only
```

If you are already inside this folder and its environment is installed, start with `source .venv/bin/activate`. Windows activation is `.venv\Scripts\activate`.

The last command checks input hashes and mapping, runs both VADER versions on the original corpora and GoEmotions, calculates bootstrap intervals, and generates public metrics, LaTeX table fragments, and figures. Keep the working directory at the repository root when installing the relative requirements file.

## 3. Run one stage at a time

Run these commands from the repository root after activating the environment:

```sh
# Verify the frozen sources and saved private inputs where present
python src/tools/validate_inputs.py

# Verify GoEmotions mapping without overwriting inputs
python src/data_processing/map_goemotions.py

# Optional: rebuild processed GoEmotions split CSVs from the checked raw release
python src/data_processing/map_goemotions.py --write

# Recalculate historical language/privacy eligibility decisions (no API calls)
python src/data_processing/preprocess_youtube.py

# Reproduce both the initial sample and all seven recorded replacements
python src/data_processing/sample_youtube.py

# Recalculate human agreement; generate an explicitly named averaged reference
python src/annotation/agreement.py

# Run just the four original corpora with both VADER implementations
python src/replication/run_replication.py

# Recompute all metrics; --no-figures is useful when only tables are needed
python src/evaluation/run_all_metrics.py --no-figures

# Rebuild PNG and editable SVG figures from the saved metrics
python src/evaluation/generate_figures.py
```

`--bootstrap 2000` is the default for metric runners. A different repetition count changes interval estimates and must be reported. Seed 8240 is used for evaluation resampling; seed 42 belongs to the historical sampling/eligibility protocol.

Key outputs:

- `reports/replication/metrics.csv`, `metrics.json`, `threshold_sensitivity.csv`, `rater_artifact_audit.csv`;
- `reports/goemotions/metrics.csv`, `metrics.json`;
- `reports/youtube/human_agreement.json`, `model_metrics.csv`, `per_class_metrics.csv`;
- `reports/youtube/individual_human_comparison.csv`, `reference_sensitivity.csv`, `pairwise_agreement.csv`;
- `reports/youtube/paired_comparisons.csv`, `domain_metrics.csv`, `error_audit.csv`;
- `reports/public/cross_dataset_results.tex`, `reports/youtube/model_results.tex`;
- `reports/youtube/figures/` with descriptive filenames, PNG at 300 dpi, SVG and a caption index.

## 4. LLM prompt, parsing and optional new API runs

Your supplied shared prompt is preserved in `prompts/supplied_judge_prompt.md`. See `prompts/protocol.json` and `prompts/README.md` for what is known and missing.

Historical exact model identifiers, inference dates, temperatures, role placement and full API transport logs are unavailable. ChatGPT has a saved prediction-object JSON list and CSV; Claude and Gemini have CSVs. **We do not label reconstructed JSON as missing raw API evidence.** The local files preserve all actual material available.

Validate a saved prediction file without any API call:

```sh
python src/llm_judge/parse_responses.py \
  --input data/youtube/llm/historical_outputs/chatgpt_saved_prediction_objects.json \
  --output data/youtube/generated/chatgpt_parsed.csv
```

New runs are optional, potentially paid, and do not reproduce unknown historical settings. They are never invoked by `run_all_metrics.py`:

```sh
python src/llm_judge/run_judges.py --provider openai --model YOUR_EXACT_MODEL_ID --limit 1
```

The command above is a **dry run**. To deliberately run a new experiment, securely export the relevant `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`, choose an actual supported model ID, and add `--execute`. Providers are `openai`, `anthropic`, `google`. Optional `--temperature` and `--system-prompt path` are logged; neither is guessed for the historical runs.

Each request contains only the original text and sample ID, plus the shared rubric. Human scores and VADER/other-model predictions are never read by this runner. Each new run archives request JSON, raw provider response JSON, public response text, input/prompt hashes, model and parameter settings, failures and the parsed predictions under a separate `data/youtube/llm/new_runs/` directory. Failed/incomplete runs do not produce a purported complete prediction file. No live API functionality was needed for the offline analysis tests.

## 5. Optional acquisition and error coding

```sh
# Configuration check only; zero API requests
python src/data_processing/collect_youtube.py
```

Adding `--execute` with an exported `YOUTUBE_API_KEY` makes a new official-API snapshot in a separate timestamped directory. It does not overwrite or restore the historical snapshot. It uses recent top-level comments, up to ten pages of 100 per video, no commenter profiles and no HTML scraping. Source collection can change over time. Applicable access/retention permissions must be resolved for a new collection.

There are no independently verified sarcasm/slang/emoji causal codes yet. `error_audit.csv` reports observable prediction disagreements. The figure generator does not fabricate a causal error-frequency chart from keyword/emoji matches.



