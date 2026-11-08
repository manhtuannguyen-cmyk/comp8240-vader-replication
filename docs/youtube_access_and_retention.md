# YouTube API compliance checkpoint

Reviewed 3 November 2026. Scope: a private local research client using an API key, not uploader OAuth authorization. This report records implementation decisions and unresolved permission questions; it does not certify approval from YouTube.

## Findings from official policies

[YouTube Developer Policies](https://developers.google.com/youtube/terms/developer-policies), §III.E.4.d, permit temporary limited storage of non-authorized API data for at most 30 calendar days before deletion or refresh. Public access is not indefinite-storage permission. §III.E.4.e requires reasonable efforts to keep stored data current; §III.E.4.g addresses requested deletion within seven days. §III.E.2 restricts aggregation across different content owners, and §III.E.4.h restricts new/derived data or metrics. The proposed pooled four-channel corpus and later sentiment scores therefore need applicable research permission or a written clarification before this implementation enables the original combined-corpus stage. A valid API key alone does not resolve that use restriction.

[Complying with Developer Policies](https://developers.google.com/youtube/terms/developer-policies-guide) advises an API compliance audit when the permitted use is unclear. Its privacy guidance also prohibits harvesting identifying/sensitive information without consent. This client requests no commenter identities and no audiovisual content. Free text can still identify a writer; contact-pattern screening is imperfect and manual privacy review remains necessary.

[API Terms](https://developers.google.com/youtube/terms/api-services-terms-of-service) govern use of the service and returned data. A documentation page's CC-BY notice is not a licence to publish user comment text. The code does not assume raw API comments may be distributed through GitHub or submitted permanently as an unrestricted assessment archive. Keep data private; determine permitted university submission, retention and research use with the supervisor and YouTube before proceeding. If the assessment requires immutable raw text indefinitely, that conflicts with this refresh/delete design and must be resolved before collection.

## Implemented safeguards

- The supplied real key is only in the ignored local `.env`, with owner-only permissions. `.env.example` is generic. Logs/reports never print key-bearing URLs, raw errors or credentials.
- Official Google Python client only; partial API fields omit commenter names, channel/profile IDs, avatars and reply bodies. Top-level comments only. Video-owner channel IDs serve identity checks.
- A 29-day local expiry gives a margin before the 30-day maximum. Entry points purge expired API data and associated reports/summaries. `scripts/purge_expired.py` can be scheduled daily by the operator; no background deletion service is installed, so deadline compliance while idle remains the operator's responsibility.
- `scripts/delete_comments.py --comment-id ID` removes local matching data and invalidates sample/template derivatives. It does not delete content on YouTube. Deletions must also reach backups, notebook outputs and externally shared copies.
- `scripts/refresh_data.py --replace-data` explicitly deletes the old snapshot and recollects current data. It does not quietly preserve a historical raw copy. A changed frame/sample must be reported and revalidated.
- Cross-channel consolidation is gated by `research_data_use_confirmed` plus `research_permission_reference`. Enable only after the actual relevant permission/clarification exists, not merely after approving the sampling plan.

## API limitations affecting this protocol

The [comment resource](https://developers.google.com/youtube/v3/docs/comments) states that textOriginal is returned to an authenticated author; even plain-text textDisplay may differ from original text. The collector requests textOriginal and stops if unavailable. It never silently stores display text under the original-text field. A revised field/protocol requires approval if public access cannot return the required original text.

The [video resource](https://developers.google.com/youtube/v3/docs/videos) exposes no public isShort flag. Current [Shorts guidance](https://support.google.com/youtube/answer/15424877) limits Shorts to three minutes; a duration above 180 seconds provides sufficient non-Short evidence. Shorter/unknown durations fail verification.

The [commentThreads endpoint](https://developers.google.com/youtube/v3/docs/commentThreads/list) supports time ordering and token pagination. A bounded ten-page frame avoids using relevance ranking as sampling. Current API costs/limits are endpoint/project-specific; the client does not hardcode a presumed universal quota or rotate credentials.

## Current real execution

The API key works. All four approved videos passed verification. The user approved the exact Kylie upload Q-7yjWQ11kQ and title correction; the amendment is recorded. The user then clarified that the immediate objective is public comment download, not research analysis. Basic per-video API retrieval does not universally require a special research-program approval; the earlier pre-collection permission gate was too broad and has been removed.

The official API retrieved ten pages/1,000 top-level comments for each video (4,000 total), stored separately. textOriginal was available in these real responses. No raw profile fields, replies or audiovisual media were requested. No YouTube research permission reference was provided or inferred. Cross-channel pooling and sentiment analysis have not been performed. Automated eligibility screening produced separate per-video pools, exclusions and uncertainty flags; it has not hand-picked final samples or generated sentiment labels.

The oldest retained API timestamp and exact 29-day purge deadline are in retention_schedule.json. Refresh or delete source comments, metadata and their report copies by that deadline. There is no automatic background deletion service; the operator must run/schedule the purge command or delete the project data before expiry. These separate private files are not an unrestricted public-release dataset.
