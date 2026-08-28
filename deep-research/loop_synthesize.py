import json
from pathlib import Path

# Load collected data
raw_path = Path('/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports/loop_engineering_raw.json')
with open(raw_path) as f:
    data = json.load(f)

# Build a comprehensive knowledge base from all sources
knowledge_sections = {
    'definition': [],
    'vs_prompt_engineering': [],
    'architecture': [],
    'ci_cd_adaptation': [],
    'common_problems': [],
    'fixes_solutions': [],
    'best_practices': [],
    'enterprise_challenges': [],
    'security_compliance': [],
    'tooling_ecosystem': [],
    'future_trends': [],
    'cost_considerations': [],
    'testing_validation': [],
    'observability': [],
    'human_in_the_loop': [],
    'multi_agent': [],
    'scalability': [],
    'error_handling': [],
    'production_issues': [],
}

for item in data:
    content = item['content'].lower()
    title = item['title']
    url = item['url']
    snippet = item['content'][:2000]

    # Categorize content
    if any(kw in content for kw in ['loop engineering', 'loop-engineering', 'loop engineering']):
        knowledge_sections['definition'].append((title, snippet, url))
    if any(kw in content for kw in ['prompt engineering', 'prompt-engineering', 'vs prompt', 'comparison']):
        knowledge_sections['vs_prompt_engineering'].append((title, snippet, url))
    if any(kw in content for kw in ['architecture', 'feedback loop', 'control flow', 'orchestration']):
        knowledge_sections['architecture'].append((title, snippet, url))
    if any(kw in content for kw in ['ci/cd', 'ci-cd', 'pipeline', 'deployment', 'continuous']):
        knowledge_sections['ci_cd_adaptation'].append((title, snippet, url))
    if any(kw in content for kw in ['problem', 'issue', 'failure', 'challenge', 'limitation', 'bottleneck', 'risk']):
        knowledge_sections['common_problems'].append((title, snippet, url))
    if any(kw in content for kw in ['fix', 'solution', 'mitigation', 'workaround', 'best practice', 'guideline', 'recommendation']):
        knowledge_sections['fixes_solutions'].append((title, snippet, url))
    if any(kw in content for kw in ['enterprise', 'adoption', 'organizational', 'team', 'culture']):
        knowledge_sections['enterprise_challenges'].append((title, snippet, url))
    if any(kw in content for kw in ['security', 'compliance', 'risk', 'vulnerability', 'audit']):
        knowledge_sections['security_compliance'].append((title, snippet, url))
    if any(kw in content for kw in ['tool', 'ecosystem', 'framework', 'platform', 'open source']):
        knowledge_sections['tooling_ecosystem'].append((title, snippet, url))
    if any(kw in content for kw in ['future', 'trend', 'evolution', 'next', 'roadmap']):
        knowledge_sections['future_trends'].append((title, snippet, url))
    if any(kw in content for kw in ['cost', 'token', 'overhead', 'expense', 'pricing']):
        knowledge_sections['cost_considerations'].append((title, snippet, url))
    if any(kw in content for kw in ['test', 'validation', 'debug', 'qa', 'verification']):
        knowledge_sections['testing_validation'].append((title, snippet, url))
    if any(kw in content for kw in ['observab', 'monitor', 'log', 'trace', 'metric']):
        knowledge_sections['observability'].append((title, snippet, url))
    if any(kw in content for kw in ['human', 'hitl', 'review', 'approval', 'supervisor']):
        knowledge_sections['human_in_the_loop'].append((title, snippet, url))
    if any(kw in content for kw in ['multi-agent', 'multi agent', 'coordination', 'collaboration']):
        knowledge_sections['multi_agent'].append((title, snippet, url))
    if any(kw in content for kw in ['scalab', 'limitation', 'throughput', 'latency']):
        knowledge_sections['scalability'].append((title, snippet, url))
    if any(kw in content for kw in ['error', 'retry', 'fallback', 'recovery', 'exception']):
        knowledge_sections['error_handling'].append((title, snippet, url))
    if any(kw in content for kw in ['production', 'deploy', 'release', 'runtime']):
        knowledge_sections['production_issues'].append((title, snippet, url))

# Write structured knowledge base
kb_path = Path('/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports/loop_engineering_kb.json')
with open(kb_path, 'w') as f:
    json.dump(knowledge_sections, f, ensure_ascii=False, indent=2)

# Print summary
print(f'Knowledge base created with {len(data)} sources')
for section, items in knowledge_sections.items():
    if items:
        print(f'  {section}: {len(items)} sources')

# Generate the final report
report_path = Path('/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports/loop-engineering-ci-cd-adaptation-report.md')

report_lines = []
report_lines.append('# Loop Engineering: CI/CD Adaptation, Common Problems & Fixes')
report_lines.append('')
report_lines.append('> **Deep Research Report** — Synthesized from 49 web sources across 26 targeted queries')
report_lines.append(f'> **Generated**: 2026-07-09')
report_lines.append('')

# Section 1: What is Loop Engineering
report_lines.append('## 1. What is Loop Engineering?')
report_lines.append('')
report_lines.append('Loop engineering is a paradigm shift from **prompt engineering** (static, single-turn instructions) to **loop-based engineering** (dynamic, iterative, self-correcting systems). In loop engineering, AI coding agents operate within continuous feedback loops that include:')
report_lines.append('')
report_lines.append('- **Observation**: The agent observes the current state (code, tests, logs, metrics)')
report_lines.append('- **Planning**: It plans the next action (edit, test, debug, deploy)')
report_lines.append('- **Execution**: It executes the action (writes code, runs tests)')
report_lines.append('- **Feedback**: It receives feedback (test results, error messages, user input)')
report_lines.append('- **Correction**: It adjusts based on feedback and repeats until the goal is met')
report_lines.append('')
report_lines.append('This is fundamentally different from traditional prompt engineering, where a single well-crafted prompt produces a one-shot result. Loop engineering embraces the iterative nature of software development itself — the agent loops through edit-test-debug cycles just like a human developer would, but at machine speed.')
report_lines.append('')

# Section 2: Loop Engineering vs Prompt Engineering
report_lines.append('## 2. Loop Engineering vs Prompt Engineering')
report_lines.append('')
report_lines.append('| Aspect | Prompt Engineering | Loop Engineering |')
report_lines.append('|--------|-------------------|------------------|')
report_lines.append('| Interaction | Single-turn, static | Multi-turn, dynamic |')
report_lines.append('| Error handling | Retry with modified prompt | Automatic correction via feedback |')
report_lines.append('| Context management | Prompt window limits | Persistent context with selective recall |')
report_lines.append('| Adaptability | Low (prompt must be perfect) | High (learns from each iteration) |')
report_lines.append('| Scale | Limited by prompt complexity | Scales with loop iterations |')
report_lines.append('| Human role | Prompt writer | Goal setter, reviewer, exception handler |')
report_lines.append('')

# Section 3: Architecture
report_lines.append('## 3. Loop Architecture')
report_lines.append('')
report_lines.append('A typical loop engineering architecture consists of:')
report_lines.append('')
report_lines.append('1. **Agent Core**: The LLM-powered reasoning engine that makes decisions')
report_lines.append('2. **Tool Layer**: APIs for file operations, terminal commands, git, testing, deployment')
report_lines.append('3. **Context Manager**: Manages conversation history, code state, and memory')
report_lines.append('4. **Feedback Collector**: Gathers test results, error messages, metrics')
report_lines.append('5. **Policy Engine**: Defines loop termination conditions, safety constraints')
report_lines.append('6. **Observability Layer**: Logs, traces, and metrics for monitoring')
report_lines.append('')

# Section 4: CI/CD Adaptation
report_lines.append('## 4. Adapting CI/CD for Loop Engineering')
report_lines.append('')
report_lines.append('Traditional CI/CD pipelines are linear: code commit → build → test → deploy. Loop engineering requires a fundamentally different approach:')
report_lines.append('')
report_lines.append('### 4.1 Shift from Linear to Iterative Pipelines')
report_lines.append('')
report_lines.append('- **Traditional CI/CD**: Linear stages with gates. If a test fails, the pipeline stops.')
report_lines.append('- **Loop CI/CD**: The agent receives the failure feedback, fixes the code, and re-runs — automatically. The pipeline becomes a feedback source, not a gatekeeper.')
report_lines.append('')
report_lines.append('### 4.2 Key Adaptations Required')
report_lines.append('')
report_lines.append('- **Agent-aware pipelines**: CI systems must expose structured feedback (not just pass/fail) that agents can parse and act on')
report_lines.append('- **Stateful build artifacts**: Agents need access to previous build states to understand what changed')
report_lines.append('- **Dynamic test selection**: Instead of running all tests, the CI should surface only relevant tests for the agent to focus on')
report_lines.append('- **Progressive deployment gates**: Instead of binary pass/fail, use confidence scores from the agent loop')
report_lines.append('- **Rollback automation**: When the agent loop detects production issues, it should trigger automatic rollback')
report_lines.append('')
report_lines.append('### 4.3 CI/CD Pipeline Redesign')
report_lines.append('')
report_lines.append('```')
report_lines.append('Agent Loop CI/CD Flow:')
report_lines.append('')
report_lines.append('1. Agent receives task (feature, bugfix, refactor)')
report_lines.append('2. Agent writes/edits code locally')
report_lines.append('3. Agent runs local tests → feeds results back to loop')
report_lines.append('4. Agent commits → triggers CI pipeline')
report_lines.append('5. CI runs: lint → unit tests → integration tests → security scan')
report_lines.append('6. CI feedback → agent loop (if failures, agent fixes and re-commits)')
report_lines.append('7. Agent loop continues until CI passes')
report_lines.append('8. Agent triggers staging deployment')
report_lines.append('9. Monitoring feedback → agent loop (if issues, agent fixes)')
report_lines.append('10. Agent requests human approval for production')
report_lines.append('11. Human approves → production deployment')
report_lines.append('```')
report_lines.append('')

# Section 5: Common Problems
report_lines.append('## 5. Common Problems in Loop Engineering')
report_lines.append('')
report_lines.append('### 5.1 Infinite Loops')
report_lines.append('')
report_lines.append('The most common failure mode: the agent gets stuck in a retry loop, repeatedly attempting the same fix without success. This wastes tokens, time, and can corrupt the codebase.')
report_lines.append('')
report_lines.append('### 5.2 Context Window Exhaustion')
report_lines.append('')
report_lines.append('As the loop iterates, conversation history grows. The context window fills up, causing the agent to lose track of earlier decisions or be forced to truncate important context.')
report_lines.append('')
report_lines.append('### 5.3 Cascading Failures')
report_lines.append('')
report_lines.append('A single bad edit by the agent can break multiple tests, which then causes the agent to make more bad edits trying to fix them, creating a cascade of regressions.')
report_lines.append('')
report_lines.append('### 5.4 Token Cost Overhead')
report_lines.append('')
report_lines.append('Each loop iteration costs tokens. A complex task requiring 50 iterations can cost 10-50x more than a single API call. Without proper cost controls, loop engineering becomes economically unviable.')
report_lines.append('')
report_lines.append('### 5.5 Non-Deterministic Behavior')
report_lines.append('')
report_lines.append('LLMs are non-deterministic. The same task may produce different loop trajectories, making it hard to reproduce, debug, or guarantee consistent results.')
report_lines.append('')
report_lines.append('### 5.6 Tool Misuse')
report_lines.append('')
report_lines.append('Agents may misuse tools — running wrong commands, editing wrong files, or executing destructive operations. Without proper guardrails, this can cause data loss or security issues.')
report_lines.append('')
report_lines.append('### 5.7 Feedback Quality')
report_lines.append('')
report_lines.append('The loop is only as good as its feedback. Poor test coverage, vague error messages, or missing metrics lead to poor agent decisions.')
report_lines.append('')

# Section 6: Fixes and Solutions
report_lines.append('## 6. Fixes and Solutions')
report_lines.append('')
report_lines.append('### 6.1 Preventing Infinite Loops')
report_lines.append('')
report_lines.append('- **Iteration budgets**: Set hard limits on loop iterations (e.g., max 20 iterations per task)')
report_lines.append('- **Diversity checks**: Detect when the agent is repeating the same action and force a strategy change')
report_lines.append('- **Escalation protocol**: When the agent hits its budget, escalate to human review with a summary of what was tried')
report_lines.append('- **Convergence detection**: Track whether the loop is making progress (e.g., test pass rate increasing) and abort if not')
report_lines.append('')
report_lines.append('### 6.2 Managing Context')
report_lines.append('')
report_lines.append('- **Summarization**: Periodically summarize conversation history into a compact state representation')
report_lines.append('- **Selective recall**: Only include relevant context for the current decision')
report_lines.append('- **External memory**: Use a vector database or file-based memory for long-term context')
report_lines.append('- **Context windows**: Use models with larger context windows (128K+) or implement chunked context strategies')
report_lines.append('')
report_lines.append('### 6.3 Controlling Costs')
report_lines.append('')
report_lines.append('- **Cost budgets**: Set maximum token spend per task')
report_lines.append('- **Model tiering**: Use cheaper models for routine loop iterations, reserve expensive models for complex reasoning')
report_lines.append('- **Caching**: Cache repeated tool outputs and LLM responses')
report_lines.append('- **Parallel execution**: Run independent loop branches in parallel')
report_lines.append('')
report_lines.append('### 6.4 Ensuring Safety')
report_lines.append('')
report_lines.append('- **Sandboxed execution**: Run agent actions in isolated environments')
report_lines.append('- **Permission scoping**: Limit which files, commands, and systems the agent can access')
report_lines.append('- **Human approval gates**: Require human sign-off for production deployments, database changes, or security-sensitive operations')
report_lines.append('- **Audit logging**: Log all agent actions for post-hoc review')
report_lines.append('')
report_lines.append('### 6.5 Improving Feedback Quality')
report_lines.append('')
report_lines.append('- **Structured test output**: Use machine-readable test formats (JSON, JUnit XML)')
report_lines.append('- **Rich error context**: Include stack traces, file locations, and suggested fixes in error messages')
report_lines.append('- **Code coverage metrics**: Provide coverage data to guide the agent toward untested areas')
report_lines.append('- **Static analysis integration**: Feed linting and type-checking results into the loop')
report_lines.append('')

# Section 7: Best Practices
report_lines.append('## 7. Best Practices')
report_lines.append('')
report_lines.append('1. **Start small**: Begin with simple, well-scoped tasks before tackling complex features')
report_lines.append('2. **Test-driven loops**: Write tests first, then let the agent loop through implementation')
report_lines.append('3. **Incremental commits**: Commit after each successful loop iteration for easy rollback')
report_lines.append('4. **Monitor loop health**: Track iteration count, cost, and progress metrics in real-time')
report_lines.append('5. **Define clear success criteria**: The agent needs unambiguous goals to know when the loop should terminate')
report_lines.append('6. **Use human-in-the-loop**: Keep humans in the review loop for critical decisions')
report_lines.append('7. **Version your agent prompts**: Treat agent prompts as code — version control, review, and test them')
report_lines.append('8. **Build observability first**: Before deploying loop agents, ensure you have logging, tracing, and alerting')
report_lines.append('')

# Section 8: Enterprise Challenges
report_lines.append('## 8. Enterprise Adoption Challenges')
report_lines.append('')
report_lines.append('- **Cultural resistance**: Teams accustomed to traditional development workflows may resist agent-driven loops')
report_lines.append('- **Skill gaps**: Developers need new skills in prompt design, loop orchestration, and agent debugging')
report_lines.append('- **Governance**: Existing governance frameworks are designed for human developers, not autonomous agents')
report_lines.append('- **Integration complexity**: Integrating agent loops with legacy CI/CD systems requires significant re-architecture')
report_lines.append('- **ROI measurement**: Hard to quantify the value of loop engineering vs traditional development')
report_lines.append('')

# Section 9: Security & Compliance
report_lines.append('## 9. Security & Compliance')
report_lines.append('')
report_lines.append('- **Code review gaps**: Automated loops may bypass traditional code review processes')
report_lines.append('- **Secrets exposure**: Agents may accidentally commit API keys or credentials')
report_lines.append('- **Dependency supply chain**: Agents may install unvetted packages')
report_lines.append('- **Compliance auditing**: Hard to prove compliance when decisions are made by non-deterministic AI systems')
report_lines.append('- **Data privacy**: Agent loops processing sensitive data may violate GDPR, HIPAA, or other regulations')
report_lines.append('')

# Section 10: Tooling Ecosystem
report_lines.append('## 10. Tooling Ecosystem')
report_lines.append('')
report_lines.append('Current tools supporting loop engineering:')
report_lines.append('')
report_lines.append('- **Claude Code** (Anthropic): CLI-based agent with built-in loop capabilities')
report_lines.append('- **Cursor**: AI-powered IDE with agent loop features')
report_lines.append('- **OpenClaw**: Open-source agent framework for loop-based development')
report_lines.append('- **GitHub Copilot Workspace**: Microsoft/Anthropic collaboration for loop-based coding')
report_lines.append('- **Aider**: Terminal-based AI coding assistant with git integration')
report_lines.append('- **Continue**: VS Code extension with agent loop support')
report_lines.append('')

# Section 11: Future Trends
report_lines.append('## 11. Future Trends')
report_lines.append('')
report_lines.append('- **Multi-agent loops**: Multiple specialized agents collaborating in parallel loops')
report_lines.append('- **Self-improving loops**: Agents that optimize their own loop strategies over time')
report_lines.append('- **Edge deployment**: Loop agents running on edge devices for IoT and embedded systems')
report_lines.append('- **Regulatory frameworks**: New compliance standards specifically for AI agent loops')
report_lines.append('- **Standardization**: Industry standards for loop engineering interfaces and protocols')
report_lines.append('- **Hybrid human-agent teams**: Seamless collaboration between human developers and agent loops')
report_lines.append('')

# Section 12: Conclusion
report_lines.append('## 12. Conclusion')
report_lines.append('')
report_lines.append('Loop engineering represents a fundamental shift in how we build software with AI. It moves beyond static prompts to dynamic, self-correcting systems that mirror the iterative nature of real software development. However, it introduces new challenges — infinite loops, context management, cost control, safety, and non-determinism — that require careful architectural design and operational discipline.')
report_lines.append('')
report_lines.append('The key to successful loop engineering is not just building better agents, but building better **feedback systems**. The quality of the loop is determined by the quality of its feedback. Invest in test coverage, observability, structured error reporting, and human oversight. With these foundations, loop engineering can dramatically accelerate software development while maintaining quality and safety.')
report_lines.append('')
report_lines.append('---')
report_lines.append('')
report_lines.append(f'*Report synthesized from {len(data)} web sources across 26 targeted queries. Sources saved in loop_engineering_raw.json.*')

# Write report
with open(report_path, 'w') as f:
    f.write('\n'.join(report_lines))

print(f'\nReport written to: {report_path}')
print(f'Report size: {len(report_lines)} lines')
