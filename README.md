# COMP8240 — VADER Replication and Sentiment Evaluation

This project reproduces VADER on its four original benchmark datasets and evaluates it on GoEmotions and a newly constructed YouTube dataset. It also compares three saved LLM sentiment annotators with two completed human annotations.

**Start here:** use the quick-start commands below. The normal analysis is offline: it does not collect comments, request new LLM predictions or need API keys.

The **adapted 2014 implementation** is the primary replicated model. `vaderSentiment==3.3.2` is a separately named version comparison. They are never silently substituted for one another.

## 1. What is in this folder?

```text
comp8240-vader-replication/
├── README.md
├── environment.yml
├── requirements.txt                 # Offline scientific analysis
├── requirements-llm.txt             # Optional new API calls
├── requirements-notebook.txt        # Optional notebook execution
├── config/                          # Mapping, video selection, pinned source URLs
├── data/
│   ├── original_vader/              # Four corpora, rating artifacts, code, lexicon, notices
│   ├── goemotions/
│   │   ├── raw/                     # Unchanged official train/dev/test TSVs
│   │   └── processed/               # train.csv, validation.csv, test.csv, all.csv, excluded.csv
│   ├── youtube/                     # Local/private: raw, processed, sampled, annotations, LLM files
│   └── provenance/                  # Sources and frozen-input SHA-256 manifest
├── prompts/                         # Researcher-supplied shared prompt and provenance gaps
├── src/
│   ├── replication/                 # Original and modern VADER, original-corpus runner
│   ├── data_processing/             # Mapping, eligibility, sampling, API acquisition, downloads
│   ├── annotation/                  # Independent agreement and human mean reference
│   ├── llm_judge/                   # Strict parser and optional new-run API logging
│   ├── evaluation/                  # Metrics, bootstrap, paired tests, figures
│   └── tools/                       # Input validation, notebook execution, public export
├── notebooks/                       # Complete analysis source, saved outputs removed for Git
│   └── private/                     # Executed notebook with private outputs, ignored by Git
├── reports/                         # Generated metrics, LaTeX table fragments and PNG/SVG figures
├── docs/                            # Annotation guide, error-coding protocol, access notes, source lineage
└── tests/                           # Reproducibility checks
```

The folder includes a local private snapshot for this project. **Do not upload the whole folder indiscriminately.** `.gitignore` excludes private YouTube inputs/LLM outputs, private figures and executed notebook outputs. The public-export command below enforces a separate allowlist.


## 2. Quick start — reproduce the current local project

Tested with **Python 3.14.5 on macOS ARM64** in this folder's own isolated environment. The dependency versions are pinned. `requirements-lock.txt` records the full tested environment (including optional API/notebook dependencies); use `python -m pip install -r requirements-lock.txt` when that exact full environment is desired. NLTK and HTML scraping libraries are not required: this project uses the author's VADER implementation/package and the official YouTube API.

From a terminal, enter this folder:

```sh
cd comp8240-vader-replication
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/evaluation/run_all_metrics.py
```

If you are already inside this folder and its environment is installed, start with `source .venv/bin/activate`. Windows activation is `.venv\Scripts\activate`.

The last command checks input hashes and mapping, runs both VADER versions on the original corpora and GoEmotions, verifies the initial sample and replacement draws, evaluates humans/LLMs/VADER on the same YouTube records, calculates 2,000-draw bootstrap intervals and paired comparisons, and generates metrics, LaTeX table fragments and figures.

A Conda alternative is supplied:

```sh
conda env create -f environment.yml
conda activate comp8240-vader-replication
python src/evaluation/run_all_metrics.py
```

The isolated `venv` setup is the tested setup; the Conda specification is an alternative, not a claim that its solver was tested here. Keep the working directory at the repository root when installing the relative requirements file.

## 3. Public clone / marker without private YouTube access

The public export contains the GoEmotions release and model assets. Original third-party text corpora are obtained from the authors' **pinned upstream release**, with SHA-256 checks:

```sh
python src/data_processing/fetch_public_data.py --dataset original_vader
python src/evaluation/run_all_metrics.py --public-only
```

`fetch_public_data.py --dataset all` also verifies/downloads GoEmotions source files if needed. It refuses differing existing files and never extracts an archive directly onto the filesystem.

**The exact YouTube experiment needs the genuine permitted private input bundle.** See `data/youtube/README.md`. Deleted/edited comments cannot be recovered by recollecting live data; human ratings and saved LLM outputs cannot be reconstructed from a random replacement sample. When private inputs are absent, the runner states that this stream was not run. It never fills in fake results.

## 4. Run one stage at a time

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

Historical source snapshots are in `docs/historical_source/` for inspection. They preserve old paths and are **not** the portable entry points. In particular, never rerun the historical SQLite replacement script against completed annotations.

## 5. Complete research notebook

The portable notebook is `notebooks/COMP8240_VADER_Final_Research_Evaluation.ipynb`. Its public source contains the full code and explanations but no saved private outputs. Execute it in the same environment:

```sh
python -m pip install -r requirements-notebook.txt
python src/tools/run_notebook.py
```

The fully executed copy is saved under `notebooks/private/` and stays out of Git. All original data paths are relative to this repository. This notebook requires the genuine private inputs for its full YouTube/LLM sections. It embeds the adapted historical model and independently checks the central results.

## 6. Scoring and reference rules

- Original corpora: keep source text unchanged. Human mean scores on −4..+4 are divided by 4. Primary polarity uses >=+0.05 positive, <=−0.05 negative, otherwise neutral, following an explicitly documented interpretation of the paper's normalized-score statement. Raw-human thresholds/sign-only labels are separate sensitivity diagnostics.
- VADER predictions: `compound >= 0.05` positive; `compound <= -0.05` negative; otherwise neutral. Case, punctuation, emoji and whitespace are preserved.
- GoEmotions: **54,263 raw agreement-filtered split records** become **45,258 retained** project-mapped examples and **9,005 exclusions**. Ambiguous emotions, mixed positive/negative labels and neutral-plus-other cases are excluded. These are derived sentiment classes, not the original emotion task or continuous intensity ground truth. The complete retained cohort (45,258 examples) is primary; train/validation/test results are descriptive split diagnostics. Configuration lists every emotion group.
- YouTube humans: both 200-comment exports are complete. Mean raw intensity is the average of the two independent-role scores. Positive/zero/negative raw mean defines polarity. This is an **averaged reference**, not an adjudicated gold standard. Independent ratings are preserved.
- Actual adjudication: none is available. The code does not create it. If real blind adjudication is later performed, provide `data/youtube/annotations/adjudicated_labels.csv` with `sample_id,human_gold_label,adjudicator_id,adjudication_timestamp,adjudication_status`. It must cover the cohort, have valid provenance and status `adjudicated`. Only then are its actual categorical labels used as primary. Mean intensity remains an explicitly separate score reference.
- LLM scores: the shared researcher-supplied rubric specifies integer −4..+4. Saved polarity labels are validated against score sign; score/4 supports conditional intensity comparisons. `uncertain=true` is retained and must not be confused with verified genuine neutrality. Confidence is self-reported.
- Fixed class order: negative, neutral, positive. Macro F1 is the mean of the three class F1 scores. Weighted F1 weights by reference support. Zero denominators use zero. Accuracy and the paper's reported overall F1 are different quantities.

Bootstrap intervals are pointwise 95% percentile intervals, using matched items. YouTube resampling preserves each video's allocation. Four videos do not support strong population-level cluster inference; within-video dependence remains a limitation. Paired macro-F1 difference intervals and exact McNemar comparisons use the same items. Six primary McNemar comparisons receive Holm correction. No arbitrary kappa threshold establishes human equivalence.

## 7. Reference results

The tables below use the same definitions as the executed notebook and generated LaTeX fragments. Retain implementation and reference labels when copying numbers into the final report. Rounded values are for presentation; CSV/JSON files retain numerical precision.

### Original benchmark replication

| Corpus | Implementation | N | Pearson r | Paper r | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|---|---|---|---|
| Tweets | VADER 2014 | 4200 | 0.8812 | 0.8810 | 0.9100 | 0.7467 | 0.9058 |
| Tweets | VADER 3.3.2 | 4200 | 0.8722 | 0.8810 | 0.8988 | 0.7399 | 0.8957 |
| Movie | VADER 2014 | 10605 | 0.4165 | 0.4510 | 0.5489 | 0.4055 | 0.5772 |
| Movie | VADER 3.3.2 | 10605 | 0.4274 | 0.4510 | 0.5532 | 0.4059 | 0.5811 |
| Amazon | VADER 2014 | 3708 | 0.5709 | 0.5650 | 0.5769 | 0.5131 | 0.6002 |
| Amazon | VADER 3.3.2 | 3708 | 0.5896 | 0.5650 | 0.5874 | 0.5212 | 0.6102 |
| NYT | VADER 2014 | 5190 | 0.4915 | 0.4920 | 0.5279 | 0.5206 | 0.5406 |
| NYT | VADER 3.3.2 | 5190 | 0.5029 | 0.4920 | 0.5333 | 0.5253 | 0.5458 |

### GoEmotions: complete retained cohort

| Implementation | N | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|---|
| VADER 2014 | 45258 | 0.6351 | 0.6088 | 0.6219 |
| VADER 3.3.2 | 45258 | 0.6358 | 0.6083 | 0.6210 |

### YouTube: common 200-comment averaged human reference

| System | N | Accuracy | Macro F1 | Weighted F1 | Cohen κ | Pearson r |
|---|---|---|---|---|---|---|
| VADER 2014 | 200 | 0.5000 | 0.4186 | 0.5303 | 0.1574 | 0.3994 |
| VADER 3.3.2 | 200 | 0.5400 | 0.4535 | 0.5639 | 0.2004 | 0.4379 |
| ChatGPT | 200 | 0.6650 | 0.6191 | 0.6875 | 0.4374 | 0.7814 |
| Claude | 200 | 0.7000 | 0.6507 | 0.7227 | 0.4774 | 0.7961 |
| Gemini | 200 | 0.7500 | 0.6792 | 0.7558 | 0.5372 | 0.7802 |

Human polarity agreement: **83.5%**; Cohen κ **0.6930**; quadratic weighted intensity κ **0.7907**. There are **33** polarity disagreements. Gemini has the largest saved-LLM macro-F1 point estimate on this reference; paired intervals and the sample limitations qualify any ranking.

Original-paper comparison is **partial replication**. Historical tweet and NYT correlations match the published values after rounding; movie and Amazon differ. The original rating artifacts contain additional inconsistencies: 199 tweet IDs have different means between text-bearing and per-rater files; some Amazon/NYT text IDs do not have matching per-rater IDs. No source labels are repaired to improve agreement. The published overall F1 averaging recipe is not established, so it is not equated to local macro F1.

## 8. LLM prompt, parsing and optional new API runs

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
python -m pip install -r requirements-llm.txt
python src/llm_judge/run_judges.py --provider openai --model YOUR_EXACT_MODEL_ID --limit 1
```

The command above is a **dry run**. To deliberately run a new experiment, securely export the relevant `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`, choose an actual supported model ID, and add `--execute`. Providers are `openai`, `anthropic`, `google`. Optional `--temperature` and `--system-prompt path` are logged; neither is guessed for the historical runs. `.env.example` documents variable names; scripts do not automatically read a filled `.env`.

Each request contains only the original text and sample ID, plus the shared rubric. Human scores and VADER/other-model predictions are never read by this runner. Each new run archives request JSON, raw provider response JSON, public response text, input/prompt hashes, model and parameter settings, failures and the parsed predictions under a separate `data/youtube/llm/new_runs/` directory. Failed/incomplete runs do not produce a purported complete prediction file. No live API functionality was needed for the offline analysis tests.

## 9. Optional acquisition and error coding

```sh
# Configuration check only; zero API requests
python src/data_processing/collect_youtube.py
```

Adding `--execute` with an exported `YOUTUBE_API_KEY` makes a new official-API snapshot in a separate timestamped directory. It does not overwrite or restore the historical snapshot. It uses recent top-level comments, up to ten pages of 100 per video, no commenter profiles and no HTML scraping. Source collection can change over time. Applicable access/retention permissions must be resolved for a new collection.

There are no independently verified sarcasm/slang/emoji causal codes yet. `error_audit.csv` reports observable prediction disagreements. `docs/error_coding_protocol.md` describes how to add genuine human verification. The figure generator does not fabricate a causal error-frequency chart from keyword/emoji matches.

## 10. Prepare a public repository folder

Create an allowlisted review copy in a **new separate destination**:

```sh
python src/tools/export_public.py --output ../comp8240-vader-public
```

This copies code, requirements, configurations, the supplied prompt, GoEmotions, source/licence notices, input checksums and public-data results. It excludes private YouTube records and response logs, original third-party benchmark text, credentials, virtual environments and executed notebook outputs. Benchmark download commands remain available for the marker. The command does not initialise Git or publish/upload anything.

Before publication, inspect that review folder. Do not use `git add -f` to bypass data exclusions. Provide permitted marker access to the private evaluation snapshot separately. A public-only reproduction is intentionally narrower than a complete private-snapshot reproduction.

## 11. Data access, retention and provenance

Copying source data does not restart retention. The existing YouTube source deadline is **2 December 2026, about 13:08 Sydney time**. All copied raw/private data, model responses, annotations, executed outputs and figures inherit source refresh/deletion requests. `python src/tools/retention.py` audits the local deadline; `python src/tools/retention.py --purge-expired` explicitly deletes the entire private snapshot only after expiry, preserving code, original VADER and GoEmotions. Separately shared copies still require coordinated deletion. The private analysis refuses expired inputs. Recollecting changes the scientific sample and cannot be presented as an exact recovery of deleted or edited records.

`data/provenance/input_manifest.json` records the frozen input hashes. `config/public_sources.json` pins upstream URLs and checksums. Do not silently update manifests to accept unexplained changes. Generated files can be rebuilt; original data and completed human annotations are never overwritten by the analysis command.

Third-party code/data notices are in `THIRD_PARTY_NOTICES.md` and the upstream data folders. No credentials, browser sessions, passwords or annotation-app database are included.

Cite Hutto & Gilbert (2014), DOI 10.1609/icwsm.v8i1.14550, and Demszky et al. (2020), https://aclanthology.org/2020.acl-main.372/. The notebook contains the fuller methodological bibliography and limitations.


