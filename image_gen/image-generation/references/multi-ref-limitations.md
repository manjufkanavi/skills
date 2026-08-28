# FLUX.2 Multi-Reference Limitations

## How Multi-Reference Actually Works

FLUX.2's multi-reference system encodes multiple photos of the **same subject** to anchor visual identity across different scenes, angles, and lighting conditions.

### What It's Designed For

- **Character consistency**: Keep the same person across multiple generated scenes
- **Multi-angle reference**: Feed 2-10 photos of one person for better identity lock-in
- **Style transfer**: Use reference images to maintain aesthetic consistency

### What It's NOT Designed For

- **Multi-person composition**: It does NOT combine two different people into one scene
- **Face blending**: It does NOT merge two faces into a single character
- **Scene composition**: It does NOT place two reference subjects together

### Technical Behavior

```
image1 → BASE SUBJECT (main person in output)
image2 → ELEMENTS to blend INTO image1 (clothing, accessories, background)
image3 → More elements to add
```

## Empirical Findings from Testing

### 4B Model (flux2-klein-4b)

- Multi-reference quality is **poor**
- Often loses the second reference entirely
- At `--image-strength 0.55`, the female reference was completely lost
- At `--image-strength 0.4`, still unreliable for two-person scenes
- **Verdict**: Not suitable for multi-person composition tasks

### 9B Model (flux2-klein-9b)

- Multi-reference quality is **significantly better**
- Both faces more likely to be present
- At `--image-strength 0.4-0.5`, better blending of reference elements
- **Verdict**: Better for multi-reference, but still not designed for two-person scenes

## Workarounds for Multi-Person Scenes

### Option A: Describe Both People in Prompt

```bash
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --prompt "a dark-skinned woman with black hair in a ponytail and a dark-skinned man with curly black hair and beard, intimate bedroom scene..." \
  --steps 4 \
  --width 1080 \
  --height 1350 \
  --seed 42 \
  --output output.png
```

### Option B: Use 9B Model + Single Reference

Use one reference as the base and describe the other person in the prompt:

```bash
mflux-generate-flux2 \
  --model flux2-klein-9b \
  --prompt "a woman with black hair in a ponytail kissing a man with curly black hair and beard, intimate bedroom scene..." \
  --image-path woman_photo.jpg \
  --image-strength 0.4 \
  --steps 4 \
  --width 1080 \
  --height 1350 \
  --seed 42 \
  --output output.png
```

### Option C: Use Different Model

Qwen-Image-Edit and FLUX.1 Kontext have better multi-person editing capabilities, but require different tooling.

## Best Practices

1. **For character consistency**: Multi-reference works well — use 2-10 photos of the same person
2. **For two-person scenes**: Describe both people in the prompt, use at most one reference
3. **Image strength**: Use `0.4` for multi-reference, `0.7` for heavy transformation
4. **Model choice**: Always use 9B over 4B for multi-reference tasks
5. **Reference order**: First image is the base — put your main subject first
