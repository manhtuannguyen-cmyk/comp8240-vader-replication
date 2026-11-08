# Original VADER inputs

The local working snapshot includes all four ground-truth text files and anonymous rating artifacts, the original paper, Python 2 code, lexicon and upstream licence notices. The public review export omits third-party benchmark text and the paper PDF. Fetch the exact authors’ release with `python src/data_processing/fetch_public_data.py --dataset original_vader`. URLs and SHA-256 values are pinned in `config/public_sources.json`.

The source release is preserved byte-for-byte. Differences between its text-bearing and per-rater artifacts are quantified by `reports/replication/rater_artifact_audit.csv`; source means are not silently replaced.
