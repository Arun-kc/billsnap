# BillSnap Brand Guidelines

> **Version:** 2.0 — April 2026
> **Status:** Approved — Direction E adopted
> This document is the single source of truth for BillSnap's visual identity, voice, and design system.

---

## 1. Brand Foundation

### Who we are

BillSnap helps Indian small shop owners digitize their bills without typing anything. Snap a photo, confirm the details, export for your accountant — in minutes, not hours.

### Primary user

A non-tech-savvy shop owner, 40s–60s, South India. Uses a smartphone for WhatsApp. Depends on a family member to manually enter bills into Excel every quarter. BillSnap eliminates that quarterly crunch.

### Brand adjectives

**Effortless · Trustworthy · Local**

### Tagline

> "Snap a bill. Done."

### Core messages (repeat everywhere)

1. No more typing bills by hand.
2. Ready for your accountant in minutes, not hours.
3. Works in your language, at your pace.

### Tone

Warm, encouraging, jargon-free. Like a patient younger family member who explains things simply. Never corporate, never condescending.

**Design references:** Swiggy (friendliness) · Apple (clarity) · Airbnb (trust)

---

## 2. Color System — Direction E

The palette is **Deep Aubergine + Yellow Gold**. Aubergine gives BillSnap gravitas and trust without being cold; gold is warm, premium, and reads as "value" — apt for a product that saves shop owners real money.

### Primary — Deep Aubergine

| Token | Hex | Use |
|---|---|---|
| `purple-600` | `#5C2D91` | Primary CTA buttons, active states, logo "Snap" wordmark |
| `purple-500` | `#7340BE` | Bill card body gradient start, icon body gradient |
| `purple-700` | `#3D1F78` | Button hover state, gradient end, deep shadow |
| `purple-800` | `#2A1450` | Darkest shade — drop shadow base, darkest gradient stop |
| `purple-50`  | `#F3EEF9` | Tinted backgrounds — badges, callouts, section backgrounds |
| `purple-100` | `#E2D5F4` | Subtle borders on purple elements |

**Contrast note:** White text on `#5C2D91` sits at ~8.1:1 — passes WCAG AAA. This is the primary interactive color.

### Accent — Yellow Gold

| Token | Hex | Use |
|---|---|---|
| `gold-500`   | `#C9A227` | Fold corner, lightning bolt, decorative accents |
| `gold-400`   | `#E8BF45` | Gradient highlight on bolt/fold |
| `gold-300`   | `#F5DC87` | Lightest gold — bolt top gradient, decorative highlights |
| `gold-600`   | `#A07A1A` | Deeper gold for hover states on gold elements |
| `gold-50`    | `#FBF6E7` | Tinted background for gold-themed elements |

### Trust Anchor — Ledger Green

| Token | Hex | Use |
|---|---|---|
| `ledger-green`       | `#1A8C5B` | Verified state, exported badge, success messages |
| `ledger-green-light` | `#E6F4EE` | Tinted background for verified/success states |

### Surfaces

| Token | Hex | Use |
|---|---|---|
| `surface`      | `#FBF8FF` | Page background — cool lavender-tinted white |
| `warm-white`   | `#FFFFFF` | Cards, modals, inputs |
| `surface-gray` | `#F0ECF8` | Dividers, disabled backgrounds |

> The surface uses `#FBF8FF` (vs. old `#FFFBF7` cream). It has a very slight cool-purple tint that harmonizes with the aubergine primary.

### Ink Scale (purple-tinted neutrals)

These neutrals have a warm purple undertone that sits naturally alongside the aubergine primary.

| Token | Hex | Use |
|---|---|---|
| `ink-900` | `#1A0D2E` | Primary text, headings, "Bill" wordmark |
| `ink-700` | `#3D1F78` | Secondary headings (same as purple-700 — deliberate) |
| `ink-500` | `#7A6690` | Supporting text, labels |
| `ink-300` | `#B8A8C8` | Placeholder text, disabled text |
| `ink-100` | `#E8DDF4` | Borders, dividers |

> Never use Tailwind's default `gray-*` or `slate-*` in BillSnap UI. They read as cold and disconnected from the aubergine brand.

### Semantic Colors

| Role | Hex | Light bg |
|---|---|---|
| Error   | `#D93025` | `#FFF1F2` |
| Warning | `#F59E0B` | `#FFFBEB` |
| Info    | `#2563EB` | — |

---

## 3. Typography

### Font pairing

| Font | Role | Source |
|---|---|---|
| **Urbanist** | Display — headings, hero, wordmark | Google Fonts |
| **Manrope**  | Body — paragraphs, labels, inputs, buttons | Google Fonts |
| **Noto Sans Malayalam** | Regional — 3 key action labels in V1 | Google Fonts (subset) |

Load maximum two font families on any single screen. Noto Sans Malayalam is subset-loaded only for the three Malayalam action labels (Upload, Review, Export).

### Type Scale

Fluid sizing with `clamp()`. Mobile values are the base; desktop values are the upper bound.

| Role | Font | Weight | Mobile | Desktop | CSS token |
|---|---|---|---|---|---|
| Hero H1 | Urbanist | 700 | 32px | 52px | `--text-hero` |
| H2 Section | Urbanist | 700 | 24px | 36px | `--text-h2` |
| H3 Card title | Urbanist | 600 | 18px | 22px | `--text-h3` |
| Body | Manrope | 400 | 16px | 17px | `--text-body` |
| Label / Button | Manrope | 600 | 15px | — | `--text-label` |
| Caption | Manrope | 400 | 13px | — | `--text-caption` |
| Input | Manrope | 400 | **16px fixed** | — | `--text-input` |

> **Input is always 16px.** iOS and Android auto-zoom on inputs with font-size below 16px. Never reduce input font below 16px.

### Letter-spacing

- Wordmark (`BillSnap`): `-0.02em`
- Display headings (Urbanist): `-0.01em` to `-0.02em`
- Body text: default (0)
- All-caps labels: `+0.05em`

---

## 4. Logo

### The Snap Bill Mark (icon)

A portrait bill rectangle with a folded top-right corner (gold), tilted −8° — instantly reads as a physical receipt. A gold lightning bolt (upright, not tilted) cuts across the top-right to represent the "snap" — instant digitization.

**Construction at 44px canvas:**
- Bill body: aubergine gradient (`#7340BE → #2A1450`), `rotate(-8 22 22)` transform
- Drop shadow: same path, `rgba(0,0,0,0.3)` fill, `translate(2 2)` offset, inside the rotate group
- Folded corner: gold gradient (`#E8BF45 → #A07A1A`), triangle path
- Ruled lines: 2 white lines at reduced opacity inside the bill body
- Lightning bolt: gold gradient (`#F5DC87 → #C9A227`), upright (no rotation), positioned top-right

**The lightning bolt path** (at 44px canvas):
```
M30,6 L21,20 L27,20 L24,32 L35,17 L29,17 Z
```

**Flat construction notes:**
- Gradients are used (not flat fills) — this is intentional for the icon; monochrome variant strips them
- No blur or raster effects — the mark renders cleanly at any size

### Wordmark

`BillSnap` in **Urbanist Bold 700**

- "Bill" in `#1A0D2E` (Ink 900)
- "Snap" in `#5C2D91` (Aubergine 600) on light backgrounds
- "Bill" in `#FFFFFF` + "Snap" in `#F5DC87` (gold) on dark backgrounds
- Letter-spacing: `-0.02em`

### Horizontal lockup proportions

- Icon: 44×44px; Wordmark: approximately 110px wide at the standard size
- Total lockup: 200px wide, 44px tall
- Gap between icon and wordmark: 10px
- Minimum rendered width: 80px (lockup), 16px (icon only)

### Color variants

| Variant | File | Use |
|---|---|---|
| Primary | `billsnap-logo.svg` | White/cream/lavender backgrounds |
| On-dark | `billsnap-logo-ondark.svg` | Dark or aubergine backgrounds — white "Bill" + gold "Snap" |
| Monochrome | `billsnap-logo-mono.svg` | Single-color print, fax, emboss — Ink 900 throughout |
| App icon | `billsnap-icon.svg` | Icon only, standalone |
| App icon on dark | `billsnap-icon-ondark.svg` | Icon on aubergine `#5C2D91` square — for app icon contexts |

### File inventory

```
logo/
├── billsnap-logo.svg              Primary horizontal lockup (light bg)
├── billsnap-logo-ondark.svg       White/gold wordmark on dark bg
├── billsnap-logo-mono.svg         Ink 900 throughout — print use
├── billsnap-icon.svg              Icon only (standalone, no bg)
├── billsnap-icon-ondark.svg       Icon on aubergine square (app icon base)
├── billsnap-logo.png              400px wide, transparent bg  [TODO]
├── favicon-32.png                 32×32                        [TODO]
├── favicon-16.png                 16×16 (simplified)           [TODO]
├── apple-touch-icon.png           180×180                      [TODO]
└── og-image.png                   1200×630                     [TODO]
```

> PNG/raster assets marked `[TODO]` need generation from SVG source.

### Logo misuse — never do these

- Do not stretch, skew, or rotate the lockup
- Do not recolor individual elements
- Do not use the on-dark variant on light backgrounds
- Do not place the logo on a busy photographic background without a clear zone
- Do not add drop shadows, glows, or emboss effects (the icon already has its own internal shadow)
- Minimum clear space: icon height on all sides

---

## 5. Visual Motifs

These are recurring design elements that create a consistent, recognizable language across all BillSnap screens and marketing materials.

### 1. Receipt Edge

SVG sawtooth / perforated-hole border. References physical receipts and bills.

- Teeth: 4px tall, 6px pitch
- Color: `ink-100` (`#E8DDF4`) on surface backgrounds; `purple-500` on dark backgrounds
- Use: section dividers on landing page, bottom edge of bill cards, export confirmation

### 2. Camera Frame

Thin corner-bracket rectangles — the four corners of a viewfinder.

- Stroke: 1.5px, `gold-300` (`#F5DC87`) default; `gold-500` on hover/active
- Use: upload area empty state, bill thumbnail hover overlay
- Never use as a decorative element on non-camera-related screens

### 3. Ruled Line

1px horizontal hairlines between data fields.

- Color: `ink-100` (`#E8DDF4`)
- References: ledger paper, account books common in Indian small business
- Use: bill detail view between each field row

### 4. Ink Stamp

"Exported" overlay stamp on exported bill cards.

- Text: "EXPORTED" in Urbanist Bold
- Color: `ledger-green` (`#1A8C5B`)
- Rotation: −3° (slight tilt — stamps are never perfectly aligned)
- Border: distressed circular border, 1.5px
- Use: exported bill card overlay only

### 5. Subtle Surface Gradient

Very light gradient from `surface` (`#FBF8FF`) to `purple-50` (`#F3EEF9`), 180° direction.

- Use: hero section background, onboarding step backgrounds only
- **Never use on data screens** (bill list, bill detail, export screen)
- One gradient per screen maximum

---

## 6. Brand Voice

### Five rules

**1. One idea per sentence.**
No compound instructions. If you need two ideas, use two sentences.

> ✓ "Your bill has been saved."
> ✗ "Your bill has been saved and you can now review the details or export to Excel."

**2. Never say** "simply", "easily", "just", "quick."
These words make users feel slow when they struggle. Our users are capable — respect that.

> ✓ "Take a photo of your bill."
> ✗ "Just take a quick photo of your bill."

**3. Confirm, don't instruct.**
Lead with the outcome. The user did the thing — acknowledge it first.

> ✓ "Your bill is saved."
> ✗ "Make sure to save your bill."

**4. Numbers are always precise.**
Exact counts and amounts build trust. Vague quantities undermine it.

> ✓ "3 bills this month · ₹4,250 total"
> ✗ "A few bills · about ₹4,000"

**5. Celebrate small wins.**
Every completed action deserves a brief, warm confirmation.

> ✓ "One more bill sorted."
> ✓ "All done. Your accountant will thank you."
> ✗ *(no feedback — user wonders if it worked)*

### Tone by context

| Context | Tone | Example |
|---|---|---|
| Onboarding | Warm, reassuring | "You're in the right place." |
| Upload | Encouraging | "Good. Now confirm the details." |
| Error | Direct, not alarming | "We couldn't read that bill. Try a clearer photo." |
| Export | Celebratory | "Your export is ready. All 12 bills." |
| Empty state | Inviting, not apologetic | "No bills yet. Snap your first one." |

### Language

- English UI by default
- Malayalam labels on 3 key actions in V1: Upload (അപ്‌ലോഡ്), Review (അവലോകനം), Export (എക്‌സ്‌പോർട്ട്)
- Full regional language toggle planned for V2
- Avoid idioms that don't translate across Indian languages and cultures

---

## 7. Component Specifications

Reference for building new screens. These specs are the authoritative design intent.

### Primary Button

| Property | Value |
|---|---|
| Height | 48px |
| Border radius | `--radius-xl` (16px) |
| Padding | `0 24px` |
| Font | Manrope 600, 16px |
| Text color | `#FFFFFF` |
| Default bg | `#5C2D91` |
| Hover bg | `#3D1F78` + `translateY(-1px)` |
| Pressed bg | `#2A1450` |
| Disabled | 40% opacity, no pointer events |
| Focus ring | `0 0 0 3px rgba(92,45,145,0.25)` |

### Input Field

| Property | Value |
|---|---|
| Height | 48px |
| Border radius | `--radius-xl` (16px) |
| Padding | `12px 16px` |
| Font | Manrope 400, **16px fixed** |
| Border | 1.5px `ink-100` (`#E8DDF4`) |
| Focus border | 1.5px `purple-600` (`#5C2D91`) |
| Focus ring | `0 0 0 3px rgba(92,45,145,0.15)` |
| Label position | Static above input (not floating) |

> Static labels are easier to read for users who may be unfamiliar with floating label UX patterns.

### Bill Card

| Property | Value |
|---|---|
| Thumbnail | 56×72px (portrait, with Camera Frame motif on hover) |
| Min touch height | 64px |
| Hover | `shadow-lg` + `translateY(-1px)` |
| Status badge | Pill shape, right-aligned |

### Status Badges (pill)

| State | Background | Border | Text |
|---|---|---|---|
| Pending | `#FFFBEB` | `#FDE68A` | `#B45309` |
| Reviewed | `#E6F4EE` | `#BBF7D0` | `#1A8C5B` |
| Exported | `#F3EEF9` | `#E2D5F4` | `#5C2D91` |

### Upload Area

| Property | Value |
|---|---|
| Height | 200px minimum |
| Border | 2px dashed `gold-400` (`#E8BF45`) |
| Border radius | `--radius-2xl` (20px) |
| Background | `purple-50` (`#F3EEF9`) |
| Icon | Lucide `camera`, 48px, `gold-500` (`#C9A227`) |
| Drag-over | Solid border `purple-600` + glow ring |

### Iconography

| Property | Value |
|---|---|
| Library | Lucide React |
| Canvas | 24×24 |
| Stroke | 2px, rounded caps and joins |
| Default size | 20px (inline UI) |
| Navigation size | 24px |
| Empty state / upload | 48px |
| Style | Outline default; filled only for active/selected states |

---

## 8. Layout Grid

Mobile-first. All margins and gutters reference the grid.

| Breakpoint | Columns | Gutter | Margin | Max width |
|---|---|---|---|---|
| 375px (mobile) | 4 | 16px | 20px | — |
| 768px (tablet) | 8 | 20px | 32px | — |
| 1024px+ (desktop) | 12 | 24px | 40px | 1024px centered |

---

## 9. Design Token Reference

All tokens are CSS custom properties defined in `landing/app/globals.css` and wired into Tailwind via `landing/tailwind.config.ts`.

### Color primitives

```css
--color-purple-600: #5C2D91;
--color-purple-500: #7340BE;
--color-purple-700: #3D1F78;
--color-purple-800: #2A1450;
--color-purple-50:  #F3EEF9;
--color-purple-100: #E2D5F4;

--color-gold-500: #C9A227;
--color-gold-400: #E8BF45;
--color-gold-300: #F5DC87;
--color-gold-600: #A07A1A;
--color-gold-50:  #FBF6E7;

--color-ledger-green:       #1A8C5B;
--color-ledger-green-light: #E6F4EE;

--color-ink-900: #1A0D2E;
--color-ink-700: #3D1F78;
--color-ink-500: #7A6690;
--color-ink-300: #B8A8C8;
--color-ink-100: #E8DDF4;

--color-surface:      #FBF8FF;
--color-warm-white:   #FFFFFF;
--color-surface-gray: #F0ECF8;
```

### Semantic aliases

```css
--color-interactive:       var(--color-purple-600);
--color-interactive-hover: var(--color-purple-700);
--color-interactive-press: var(--color-purple-800);
--color-accent:            var(--color-gold-500);
--color-success:           var(--color-ledger-green);
--color-success-light:     var(--color-ledger-green-light);
--color-error:             #D93025;
--color-error-light:       #FFF1F2;
--color-warning:           #F59E0B;
--color-warning-light:     #FFFBEB;
--color-info:              #2563EB;
--color-border:            var(--color-ink-100);
--color-border-focus:      var(--color-purple-600);
```

### Border radius

```css
--radius-sm:   0.375rem;  /*  6px */
--radius-md:   0.5rem;    /*  8px */
--radius-lg:   0.75rem;   /* 12px */
--radius-xl:   1rem;      /* 16px — buttons, inputs */
--radius-2xl:  1.25rem;   /* 20px — large cards */
--radius-full: 9999px;    /* pills */
```

### Z-index scale

```css
--z-raised:  10;   /* elevated cards */
--z-overlay: 20;   /* dropdown menus, tooltips */
--z-modal:   40;   /* modal dialogs */
--z-nav:     50;   /* sticky navigation */
--z-toast:   60;   /* toast notifications */
```

---

## 10. Accessibility Checklist

- [ ] All text/background pairs meet WCAG AA (4.5:1 body, 3:1 large/bold)
- [ ] Aubergine primary `#5C2D91` with white text: ~8.1:1 — passes WCAG AAA
- [ ] Focus rings visible on all interactive elements (3px aubergine glow)
- [ ] Input font fixed at 16px (prevents iOS/Android auto-zoom)
- [ ] Static labels on all inputs (no floating labels that disappear)
- [ ] Minimum touch target: 44×44px (iOS HIG), 48×48px preferred
- [ ] All images have alt text
- [ ] Error messages communicate the issue in plain language
- [ ] Color is never the sole indicator of state (use icon + text + color together)
