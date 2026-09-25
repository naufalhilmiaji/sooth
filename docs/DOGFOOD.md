# Dogfood log — week of 2026-09-25

Run Sooth on your own real AI output before building anything new. One row per session. Findings here drive Phase 4/5 decisions.

## Loop (5 min per draft)

1. Take an AI draft you were about to trust (reply, summary, PR description, doc).
2. `sooth --source <the ground truth> --text <the draft> --log dogfood.jsonl`
3. Read the report. Mark each verdict right/wrong by your own eyes.
4. Log one row below.

| Date | Draft type | Verdicts right/wrong | Surprise (if any) | Want next |
|------|------------|----------------------|-------------------|-----------|
|      |            |                      |                   |           |

## Question this answers

Does anyone actually paste ground truth + draft and act on the report? If the tool dies on real drafts (formatting, length, language), Phase 4 chunking/URL input jumps the queue. If the report is ignored even when right, the web app idea is wrong.
