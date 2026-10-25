# Per-Screen Evaluation Checklist

Apply every dimension to each screen. Not all carry equal weight — see `severity-ranking.md`.

## Functionality / correctness
- Do controls actually do what they say? (A toggle that doesn't toggle, a submit button that
  fires regardless of state.)
- Is there an input where one is required? (A Q&A screen with no text box, a key field with no
  entry.)
- Do error paths exist and make sense (401/429/quota for network calls)?

## Information architecture & flow
- Is there a step indicator when work spans multiple screens? (Onboarding is often 2+ steps.)
- Is back/escape always available, and does leaving mid-flow warn about lost progress? (Quiz
  abandoned on back-button is a classic loss.)
- Is the primary next action obvious and reachable without scrolling?

## Affordance & discoverability
- Is clickability visible (chevron, arrow, clear CTA) rather than implied by a tiny glyph?
- Do CTAs have visual weight matching their commitment (primary vs. secondary)?

## Feedback
- Progress, completion, and current state are communicated (in-lesson progress, "X of N
  answered", score with explanation).
- Is feedback distinct where the spec requires it (pause vs. stop, playing vs. paused)?

## Accessibility
- `contentDescription` / semantic role on icons, progress bars, and emoji-only elements.
- Contrast: text ≥ 4.5:1 (≥3:1 large), non-text UI ≥ 3:1.
- Tap targets ≥ 24×24dp at all font scales; focus order matches visual order.
- Body text remains readable at large system font sizes.

## Copy & clarity
- No internal jargon shown to users ("verified at build time" → "reviewed against AWS docs").
- Marketing copy must match what's built ("timed quiz with no timer" is an over-promise).

## State handling
- Empty, loading, and error states are designed — not just the happy path.
- Empty state is actionable ("complete a quiz to see coverage", not just "no data").
