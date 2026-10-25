# Severity Ranking for UX Findings

Rank every finding so the critique leads with what matters. Do not list cosmetic issues at equal
weight to real ones.

## P0 — Broken or inaccessible (fix immediately)
The app is failing its user, not just a learner. A control that doesn't do what it claims
(consent toggle won't toggle, submit fires regardless of answers), a missing input where one is
required (Q&A with no text field), or an accessibility failure that breaks a core flow. These are
also the worst kind of contradiction: the spec/ADR says it exists, so you under-delivered on a
promise.

## P1 — Missing core flow or promise (high leverage)
The feature was advertised but not built, the core action is absent, or the single most valuable
insight isn't surfaced. Examples:
- Advertised but unbuilt: "timed quiz" with no timer.
- Missing core action: a reader screen with no bookmark / "mark understood" control.
- Untapped insight: a readiness screen that shows "% complete" but never tells the user what to
  study next.
These are high-leverage because they touch retention and trust, not just polish.

## P2 — Cosmetic / polish (do last)
Layout balance, visual hierarchy, emoji-vs-icon in secondary elements, wording tweaks. Nice-to-have
— never let P2 crowd out P0/P1 in the ordering.
