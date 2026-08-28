# Cinematographer Prompts — B-Roll Visual Continuity Patterns

## Problem

When generating multiple video clips from separate prompts, each clip can look like a different video — different characters, lighting, colors, or styles. This breaks the illusion of a continuous reel.

## Solution: B-Roll Cinematographer with Continuity Rules

Use an LLM (agy/gemini-3.1-pro-high) to generate prompts that enforce **strict visual continuity** across all clips — but for **B-roll footage**, not talking heads.

### Continuity Rules (include in prompt)

1. **SAME STYLE**: Consistent cinematic look — professional film quality throughout
2. **SAME COLOR GRADING**: Warm tones, vibrant colors, consistent grading
3. **SAME LIGHTING**: Golden-hour / natural daylight throughout
4. **SAME ASPECT**: Vertical 9:16, modern social-media reel aesthetic
5. **PROGRESSIVE SHOTS**: Wide → Medium → Close-up → Medium → Wide (cycle through)
6. **TOPIC-RELEVANT**: Each scene shows what the script line describes
7. **NO TALKING HEADS**: No presenters, no podcaster, no talking faces

### Prompt Template

```
You are a cinematographer creating a [DURATION]-second vertical (9:16) social media reel.
The reel has exactly [NUM_CLIPS] segments of [CLIP_DURATION] seconds each.
You must create [NUM_CLIPS] B-ROLL visual prompts that maintain STRICT VISUAL CONTINUITY.

CRITICAL: These are B-ROLL clips — NOT a talking head. Each clip shows RELEVANT SCENES
that match what the narrator is saying. The viewer sees the story through visuals,
not a presenter.

CRITICAL CONTINUITY RULES:
1. SAME STYLE: Consistent cinematic look — professional film quality throughout
2. SAME COLOR GRADING: Warm tones, vibrant colors, consistent grading
3. SAME LIGHTING: Golden-hour / natural daylight throughout
4. SAME ASPECT: Vertical 9:16, modern social-media reel aesthetic
5. PROGRESSIVE SHOTS: Wide → Medium → Close-up → Medium → Wide (cycle through)
6. TOPIC-RELEVANT: Each scene shows what the script line describes — NOT a person talking
7. NO TALKING HEADS: No presenters, no podcaster, no talking faces

SCRIPT (each line = one 5s clip):
{script_text}

TOPIC: {topic}

Create exactly [NUM_CLIPS] visual prompts, one per line, numbered 1-[NUM_CLIPS].
Each prompt describes a distinct B-ROLL scene matching the script line.
Be specific about what the viewer sees — locations, objects, actions, people in context.

Output ONLY the [NUM_CLIPS] prompts, one per line, no extra text.
```

### Example: 60s Reel (12 × 5s clips) — B-Roll

```
You are a cinematographer creating a 60-second vertical (9:16) social media reel.
The reel has exactly 12 segments of 5 seconds each.
You must create 12 B-ROLL visual prompts that maintain STRICT VISUAL CONTINUITY.

CRITICAL: These are B-ROLL clips — NOT a talking head. Each clip shows RELEVANT SCENES
that match what the narrator is saying. The viewer sees the story through visuals,
not a presenter.

CRITICAL CONTINUITY RULES:
1. SAME STYLE: Consistent cinematic look — professional film quality throughout
2. SAME COLOR GRADING: Warm tones, vibrant colors, consistent grading
3. SAME LIGHTING: Golden-hour / natural daylight throughout
4. SAME ASPECT: Vertical 9:16, modern social-media reel aesthetic
5. PROGRESSIVE SHOTS: Wide → Medium → Close-up → Medium → Wide (cycle through)
6. TOPIC-RELEVANT: Each scene shows what the script line describes — NOT a person talking
7. NO TALKING HEADS: No presenters, no podcaster, no talking faces

SCRIPT (each line = one 5s clip):
ಏನ್ ಗೊತ್ತಾ? ಬೆಂಗಳೂರಲ್ಲಿ ಹೊಸ ಪಾಲಿಟಿಕ್ಸ್ ಶುರುವಾಗಿದೆ!
ಬಿಡದಿ ಟೌನ್‌ಶಿಪ್ ಬಗ್ಗೆ ಬಿಜೆಪಿ-ಕಾಂಗ್ರೆಸ್ ಭರ್ಜರಿ ಫೈಟ್.
ಸರ್ಕಾರ ಇಲ್ಲಿ ಹೊಸ ಲೇಔಟ್ ಮಾಡೋಕೆ ಹೊರಟಿದೆ.
ಇದು ಕಾಂಗ್ರೆಸ್‌ನ ರಿಯಲ್ ಎಸ್ಟೇಟ್ ದಂಧೆ ಅಂತ ಬಿಜೆಪಿ ಆರೋಪ.
ಫ್ರೀಡಂ ಪಾರ್ಕ್‌ನಲ್ಲಿ ಇದರ ವಿರುದ್ಧ ದೊಡ್ಡ ಪ್ರೊಟೆಸ್ಟ್ ನಡೀತು.
ಲಕ್ಷಾಂತರ ಮರ ಕಡಿದು ಹಸಿರು ನಾಶ ಮಾಡ್ತಿದ್ದಾರೆ!
ರೈತರು ಕೂಡ ಜಾಗ ಕೊಡಲು ರೆಡಿ ಇಲ್ಲ.
ಎಲೆಕ್ಷನ್‌ ಫಂಡ್‌ಗಾಗಿ ಈ ಪ್ಲಾನ್ ಅಂತ ಅಶೋಕ್ ಗುಡುಗಿದ್ದಾರೆ.
ಭೂಮಾಫಿಯಾವೇ ಸರ್ಕಾರವಾಗಿದೆ ಅಂತ ಶೋಭಾ ಕರಂದ್ಲಾಜೆ ಆಕ್ರೋಶ.
ಸರ್ಕಾರ ಮಾತ್ರ ಯಾರನ್ನೂ ಬಲವಂತ ಮಾಡಲ್ಲ ಅಂತಿದೆ.
ಅಭಿವೃದ್ಧಿ ಹೆಸರಲ್ಲಿ ಭೂಮಿ ಕಸಿಯೋದು ಸರಿನಾ?
ಕಮೆಂಟ್ ಮಾಡಿ, ಪೇಜ್ ಫಾಲೋ ಮಾಡಿ!

TOPIC: Bengaluru park commercialisation sparks BJP-Congress row

Create exactly 12 visual prompts, one per line, numbered 1-12.
Each prompt describes a distinct B-ROLL scene matching the script line.
Be specific about what the viewer sees — locations, objects, actions, people in context.

Output ONLY the 12 prompts, one per line, no extra text.
```

### Expected B-Roll Output Example

```
Wide aerial shot of Bengaluru cityscape with political banners and construction cranes, golden-hour sunlight, vertical 9:16
Medium shot of BJP and Congress party members arguing at a town planning office, natural daylight, vertical 9:16
Close-up of government layout plan documents on a desk, warm lighting, shallow depth of field, vertical 9:16
Medium shot of real estate developers meeting in a conference room, professional setting, vertical 9:16
Wide shot of Freedom Park protest — people holding signs and banners, daytime, vertical 9:16
Close-up of tree stumps and deforested land, golden-hour lighting, emotional impact, vertical 9:16
Medium shot of farmers standing firmly on their land with protest signs, natural daylight, vertical 9:16
Close-up of election funding documents and money, dramatic lighting, vertical 9:16
Wide shot of politicians arguing in parliament, intense atmosphere, vertical 9:16
Medium shot of government building with officials, neutral daylight, vertical 9:16
Close-up of land records and property documents, tense lighting, vertical 9:16
Wide shot of Bengaluru skyline with text overlay "Comment Below", warm sunset, vertical 9:16
```

### Fallback Prompts (when agy fails)

If the LLM fails, use hardcoded B-roll fallback prompts with a shared `base_style`:

```python
base_style = "vertical 9:16, cinematic, golden-hour natural lighting, warm vibrant colors, professional film quality, social-media reel aesthetic"
prompts = [
    f"Establishing wide shot of the location related to '{topic}', aerial perspective showing the full scene, {base_style}",
    f"Medium shot of people involved in the story about '{topic}', natural candid moment, {base_style}",
    f"Close-up of key objects or details related to '{topic}', shallow depth of field, {base_style}",
    # ... continue with progressive shots
]
```

## Key Insight

The `base_style` suffix in each prompt is the critical trick — it forces the video generation model to use the same visual DNA across all clips, even though each prompt describes a different scene. For B-roll, the continuity comes from **style consistency** (lighting, color, aspect ratio) rather than **character consistency**.

## Related

- `kannada-reel` skill — uses this pattern for 12-clip B-roll reels
- `kannada-cinematographer` skill — generates detailed scene-by-scene cinematography breakdowns for Kannada text
- `whats-trending-reel` — uses Veo 3 with reference images (different continuity approach)
