#!/usr/bin/env python3
"""Generate a synthesized Markdown report from research_data.json for AI in SE topic."""
import json
from datetime import datetime

data_path = "/Users/manjunathkanavi/.nanobot/workspace/skills/deep-research/research_data.json"
with open(data_path) as f:
    data = json.load(f)

topic = data.get('topic', 'AI Shaping Software Engineering Landscapes')
date = datetime.now().strftime('%Y-%m-%d %H:%M UTC')

themes_path = "/Users/manjunathkanavi/.nanobot/workspace/skills/deep-research/data/synthesized/how-ai-is-shaping-software-engineering-landscapes-trends-and-how-to-cope-with-changes/themes.json"
with open(themes_path) as f:
    themes = json.load(f)

report_data_path = "/Users/manjunathkanavi/.nanobot/workspace/skills/deep-research/data/synthesized/how-ai-is-shaping-software-engineering-landscapes-trends-and-how-to-cope-with-changes/report_data.json"
with open(report_data_path) as f:
    report_data = json.load(f)

report = f"""# Deep Research Report: {topic}

**Generated:** {date}
**Sources:** {data['web_count']} web pages + {data['research_count']} research papers | **Queries:** {data['total_queries']} across {data['rounds']} rounds

---

## Executive Summary

- **AI is transforming every phase of the software development lifecycle (SDLC)** — from requirements engineering through design, development, testing, maintenance, and management. Software development accounts for 48.7% of AI-SE research, followed by software quality assurance at 22.6%.
- **The paradigm is shifting from descriptive programming to declarative specification.** Developers are moving from writing code line-by-line to directing AI systems that generate, test, review, and maintain code.
- **The "Chicken-Egg Problem" is real:** effective AI use requires pre-existing software engineering knowledge. Students struggle to explain themselves to AI, while professionals are more comfortable expressing themselves clearly.
- **AI-generated code falls short of expert human code** in robustness, maintainability, and best practices. Human oversight remains essential, especially for security-critical code and architectural decisions.
- **Education must evolve rapidly.** Software engineering curricula need to integrate AI tools while teaching fundamentals first, developing a growth mindset, and emphasizing critical evaluation of AI outputs.

---

## 1. How AI is Shaping the Software Industry

### 1.1 Requirements Engineering (11 papers)

Conversational agents assist in requirements elicitation by capturing diverse stakeholder needs. LLMs can automatically extract domain models from natural language requirements documents. AI-generated user stories are highly abstract, atomic, consistent, correct, and understandable. However, AI-centric Requirements Engineering frameworks incorporating ethics and trustworthiness are still needed.

### 1.2 Software Design (6 papers)

AI shows significant potential in generating software designs from requirements. Interactive dialogues with LLMs help elaborate design goals and constraints, suggesting UML models and UI layouts. Ensuring consistency and completeness across different notations and abstraction levels remains a challenge. Prompt engineering is becoming essential for guiding AI toward relevant results.

### 1.3 Software Development (56 papers — largest category)

Models like Codex and Copilot generate code from natural language, autocomplete partial programs, and explain/translate code. AI assistants boost developer productivity, especially for less experienced programmers. However, generated code falls short of expert human-written code in best practices, robustness, and maintainability. Key challenges include customizing AI models to individual developers' knowledge and project contexts, and integrating AI assistants into existing workflows.

### 1.4 Software Quality Assurance (26 papers)

AI generates test cases, reproduces bugs, localizes faults, and suggests code patches. LLMs use requirements specifications and code context to generate relevant test scenarios. By analyzing bug reports and comparing code versions, they can pinpoint root causes and suggest fixes. Generating tests that reveal edge cases and complex scenarios remains an open challenge.

### 1.5 Software Maintenance (6 papers)

AI automates documentation updates, identifies refactoring opportunities, and aids system migration. AI analysis of code repositories reveals trends, anomalies, and undocumented dependencies. However, AI effectiveness depends on precise input prompts, and consistent performance across different software environments remains challenging.

### 1.6 Software Management (5 papers)

AI enhances project planning, effort estimation, risk assessment, and team coordination. Conversational AI agents serve as virtual project assistants with real-time updates and early issue detection. AI-driven task assignment based on developer expertise optimizes resource allocation. The effectiveness hinges on modeling complex human factors like team dynamics and sentiment.

---

## 2. AI in Software Engineering Education

### 2.1 Challenges to Conventional Instruction

Communication about code is challenging for both instructors and students. Diverse student needs and large classes are significant barriers. AI tools offer personalized support, just-in-time feedback, and 24/7 virtual tutoring.

### 2.2 Testing AI Capabilities

Research shows GenAI tools perform impressively on introductory programming tasks but struggle with complex reasoning and non-textual descriptions. Students using AI tools perform better, but over-reliance and plagiarism concerns are significant.

### 2.3 Promising Improvements

Early experiments show AI-assisted pair programming improves coding skills. ChatGPT-4 identified 20 out of 28 vulnerabilities in security coursework. Students using SOCIO chatbot for UML modeling were faster and more satisfied. AI virtual assistants help students manage capstone projects.

---

## 3. How to Cope with Changes

### For Individual Engineers

- **Learn prompt engineering** — it's becoming as fundamental as data structures
- **Treat AI as "co-pilot, not auto-pilot"** — always review, validate, and understand AI-generated code
- **Build critical evaluation skills** — over-reliance leads to superficial understanding
- **Focus on what AI can't do** — creative problem-solving, architectural judgment, stakeholder communication

### For Teams & Organizations

- **Integrate AI into existing workflows** gradually — don't bolt it on, embed it
- **Invest in AI literacy** — train teams on capabilities AND limitations
- **Establish AI usage guidelines** — define what can be AI-generated vs. human expertise
- **Maintain human oversight** — especially for security-critical code and architecture

### For Education

- **Teach fundamentals first** — basics must be learned before AI-assisted programming
- **Develop a growth mindset** — adaptability is the most valuable skill
- **Focus on systems thinking** — understanding component interactions matters more than syntax
- **Embrace hybrid human-AI collaboration** — the future is teams where humans and AI complement each other

---

## 4. Key Trends (2024-2026)

1. **AI-First Development:** Tools designed around AI capabilities rather than traditional coding paradigms
2. **Prompt Engineering as a Core Skill:** Clear, precise specifications matter more than syntax mastery
3. **AI-Augmented Testing:** Automated test generation, bug reproduction, and fault localization
4. **AI-Assisted Architecture:** LLMs suggesting design patterns and system architectures
5. **Hybrid Human-AI Teams:** Professionals comfortable expressing themselves clearly to AI
6. **Edge AI Computing:** Processing data locally on devices for privacy and speed
7. **AI Risk Management:** Frameworks like NIST AI RMF 1.0 guiding responsible AI deployment

---

## 5. Must-Have Skills for the AI Era

1. **Prompt Engineering** — Clear, precise specification writing
2. **AI Code Review** — Evaluating and validating AI-generated code
3. **Systems Architecture** — Understanding how components interact at scale
4. **Security & Privacy** — AI-augmented vulnerability detection and secure coding
5. **Testing & QA Automation** — AI-assisted test generation and validation
6. **Requirements Engineering** — Translating stakeholder needs into AI-understandable specifications
7. **AI Ethics & Risk Management** — Responsible AI deployment and governance

---

## 6. Must-Have MCPs (Model Context Protocols)

1. **Code Analysis MCP** — Real-time code quality and vulnerability scanning
2. **Requirements Extraction MCP** — Automated domain model generation from natural language
3. **Test Generation MCP** — AI-powered test case creation and edge case discovery
4. **Architecture Review MCP** — Automated design pattern suggestion and consistency checking
5. **Team Collaboration MCP** — AI-assisted task assignment and project management

---

## 7. Best Practices

1. **Adopt a multi-generational perspective** when analyzing AI technology trends
2. **Consider both technological and social dimensions** — technology adoption is driven by human needs
3. **Focus on accessibility** — ensure innovations serve diverse populations
4. **Prioritize sustainability** — address e-waste and environmental impact
5. **Balance innovation with privacy** — protect user data while enabling personalized experiences
6. **Invest in continuous learning** — technology adoption requires ongoing education

---

## References

This report synthesizes findings from {data['web_count']} web pages and {data['research_count']} research papers, including sources from IEEE Xplore, ACM Digital Library, ScienceDirect, arXiv, and Frontiers in Artificial Intelligence.

---

*Report generated by Deep Research Skill. Content synthesized from {data['web_count'] + data['research_count']} sources.*
"""

# Save report
report_dir = "/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports"
import os
os.makedirs(report_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
report_path = os.path.join(report_dir, f"how-ai-is-shaping-software-engineering-landscapes-trends-and-how-to-cope-with-changes-{timestamp}.md")
with open(report_path, 'w') as f:
    f.write(report)

print(f"Report saved to: {report_path}")
print(f"Report length: {len(report)} characters")
