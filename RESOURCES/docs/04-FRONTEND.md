# Frontend — Design Guide Reference

The complete frontend design system lives in `FRONTEND-DESIGN.md` (project root).
Read it before writing any HTML.

## Summary

- **Single file:** `frontend/index.html` — HTML + CSS + JS, no build step
- **Design system:** Linear-inspired dark dashboard
- **Font:** Inter (Google Fonts) — one family, weights 400/500/600
- **Colors:** Near-black backgrounds (`#08090a`), one accent (`#5e6ad2`)
- **Borders:** Semi-transparent white (`rgba(255,255,255,0.08)`)
- **Components:** Cards, stat cards, tables, badges, tabs, inputs, buttons, toasts

## Quick Reference

```css
:root {
    --bg-deep: #08090a;
    --bg-panel: #0f1011;
    --bg-surface: #191a1b;
    --text-primary: #f7f8f8;
    --text-secondary: #d0d6e0;
    --text-muted: #62666d;
    --accent: #5e6ad2;
    --accent-hover: #7170ff;
    --green: #27a644;
    --red: #ef4444;
    --yellow: #eab308;
    --border: rgba(255, 255, 255, 0.08);
}
```

## Dashboard Tabs

1. **Dashboard** — Stats row, schedule card, recent applications table
2. **Jobs** — Scraped jobs table with "Scrape Now" button
3. **Applications** — Full application history
4. **Settings** — Candidate profile, search config, LLM, email, resume, cover letter

## API Calls

All calls go to `window.location.origin` (same server).

```javascript
// Load available platforms
const platforms = await fetch('/api/platforms').then(r => r.json());
// platforms = [{id: "linkedin", name: "LinkedIn", type: "jobspy"}, ...]

// Load dashboard stats
const stats = await fetch('/api/applications/stats').then(r => r.json());
// stats = {total_jobs_scraped, sent, failed, pending}

// Load settings
const settings = await fetch('/api/settings').then(r => r.json());

// Save settings (including platforms selection)
await fetch('/api/settings', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        candidate: {...},
        search: {
            job_titles: ["Project Manager", "Program Manager"],
            locations: ["Remote", "New York, NY"],
            platforms: ["linkedin", "indeed", "craigslist"],  // ← user picks these
            jobs_per_day: 10,
            hours_old: 24,
            min_salary: 80000,
        },
        llm: {...}
    })
});

// Run pipeline
await fetch('/api/pipeline/run', {method: 'POST'});

// Update schedule
await fetch('/api/schedule?hour=8&minute=0', {method: 'PUT'});
```

## Anti-Slop Checklist

- [ ] No gradients
- [ ] No glassmorphism / backdrop-filter
- [ ] No emoji in the UI
- [ ] No decorative icons
- [ ] No placeholder content
- [ ] No animations on load
- [ ] Only ONE accent color family
- [ ] All text is Inter at correct weights
- [ ] Borders are semi-transparent, never solid
- [ ] Card backgrounds are `rgba(255,255,255,0.02)`, never solid

See `FRONTEND-DESIGN.md` for full component specs, type scale, spacing, and responsive rules.
