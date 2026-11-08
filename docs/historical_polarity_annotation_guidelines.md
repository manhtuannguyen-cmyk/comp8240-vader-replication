# Text-only human sentiment annotation guidelines

These instructions prepare a later human task. No annotations have been generated in this preprocessing run. Current per-video templates cover retained **candidate records**, not a sampled 200-comment dataset. Finish eligibility review and the agreed sampling stage before issuing the final annotation task.

## Independent work and information available

Two annotators work on separate copies with the same text and stable candidate IDs. Do not share scores, notes or discussions until both independently finish. Each annotator fills only their assigned sentiment field and annotation_notes in their private copy. Leave the other annotator's score and final_human_sentiment blank. The researcher merges completed files later; this task does not calculate agreement or adjudicate labels. Do not use VADER, an LLM, GoEmotions mappings or any model suggestions.

Judge the comment text alone. Do not open its video, replies, parent conversation or commenter profile. Category is supplied for traceability, not evidence of sentiment. Preserve comment text exactly. Do not equate agreement with positivity, disagreement with negativity or zero likes with neutrality.

## Three allowed labels

**Positive**: the wording communicates an overall favourable evaluation, enjoyment, appreciation, affection or clearly positive emotional reaction. Example invented for this guideline: “Loved this, absolutely hilarious 😂”.

**Negative**: the wording communicates an overall unfavourable evaluation, displeasure, disappointment, anger, distress or clearly negative emotional reaction. Invented example: “That was painfully disappointing.” Profanity alone does not decide the label; “that was fucking amazing” may be positive.

**Neutral**: the text has no clear positive/negative evaluation or emotion, such as a factual statement or straightforward information-seeking question. Invented example: “What time does the next episode start?” Neutral is not a catch-all for text you do not understand.

Labels must be exactly Positive, Neutral or Negative. Do not enter a fourth sentiment label or a numeric score. All examples here are invented teaching examples, not corpus records or additional ground truth.

## Mixed sentiment

If positive and negative feelings coexist but one clearly dominates the overall expressed stance, use the dominant label and explain the mixture in notes. If neither dominates, leave the sentiment cell blank and write `mixed_no_dominant_polarity` in notes. Do not force balanced mixed sentiment into Neutral; it expresses sentiment even when polarity is unresolved. The later study protocol must decide how to handle such unresolved cases before evaluation.

## Sarcasm, irony, slang and emoji

Interpret the intended attitude when textual cues support it. An explicit sarcasm marker, contradiction within the comment or conventional ironic phrasing can reverse literal wording. Invented example: “Amazing, another crash. /s” is negative if the sarcastic complaint is clear from those words. If irony requires seeing the video or guessing a speaker's intention, leave the label blank and note `sarcasm_uncertain`.

Read slang, abbreviations, repeated letters, capitalization and punctuation in context. Do not normalize or delete them. Emoticons and emoji can carry or intensify sentiment; laughter may be enjoyment or mockery. A meaningful emoji-only reaction may be interpretable, but if its polarity or target is unclear, flag `emoji_uncertain` rather than automatically excluding it or choosing Neutral.

## Ambiguity and missing context

A short comment can be meaningful. An emotionless comment can be Neutral. A language/meaning/context problem is an uncertainty flag, not a sentiment class. When the text relies on unseen visual events, a parent comment, an unexplained reference or an ambiguous pronoun, leave the sentiment field blank and note `context_required`. Use `meaning_uncertain`, `language_uncertain` or `sentiment_uncertain` where appropriate. Do not view missing context to resolve it; all annotators and the later text-based model must receive equivalent evidence.

If text contains identifying/contact information, stop annotating that record and alert the researcher privately using its candidate ID. Do not copy that information into notes or a public report. Eligibility decisions and any later exclusions must be documented separately and must not depend on whether sentiment is easy for VADER.

## Handling unresolved records and the blank final field

Notes may flag more than one issue. Blank scores with explicit flags are valid unfinished decisions, not missing values to invent. After independent annotation, the researcher reviews genuine disagreements/uncertainties under an agreed adjudication protocol. final_human_sentiment stays blank until that separate process. Do not infer it automatically from the two labels now.

## Access, retention and sharing

Templates contain API-derived YouTube text and inherit the source's existing refresh/delete deadline; making a new template does not start a new retention period. Keep files private. Before sharing with annotators or submitting text, confirm permitted access and the relevant platform/institutional conditions. Separate copies and backups must receive deletion/refresh requests too. Source YouTube comments and metadata must not be retained indefinitely merely to preserve a frozen research record.
