# Optional qualitative error coding

The current record supports exact observable disagreement patterns. It does not contain independently verified sarcasm/slang/emoji causal categories. A keyword or emoji detector must not silently create those categories.

If human inspection is performed, create `data/youtube/annotations/error_coding.csv` with:

`sample_id,error_tags,coder_id,verification_status`

Use semicolon-separated multi-tags chosen from a declared rubric: sarcasm, slang, emoji, mixed_sentiment, negation, intensifier, capitals, context_dependence, lexical_gap, neutral_ambiguity. Add evidence notes and adjudication details if available. A human coder should inspect the comment's actual wording and record only supported readings; distinguish a visible feature from evidence that it caused an error. Mark records `human_verified` only following real human verification. AI-proposed codes remain `provisional_ai`.

`generate_figures.py` produces a verified error-category frequency plot only when actual human-verified coding records are supplied. Counts can overlap and do not estimate causal effects. Existing human sentiment ratings must never be changed to improve model results.
