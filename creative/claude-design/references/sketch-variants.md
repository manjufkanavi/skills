# Sketch: Multi-Variant Design Exploration

## Core method
```
intake  →  variants  →  head-to-head  →  pick winner (or iterate)
```

### 1. Intake
Before generating variants, get three things:
1. **Feel.** "What should this feel like?" — adjectives, emotions, a vibe
2. **References.** "What apps, sites, or products capture the feel?"
3. **Core action.** "What's the single most important thing a user does?"

### 2. Variants (2-3, never 1, rarely 4+)
Each variant is a **single self-contained HTML file** taking a different design stance:

- **Density:** compact / airy / ultra-dense
- **Emphasis:** content-first / action-first / tool-first
- **Aesthetic:** editorial / utilitarian / playful
- **Layout:** single-column / sidebar / split-pane
- **Grounding:** card-based / bare-content / document-style

### 3. Variant README
Each variant needs a README.md answering:
- Design stance (one sentence)
- Key choices (layout, typography, color, interaction)
- Trade-offs (strong at / weak at)
- Best for (target user/use case)

### 4. Head-to-head
Present as a comparison table with opinionated assessment. Don't just list — opinionate.

### Variant naming convention
```
sketches/
├── 001-calm-editorial/
│   ├── index.html
│   └── README.md
├── 001-utilitarian-dense/
│   ├── index.html
│   └── README.md
└── 001-playful-split/
    ├── index.html
    └── README.md
```

### Interactivity bar
A sketch is interactive enough when the user can:
1. Click a primary action and something visible happens
2. See one meaningful state transition
3. Hover recognizable affordances

More than that is over-engineering a throwaway. Less than that is a screenshot.

### Theming
If the project has a visual identity, put shared tokens in `sketches/themes/tokens.css` and `@import` them in each variant. Keep tokens minimal — three colors and one font is usually enough.

### Verification
Load each variant in the browser and use `browser_vision` to check for layout bugs:
```
browser_navigate(url="file:///absolute/path/to/sketches/001-calm-editorial/index.html")
browser_vision(question="Does this layout look clean? Any visible bugs?")
```
