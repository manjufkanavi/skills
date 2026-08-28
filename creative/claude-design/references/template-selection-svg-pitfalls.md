# Template Selection & SVG Rendering Pitfalls

When rebuilding or adapting HTML presentation decks from existing project templates.

## When Existing Presentation is "Poorly Formatted, No Colors"

**Symptom:** User says the presentation is poorly formatted and has no colors.

**Root cause:** The project has two templates:
- `template_a_minimal.html` — plain, mostly black/white, minimal styling
- `template_b_dark.html` — full color system, gradients, badges, proper typography

**Fix:** Do NOT just reflow content into template A. Find and build from template B (the richer variant). The new presentation inherits:
- 6+ CSS color variables (`--cyan`, `--magenta`, `--violet`, `--amber`, `--emerald`, `--rose`)
- Gradient definitions (`--cyan-g`, `--mag-g`)
- Badge system (`badge-high`, `badge-med`, `badge-low`)
- Card/box utilities (`.glass`, `.cards-2`, `.cards-3`)
- Font definitions (DM Sans + DM Mono)
- Print-to-PDF styles

**Template inheritance checklist:**
1. `grep -l template_b` project directory to find the alternate
2. Read template B's `<style>` block fully — it's the CSS framework to inherit
3. Copy the CSS framework, replace only content and data
4. Do NOT rewrite CSS unless domain requires it (e.g., non-technical audience needs light theme)

## SVG In Deck Presentations — Color Rendering

**Problem:** SVG architecture diagrams rendered with black/white or missing colors even when CSS defines `var(--cyan)` etc.

**Root cause:** SVG presentation decks reuse CSS `var(--*)` variables in two contexts:
- CSS selectors — works fine (`color: var(--cyan)`, `stroke: var(--emerald)`)
- SVG attribute strings — may NOT work depending on browser (`fill="var(--cyan)"` in SVG `fill` attribute, `stroke` in SVG `<line>` or `<rect>`)

**Fix for SVG colors:**
- **SVG `<text>` elements:** `var(--*)` works — text color properties resolve from CSS
- **SVG `<rect>`, `<line>`, `<path>` attributes:** Use explicit hex/rgba values in attribute strings. In the SVG `<style>` block, define CSS rules that target SVG elements by class, or inline the resolved color values.
- **Best pattern:** Define CSS classes (`.box-cyan { fill: var(--cyan); stroke: var(--cyan); }`) and apply them via the SVG `class` attribute rather than setting `fill="var(--cyan)"` in the attribute string.
- **Fallback:** When in doubt, use explicit hex values like `fill="#00d4ff"` or `fill="rgba(0,212,255,0.1)"`.

**Verification:** Always check the architecture diagram slide with `browser_vision` specifically — SVG rendering issues are invisible until you see it.

## Git Repo Structure Gotcha

When working with files under `~/.hermes/git_clone_dir/` or `~/.nanobot/workspace/git_clone_dir/`:
- The `git_clone_dir` directory is in `.gitignore`
- The ACTUAL git repo is the parent (`~/.nanobot/workspace/`)
- Use `git add -f` to force-add ignored paths
- Always verify which remote the parent repo points to before pushing
