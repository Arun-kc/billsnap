# BillSnap — Backend Architecture

> Designed: 2026-04-12. V1 single-tenant scope.

---

## ERD

```
users
  │
  ├─── 1:N ──── bills ────── 1:N ──── line_items
  │               │
  │               └──── 1:1 ──── ocr_jobs
  │
  └─── 1:N ──── audit_log
```

---

## Postgres Schema

### `users`

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    phone       VARCHAR(15) NOT NULL UNIQUE,   -- primary login identifier
    role        VARCHAR(20) NOT NULL DEFAULT 'owner'
                    CHECK (role IN ('owner', 'admin')),
    pin_hash    VARCHAR(255),                   -- optional 4-digit PIN
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Two rows in V1: shop owner + admin (Arun). Phone-based identity suits non-tech-savvy users.

---

### `ocr_jobs`

```sql
CREATE TYPE job_status AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'needs_review'
);
CREATE TYPE ocr_model_tier AS ENUM ('haiku', 'sonnet');

CREATE TABLE ocr_jobs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id),
    status                job_status NOT NULL DEFAULT 'pending',
    model_tier            ocr_model_tier NOT NULL DEFAULT 'haiku',
    original_file_key     VARCHAR(512) NOT NULL,      -- S3 key
    thumbnail_key         VARCHAR(512),
    file_content_type     VARCHAR(50) NOT NULL,
    file_size_bytes       INTEGER NOT NULL,
    extraction_confidence NUMERIC(4,2),
    extraction_notes      TEXT,
    raw_ocr_response      JSONB,                      -- full model response, for reprocessing
    error_message         TEXT,
    retry_count           SMALLINT NOT NULL DEFAULT 0,
    max_retries           SMALLINT NOT NULL DEFAULT 2,
    started_at            TIMESTAMPTZ,
    completed_at          TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ocr_jobs_status ON ocr_jobs(status) WHERE status IN ('pending', 'processing');
CREATE INDEX idx_ocr_jobs_user_id ON ocr_jobs(user_id);
```

---

### `bills`

```sql
CREATE TYPE document_type AS ENUM (
    'tax_invoice', 'bill_of_supply', 'credit_note', 'debit_note', 'receipt', 'other'
);

CREATE TABLE bills (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ocr_job_id            UUID NOT NULL UNIQUE REFERENCES ocr_jobs(id),
    user_id               UUID NOT NULL REFERENCES users(id),

    -- Vendor (OCR-extracted, user-editable)
    vendor_name           VARCHAR(255),
    vendor_gstin          VARCHAR(15),

    -- Identity (OCR-extracted, user-editable)
    bill_number           VARCHAR(100),
    bill_date             DATE,
    document_type         document_type NOT NULL DEFAULT 'tax_invoice',
    category              VARCHAR(100),

    -- Amounts in INR (OCR-extracted, user-editable)
    total_amount          NUMERIC(12,2),
    taxable_amount        NUMERIC(12,2),
    cgst_amount           NUMERIC(10,2) DEFAULT 0,
    sgst_amount           NUMERIC(10,2) DEFAULT 0,
    igst_amount           NUMERIC(10,2) DEFAULT 0,

    -- Review state
    is_verified           BOOLEAN NOT NULL DEFAULT false,
    user_notes            TEXT,
    extraction_confidence NUMERIC(4,2),

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_bills_user_date     ON bills(user_id, bill_date);
CREATE INDEX idx_bills_vendor_gstin  ON bills(vendor_gstin) WHERE vendor_gstin IS NOT NULL;
CREATE INDEX idx_bills_unverified    ON bills(is_verified) WHERE is_verified = false;
```

---

### `line_items`

```sql
CREATE TABLE line_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id     UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    item_name   VARCHAR(255),
    hsn_code    VARCHAR(8),
    quantity    NUMERIC(10,3),
    unit        VARCHAR(20),
    unit_price  NUMERIC(10,2),
    total_price NUMERIC(12,2),
    gst_rate    NUMERIC(4,2),
    sort_order  SMALLINT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_line_items_bill_id ON line_items(bill_id);
```

Line items are optional — many Indian bills have only a total with no itemized breakdown.

---

### `audit_log`

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    entity_type VARCHAR(50) NOT NULL,   -- 'bill', 'line_item', 'ocr_job'
    entity_id   UUID NOT NULL,
    action      VARCHAR(20) NOT NULL,   -- 'create', 'update', 'delete', 'verify'
    changes     JSONB,                  -- {field: {old: x, new: y}}
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Shared `updated_at` Trigger

```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at      BEFORE UPDATE ON users      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_bills_updated_at      BEFORE UPDATE ON bills      FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_line_items_updated_at BEFORE UPDATE ON line_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_ocr_jobs_updated_at   BEFORE UPDATE ON ocr_jobs   FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## S3 / Object Storage Structure

```
billsnap-storage/
├── uploads/
│   └── {user_id}/
│       └── {YYYY}/{MM}/
│           └── {ocr_job_id}.{ext}          # original file (jpeg, png, pdf)
│
├── thumbnails/
│   └── {user_id}/
│       └── {YYYY}/{MM}/
│           └── {ocr_job_id}_thumb.webp     # compressed preview, max 800px wide
│
└── exports/
    └── {user_id}/
        └── {YYYY-MM}_bills.{csv|xlsx}      # ephemeral, TTL 24h
```

- All objects private. Frontend receives short-lived signed URLs (15 min).
- No user-supplied filenames in storage — ocr_job_id as filename only.
- Exports generated on demand, not persisted.

---

## API Contracts

Base path: `/api/v1`

Auth V1: static Bearer tokens per user (`AUTH_TOKEN_OWNER`, `AUTH_TOKEN_ADMIN` in env).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/bills/upload` | Upload a bill image/PDF → returns `job_id` (202) |
| `GET`  | `/jobs/{job_id}` | Poll OCR job status |
| `GET`  | `/bills` | List bills (`?month=`, `?verified=`, `?category=`, pagination) |
| `GET`  | `/bills/{bill_id}` | Full bill detail + line items + signed image URLs |
| `PATCH`| `/bills/{bill_id}` | Update fields + full line_items array replace |
| `GET`  | `/bills/export` | Stream CSV or Excel (`?month=`, `?format=csv\|xlsx`) |
| `DELETE`| `/bills/{bill_id}` | Hard delete + S3 cleanup |
| `GET`  | `/dashboard` | Monthly summaries for last N months |

### Key shapes

**POST /bills/upload → 202**
```json
{ "job_id": "uuid", "status": "pending" }
```

**GET /jobs/{job_id} → 200**
```json
{ "job_id": "uuid", "status": "completed", "bill_id": "uuid", "extraction_confidence": 0.87 }
```

**GET /bills → 200**
```json
{
  "bills": [{ "id": "uuid", "vendor_name": "...", "bill_date": "2026-04-10",
               "total_amount": 1250.00, "is_verified": false, "thumbnail_url": "..." }],
  "pagination": { "page": 1, "per_page": 20, "total": 47 },
  "summary": { "total_amount": 34520.00, "total_cgst": 1850.00, "total_sgst": 1850.00,
                "bill_count": 47, "unverified_count": 5 }
}
```

**PATCH /bills/{id}** — partial update; `line_items` array fully replaces existing items when present.

---

## Async Processing

**Decision: In-process background worker (no Redis/Celery).**

An async coroutine started at FastAPI startup polls `ocr_jobs` for `status = 'pending'` every 3 seconds. Stuck jobs (`processing` for > 5 min) are auto-reset to `pending` on startup.

### Job State Machine

```
upload → pending → processing → completed
                             └→ needs_review  (retry with Sonnet if retry_count < max)
                             └→ failed
```

Confidence threshold for Sonnet retry: `< 0.70` (tunable).

---

## Project Structure

```
billsnap/
├── alembic/                    # DB migrations
├── app/
│   ├── main.py                 # FastAPI app + startup
│   ├── config.py               # pydantic-settings
│   ├── dependencies.py         # get_db, get_current_user
│   ├── models/                 # SQLAlchemy: user, bill, line_item, ocr_job, audit_log
│   ├── schemas/                # Pydantic: bill, ocr_job, export, dashboard
│   ├── routers/                # bills, jobs, export, dashboard
│   ├── services/               # ocr_service, bill_service, export_service, storage_service
│   └── workers/
│       └── ocr_worker.py
├── tests/
├── docs/
│   └── architecture.md         # this file
├── evals/
│   └── ocr_benchmark/
├── pyproject.toml
├── Dockerfile
└── .env.example
```

---

## Architectural Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| ADR-001 | Static Bearer token auth | Two known users, V1. Replace with phone+OTP when onboarding external businesses. |
| ADR-002 | In-process worker, no task queue | Under 10 bills/day makes Redis/Celery over-engineering. DB state machine provides durability. |
| ADR-003 | Full line-item array replace on PATCH | Simpler frontend logic; negligible DB overhead for ≤20 items. |
| ADR-004 | Store raw OCR response as JSONB | Enables reprocessing with improved prompts without re-calling the API. |
| ADR-005 | Haiku-first, Sonnet fallback at < 0.70 confidence | Keeps avg cost ~₹0.35/bill; Sonnet only for hard cases. Threshold tunable. |

---

## V1 Cost Estimate

| Item | Provider | Cost/month |
|------|----------|-----------|
| Postgres + Storage | Supabase free tier | ₹0 |
| Compute | Railway/Render starter | ₹0–500 |
| OCR (100 bills, 80% Haiku / 20% Sonnet) | Anthropic API | ~₹60 |
| **Total** | | **~₹300–800** |

---

## Deferred to V2

- Multi-tenancy / organisations
- Role-based access control
- Duplicate bill detection
- WhatsApp upload integration
- Direct GST filing / GSTR integration
- Bulk upload
