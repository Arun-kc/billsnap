# Project: BillSnap - Bill & Receipt Digitization for Indian SMEs

## Mission

BillSnap helps Indian small shop owners digitize their bills without typing anything.
The primary user is a non-tech-savvy shop owner (40s–60s, South India) who currently
relies on a family member to manually enter bills into Excel at the end of every quarter.

BillSnap eliminates that quarterly crunch: snap a photo of a bill, confirm the extracted
details, and export a clean spreadsheet for your accountant — in minutes, not hours.

The V1 scope:
- Single-tenant, mobile-first web app.
- Upload image/PDF → OCR extraction → user review/edit → monthly CSV/Excel export.
- No full accounting, no direct GST filing, no multi-org features, no email automation.

## Tech Stack & Constraints

- Backend: Python (FastAPI) OR Node (Express/Nest) – decide once and stay consistent.
- Frontend: React / Next.js with a simple, mobile-friendly UI.
- Data: Postgres for metadata, object storage (S3-compatible) for bill images.
- OCR: Start with a commercial invoice OCR API + LLM mapping into our schema.
- Security: Never log or print raw keys or full personal identifiers.
- Testing: Use ECC TDD workflows; critical functions must have tests.

## Subagents & AI Teams

Use these global subagents from Everything Claude Code for engineering tasks:
- `planner` – feature planning and breakdown.
- `architect` – system and data model design.
- `tdd-guide` – test-first implementation.
- `code-reviewer` – style, correctness, and refactor suggestions.
- `security-reviewer` – security, PII handling, and compliance considerations.

Use these Agency Agents for auxiliary work:
- Engineering: `Frontend Developer`, `Backend Architect`, `DevOps Automator`.
- Product: `Product Manager`, `Sprint Prioritizer`.
- Marketing: `Growth Hacker`, `Content Creator`, `SEO Specialist`.
- Ops/Analytics: `Analytics Reporter`, `Finance Tracker`.
- Quality: `Reality Checker` for “is this ready to show to real users?”.

When I say “delegate” or “activate” one of these roles in a prompt,
switch into that agent’s mode and follow its documented workflow.

## Workflow Rules for This Repo

- Always start new features with `planner` and `architect` to:
  - Clarify user stories and acceptance criteria.
  - Propose minimal data models and API contracts.

- Implementation:
  - Use `tdd-guide` to write tests before or alongside code for core flows.
  - Keep backend and frontend cleanly separated, with clear API contracts.

- Quality & Security:
  - Before calling anything “done”, run `code-reviewer` and `security-reviewer`
    over the relevant files.
  - Never hardcode secrets; use environment variables and clearly mark
    placeholders in the code.

- Documentation:
  - Use `doc-updater` (if available in ECC) or an Agency Technical Writer agent
    to keep README and API docs in sync with code changes.

- Marketing & Launch:
  - For landing page copy, emails, and content, use
    `Growth Hacker` + `Content Creator` + `SEO Specialist`.
  - Use `Analytics Reporter` to define and refine KPIs and simple dashboards.

## Project Context You Should Remember

- **First user:** Arun's father — 60s, electric shop owner in Kerala, not tech-savvy,
  uses smartphone for WhatsApp. Full dependency on Arun for bill digitization today.
- **Primary pain:** Bills pile up all quarter, then require hours of manual Excel entry.
- **Primary value:** Eliminate the quarterly crunch; let the shop owner self-serve
  with minimal handholding after initial setup.
- **V1 success signal:** "That was easy and it saved a lot of time." (self-reported)
- **Budget:** ₹1,000–5,000/month for OCR + hosting. Keep costs minimal until user base grows.
- **Build pace:** ~8 hrs/week.
- Phase 1: Build a version that works for Arun's father without external help.
- Phase 2: Onboard 3–5 friendly local businesses and learn from their usage.

## Brand & Product Decisions

- **Name:** BillSnap
- **Tagline:** "Snap a bill. Done."
- **Tone:** Warm, encouraging, jargon-free. Like a patient younger family member who
  explains things simply. Never corporate, never condescending.
- **Brand adjectives:** Effortless · Trustworthy · Local
- **Core messages (repeat everywhere):**
  1. "No more typing bills by hand."
  2. "Ready for your accountant in minutes, not hours."
  3. "Works in your language, at your pace."
- **Language strategy:** English UI by default. Malayalam labels on the 3 key
  actions (Upload, Review, Export) in V1. Full regional language toggle in V2.
- **Design references:** Swiggy (friendliness), Apple (clarity), Airbnb (trust).
  Mobile-first. Large tap targets, simple forms, step-by-step guidance.

## What You Should Ask Before Big Changes

Before major architectural decisions, changing OCR vendors, or altering
the data model, ask me:
- Which segment we care about first (family, shop, freelancer, etc.).
- What problems we’ve seen with accuracy and review time so far.
- Any feedback or complaints from early users.

## Team Collaboration & Kickoff Workflow

For high-level planning, one agent acts as Orchestrator:
- Prefer `planner` (ECC) for technical/feature planning.
- Prefer `Agency Orchestrator` (from Agency Agents) when the work
  spans product, brand, and marketing in addition to engineering.

When I say "run a workshop" or "run a kickoff", the Orchestrator must:
1. Ask me 5–10 focused questions to clarify:
   - Target users and geography
   - The main problem we solve
   - How success is measured (e.g., time saved, fewer errors)
   - Budget/constraints (time, money, tech)
   - Any initial ideas for name/branding

2. Summarise my answers back to me and wait for my confirmation.

3. Coordinate a small team of specialists:
   - Product: `Product Manager`, `Sprint Prioritizer`
   - Brand/Marketing: `Growth Hacker`, `Content Creator`, `SEO Specialist`
   - Engineering: `architect`, `Frontend Developer`, `Backend Architect`

4. Produce:
   - A 1-page product brief (problem, audience, solution, scope of V1)
   - 3–5 name & tagline options
   - A simple brand direction (tone, 2–3 colours, key messages)
   - A short initial launch plan (how to get first 5–10 users)

5. Propose concrete edits to CLAUDE.md under:
   - Mission
   - Target users
   - Brand & product decisions
   - Roadmap

Do NOT silently edit CLAUDE.md. Always show me the proposed changes
first and apply them only after I approve.