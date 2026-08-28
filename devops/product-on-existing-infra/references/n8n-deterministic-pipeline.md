# n8n Deterministic Pipeline Patterns

## Pattern: Deterministic Scoring + LLM Generation

**Principle:** Keep all comparison, scoring, and matching logic in n8n code nodes (deterministic). Only use LLM for creative generation (improvements, suggestions, rewrites).

### Why This Matters

- **Consistency:** Deterministic scoring produces the same result every time
- **Speed:** Code nodes execute in milliseconds; LLM calls take seconds
- **Cost:** LLM calls are expensive; deterministic logic is free
- **Debuggability:** Deterministic logic is easy to test and verify

### Example: ATS Scoring in n8n Code Node

```javascript
// Input: { sections: {...}, raw_text: "...", word_count: 150 }
const sections = $input.first().json.sections || {};
const rawText = $input.first().json.raw_text || '';

// Completeness scoring
const requiredSections = {
  contact_info: ['email', 'phone', 'linkedin'],
  summary: ['summary', 'objective', 'profile'],
  experience: ['experience', 'work', 'employment'],
  education: ['education', 'degree', 'university'],
  skills: ['skills', 'technical', 'competencies']
};

let completenessScore = 0;
for (const [section, keywords] of Object.entries(requiredSections)) {
  const text = (sections[section] || '').toLowerCase();
  if (keywords.some(kw => text.includes(kw))) completenessScore++;
}
completenessScore = Math.round((completenessScore / Object.keys(requiredSections).length) * 100);

// Formatting scoring
let formattingScore = 100;
const bulletCount = (rawText.match(/^\s*[-•*]\s+/gm) || []).length;
if (bulletCount === 0) formattingScore -= 30;
if (wordCount < 100) formattingScore -= 20;
formattingScore = Math.max(0, formattingScore);

// Keyword scoring
const jobTitle = $input.first().json.job_title || '';
let keywordScore = 50;
let missingKeywords = [];
if (jobTitle) {
  const industryKeywords = {
    software: ['python', 'java', 'javascript', 'react', 'api', 'sql', 'docker', 'aws'],
    data: ['python', 'sql', 'machine learning', 'pandas', 'tensorflow']
  };
  let targetKeywords = [];
  for (const [industry, keywords] of Object.entries(industryKeywords)) {
    if (jobTitle.toLowerCase().includes(industry)) {
      targetKeywords = targetKeywords.concat(keywords);
    }
  }
  if (targetKeywords.length > 0) {
    const rawLower = rawText.toLowerCase();
    const matched = targetKeywords.filter(kw => rawLower.includes(kw));
    missingKeywords = targetKeywords.filter(kw => !rawLower.includes(kw));
    keywordScore = Math.round((matched.length / targetKeywords.length) * 100);
  }
}

// Overall score
const overall = Math.round(
  keywordScore * 0.30 +
  formattingScore * 0.25 +
  completenessScore * 0.30 +
  (100 - (rawText.match(/\d+%/g) ? 0 : 15)) * 0.15
);

return [{
  json: {
    ats_score: {
      overall: overall,
      keywords_match: keywordScore,
      formatting: formattingScore,
      completeness: completenessScore,
      missing_keywords: missingKeywords.slice(0, 20),
      recommendations: []
    }
  }
}];
```

### Example: LLM Improvement Generation

```javascript
// Call Ollama for improvement suggestions
const axios = require('axios');

const atsScore = $input.first().json.ats_score;
const ocrJson = $input.first().json;
const jobTitle = $input.first().json.job_title || 'Not specified';

// Build resume content
const sections = ocrJson.sections || {};
let contentParts = [];
for (const [name, text] of Object.entries(sections)) {
  if (text) contentParts.push(`=== ${name.toUpperCase()} ===\n${text}`);
}
const resumeContent = contentParts.join('\n\n') || ocrJson.raw_text || 'No content';

const prompt = `You are an expert resume reviewer. Analyze this resume and provide improvements.

## Resume Content
${resumeContent.substring(0, 3000)}

## ATS Score
${JSON.stringify(atsScore, null, 2)}

## Job Title
${jobTitle}

Return JSON with: rewritten_sections, suggestions, keyword_suggestions, formatting_tips, estimated_ats_score_after`;

try {
  const response = await axios.post('http://ollama:11434/api/generate', {
    model: 'qwen2.5:0.5b',
    prompt: prompt,
    stream: false,
    options: { temperature: 0.3, max_tokens: 2048 }
  });

  let rawOutput = response.data.response || '';
  rawOutput = rawOutput.replace(/^```json\s*|\s*```$/g, '').trim();
  const improvements = JSON.parse(rawOutput);

  return [{ json: { improvements, status: 'completed' } }];
} catch (error) {
  // Fallback when Ollama is unavailable
  return [{
    json: {
      improvements: {
        rewritten_sections: {},
        suggestions: ['Add a professional summary', 'Use action verbs', 'Quantify achievements'],
        keyword_suggestions: [],
        formatting_tips: ['Use consistent formatting', 'Include bullet points'],
        estimated_ats_score_after: Math.min(100, atsScore.overall + 15)
      },
      status: 'completed',
      fallback: true
    }
  }];
}
```

### Example: Saving Results to API

```javascript
const axios = require('axios');

const resumeId = $input.first().json.resume_id;
const atsScore = $input.first().json.ats_score;
const improvements = $input.first().json.improvements;

// Save ATS score
try {
  await axios.post('http://resume-api:3006/api/v1/internal/n8n/process-resume', {
    resume_id: resumeId,
    action: 'score',
    data: atsScore
  }, {
    headers: { 'X-API-Key': process.env.N8N_API_KEY || 'change-me-secret' }
  });
} catch (e) {
  console.log('ATS save failed:', e.message);
}

// Save improvements
try {
  await axios.post('http://resume-api:3006/api/v1/internal/n8n/process-resume', {
    resume_id: resumeId,
    action: 'improve',
    data: improvements
  }, {
    headers: { 'X-API-Key': process.env.N8N_API_KEY || 'change-me-secret' }
  });
} catch (e) {
  console.log('Improvements save failed:', e.message);
}

return [{
  json: {
    resume_id: resumeId,
    status: 'pipeline_complete',
    ats_score: atsScore,
    improvements: improvements
  }
}];
```

## n8n Workflow Configuration

### Webhook Trigger Node
- **HTTP Method:** POST
- **Path:** `resume-upload`
- **Response Mode:** Response Node
- **Authentication:** API Key (X-API-Key header)

### Code Node Settings
- **Output Key:** `default`
- **Timeout:** 300 seconds (for LLM calls)
- **Save Data:** All (for debugging)

### Error Handling
- Set `saveDataErrorExecution: all` in workflow settings
- Use try/catch in all code nodes
- Always provide deterministic fallbacks

## Common Pitfalls

1. **Ollama URL:** Use `http://127.0.0.1:11434` (host-level), NOT `http://ollama:11434` (Docker hostname)
2. **Token limits:** Truncate resume content to ~3000 chars to avoid Ollama token limits
3. **JSON parsing:** LLM responses may include markdown code blocks — strip them before parsing
4. **API key:** Internal n8n-to-API communication requires `X-API-Key` header
5. **Timeout:** LLM calls can take 30-60 seconds — set workflow timeout to 300s
6. **Fallback:** Always provide deterministic fallback when LLM is unavailable
