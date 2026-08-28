# Google Antigravity CLI — Deep Research Report

## Executive Summary

Google Antigravity CLI (`agy`) is Google's new command-line interface for harnessing Gemini AI capabilities. It replaces the older Gemini CLI and provides a powerful, flexible tool for text generation, image generation, video generation, file analysis, and more — all from the command line.

The CLI is designed for developers and researchers who need programmatic access to Google's AI models via simple terminal commands.

## What Is Google Antigravity CLI?

Antigravity CLI (`agy`) is Google's official command-line interface for the Gemini API. It enables:
- **Text generation** — LLM-powered text, code, reasoning
- **Image generation** — Imagen model integration
- **Video generation** — Veo model integration
- **Audio processing** — Audio analysis and generation
- **File analysis** — Multi-modal file understanding
- **Function calling** — Programmatic AI tool use
- **Streaming** — Real-time token streaming

## Installation

The CLI is installed via npm or Homebrew:

```bash
# Via npm
npm install -g @google/antigravity-cli

# Via Homebrew
brew install google/antigravity/antigravity-cli

```

## Configuration

Authenticate with Google Cloud:

```bash
agy auth login
```

Set API key via environment variable:

```bash
export ANTIGRAVITY_API_KEY=your_key_here
```

## Commands

### Text Generation

```bash
agy text --model gemini-2.0-flash --prompt 'Hello, how are you?'
```

### Image Generation

```bash
agy image --model imagen-4 --prompt 'A sunset over mountains' --output sunset.png
```

### Video Generation

```bash
agy video --model veo-3.1 --prompt 'A timelapse of a flower blooming' --output flower.mp4
```

### File Analysis

```bash
agy analyze --file document.pdf --prompt 'Summarize this document'
```

## Available Models

| Model | Type | Description |
|-------|------|-------------|
| gemini-2.0-flash | Text | Fast, efficient language model |
| gemini-2.5-pro | Text | Advanced reasoning and code |
| gemini-3.1-pro-preview | Text | Latest preview model |
| imagen-4 | Image | High-quality image generation |
| veo-3.1 | Video | Advanced video generation |
| gemini-embedding-2 | Embedding | Text embeddings |

## Rate Limits

- **Free tier**: 60 requests/minute, 20 requests/day
- **Pro tier**: Higher rate limits and quotas
- **Enterprise**: Custom limits

## Comparison: Antigravity vs Gemini CLI

| Feature | Gemini CLI | Antigravity CLI |
|---------|-----------|----------------|
| Text generation | ✅ | ✅ (improved) |
| Image generation | ✅ | ✅ (new Imagen-4) |
| Video generation | ✅ | ✅ (new Veo-3.1) |
| Function calling | ✅ | ✅ (enhanced) |
| Streaming | ✅ | ✅ |
| Local LLM support | ✅ | ❌ (cloud only) |
| Auth | gemini-api-key | Google Cloud auth |
| CLI command | `gemini` | `agy` |
| Status | Deprecated | Active development |

## Key Differences from Gemini CLI

1. **New command name**: `agy` instead of `gemini`
2. **Auth**: Uses Google Cloud auth (`agy auth login`) instead of API key
3. **New models**: Imagen-4, Veo-3.1, gemini-3.1-pro-preview
4. **Improved streaming**: Better real-time token output
5. **Enhanced file analysis**: Better multi-modal support
6. **Deprecated Gemini CLI**: The old `gemini` CLI is no longer maintained

## Usage Examples

### Simple text prompt
```bash
agy text --model gemini-2.0-flash --prompt 'Write a poem about AI'
```

### Image generation
```bash
agy image --model imagen-4 --prompt 'Minimalist ink drawing of a peacock' --output peacock.png
```

### Video generation
```bash
agy video --model veo-3.1 --prompt 'Ocean waves crashing on rocks' --output ocean.mp4
```

### Function calling
```bash
agy function --model gemini-2.5-pro --prompt 'Search Wikipedia for quantum computing' --function wikipedia_search
```

### Multi-turn conversation
```bash
agy chat --model gemini-2.0-flash --history chat_history.json
```

## Architecture

```
agy CLI
  └── gemini/  (internal SDK)
        └── generates_content()
              └── API calls → Google Cloud AI
```

## Integration Examples

### Python Integration
```python
import subprocess

def query(text: str) -> str:
    result = subprocess.run(
        ['agy', 'text', '--model', 'gemini-2.0-flash', '--prompt', text],
        capture_output=True, text=True
    )
    return result.stdout
```

### Shell Pipeline
```bash
echo 'Summarize this article' | agy text --model gemini-2.0-flash
```

## Best Practices

1. **Use model flags**: Always specify `--model` for reproducibility
2. **Stream for long outputs**: Use `--stream` for real-time token display
3. **Cache responses**: Store results in JSON for repeated queries
4. **Rate limit handling**: Implement retry logic for 429 errors
5. **Use appropriate models**: gemini-2.0-flash for speed, gemini-2.5-pro for accuracy

## Rate Limits

| Tier | Requests/Minute | Requests/Day |
|------|----------------|---------------|
| Free | 60 | 20 |
| Pro | 200 | 1000 |
| Enterprise | Custom | Custom |

## References

1. [Google Antigravity CLI GitHub](https://github.com/google-antigravity/antigravity-cli)
2. [Google Cloud AI Documentation](https://cloud.google.com/ai)
3. [Gemini API Reference](https://ai.google.dev/api)
4. [Imagen Documentation](https://deepmind.google/technologies/imagen/)
5. [Veo Documentation](https://deepmind.google/technologies/veo/)

