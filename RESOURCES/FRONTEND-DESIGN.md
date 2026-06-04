# Frontend Design Guide — Job Hunter Dashboard

> This file is the single source of truth for the frontend. Follow it exactly.
> The dashboard is a single `index.html` — no build step, no npm, no framework.
> All CSS is embedded. All JS is embedded. One file, open in browser, done.

---

## Design System: Linear-Inspired Dark Dashboard

The visual identity borrows from Linear's dark-mode precision: near-black canvas, luminous text, semi-transparent borders, one accent color. This is NOT a marketing page — it's a working dashboard where data density matters.

---

## 1. Color Palette

Use CSS custom properties. These are the ONLY colors allowed.

```css
:root {
    /* Backgrounds — darkest to lightest */
    --bg-deep: #08090a;          /* Page background */
    --bg-panel: #0f1011;         /* Sidebar, header */
    --bg-surface: #191a1b;       /* Cards, elevated surfaces */
    --bg-hover: #28282c;         /* Hover states */

    /* Text — brightest to dimmest */
    --text-primary: #f7f8f8;     /* Headings, important text */
    --text-secondary: #d0d6e0;   /* Body text, descriptions */
    --text-tertiary: #8a8f98;    /* Metadata, timestamps */
    --text-muted: #62666d;       /* Disabled, subtle labels */

    /* Accent — ONE color family only */
    --accent: #5e6ad2;           /* Primary brand (buttons, CTAs) */
    --accent-hover: #7170ff;     /* Interactive hover */
    --accent-light: #828fff;     /* Active states, links */

    /* Status */
    --green: #27a644;            /* Sent, success */
    --green-soft: #10b981;       /* Badge backgrounds */
    --red: #ef4444;              /* Failed, errors */
    --yellow: #eab308;           /* Pending, warnings */

    /* Borders — semi-transparent white, NEVER solid dark */
    --border-subtle: rgba(255, 255, 255, 0.05);
    --border-standard: rgba(255, 255, 255, 0.08);
    --border-strong: rgba(255, 255, 255, 0.12);
}
```

### Color Rules
- NEVER use pure black (`#000`) or pure white (`#fff`) for text
- NEVER use solid colored borders on dark backgrounds
- The accent color (`#5e6ad2`) is ONLY for interactive elements — buttons, links, active states
- Status colors are ONLY for status indicators — never decorative
- Everything else is grayscale

---

## 2. Typography

Font: Inter (Google Fonts). ONE font family for everything.

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

```css
body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    font-feature-settings: "cv01", "ss03";  /* Geometric alternates */
}
```

### Type Scale

| Role | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| Display | 32px | 600 | 1.1 | -0.7px | Page titles |
| Heading | 20px | 600 | 1.3 | -0.24px | Card titles, section headers |
| Subheading | 16px | 500 | 1.4 | normal | Labels, nav items |
| Body | 14px | 400 | 1.5 | normal | Default text, table cells |
| Caption | 13px | 400 | 1.5 | -0.13px | Metadata, timestamps |
| Label | 12px | 500 | 1.4 | normal | Buttons, badges, tags |
| Micro | 11px | 500 | 1.4 | normal | Tiny labels, counts |

### Typography Rules
- Weight 500 is the default for UI elements (labels, nav, buttons)
- Weight 400 is for body/reading text
- Weight 600 is for headings and emphasis
- NEVER use weight 700+ in the dashboard (too heavy for dark backgrounds)
- Negative letter-spacing on anything 20px+
- UPPERCASE with 0.5px letter-spacing for category labels only

---

## 3. Spacing & Layout

Base unit: 8px. All spacing is a multiple of 8.

```css
/* Spacing scale */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

### Layout Structure
```
┌─────────────────────────────────────────────┐
│  Header (fixed, --bg-panel)                 │
├─────────────────────────────────────────────┤
│  Container (max-width: 1200px, centered)    │
│  ┌─────────────────────────────────────┐    │
│  │  Stats Row (grid, 4 cols)           │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  Main Card (table, form, content)   │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  Secondary Card                     │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### Grid
```css
.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
}
```

---

## 4. Components

### Cards
```css
.card {
    background: rgba(255, 255, 255, 0.02);  /* NEVER solid */
    border: 1px solid var(--border-standard);
    border-radius: 12px;
    padding: 24px;
}
```

### Stat Cards
```css
.stat-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-standard);
    border-radius: 12px;
    padding: 20px;
}
.stat-card .label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.stat-card .value {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.5px;
}
```

### Buttons

**Primary (CTA)**
```css
.btn-primary {
    background: var(--accent);
    color: var(--text-primary);
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s;
}
.btn-primary:hover {
    background: var(--accent-hover);
}
```

**Ghost (Secondary)**
```css
.btn-ghost {
    background: rgba(255, 255, 255, 0.02);
    color: var(--text-secondary);
    border: 1px solid var(--border-standard);
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
}
.btn-ghost:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--text-primary);
}
```

### Inputs
```css
input, textarea, select {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border-standard);
    border-radius: 6px;
    padding: 10px 12px;
    color: var(--text-primary);
    font-size: 14px;
    font-family: inherit;
    width: 100%;
}
input:focus, textarea:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.2);
}
input::placeholder {
    color: var(--text-muted);
}
```

### Tables
```css
table {
    width: 100%;
    border-collapse: collapse;
}
th {
    text-align: left;
    padding: 10px 12px;
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border-subtle);
}
td {
    padding: 12px;
    font-size: 14px;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-subtle);
}
tr:hover td {
    background: rgba(255, 255, 255, 0.02);
}
```

### Badges / Status Pills
```css
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 500;
}
.badge::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}
.badge-green { background: rgba(16, 185, 129, 0.12); color: var(--green-soft); }
.badge-red { background: rgba(239, 68, 68, 0.12); color: var(--red); }
.badge-yellow { background: rgba(234, 179, 8, 0.12); color: var(--yellow); }
.badge-blue { background: rgba(94, 106, 210, 0.12); color: var(--accent-light); }
```

### Navigation Tabs
```css
.nav-tabs {
    display: flex;
    gap: 2px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
    padding: 3px;
    border: 1px solid var(--border-subtle);
}
.nav-tab {
    padding: 7px 14px;
    border-radius: 6px;
    border: none;
    background: none;
    color: var(--text-muted);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
}
.nav-tab.active {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-primary);
}
.nav-tab:hover:not(.active) {
    color: var(--text-secondary);
}
```

### Toast Notifications
```css
.toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    padding: 12px 20px;
    background: var(--bg-surface);
    border: 1px solid var(--border-standard);
    border-radius: 8px;
    font-size: 13px;
    color: var(--text-secondary);
    box-shadow: rgba(0, 0, 0, 0.4) 0px 2px 8px;
    z-index: 1000;
    transform: translateY(20px);
    opacity: 0;
    transition: all 0.2s ease;
}
.toast.show {
    transform: translateY(0);
    opacity: 1;
}
```

---

## 5. Dashboard Sections

### Section 1: Stats Row
Four stat cards in a grid:
- Jobs Scraped (blue badge)
- Applications Sent (green badge)
- Failed (red badge)
- Pending (yellow badge)

### Section 2: Schedule Card
- Current schedule time with green dot indicator
- "Run Now" button (primary)
- Time picker inputs (hour/minute)
- "Update Schedule" button (ghost)

### Section 3: Recent Applications Table
Columns: Job Title, Company, Contact, Status, Date
- Job title links to the job posting
- Status shown as badge pills
- Empty state: centered muted text, no data yet

### Section 4: Jobs Tab
- "Scrape Now" button top-right
- Table: Title (linked), Company, Location, Score, Status
- Score displayed as a number, color-coded by range
- Status badges: new (blue), applied (green)

### Section 5: Applications Tab
- Full history table: Job, Company, Contact, Email, Status, Date
- Scrollable, 100-row limit

### Section 6: Settings Tab
- Grouped cards: Candidate Profile, Job Search, Platform Selection, LLM Config, Email, Resume, Cover Letter
- Two-column form layout for related fields
- **Platform Selection:** Checkboxes for each available platform (LinkedIn, Indeed, Craigslist, etc.)
  - Loaded from `GET /api/platforms`
  - Stored as array in `search.platforms`
  - Default: LinkedIn, Indeed, Glassdoor, Google Jobs
- "Save All Settings" button at bottom
- Password fields for API keys and platform credentials

---

## 6. Motion & Interaction

```css
/* Hover transitions — keep fast */
.card:hover { border-color: var(--border-strong); }
.btn-primary:hover { background: var(--accent-hover); }
tr:hover td { background: rgba(255, 255, 255, 0.02); }

/* Loading state */
.loading { opacity: 0.5; pointer-events: none; }

/* Empty states */
.empty-state {
    text-align: center;
    padding: 48px 24px;
    color: var(--text-muted);
    font-size: 14px;
}
```

### Rules
- All transitions are 0.15s ease — fast, no bounce, no spring
- NO animations on page load
- NO skeleton screens (keep it simple)
- NO parallax, no scroll effects
- Hover feedback on all interactive elements
- Focus ring on inputs: 2px accent color with 0.2 opacity

---

## 7. Responsive

```css
/* Mobile-first */
@media (max-width: 768px) {
    .stats-row { grid-template-columns: 1fr 1fr; }
    .form-row { grid-template-columns: 1fr; }
    .container { padding: 16px; }
    header { flex-direction: column; gap: 12px; }
}
@media (max-width: 480px) {
    .stats-row { grid-template-columns: 1fr; }
}
```

---

## 8. Anti-Slop Rules

DO NOT:
- Use gradient backgrounds
- Use glassmorphism or backdrop-filter
- Use emoji in the UI
- Use decorative icons
- Use placeholder testimonials or fake metrics
- Add sections that don't serve a function
- Use more than one accent color
- Add animations that delay the user

DO:
- Keep every element functional
- Use whitespace as the primary design tool
- Let the data be the visual interest
- Keep the color palette tight (grayscale + one accent)
- Make the UI feel fast and precise

---

## 9. API Integration

The frontend calls these endpoints on the same origin:

```javascript
const API = window.location.origin;

// Settings
GET  /api/settings          → returns all settings
PUT  /api/settings          → updates settings (body: JSON)

// Jobs
GET  /api/jobs?limit=50     → list scraped jobs
GET  /api/jobs/new           → list unapplied jobs

// Applications
GET  /api/applications?limit=100  → history
GET  /api/applications/stats       → {total_jobs_scraped, sent, failed, pending}

// Pipeline
POST /api/pipeline/run      → run full pipeline
POST /api/pipeline/scrape   → just scrape

// Schedule
GET  /api/schedule           → {enabled, next_run, hour, minute}
PUT  /api/schedule?hour=8&minute=0  → update schedule
```

All responses are JSON. Error responses include a `detail` field.

---

## 10. File Structure

```
frontend/
└── index.html    ← EVERYTHING in one file (HTML + CSS + JS)
```

No external CSS files. No external JS files. No build step.
The only external dependency is the Google Fonts `<link>` tag for Inter.

---

## 11. Verification Checklist

Before considering the frontend done:

- [ ] Opens directly in a browser (no server needed for static)
- [ ] All 4 tabs work (Dashboard, Jobs, Applications, Settings)
- [ ] Settings form saves and loads correctly
- [ ] "Run Now" triggers the pipeline
- [ ] "Scrape Now" triggers a scrape
- [ ] Schedule time updates work
- [ ] Tables show data when API returns it
- [ ] Empty states show when no data
- [ ] Responsive on mobile (test at 375px width)
- [ ] No console errors
- [ ] Toast notifications appear and dismiss
- [ ] All colors match the palette (no random colors)
- [ ] All fonts are Inter at the correct weights
- [ ] No emoji, no gradients, no glassmorphism
