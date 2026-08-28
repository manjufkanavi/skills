# SVG Image Generator Skill

## Purpose

Generate high-quality SVG images from natural language prompts. The skill enhances user requests through a unified **Creative Director** persona (Senior Prompt Engineer × Senior Graphic Designer) and produces both SVG source code and JPEG output images.

## Workflow

### Step 0: Ask User What to Generate

When the user invokes the SVG image generator skill, **always ask them what they want to generate** before producing anything.

**Process:**
1. Respond with a friendly prompt asking the user to describe the SVG image they want
2. Wait for their description
3. Only then proceed with Steps 1–5 (Prompt Enhancement → SVG Generation → SVG Output → JPEG Conversion → GitHub Upload)

**Example interaction:**
- User: "Run svg image generator skill"
- Assistant: "Sure! What would you like me to generate? Describe the SVG image you have in mind — it can be an icon, logo, illustration, chart, or anything else."
- User: "A minimalist mountain landscape with a sunset"
- Assistant: *(then proceeds through the full workflow)*

### Step 1: Prompt Enhancement via Creative Director Persona

When the user provides a natural language request, **always** enhance it using the **Creative Director** persona defined in `creative-director-persona.md`.

**Process:**
1. Read `creative-director-persona.md` to understand the persona's principles, workflow, and prompt template
2. Analyze the user's request through the Creative Director lens:
   - What is the purpose and audience?
   - What style, colors, and constraints fit best?
   - What complexity level is appropriate?
3. Transform the request into a structured, detailed SVG prompt using the persona's prompt template
4. The enhanced prompt should specify: viewBox, element count limits, color palette, style, technical constraints, and context

**Example transformation:**
- User says: "Make a sun icon"
- Creative Director enhances: "Create a minimalist flat-style sun icon with 3-5 elements, viewBox 64×64, using a warm gradient palette (#F59E0B, #FBBF24, #FCD34D), centered circular sun body with 8 geometric rays, clean vector lines, no gradients, suitable for a weather app favicon at 32px display size"

### Step 2: SVG Generation

Generate the SVG code using the enhanced prompt. Follow these rules:

- Use semantic SVG elements (`<rect>`, `<circle>`, `<path>`, `<polygon>`, `<line>`, `<text>`)
- Proper grouping with `<g>` and `id` attributes
- Reusable styles in `<defs>` with gradients and patterns
- Responsive `viewBox` and percentage dimensions
- Accessibility attributes (`role="img"`, `aria-label`)
- Code optimization (no redundancy, clean formatting)
- All tags properly closed, valid XML
- All coordinates within viewBox bounds

### Step 3: SVG Output

Present the SVG code to the user in a code block.

### Step 4: JPEG Conversion and Save

After generating the SVG:

1. Run the conversion script:
   ```bash
   python3 skills/svg-image-generator/scripts/svg_to_jpeg.py "<svg_content>"
   ```
2. The script saves the JPEG to `skills/svg-image-generator/generated_images/` with a timestamped filename
3. Report the generated JPEG path to the user

### Step 5: GitHub Upload

After generating the JPEG:

1. Add the generated image to git:
   ```bash
   git add skills/svg-image-generator/generated_images/*.jpg
   ```
2. Commit with a descriptive message:
   ```bash
   git commit -m "feat: generate JPEG for [description of image]"
   ```
3. Push to remote:
   ```bash
   git push
   ```
4. Report the commit URL to the user

## Files

- `creative-director-persona.md` — The unified Creative Director persona (prompt engineer + graphic designer)
- `scripts/svg_to_jpeg.py` — Converts SVG strings to JPEG images
- `generated_images/` — Directory where generated JPEGs are saved

## Requirements

- **cairosvg** — Converts SVG to PNG (rendering engine)
- **Pillow** — Converts PNG to JPEG (image library)
- Install with: `pip install cairosvg Pillow`

## Quality Checklist

Before presenting output:
- [ ] Prompt was enhanced through Creative Director persona
- [ ] SVG is valid XML (all tags closed, proper nesting)
- [ ] Correct `xmlns` attribute
- [ ] Valid `viewBox` dimensions
- [ ] All coordinates within viewBox bounds
- [ ] No invalid SVG attributes
- [ ] Consistent styling across elements
- [ ] No duplicate IDs
- [ ] Proper use of self-closing tags
- [ ] Accessibility attributes present
- [ ] JPEG generated and saved to `generated_images/`
- [ ] Image committed and pushed to GitHub
