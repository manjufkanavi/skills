# WeasyPrint Flexbox → Empty Orphan Pages

## Problem
Pages with 1-2 lines of content, or fully blank pages, appearing in the output PDF. The PDF has more pages than expected (e.g., 109 instead of 52 for a 17-poem book).

## Root Cause
WeasyPrint's layout engine fully respects CSS flexbox. When `.content` uses `display: flex; flex-direction: column`, content that exceeds the A4 boundary does not clip — it spills over and WeasyPrint creates new pages to accommodate the overflow. Additionally:

- `.closing { margin-top: auto }` pushes content to the top, leaving dead space below
- `.meaning-card { display: flex }` creates empty boxes when grid children have minimal content
- Line-height 2.2+ on text blocks inflates vertical space beyond what fits

## Fix Pattern

### Step 1: Replace flexbox in page layout
```css
/* WRONG */
.content {
  display: flex;
  flex-direction: column;
}

/* CORRECT */
.content {
  display: block;
  height: 238mm;   /* A4 (297mm) - header/footer padding */
  overflow: hidden;
}
```

### Step 2: Remove auto margins
```css
/* WRONG */
.closing {
  margin-top: auto;
}

/* CORRECT */
.closing {
  margin-top: 0;
}
```

### Step 3: Break cards into block flow
```css
/* WRONG */
.meaning-card {
  display: flex;
  flex-direction: column;
}

/* CORRECT */
.meaning-card {
  display: block;
  break-inside: avoid;
}
```

### Step 4: Reduce line-heights for fitting
- Lyrics: `2.2 → 1.9`
- Explanations: `1.7 → 1.6`
- Lessons: `1.7 → 1.7`

### Step 5: Build as single HTML + single PDF
Instead of individual pages + merge, write ONE HTML with `page-break-after: always` between logical pages. Run WeasyPrint once. This gives:
- Global page numbering (1-N)
- Consistent styling
- No overflow pages

## Debug Checklist
- [ ] Run `python3` to inspect PDF pages with pypdf: `len(r.pages)` should match expected count
- [ ] Check each page: `r.pages[i].extract_text().strip()` — non-whitespace chars should be >50
- [ ] Pages with <5 lines need content pulled from next page or spacing adjusted
- [ ] Empty pages (<50 chars) indicate flexbox overflow — re-check `.content` CSS
