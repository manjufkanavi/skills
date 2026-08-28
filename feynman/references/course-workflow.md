# Learning & Course Material Workflow

## When to Use Feynman for Courses
When working with academic or course materials (midsem reports, project abstracts, presentations):

1. **Convert first** — Use markitdown or HTML-to-PDF to convert PDFs/PPTX to markdown for better context
2. **Feynman the content** — Use `/feynman [topic]` to generate simple explanations of course concepts
3. **Cross-reference** — Use `/feynman` output alongside the original document to identify gaps in understanding
4. **Teach back** — The final step is explaining the concept in your own words, which serves as both study and documentation

## Document Processing Tips
- PDF → Markdown: `pip install markitdown` then `markitdown input.pdf > output.md`
- PowerPoint → Markdown: same command works for `.pptx` files
- Always keep originals in a `backup/` directory alongside converted markdown