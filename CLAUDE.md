# BillSnap Project Instructions

## Mission
BillSnap helps non-tech-savvy Indian small business owners digitize paper bills and receipts by taking a photo, reviewing extracted details, and exporting accountant-ready spreadsheets.

## Primary user
The first target user is Arun's father: a Kerala electric shop owner in his 60s who uses a smartphone mainly for WhatsApp and currently depends on Arun to enter bills into Excel every quarter.

## Product goal
Eliminate the quarterly bill-entry crunch. The product should feel simple, reassuring, and self-serve after initial setup.

## V1 scope
Build and maintain only this flow:
- Upload bill image or PDF
- Run OCR extraction
- Map OCR data into BillSnap schema
- Let user review and edit extracted details
- Export monthly CSV or Excel for accountant use

## V1 non-goals
Do not add these unless the user explicitly approves:
- Full accounting system features
- GST filing
- Multi-tenant or multi-organization support
- Email automation
- Complex analytics dashboards
- Deep ERP integrations

## Repo structure
- `app/` = FastAPI backend
- `web-app/` = main product UI in Next.js
- `landing/` = marketing/waitlist site
- `tests/` = backend tests
- `evals/ocr_benchmark/` = OCR experiments and benchmarking
- `docs/` = product and architecture context

## Technical decisions
- Backend: Python + FastAPI
- Frontend: Next.js
- Data: Postgres for metadata
- Files: S3-compatible object storage
- OCR: commercial OCR API plus LLM/schema mapping
- Migrations: Alembic

Stay consistent with this stack. Do not introduce a second backend stack.

## Coding rules
- Keep backend layered: routers -> services -> models/schemas.
- Keep frontend mobile-first and simple.
- Prefer small, reversible changes.
- Reuse existing modules before adding new abstractions.
- Avoid premature generic frameworks inside the repo.
- Keep code readable for future Claude sessions and human review.

## Testing rules
Critical flows must have tests or updated tests:
- OCR mapping and normalization
- Bill creation and update flows
- Export formatting and totals
- Worker/job processing behavior
- Core API routes

When changing critical logic, update tests in the same task.

## Security and privacy rules
- Never log raw API keys, secrets, or tokens.
- Never log full personal identifiers or raw OCR payloads unless explicitly redacted.
- Treat uploaded bills and receipts as sensitive business documents.
- Validate uploaded file types and sizes.
- Use environment variables for secrets.
- Flag security-sensitive changes for review.

## UX rules
- Default to mobile-first UX.
- Use warm, jargon-free language.
- Optimize for users in their 40s-60s with low technical confidence.
- Use large tap targets and step-by-step flows.
- Malayalam helper labels are useful on key actions like Upload, Review, and Export.

## Ask before major changes
Pause and ask before making any of these changes:
- Changing OCR vendor or OCR response mapping strategy
- Changing core bill/export schema
- Adding auth complexity or multi-tenant architecture
- Merging `landing/` and `web-app/`
- Expanding product scope beyond V1

## Recommended workflow
For significant feature work:
1. Use the local `planner` agent to produce user story, acceptance criteria, and tasks.
2. Use the local `architect` agent if the feature affects API contracts, schema, storage, workers, or cross-app boundaries.
3. Use the local `tdd-guide` agent for critical logic before implementation.
4. Implement the smallest working vertical slice.
5. Use the local `code-reviewer` and `security-reviewer` before calling work done.
6. Use `doc-updater` when docs, setup, API behavior, or flows changed.

## Files to consult
@docs/product-brief.md
@docs/architecture.md