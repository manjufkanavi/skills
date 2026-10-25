---
name: ux-review
description: Critique app screens, or deliver a UX redesign package.
---

# UX Review (Usability Critique)

## When to Use

Use when the user wants a critical evaluation of how an app, prototype, or UI codebase works
from a usability standpoint — which screens are good/bad and what to improve. Applies to
Android/iOS/web apps, Figma exports, or UI source (Compose, HTML/CSS, etc.).

## Workflow (do in this order)
1. **Find the authoritative intent first.** Read the IA / screen-inventory doc, accessibility
   spec, and any flow specs (onboarding, cost clarity) before touching screens. These define
   what each screen is *supposed* to do; they are your rubric.
2. **Read every actual screen implementation** (or view every real screen). Never judge from
   the inventory alone — the gap between documented intent and shipped UI is where the real
   findings live.
3. **Detect mockup vs. live app.** If all data flows from demo/fake sources and screens hold no
   state, treat it as design intent — but still flag the missing loading / error / empty states,
   because those are real UX failures regardless.
4. Walk every screen in the inventory one by one, applying the checklist
   (`references/evaluation-framework.md`).
5. Order each screen's findings by severity — non-functional and accessibility failures first,
   cosmetic issues last.
6. Close with a cross-cutting section (patterns that recur across all screens) and a short
   "fix these three first" triage so the user gets immediate priorities.

## Findings: how to rank severity
Rank every finding P0 / P1 / P2 (see `references/severity-ranking.md`). Listing cosmetic issues
alongside real ones at equal weight is the most common mistake — severity order is what makes the
critique actionable, not how many points you make.

## Output format (this user's preference)
- Lead with a one-line framing note: what the artifact is, that you judged it against its
  documented intent, and whether it's a mockup.
- Per-screen bullets, most severe first. Each finding is "what it does wrong" + the concrete fix
  — never a complaint with no remedy.
- One cross-cutting section for global patterns (states, settings access, personalization).
- End with "fix only these three first" — the top 3 highest-leverage fixes.

## Non-negotiable lens
Run an accessibility pass on every screen (TalkBack / `contentDescription`, contrast for text and
non-text UI, tap-target size ≥ 24dp). The accessibility spec tells you what is *supposed* to
exist; a control that exists on paper but not in the UI — e.g. a consent toggle that doesn't
toggle, or a speed selector rendered as static text — is the highest-severity kind of finding:
you promised it and didn't build it.

## Redesign mode (the ask is "redesign", not "review")

Workflow steps 1–3 apply unchanged (intent docs, every actual screen, mockup detection), and
findings are still severity-ranked — but the deliverable is a replacement design, not a
critique memo:

1. **Package shape** (in the repo's design directory; old artifacts deleted in the same
   commit as the new package): `README.md` (severity-ranked findings table, 1–2-sentence
   redesign thesis, v1→v2 decision table with a *why* column, new IA, implementation
   roadmap) · `design-system.md` (tokens with **computed** WCAG contrast ratios — never
   assert "AA compliant" without the numbers; typography; spacing grid; iconography;
   component specs; a11y contract; a permanent anti-pattern list) · `user-journey.md`
   (mental model, named flows, adaptive layout, guarantees) · `screens.md` (per screen:
   purpose → what the old version got wrong, citing the code → redesigned layout
   referencing tokens → loading/empty/error states → a11y notes; plus an old→new copy map).
2. **Keep what v1 did right.** An explicit "kept" list in the README (working switches,
   cost clarity, provenance…). A redesign that discards earned properties is a regression.
3. **Theme must fit the product's trust requirements.** A credibility-dependent or
   professional product gets a professional design language; novelty or fantasy theming
   on such a product is a P0 finding, not a style quirk.
4. **Quality bars that survived review:** no emoji as UI icons (real icon set,
   theme-tinted); money never renders in the success color; every rendered control must
   actually function; every screen ships loading/empty/error; semantic roles must be
   visually distinct (error ≠ reward).
5. **Land in git per `references/design-delivery-git.md`.** If the repo keeps a decision
   log (ADR), add one ADR recording the direction; superseded docs get a banner, not
   silent deletion.
