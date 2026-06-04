# Skills Reference — Compiled from Hermes Skill Hub

These are actionable references extracted from the Hermes skills library.
They contain exact values, patterns, and rules — not generic advice.

---

## Skill 1: Humanizer (for Cover Letters)

**Source:** `skills/creative/humanizer` — Strips AI-generated text patterns to sound human.

**Why it matters:** The LLM writes cover letters. Without humanization, they'll sound
robotic and hiring managers will ignore them. Apply these rules to every cover letter
the LLM generates.

### The 10 Most Important Anti-AI Rules

1. **No significance inflation.** Never write "stands as a testament," "pivotal moment,"
   "evolving landscape," "vital role." Just state the fact.

2. **No -ing endings for fake depth.** Never write "highlighting the importance,"
   "underscoring the need," "reflecting the commitment." Just say what happened.

3. **No promotional language.** Never write "groundbreaking," "innovative,"
   "cutting-edge," "best-in-class." Be specific instead.

4. **No "Not only...but also."** This construction is overused by LLMs.
   Just make the statement directly.

5. **No rule of three.** LLMs force ideas into groups of three.
   Use two or four, or just one strong point.

6. **No copula avoidance.** Write "I am" not "I serve as." Write "I have" not
   "I boast a track record of."

7. **No filler phrases.** Never write "In order to," "Due to the fact that,"
   "At this point in time," "It is important to note that."

8. **No excessive hedging.** Never write "It could potentially possibly be argued."
   State it or don't.

9. **No generic conclusions.** Never write "The future looks bright," "Exciting times
   lie ahead," "I look forward to hearing from you at your earliest convenience."

10. **No em dash overuse.** Use commas or periods instead. Humans rarely use
    more than one em dash per paragraph.

### What Good Cover Letters Sound Like

**Before (AI):**
> I am writing to express my strong interest in the Project Manager position at
> Acme Corp. With over 8 years of experience in cross-functional team leadership
> and a proven track record of delivering impactful results, I am confident in my
> ability to contribute to your organization's continued success.

**After (human):**
> I saw the PM opening at Acme and wanted to reach out. I've spent the last 8 years
> running cross-functional projects — most recently at TechCo, where I shipped a
> platform rebuild that cut support tickets by 40%.

### Voice Calibration for Cover Letters

- **Sentence length:** Mix short (8 words) and medium (15 words). No sentences over 25 words.
- **Word choice:** Use "built," "led," "shipped," "fixed" — not "spearheaded," "orchestrated," "leveraged."
- **Tone:** Confident but not arrogant. Specific but not bragging. Direct but not cold.
- **Structure:** Hook → 2-3 specific achievements mapped to JD → close. No fluff paragraphs.

---

## Skill 2: Popular Web Designs (for Dashboard)

**Source:** `skills/creative/popular-web-designs` — 54 real design systems as CSS specs.

### Design Choice: Linear

For a data dashboard, Linear's design system is the best fit:
- Dark-mode native (near-black canvas)
- Ultra-precise typography
- One accent color (indigo)
- Semi-transparent borders (no solid dark borders)
- Data-dense but not cluttered

### Linear Quick Reference

**Colors:**
```
Page background:    #08090a
Panel background:   #0f1011
Surface/Card:       #191a1b
Text primary:       #f7f8f8
Text secondary:     #d0d6e0
Text muted:         #8a8f98
Accent:             #5e6ad2
Accent hover:       #7170ff
Border:             rgba(255,255,255,0.08)
Border subtle:      rgba(255,255,255,0.05)
```

**Typography:**
```
Font:               Inter, system-ui, sans-serif
OpenType features:  "cv01", "ss03"
Display (32px):     weight 600, letter-spacing -0.7px
Heading (20px):     weight 600, letter-spacing -0.24px
Body (14px):        weight 400, line-height 1.5
Label (12px):       weight 500, uppercase, letter-spacing 0.5px
```

**Components:**
```
Card background:    rgba(255,255,255,0.02)
Card border:        1px solid rgba(255,255,255,0.08)
Card radius:        12px
Button bg:          rgba(255,255,255,0.02) (ghost) or #5e6ad2 (primary)
Button radius:      6px
Input bg:           rgba(255,255,255,0.02)
Input border:       1px solid rgba(255,255,255,0.08)
Input focus:        border-color: #5e6ad2, box-shadow: 0 0 0 2px rgba(94,106,210,0.2)
```

**Rules:**
- NEVER use pure white (#fff) for text — use #f7f8f8
- NEVER use solid backgrounds for cards — use rgba(255,255,255,0.02)
- NEVER use solid dark borders — use rgba(255,255,255,0.08)
- Accent color is ONLY for interactive elements (buttons, links, active states)
- Weight 500 is the default for UI labels, 400 for body text, 600 for headings
- 8px spacing grid: 8, 16, 24, 32, 40, 48

---

## Skill 3: Writing Plans (for Implementation)

**Source:** `skills/software-development/writing-plans` — Bite-sized task methodology.

### Core Rules

1. **Each task = 2-5 minutes of focused work.** If a task takes longer, break it down.
2. **Exact file paths.** Never say "create the model file." Say `backend/database.py`.
3. **Complete code.** Every task includes the actual code, not a description of what to write.
4. **Verification steps.** Every task ends with "run X, expect Y."
5. **One action per step.** "Write the test" is one step. "Run it" is another.

### Task Format

```markdown
### Task N: Descriptive Name

**Objective:** One sentence
**Files:** Create: path/to/file.py

**Steps:**
1. Write code
2. Verify it works
3. Commit
```

### Principles

- **DRY:** Don't repeat yourself. Extract shared logic into functions.
- **YAGNI:** Don't build for hypothetical future needs. Build what's needed now.
- **Frequent commits:** Commit after every task. Small commits are easy to review and revert.

---

## Skill 4: Claude Design (for Design Process)

**Source:** `skills/creative/claude-design` — Design taste and process for HTML artifacts.

### Key Rules for This Project

1. **Start from context, not vibes.** The design system (Linear) is defined. Follow it.
2. **No filler content.** Every element must earn its place.
3. **No AI design slop:**
   - No aggressive gradient backgrounds
   - No glassmorphism by default
   - No emoji
   - No generic SaaS cards with icons everywhere
   - No fake dashboards filled with arbitrary numbers
   - No stock-photo hero sections
   - No rainbow palettes
4. **Typography as hierarchy.** Use size and weight to create hierarchy before adding boxes, icons, or color.
5. **One idea per section.** Don't cram everything into one card.
6. **Mobile hit targets ≥ 44px.** Every clickable element must be tappable on a phone.

### Verification Checklist

Before saying the frontend is done:
- [ ] File exists and opens in browser
- [ ] No console errors
- [ ] All tabs work
- [ ] Forms save and load
- [ ] Responsive at 375px width
- [ ] All colors match the palette
- [ ] No emoji, no gradients, no glassmorphism
- [ ] Empty states show when no data
