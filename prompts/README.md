# Historical prompt and prospective API protocol

`supplied_judge_prompt.md` contains the shared sentiment prompt supplied by the researcher on 5 November 2026. Wording is retained; pasted line continuations and tables are formatted for readability. `protocol.json` records provenance and the remaining historical gaps.

The shared prompt is known now. Exact model identifiers, inference dates, temperature/top-p, provider transport settings and the split between system/user messages are still unknown. No fictional system prompt has been created.

Historical evidence available locally:

- ChatGPT: prediction CSV and JSON prediction-object list. The latter is **not verified as a raw API response envelope**.
- Claude: prediction CSV; original raw provider output is unavailable.
- Gemini: prediction CSV; original raw provider output is unavailable.

A CSV-to-JSON conversion would be a derived representation, not recovery of a missing raw API response. We therefore do not claim the raw-response archival requirement has been retrospectively satisfied for all three providers.

`src/llm_judge/run_judges.py` implements a new, explicit one-record-per-request protocol. It appends only the sample ID and original text to this shared rubric, optionally accepts a real system-prompt file, requires an explicit model ID, and archives request configuration, raw SDK response JSON, public response text and parsing status. No historical predictions are replaced. New runs do not prove the historical systems used this exact wrapper.

The prompt's insufficient-context instruction assigns score zero with `uncertain=true`. Analysis must not treat those outputs as verified genuine neutrality. Confidence is self-reported certainty, not a calibrated probability of correctness.

API implementations were checked against the [OpenAI Python documentation](https://developers.openai.com/api/reference/python), [Anthropic Messages documentation](https://platform.claude.com/docs/en/api/messages), and [Google generateContent reference](https://aistudio.google.com/api-reference/generate-content). Live access and model availability are not tested by offline reproduction.
