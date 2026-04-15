# OCR Optimization — Plan & Baseline

> Created 2026-04-15 after running the current production OCR against 8 labelled fixtures.
> Source of truth for the next multi-stage rewrite. Delete this doc once all stages are shipped and measured.

## Goals (per Arun, 2026-04-15)

1. **Accuracy first.** Every field on the export sheet must be right. Today it is not.
2. **Speed second.** User must not wait > 3 s for a single-bill result.
3. **Perspective classification.** Each bill must be tagged as `purchase` / `sales` / `credit_note` so the export splits cleanly.
4. **Multi-user.** Product will serve more than Arun's father. Never hardcode Babu Electrical or `32AVTPC7423K1ZE` in app code — store on `users` table.

## Baseline (unoptimised, current `ocr_service.py`)

Run at `evals/ocr_benchmark/results/baseline_20260415_181817.json`.

| Metric | Value |
|---|---|
| Perspective accuracy | 50% (4/8) |
| Field accuracy | 53% (26/49) |
| Avg latency | 18.9 s |
| Avg cost | ₹1.54 / bill |
| Worst case | `billsample3.jpeg`: 41 s, ₹4.16, 0 fields extracted |

### Failure taxonomy observed

1. **DD/MM/YY date parsing** — 4/8 bills wrong. Model flips day/month or treats `26` as the year incorrectly.
2. **GSTIN character-swap** — `AASFP→AASEP` (F↔E), `AAOFT→AAQFT` (O↔Q), once full hallucination `32AAOFT→24AABCT`.
3. **Party confusion** — `billsample5`: claude swapped `vendor_gstin` with owner's `32AVTPC7423K1ZE`, causing "sales" classification on a purchase bill.
4. **Document-type miss** — `billsample4` (credit note `CDNR25-26/00532`) extracted as tax_invoice with data from an adjacent reference on the page.
5. **Full failure on low-quality image** — `billsample3` went to Sonnet fallback, returned all nulls, cost ₹4.16.
6. **Sonnet over-firing** — 5 of 8 bills triggered fallback. Each adds 10–20 s. Retry gate is too permissive.

## Staged plan

### Stage 1 — Accuracy via prompt + classifier (no schema changes)

Files touched:
- `app/services/ocr_service.py` — rewrite `EXTRACTION_PROMPT`; accept owner GSTIN as kwarg; tighten `_needs_sonnet_retry`.
- `app/services/classifier.py` (new) — `classify(extracted, owner_gstin) -> Literal["purchase","sales","credit_note","unknown"]`.
- Callsite in `app/workers/ocr_worker.py` — pass `user.gstin` through (nullable OK; classifier returns "unknown" when absent).
- Re-run `evals/ocr_benchmark/score_baseline.py` → save as `stage1_*.json`.

Prompt rewrite must include:
- "Dates on Indian bills are DD/MM/YY or DD/MM/YYYY. Year `26` = 2026. Never swap day and month."
- Owner GSTIN injected: "The user's own GSTIN is `<OWNER_GSTIN>` (if provided). If you see this on the bill, it belongs to the BUYER, not the VENDOR."
- Explicit credit-note title detection step: "Look for 'Credit Note', 'Debit Note', 'CDNR', 'DBNR' in the title or header BEFORE extracting any other field."
- PAN entity-letter sanity: 4th char of PAN ∈ {P, F, C, H, A, T, B, L, J, G}. Prefer `F` on business letterheads over `P`.
- Drop `raw_text` and `line_items` from the primary response — not used by V1 export.
- Reduce `max_tokens` from 3072 → 800.

Sonnet retry gate (tightened):
- Retry only if `total_amount` is null OR `vendor_gstin` fails regex OR word-form/numeric scale mismatch.
- Do NOT retry based on `confidence == "medium"` alone.

Target: perspective 100%, field accuracy ≥ 85%, latency ≤ 8 s (still without caching).

### Stage 2 — Latency via caching + image pipeline

- Anthropic prompt caching (`cache_control: ephemeral`) on the static instruction block.
- Image preprocessing in `_fix_orientation`: downscale to max 1600 px; autocontrast when histogram variance is low (helps `bill3.jpeg` and `billsample3.jpeg`).
- Parallelise Sonnet retry (kick off both Haiku and Sonnet when structural pre-check fails on the *image bytes* — but defer if complexity too high).

Target: avg latency ≤ 3 s, cost ≤ ₹0.40 / bill.

### Stage 3 — Schema + UI + export

- Alembic migration: `users.gstin`, `users.shop_name`, `users.state_code` (all nullable).
- Seed migration: populate owner row with `32AVTPC7423K1ZE` / `Babu Electrical` / `32`.
- Alembic migration: `bills.perspective` enum `purchase | sales | credit_note | unknown` default `unknown`.
- Bill service: persist classifier output on creation.
- Review screen: segmented control for perspective so user can correct.
- Export: split into 3 sheets (`Purchases`, `Sales`, `Credit Notes`).

## What the user still needs to do

- Open `evals/ocr_benchmark/sample_bills/billsample3.jpeg` by eye. If unreadable to a human, add to a "must-review" cohort; don't blame OCR.
- Confirm GSTIN caps convention (user said "should be uppercase" — we will normalise everywhere).

## Ground truth file

`evals/ocr_benchmark/sample_bills/ground_truth.yaml` — 8 fixtures with owner block. Do NOT commit the sample images if they contain real business data; the YAML alone is enough for regression.

## Scoring harness

`evals/ocr_benchmark/score_baseline.py` — runs prod OCR async against fixtures, prints a per-field verdict table, saves JSON report to `results/`. Re-used at the end of each stage.
