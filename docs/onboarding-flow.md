# BillSnap — Onboarding Flow Design

> Designed: 2026-04-13. V1 single-user scope.
> Target user: Arun's father, 60s, Kerala electric shop owner, not tech-savvy.
> Constraints: mid-range Android (360–393px wide, ~6"), one-handed use, WhatsApp-level familiarity.

---

## Flow Overview

```
[Screen 1: Snap]  →  [Loading: Reading...]  →  [Screen 2: Review]  →  [Screen 3: Done]
      ↑                                               |
      └─────────────── Retake photo ─────────────────┘
```

Three screens, no dead ends. Every error has a clear recovery path.

---

## Screen 1 — Snap / Upload

**Purpose:** Get a photo of the bill into the app with zero friction.

### Layout (portrait, bottom-thumb zone first)

```
┌─────────────────────────────┐
│  ← Back          Step 1/3  │  ← top bar, minimal
│                             │
│  ┌─────────────────────────┐│
│  │                         ││
│  │   [Bill preview area]   ││  ← full-width, 16:9 aspect ratio
│  │   or camera viewfinder  ││     placeholder: faint dotted border
│  │                         ││     + bill icon in center
│  └─────────────────────────┘│
│                             │
│  Hold the bill flat         │  ← instruction, 16sp, muted colour
│  and fit it inside the box  │
│                             │
│  ┌─────────────────────────┐│
│  │  📷  Take Photo          ││  ← PRIMARY CTA, 56px height, full width
│  │  ഫോട്ടോ എടുക്കൂ           ││     Malayalam subtitle below English
│  └─────────────────────────┘│
│                             │
│  [ Choose from gallery ]    │  ← secondary, text button, smaller
│                             │
└─────────────────────────────┘
```

### After capture — preview step

```
┌─────────────────────────────┐
│  ← Retake        Step 1/3  │
│                             │
│  ┌─────────────────────────┐│
│  │                         ││
│  │   [Captured bill photo] ││  ← full photo, zoomable via pinch
│  │                         ││
│  └─────────────────────────┘│
│                             │
│  ┌─────────────────────────┐│
│  │  ✓  Use this photo       ││  ← PRIMARY CTA
│  └─────────────────────────┘│
│                             │
│  [ Retake ]                 │  ← secondary text button
│                             │
└─────────────────────────────┘
```

### Design rules for this screen
- Camera button sits in the bottom 40% of the screen — reachable with one thumb.
- No file format jargon. Never say "JPEG" or "PNG" to the user.
- If the photo is clearly blurry (detect on client via blur score), show an inline warning before "Use this photo" becomes active.
- Aspect ratio guide overlay on viewfinder helps frame the bill.
- No permissions dialog during onboarding — camera permission is requested the first time this screen loads (Android system dialog, before the UI appears).

---

## Loading State — "Reading your bill"

Shown after "Use this photo" while the image uploads and OCR runs (~5–15 seconds on 4G).

```
┌─────────────────────────────┐
│              Step 2/3       │
│                             │
│                             │
│         🔍                  │  ← large icon, centered
│                             │
│   Reading your bill...      │  ← 20sp, friendly
│                             │
│   ══════════░░░░  65%       │  ← animated progress bar
│                             │
│   This takes about          │
│   10–15 seconds             │  ← muted helper text
│                             │
│                             │
│   [ Cancel ]                │  ← escape hatch, bottom
│                             │
└─────────────────────────────┘
```

### Design rules
- Progress bar animates continuously (fake progress is OK — real progress is unavailable from OCR API).
- Do not show a spinner alone. The progress bar + timer copy reduces anxiety for older users unfamiliar with "loading" metaphors.
- If OCR takes > 30 seconds: show "Still working, almost there..." to prevent abandon.
- If OCR fails: do not show a technical error. Go directly to Screen 2 with blank fields and a friendly explanation (see Error States section).

---

## Screen 2 — Review & Edit

**Purpose:** Let the user confirm or correct what the app extracted. This is the trust-building step.

### Layout

```
┌─────────────────────────────┐
│  ← Back          Step 2/3  │
│                             │
│  ┌──────┐                  │
│  │ Bill │  Sharma Elec...  │  ← thumbnail (60×80px) + vendor name
│  │ thumb│  12 Apr 2026     │     date beside it
│  └──────┘                  │
│  ─────────────────────────  │
│                             │
│  Vendor Name                │  ← label, 12sp muted
│  ┌─────────────────────────┐│
│  │ Sharma Electricals      ││  ← input, 18sp, 48px height
│  └─────────────────────────┘│
│                             │
│  Date                       │
│  ┌─────────────────────────┐│
│  │ 12 April 2026       📅  ││  ← date picker trigger
│  └─────────────────────────┘│
│                             │
│  Total Amount (₹)           │
│  ┌─────────────────────────┐│
│  │ 1,234.00                ││  ← number input, 22sp (larger than others)
│  └─────────────────────────┘│
│                             │
│  Category                   │
│  ┌─────────────────────────┐│
│  │ Electrical Supplies  ▼  ││  ← dropdown/bottom sheet picker
│  └─────────────────────────┘│
│                             │
│  [ More details ▼ ]         │  ← collapsed: GSTIN, doc type, notes
│                             │
│  ┌─────────────────────────┐│
│  │  ✓  Looks good!          ││  ← PRIMARY CTA, 56px, sticky bottom
│  │     ശരി                  ││     Malayalam subtitle
│  └─────────────────────────┘│
└─────────────────────────────┘
```

### "More details" expanded (collapsed by default)

```
│  ▲ More details             │
│                             │
│  Bill Number                │
│  ┌─────────────────────────┐│
│  │ INV-2026-042            ││  ← free text, no validation
│  └─────────────────────────┘│
│                             │
│  Document Type              │
│  ┌─────────────────────────┐│
│  │ Tax Invoice          ▼  ││
│  └─────────────────────────┘│
│                             │
│  Vendor GSTIN               │
│  ┌─────────────────────────┐│
│  │ 32AABCU9603R1ZX         ││
│  └─────────────────────────┘│
│                             │
│  ── Tax Breakdown ─────────  │  ← muted section divider, not a card
│                             │
│  Taxable Amount (₹)         │
│  ┌─────────────────────────┐│
│  │ 1,045.76                ││
│  └─────────────────────────┘│
│                             │
│  CGST (₹)    SGST (₹)       │  ← side-by-side pair
│  ┌──────────┐ ┌────────────┐│     CGST = SGST for intra-state
│  │  94.12   │ │   94.12    ││     (Kerala shop common case)
│  └──────────┘ └────────────┘│
│                             │
│  GST Rate                   │
│  18%  (computed)            │  ← read-only: (cgst+sgst)/taxable×100
│                             │
│  IGST Amount (₹)            │
│  ┌─────────────────────────┐│
│  │ 0.00                    ││  ← greyed out; non-zero for inter-state
│  └─────────────────────────┘│
│                             │
│  Notes (optional)           │
│  ┌─────────────────────────┐│
│  │                         ││  ← free text
│  └─────────────────────────┘│
```

### Design rules for this screen
- The 4 primary fields (Vendor, Date, Amount, Category) are always visible without scrolling on a 6" screen.
- GSTIN, Document Type, and Notes are hidden under "More details" — the shop owner rarely needs to touch these.
- Low-confidence fields get a **soft amber left border** (not red, not an error icon). Hover tooltip (long-press): "We're not fully sure about this — please check."
- Total Amount uses a larger font size (22sp) to make it the visual anchor of the screen. Money is what the user cares about most.
- Category dropdown uses plain language labels (no GST chapter codes):
  - Electrical Supplies
  - Tools & Equipment
  - Packaging
  - Office & Stationery
  - Transport & Delivery
  - Other
- "Looks good!" CTA is sticky at the bottom — always visible even when keyboard is open. Use `adjustResize` window soft input mode on Android + CSS `env(safe-area-inset-bottom)`.
- "I'll fix this later" is not a button — users can tap "Looks good!" even with wrong data. They can always edit from the bills list.
- **Bill Number** is free-text with no format validation — some handwritten bills have no number at all.
- **CGST and SGST** are rendered as a side-by-side pair. For intra-state Kerala purchases (the common case), these two values are always equal. Editing one does NOT auto-fill the other — keep them independent so the user can correct unusual bills.
- **GST Rate %** is a read-only computed display: `(cgst_amount + sgst_amount) / taxable_amount × 100`. Label: "GST Rate". Value format: "18% (computed)". Do not expose it as an editable field.
- **IGST Amount** is shown greyed/muted by default (value is typically 0 for intra-state). Keep it editable so the user can correct inter-state purchases if needed.
- Tax breakdown sits under a thin muted divider labelled "Tax Breakdown" — not inside a card or elevated surface.

---

## Screen 3 — Done

**Purpose:** Celebrate the win. Give the user one clear next action.

### Layout

```
┌─────────────────────────────┐
│                 Step 3/3   │
│                             │
│                             │
│          ✅                 │  ← 80px icon, green, centered
│                             │
│    Bill saved!              │  ← 24sp, bold
│                             │
│    ₹1,234 from              │  ← 18sp, summary line
│    Sharma Electricals       │
│    12 April 2026            │
│                             │
│  ─────────────────────────  │
│                             │
│  ┌─────────────────────────┐│
│  │  📷  Add another bill    ││  ← PRIMARY CTA
│  │      വേറൊന്ന് ചേർക്കൂ   ││     Malayalam subtitle
│  └─────────────────────────┘│
│                             │
│  [ View all bills ]         │  ← secondary text button
│                             │
│                             │
└─────────────────────────────┘
```

### Design rules for this screen
- The ✅ icon should animate in (scale from 0 → 1 with a gentle spring, ~300ms). This single moment of delight is the memory the user takes away.
- Summary line uses plain language: "₹1,234 from Sharma Electricals" — not "Bill ID: abc-123".
- Primary CTA is "Add another bill" because in a real session, the shop owner typically has a stack of bills to process.
- "View all bills" takes the user to the bills list (the main app screen).
- If it's the last week of the month, show a third option: "Export this month" as a text button.
- No "Share" or social features on this screen.

---

## Error States

### 1. Blurry photo (detected client-side before upload)

```
[ Warning banner above "Use this photo" CTA ]
⚠️  This photo looks blurry. Try again in better light or hold the phone steady.
[ Retake ]   [ Use anyway ]
```

### 2. OCR could not read the bill

Shown on Screen 2 with all fields blank:

```
[ Info banner at top of Screen 2 ]
ℹ️  We couldn't read this bill clearly. Please fill in the details below.
```
- All fields editable, none highlighted amber.
- User fills in manually and taps "Looks good!"
- This is not a failure — it's a graceful fallback. Frame it as "you're in control now."

### 3. Network error during upload

```
[ Bottom sheet ]
No internet connection

Your photo is saved on this device.
We'll upload it automatically when you're back online.

[ OK ]
```
*(Note: actual offline queue is a V2 feature — in V1 this is shown as an error with a retry button instead.)*

V1 actual message:
```
Couldn't upload the bill

Please check your connection and try again.

[ Try again ]   [ Cancel ]
```

### 4. File too large (> 10 MB)

```
[ Inline error on Screen 1 ]
This photo is too large (max 10 MB). Try lowering your camera quality in Settings, or crop the image.
```

### 5. Unsupported file type (from gallery)

```
[ Inline error on Screen 1 ]
Only JPEG and PNG photos are supported. PDFs will be added soon.
```

---

## Component Inventory (for frontend developer)

| Component | Notes |
|---|---|
| `BillCaptureView` | Camera viewfinder + capture button + gallery picker |
| `BillPreviewView` | Photo preview + "Use this" / "Retake" |
| `OcrLoadingView` | Animated progress bar + friendly copy |
| `ReviewForm` | 4 primary fields + collapsible "More details" section |
| `ConfidenceIndicator` | Amber left border on low-confidence fields |
| `CategoryPicker` | Bottom-sheet list (not a native select) |
| `DatePicker` | Bottom-sheet calendar (not native input[type=date] on Android) |
| `DoneView` | Animated checkmark + summary + two CTAs |
| `BillThumbnail` | 60×80px rounded image, shown on Screen 2 header |
| `TaxBreakdownGroup` | Section divider + Taxable Amount + CGST/SGST pair + GST Rate (computed, read-only) + IGST field |
| `ComputedField` | Read-only display field with muted "(computed)" label; used for GST Rate % |

---

## Accessibility & Android-specific rules

- Minimum tap target: **48×48 dp** for all interactive elements.
- Font sizes: **16sp minimum** for body, **18sp** for field values, **22sp** for Amount.
- Do not rely on colour alone to convey state — pair amber border with a label or icon.
- Test with TalkBack enabled: all images need `contentDescription`, all inputs need `labelledBy`.
- Keyboard behaviour: `android:windowSoftInputMode="adjustResize"` so the sticky CTA lifts above the keyboard.
- Category and Date pickers use **bottom sheets** (thumb-reachable) not top-of-screen dropdowns.
- Back button on Screen 2 goes to Screen 1 with the photo already loaded (not all the way out).

---

## Malayalam Labels (V1)

| Action | English | Malayalam |
|---|---|---|
| Take Photo | Take Photo | ഫോട്ടോ എടുക്കൂ |
| Confirm / Looks good | Looks good! | ശരി |
| Add another bill | Add another bill | വേറൊന്ന് ചേർക്കൂ |

These appear as subtitles under the English label on primary CTAs only.
Font: Noto Sans Malayalam (system font on Android 5+, no additional download needed).

---

## What this flow does NOT include (V1)

- PDF upload (show "coming soon" hint if user tries)
- Offline queue (V2)
- Duplicate detection
- Bill splitting across vendors
- Multi-page bills
- Any login/registration screen (bearer token is pre-configured by Arun during setup)
