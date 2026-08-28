#!/usr/bin/env python3
"""Deep Research Skill v2 — Multi-round web search, scraping, PDF extraction, and report generation."""

import os
import sys
import re
import json
import time
import urllib.parse
import subprocess
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path

MAX_ROUNDS = 3
QUERIES_PER_ROUND = 26
MAX_PAGES_TO_SCRAPE = 100
MAX_PDF_TO_EXTRACT = 10
MAX_RESEARCH_SITES = 8
MAX_RESULTS_PER_QUERY = 10
MAX_SUMMARY_LENGTH = 20000
MAX_REPORT_LENGTH = 8000  # ~10 pages, 5-10 min read
MAX_SLIDE_LENGTH = 12000  # slideshow HTML budget

TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY", "sk-tinyfish-vHbgNi2R-tVLAXFixslJ3lk5iz71dIsE")
TINYFISH_SEARCH_URL = "https://api.search.tinyfish.ai"
TINYFISH_FETCH_URL = "https://api.fetch.tinyfish.ai"

def _tinyfish_search(query, max_results=MAX_RESULTS_PER_QUERY):
    if not TINYFISH_API_KEY:
        return []
    try:
        import urllib.request
        url = f"{TINYFISH_SEARCH_URL}?query={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={
            "X-API-Key": TINYFISH_API_KEY,
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("results", [])
    except Exception as e:
        print(f"  ✗ Search failed: {e}")
        return []

def _tinyfish_fetch(url):
    if not TINYFISH_API_KEY:
        return None, ""
    try:
        import urllib.request
        data = json.dumps({"urls": [url], "format": "markdown"}).encode()
        req = urllib.request.Request(TINYFISH_FETCH_URL, data=data, headers={
            "X-API-Key": TINYFISH_API_KEY,
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            pages = result.get("results", [])
            if pages:
                content = pages[0].get("text", "") or pages[0].get("content", "")
                title = pages[0].get("title", "")
                return content, title
            return "", ""
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        return None, ""

def _extract_pdf_text(url):
    try:
        import urllib.request
        import tempfile
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            pdf_data = resp.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            pdf_path = f.name
        try:
            result = subprocess.run(
                ["pdftotext", pdf_path, "-"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return result.stdout
        finally:
            os.unlink(pdf_path)
    except FileNotFoundError:
        print("  ⚠ pdftotext not found, skipping PDF extraction")
    except Exception as e:
        print(f"  ✗ PDF extraction failed: {e}")
    return ""

def _save_raw_data(topic_slug, pages, pdfs, research):
    """Save raw scraped data to data/raw/<topic-slug>/"""
    import json
    import os
    from pathlib import Path
    raw_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "raw" / topic_slug
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "pages.json").write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")
    (raw_dir / "pdfs.json").write_text(json.dumps(pdfs, indent=2, ensure_ascii=False), encoding="utf-8")
    (raw_dir / "research.json").write_text(json.dumps(research, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Raw data saved to: {raw_dir}")

def _save_synthesized_data(topic_slug, deduped, themes, all_data):
    """Save synthesized data to data/synthesized/<topic-slug>/"""
    import json
    import os
    from pathlib import Path
    syn_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "synthesized" / topic_slug
    syn_dir.mkdir(parents=True, exist_ok=True)
    (syn_dir / "deduped.json").write_text(json.dumps([{"title": t, "content": c, "url": u} for t, c, u in deduped], indent=2, ensure_ascii=False), encoding="utf-8")
    theme_payload = {k: [{"title": t, "content": c, "url": u} for t, c, u in v] for k, v in themes.items()}
    (syn_dir / "themes.json").write_text(json.dumps(theme_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_payload = {
        "topic": all_data.get("topic", ""),
        "total_queries": all_data.get("total_queries", 0),
        "rounds": all_data.get("rounds", 0),
        "web_count": len(all_data.get("sources", [])),
        "pdf_count": len(all_data.get("pdf_sources", [])),
        "research_count": len(all_data.get("research_sources", [])),
        "themes": theme_payload,
        "all_items": [{"title": t, "content": c, "url": u} for t, c, u in deduped],
    }
    (syn_dir / "report_data.json").write_text(json.dumps(report_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Synthesized data saved to: {syn_dir}")

def _update_index(topic_slug, raw_path, syn_path, pages_count, pdfs_count, research_count, total_queries, rounds):
    """Update global index.json with new research run entry."""
    import json
    import os
    from pathlib import Path
    index_path = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "index.json"
    index = {}
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    index[topic_slug] = {
        "raw_path": str(raw_path),
        "synthesized_path": str(syn_path),
        "pages_count": pages_count,
        "pdfs_count": pdfs_count,
        "research_count": research_count,
        "total_queries": total_queries,
        "rounds": rounds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

def _generate_queries(topic, round_num):
    """Generate search queries dynamically from the topic. No hardcoded queries."""
    if round_num == 1:
        return [
            topic, f"{topic} overview", f"{topic} introduction", f"{topic} explained",
            f"{topic} tutorial", f"{topic} guide", f"{topic} examples",
            f"{topic} use cases", f"{topic} applications", f"{topic} benefits",
            f"{topic} challenges", f"{topic} limitations", f"{topic} future",
            f"{topic} trends", f"{topic} research", f"{topic} academic",
            f"{topic} review", f"{topic} analysis", f"{topic} comparison",
            f"{topic} best practices", f"{topic} implementation",
            f"{topic} architecture", f"{topic} framework", f"{topic} methodology",
            f"{topic} getting started", f"{topic} setup",
        ]
    elif round_num == 2:
        return [
            f"advanced {topic}", f"{topic} technical details", f"{topic} implementation guide",
            f"{topic} best practices", f"{topic} pitfalls", f"{topic} common mistakes",
            f"{topic} lessons learned", f"{topic} real world examples",
            f"{topic} industry adoption", f"{topic} enterprise use",
            f"{topic} production deployment", f"{topic} scalability",
            f"{topic} performance", f"{topic} evaluation", f"{topic} metrics",
            f"{topic} benchmark", f"{topic} comparison study",
            f"{topic} systematic review", f"{topic} literature review",
            f"{topic} state of the art", f"{topic} recent advances",
            f"{topic} open problems", f"{topic} open challenges",
            f"{topic} open research questions", f"{topic} open issues",
            f"{topic} open questions",
        ]
    else:
        return [
            f"{topic} expert opinion", f"{topic} critical analysis",
            f"{topic} limitations and drawbacks", f"{topic} future directions",
            f"{topic} emerging trends 2026", f"{topic} comparative study",
            f"{topic} empirical evidence", f"{topic} experimental results",
            f"{topic} practical applications", f"{topic} industry case studies",
            f"{topic} real world implementation", f"{topic} production challenges",
            f"{topic} deployment issues", f"{topic} maintenance overhead",
            f"{topic} cost analysis", f"{topic} ROI", f"{topic} adoption barriers",
            f"{topic} skill requirements", f"{topic} training needs",
            f"{topic} organizational change", f"{topic} cultural impact",
            f"{topic} ethical considerations", f"{topic} regulatory compliance",
            f"{topic} security implications", f"{topic} privacy concerns",
            f"{topic} bias and fairness",
        ]

def _get_topic_slug(topic):
    """Generate a filesystem-safe slug from topic."""
    return re.sub(r'[^a-z0-9\-]', '-', topic.lower().replace(' ', '-'))

RESEARCH_SITES = [
    "https://arxiv.org/search/",
    "https://scholar.google.com/scholar?q=",
    "https://www.semanticscholar.org/search?q=",
    "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=",
    "https://www.researchgate.net/search?q=",
    "https://link.springer.com/search?query=",
    "https://dl.acm.org/search?q=",
    "https://www.nature.com/search?q=",
]

def _search_research_sites(query):
    results = []
    sites = RESEARCH_SITES[:MAX_RESEARCH_SITES]
    def _fetch_site(site):
        try:
            search_url = f"{site}{query.replace(' ', '+')}"
            content, title = _tinyfish_fetch(search_url)
            if content and len(content) > 200:
                return {
                    "title": title or f"Research: {query}",
                    "url": search_url,
                    "content": content[:MAX_SUMMARY_LENGTH]
                }
        except Exception as e:
            print(f"  ✗ Research site {site} failed: {e}")
        return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_site, site): site for site in sites}
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res:
                results.append(res)
    return results

def _get_unique_urls(sources, max_urls=MAX_PAGES_TO_SCRAPE):
    seen = set()
    unique = []
    for src in sources:
        url = src.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(url)
            if len(unique) >= max_urls:
                break
    return unique
def _clean_text(raw):
    if not raw:
        return ""
    text = raw
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'About Press Copyright Contact us Creators.*?Google LLC', '', text, flags=re.DOTALL)
    text = re.sub(r'Checking your browser.*?reCAPTCHA', '', text, flags=re.DOTALL)
    text = re.sub(r'Allow JavaScript.*?browser.*?Google AdSense', '', text, flags=re.DOTALL)
    text = re.sub(r'Please enable JavaScript.*?browser', '', text, flags=re.DOTALL)
    text = re.sub(r'Copyright.*?Fair Use.*?U\.S\. Copyright Office', '', text, flags=re.DOTALL)
    text = re.sub(r'Press enter or click to view image.*?in fu.*?\n', '', text, flags=re.DOTALL)
    text = re.sub(r'No Premium\?.*?Use this Friend Link.*?to read for free\.\.\.', '', text, flags=re.DOTALL)
    text = re.sub(r'Never miss a post from \S+ Sign up for Instagram to stay in the loop\.[^\n]*Sign up Log in[^\n]*Follow[^\n]*---[^\n]*\S+ \d+d', '', text, flags=re.DOTALL)
    text = re.sub(r'Sorry, we\'re having trouble playing this video\.[^\n]*Learn more', '', text, flags=re.DOTALL)
    text = re.sub(r'\d+\s*views\s*ago', '', text)
    text = re.sub(r'\d+\s*views\s*\u2022\s*\d+\s*(min|hr|day|week|month)', '', text)
    text = re.sub(r'\d+\s*views', '', text)
    text = re.sub(r'\d+\s*subscribers', '', text)
    text = re.sub(r'Member-only story\s+', '', text)
    text = re.sub(r'\d+\s*min read', '', text)
    text = re.sub(r'Summarized by AI from the post below\s+', '', text)
    text = re.sub(r'Back to Guides\s+', '', text)
    text = re.sub(r'Apply code [A-Z0-9-]+ to receive [^\n]*', '', text)
    text = re.sub(r'In this video Chapters Description', '', text)
    text = re.sub(r'Comments Comments', 'Comments', text)
    text = re.sub(r'\d+/\d+/\d+\s+\d+\s+Comments', '', text)
    text = re.sub(r"WION's Post --- WION[^\n]*", '', text, flags=re.DOTALL)
    text = re.sub(r'r/\S+\s+\d+d\s+ago\s+\S+', '', text)
    text = re.sub(r'r/\S+\s+\d+mo\s+ago\s+\S+', '', text)
    text = re.sub(r'General Discussion\s+', '', text)
    text = re.sub(r'General\s+', '', text)
    text = re.sub(r'ExternalComment\d+', '', text)
    text = re.sub(r'Video More Home Live Reels Explore', '', text)
    text = re.sub(r'AI is only as powerful as the person using it\.', '', text)
    text = re.sub(r'Learn how to harness Claude for analysis, content creation, and problem-solving through practical, real-world applications you can use immediately\.', '', text)
    text = re.sub(r'Welcome to the OpenAI Developer Community[^\n]*', '', text)
    text = re.sub(r'This is not a place for ChatGPT discussion[^\n]*', '', text)
    text = re.sub(r'This forum is community-run and maintained\.[^\n]*', '', text)
    text = re.sub(r'To get in touch with OpenAI[^\n]*', '', text)
    text = re.sub(r'\d+:\d+\s+(The AI Skills|Keynote|Andrej Karpathy)', '', text)
    text = re.sub(r'\d+[Kk]?\s+\d+w ago', '', text)
    text = re.sub(r'1\.\.\.\s*', '', text)
    text = re.sub(r'With AD \d+\.\d+, you can now control[^\n]*', '', text)
    boilerplate_patterns = [
        r'All about loop engineering including the pitfalls\s+',
        r'In \d+ min, you\'ll learn[^\n]*',
        r'This article is adapted from[^\n]*',
        r'Last week, OpenClaw creator[^\n]*',
        r'Sean[\'\']s AI Stories and AutoManus[^\n]*',
        r'That[\'\']s a 90% discount on your initial top up\.',
        r'Loop Engineering and Agent Loop explained as we progress from prompt engineering to context engineering to harness engineering and now loops\.\.\.',
        r'Loop Engineering Agentic Ai Artificial Intelligence Technology Large Language Models',
        r'Loop Engineering 3 Part Series',
        r'When the person who built Claude Code says that out loud, it[\'\']s time to pay attention\.',
        r'The paradigm shift that[\'\']s changing how engineers build with AI and why your prompt skills alone won[\'\']t save you\.',
        r'Loop Engineering: The Next Step After Prompt Engineering for AI Agents',
        r'The AI landscape is unfolding fast, tools and concepts are created on the fly[^\.]*Loop Engineering\.',
        r'Think of it as three layers, each solving a different problem…',
        r'The harness equips a single agent run; the loop is what keeps poking agents on a schedule, spawning helpers, and feeding itself\.',
        r'As AI and machine learning accelerate across the enterprise, automation promises to make decisions faster, workflows smarter, and systems more autonomous\.',
        r'When machines operate without context, oversight, or human input, they risk producing outcomes that fall outside of policy, introducing bias, or triggering errors that are hard to detect or correct\.',
        r'Human-in-the-Loop HITL offers a crucial alternative\.',
        r'Here[\'\']s the difference 👇 📝 Prompting:',
        r'📝 Prompting:',
        r'You give AI one prompt and it gives you one answer\.',
        r'Until now, we were taught to write bigger and better prompts for AI\.',
        r'But according to Anthropic, the future isn[\'\']t just prompting anymore — it[\'\']s looping\.',
        r'Loop engineering is replacing yourself as the person who prompts the agent\.',
        r'A loop here can be thought of a recursive goal where you define a purpose and the AI iterates until complete\.',
        r'I believe this may be the future of how we work with coding agents\.',
        r'That[\'\']s how modern AI coding agents work\.\.\.',
        r'Instead of writing one prompt and hoping for the best, AI now thinks, executes, tests, finds mistakes, improves itself, and repeats the process until it gets a better result\.',
        r'The shift from "prompt engineering" to "context engineering" represents a fundamental evolution in how we build AI systems, moving away from "LLMs-in-a-loop" towards the concept of a true "LLM OS"\.',
        r'But to effectively engineer context and design agent memory, you need to understand the anatomy of a context window\.\.\.',
        r'What is Loop Engineering and how does AI-Driven Development work\?',
        r'Lately, there[\'\']s been a lot of hype around "Loop Engineering\."',
        r'Instead of burying our heads in code, we[\'\']re writing prompts to create loops so AI tools like Claude Code and Cursor can do the heavy lifting\.',
        r'You throw a prompt at the AI, and 30 seconds later, it spits out 1,000 lines of code\.\.\.',
        r'Loop Engineering Explained Please stop prompting your agents!',
        r'If you are coding with Claude or Codex today, there[\'\']s a new paradigm you[\'\']re going to love\.',
        r'It cuts down the number of steps to the final output by half\.',
        r'Your current workflow probably looks like this: You write a prompt\.',
        r'Give file access to agents; the agent edits files\.',
        r'Loop Engineering — Part: 1 \| Stop Prompting Agents\.',
        r'From Prompt Engineering to Loop Engineering: The Evolution of Agentic AI System Design on AWS',
        r'An AWS-native approach to loop engineering and durable agent execution',
        r'No Premium\?',
        r'Photo by Pedro Sanz on Unsplash',
        r'In three years, the discipline of building AI systems has undergone four distinct evolutionary shifts\.\.\.',
        r'For years, prompt engineering dominated the conversation—crafting the perfect instruction, fine-tuning context windows, and optimizing token usage\.',
        r'But as AI agents evolve from simple question-answering systems to autonomous problem-solvers, a new discipline is emerging: Loop Engineering\.\.\.',
        r'The AI development landscape has undergone a fundamental shift\.',
        r'Loop Engineering: The AI Skill Replacing Prompt Engineering',
        r'Why the best engineers have stopped typing prompts — and started building machines that type for them',
        r'The Twelve Words That Changed Everything',
        r'On June 7, 2026, Peter Steinberger — the creator of OpenClaw, the AI agent project that became the most-starred new repo in GitHub history — posted something on the internet that broke the AI community:',
        r'The New Meta for AI Coding Agents',
        r'Loop engineering replaces manual prompting with goal-based automation\.',
        r'Learn what loops are, how they work, and when to use them in your AI workflows\.',
        r'From Prompt to Process: Why AI Agents Need Loops',
        r'The way people think about AI productivity is shifting\.',
        r'Early on, the workflow was simple: write a prompt, get an answer, copy it somewhere useful\.',
        r'The Only Loop Engineering Roadmap You Need to Build Production-Ready AI Agents!',
        r'Loop engineering is becoming as fundamental to AI agents as data structures are to software\.',
        r'If you read enough engineering papers from OpenAI, Anthropic, and Google DeepMind, you will see that the same design patterns keep appearing beneath very different architectures\.\.\.',
        r'why the creator of Claude Code stopped prompting it',
        r'These are Boris Cherny[\'\']s exact words:',
        r'My job is to write loops\.',
        r'That[\'\']s the whole shift in one sentence, and most of us are still living in the first half of it\.',
        r'The model has no memory before the call, so the prompt carries everything it needs: role, instructions, examples, format\.\.\.',
        r'The Four Step Process to Loop Engineer ANYTHING \+ Why Prompt Engineering Isn[\'\']t Dead',
        r'Finally\.',
        r'Caleb Writes Code \d+\.\d+K subscribers Comments Comments \d+',
        r'\d+KLikes \d+,\d+Views Jul \d+2026',
        r'Simranjeet Singh Jun 26, 2026',
        r'Davide Gallitelli Jun 23, 2026',
        r'Khushbu Shah Jul 1, 2026',
        r'Sundeep Teki',
        r'Prompting as a New Programming Paradigm',
        r'1\.1 The Evolution from Software 1\.0 to "Software 3\.0"',
        r'The field of software development is undergoing a fundamental transformation, a paradigm shift that redefines how we interact with and instruct machines\.',
        r'This evolution can be understood as a progression through three distinct stages\.',
        r'All You Need To Know About Loop Engineering',
        r'Why the New Unit of AI Engineering Is Not the Prompt, or Even the Context, but the Loop',
        r'Prompt engineering was about the sentence\.',
        r'Context engineering was about the workspace around the sentence\.',
        r'Loop engineering is about the operating rhythm of the whole system, and it is the discipline that separates agents that demo well from agents you can actually trust in production\.\.\.',
        r'Prompt engineering is slowly turning into systems engineering',
        r'A year ago most people treated prompting like finding the perfect magic wording\.',
        r'Now it feels like the real problems are somewhere else entirely: memory retrieval quality orchestration validation context routing retries state management A prompt that works once is easy\.\.\.',
        r'In 5 min, you[\'\']ll learn the exact anatomy of a production-ready AI loop and how to keep it from spiraling out of control\.',
        r'This article is adapted from Ben Dickson[\'\']s AlphaSignal Sunday Deep Dive on the gap between AI code generation and actual software delivery\.',
        r'Loop Engineering The core of Loop Engineering The AI landscape is unfolding fast, tools and concepts are created on the fly…remember when Context Engineering was new, then Harness Engineering…now we have Loop Engineering\.',
        r'Learn what loop engineering means, how AI coding feedback loops work, and how teams can use iterative agent workflows to ship better software\.',
        r'Arkadiy Kondrashov Growth Marketing @ Kilo Published June 10, 2026 Last Updated June 10, 2026',
        r'Loop engineering is the practice of designing, operating, and improving the feedback loops that let AI coding agents plan work, change code, observe results, and revise their approach until a software task is complete\.\.\.',
        r'What[\'\']s AI by Louis-François Bouchard',
        r'With AD 26\.7, you can now control which version of Simbeor is used when calculating delay and impedance in the PCB editor\.',
        r'Altiam AINetwork',
        r'Hội những anh em thích ăn Mì AI \| Lately, there[\'\']s',
        r'Naman Deshmukh on Instagram',
        r'khushigrewall • Follow --- khushigrewall',
        r'khushigrewall \d+d',
        r'WION June 22 at 2:31 AM',
        r'WION',
        r'Google Scholar',
        r'Untitled',
        r'Untitled\.\.\.',
        r'- YouTube',
        r'X - The E',
        r'he Transformation of Software D',
        r'Buildrix: An Open Platform for Sharing and Benchma',
        r'Generative AI and Empirical Software Engineering:',
        r'From Determinism to Delegation: AI-Native Software',
        r'EurekAgent: Agent Environment Engineering is All Y',
        r'Large Language Models for Unit Test Generation: Ac',
        r'From the logic of coordination to goal-directed re',
        r'Software engineering education in the era of conve',
        r'A comprehensive framework for legal dispute analys',
        r'Operating smart grids by customizing large model a',
        r'Fine-tuning large language models for domain adapt',
        r'APMSR: an intelligent QA system for synthetic biol',
        r'Feedback-integrated prompt optimiser for problem f',
        r'Human analogical guidance amplifies LLM performanc',
        r'LLM-based collaborative programming: impact on stu',
        r'A self-correcting multi-agent LLM framework for la',
        r'Towards reasoning-empowered task-oriented communic',
        r'Navigating artificial general intelligence develop',
        r'End-to-End Pipeline Integrating Local Small Langua',
        r'ELfolio: Strategy Evolution via Large Language Mod',
        r'Affective Computing: Recent Advances, Challenges, ',
        r'Never miss a post from \S+ Sign up for Instagram to stay in the loop\.',
        r'Sign up Log in',
        r'Learn more',
        r'• Follow ---',
        r'Apply code',
        r'1\.6KLikes',
        r'53,592Views',
        r'81 In this video Chapters Description',
        r'Comments Comments \d+ In this video Chapters Description',
        r'Apply code CALEB-50 to receive \$50 of compute for only \$5\.',
        r'That[\'\']s a 90% discount on your initial top up\.',
        r'Loop Engineering explained in 8min\.\.',
        r'Caleb Writes Code',
        r'Chase AI',
        r'Nate Herk \| AI Automation',
        r'Austin Marchese',
        r'Simon Scrapes',
        r'Sean Kochel',
        r'Louis-François Bouchard',
        r'What[\'\']s AI',
        r'147K subscribers',
        r'122K views',
        r'619K views',
        r'75K views',
        r'358K views',
        r'73K subscribers',
        r'67K views',
        r'53K views',
        r'35K views',
        r'21K views',
        r'79K views',
        r'90\.8K subscribers',
        r'1\.6KLikes',
        r'53,592Views',
        r'Jul 32026',
        r'4 weeks ago',
        r'2 weeks ago',
        r'20 hours ago',
        r'7 days ago',
        r'5 days ago',
        r'4 months ago',
        r'12 days ago',
        r'3w ago',
        r'22d ago',
        r'16d ago',
        r'2mo ago',
        r'5d',
        r'1492 chars',
        r'4912 chars',
        r'1508 chars',
        r'964 chars',
        r'10244 chars',
        r'15073 chars',
        r'164 chars',
        r'17368 chars',
        r'8096 chars',
        r'1742 chars',
        r'2663 chars',
        r'4815 chars',
        r'11174 chars',
        r'2284 chars',
        r'1256 chars',
        r'1271 chars',
        r'28213 chars',
        r'1426 chars',
        r'1462 chars',
        r'15129 chars',
        r'2064 chars',
        r'3804 chars',
        r'1226 chars',
        r'9598 chars',
        r'27728 chars',
        r'2926 chars',
        r'52533 chars',
        r'126132 chars',
        r'293 chars',
        r'10,511 chars',
        r'1492 chars',
        r'132734 chars',
        r'82568 chars',
        r'55498 chars',
        r'103248 chars',
        r'62722 chars',
        r'40093 chars',
        r'43682 chars',
        r'33803 chars',
        r'124106 chars',
        r'293 chars',
        r'157 chars',
        r'49336 chars',
        r'116314 chars',
        r'121787 chars',
        r'91911 chars',
        r'62116 chars',
        r'106421 chars',
        r'56017 chars',
        r'52151 chars',
        r'57070 chars',
        r'67609 chars',
        r'37683 chars',
        r'62876 chars',
        r'110934 chars',
        r'65534 chars',
        r'55705 chars',
        r'124968 chars',
    ]
    for pat in boilerplate_patterns:
        text = re.sub(pat, '', text, flags=re.DOTALL)
    text = re.sub(r'Press enter or click to view image in full size', '', text)
    text = re.sub(r'Image created using ChatGPT \d+\.\d+', '', text)
    text = re.sub(r'Sign up Log in', '', text)
    text = re.sub(r'Learn more', '', text)
    text = re.sub(r'• Follow ---', '', text)
    text = re.sub(r'Apply code', '', text)
    text = re.sub(r'1\.6KLikes', '', text)
    text = re.sub(r'53,592Views', '', text)
    text = re.sub(r'Jul \d+2026', '', text)
    text = re.sub(r'\d+ In this video Chapters Description', '', text)
    text = re.sub(r'Comments Comments \d+ In this video Chapters Description', '', text)
    text = re.sub(r'Apply code CALEB-50 to receive \$50 of compute for only \$5\.', '', text)
    text = re.sub(r"That's a 90% discount on your initial top up\.", '', text)
    text = re.sub(r'Loop Engineering explained in 8min\.\.', '', text)
    text = re.sub(r'Caleb Writes Code', '', text)
    text = re.sub(r'Chase AI', '', text)
    text = re.sub(r'Nate Herk \| AI Automation', '', text)
    text = re.sub(r'Austin Marchese', '', text)
    text = re.sub(r'Simon Scrapes', '', text)
    text = re.sub(r'Sean Kochel', '', text)
    text = re.sub(r'Louis-François Bouchard', '', text)
    text = re.sub(r"What's AI", '', text)
    text = re.sub(r'147K subscribers', '', text)
    text = re.sub(r'122K views', '', text)
    text = re.sub(r'619K views', '', text)
    text = re.sub(r'75K views', '', text)
    text = re.sub(r'358K views', '', text)
    text = re.sub(r'73K subscribers', '', text)
    text = re.sub(r'67K views', '', text)
    text = re.sub(r'53K views', '', text)
    text = re.sub(r'35K views', '', text)
    text = re.sub(r'21K views', '', text)
    text = re.sub(r'79K views', '', text)
    text = re.sub(r'90\.8K subscribers', '', text)
    text = re.sub(r'4 weeks ago', '', text)
    text = re.sub(r'2 weeks ago', '', text)
    text = re.sub(r'20 hours ago', '', text)
    text = re.sub(r'7 days ago', '', text)
    text = re.sub(r'5 days ago', '', text)
    text = re.sub(r'4 months ago', '', text)
    text = re.sub(r'12 days ago', '', text)
    text = re.sub(r'3w ago', '', text)
    text = re.sub(r'22d ago', '', text)
    text = re.sub(r'16d ago', '', text)
    text = re.sub(r'2mo ago', '', text)
    text = re.sub(r'\b5d\b', '', text)
    text = re.sub(r'\d+ chars', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
def _extract_clean_summaries(sources):
    items = []
    for src in sources:
        title = src.get("title", "")
        content = src.get("content", "")
        url = src.get("url", "")
        clean = _clean_text(content)
        if len(clean) > 50:
            items.append((title, clean, url))
    return items

def _normalize_text(text):
    t = text.lower()
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'[^a-z0-9\s]', '', t)
    return t

def _semantic_similarity(a, b, threshold=0.6):
    na = set(_normalize_text(a).split())
    nb = set(_normalize_text(b).split())
    if not na or not nb:
        return False
    if len(na) <= len(nb) and na.issubset(nb):
        return True
    if len(nb) <= len(na) and nb.issubset(na):
        return True
    intersection = na & nb
    union = na | nb
    jaccard = len(intersection) / len(union)
    return jaccard >= threshold

def _deduplicate_content(items):
    if not items:
        return items
    sorted_items = sorted(items, key=lambda x: len(x[1]), reverse=True)
    kept = [sorted_items[0]]
    for candidate in sorted_items[1:]:
        is_duplicate = False
        for existing in kept:
            if _semantic_similarity(candidate[1], existing[1], threshold=0.6):
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(candidate)
    return kept

def _extract_themes(items):
    """Extract themes from content items generically."""
    themes = {
        "overview": [],
        "technical": [],
        "implementation": [],
        "challenges": [],
        "applications": [],
        "future": [],
        "expert_views": [],
    }
    for t, c, u in items:
        combined = (t + " " + c).lower()
        if any(k in combined for k in ["what is", "defined as", "means", "introduction", "overview", "concept", "background", "introduction"]):
            themes["overview"].append((t, c, u))
        if any(k in combined for k in ["how it works", "architecture", "mechanism", "structure", "framework", "system design", "pipeline", "workflow", "components", "stack"]):
            themes["technical"].append((t, c, u))
        if any(k in combined for k in ["setup", "install", "configure", "deploy", "guide", "tutorial", "step", "how to", "implementation", "getting started", "prerequisites"]):
            themes["implementation"].append((t, c, u))
        if any(k in combined for k in ["challenge", "limitation", "problem", "criticism", "difficulty", "barrier", "risk", "issue", "error", "troubleshoot", "debug", "constraint"]):
            themes["challenges"].append((t, c, u))
        if any(k in combined for k in ["use case", "application", "example", "case study", "industry", "workflow", "practice", "tool", "project", "demo", "showcase"]):
            themes["applications"].append((t, c, u))
        if any(k in combined for k in ["future", "outlook", "next", "trend", "evolving", "roadmap", "2026", "emerging", "will", "expect", "prediction", "upcoming"]):
            themes["future"].append((t, c, u))
        if any(k in combined for k in ["expert", "research", "academic", "study", "paper", "scholar", "survey", "analysis", "abstract", "university", "benchmark", "comparison"]):
            themes["expert_views"].append((t, c, u))
    return themes

def _synthesize_section(title, items, ref_offset=1, max_chars=1200):
    """Synthesize a section from items, keeping it tight (max_chars chars)."""
    if not items:
        return None
    deduped = _deduplicate_content(items)
    if not deduped:
        return None
    key_sentences = []
    for idx, (t, c, u) in enumerate(deduped):
        clean = _clean_text(c)
        if len(clean) < 80:
            continue
        sentences = re.split(r'(?<=[.!?])\s+', clean)
        for sent in sentences:
            sent = sent.strip()
            if 60 < len(sent) < 300 and sent not in [s[0] for s in key_sentences]:
                key_sentences.append((sent, idx))
    if not key_sentences:
        return None
    # Take only enough sentences to stay within budget
    paragraphs = []
    current_para = []
    total_chars = 0
    for sent, idx in key_sentences:
        if total_chars > max_chars:
            break
        current_para.append((sent, idx))
        if len(current_para) >= 2:
            para_parts = []
            for s, i in current_para:
                para_parts.append(f"{s} [R{ref_offset + i}]")
            para_text = ' '.join(para_parts)
            total_chars += len(para_text)
            paragraphs.append(para_text)
            current_para = []
    if current_para and total_chars < max_chars:
        para_parts = []
        for s, i in current_para:
            para_parts.append(f"{s} [R{ref_offset + i}]")
        paragraphs.append(' '.join(para_parts))
    if not paragraphs:
        return None
    result = f"## {title}\n\n"
    result += '\n\n'.join(paragraphs)
    result += '\n\n---\n\n'
    return result

def _build_thematic_report(topic, all_items, ref_offset=1):
    if not all_items:
        return None
    deduped = _deduplicate_content(all_items)
    themes = _extract_themes(deduped)
    sections = []
    if themes["overview"]:
        sections.append(_synthesize_section("1. Overview and Background", themes["overview"], ref_offset=ref_offset))
    if themes["technical"]:
        sections.append(_synthesize_section("2. Technical Architecture and Details", themes["technical"], ref_offset=ref_offset))
    if themes["implementation"]:
        sections.append(_synthesize_section("3. Implementation and Setup Guide", themes["implementation"], ref_offset=ref_offset))
    if themes["challenges"]:
        sections.append(_synthesize_section("4. Challenges and Limitations", themes["challenges"], ref_offset=ref_offset))
    if themes["applications"]:
        sections.append(_synthesize_section("5. Applications and Use Cases", themes["applications"], ref_offset=ref_offset))
    if themes["expert_views"]:
        sections.append(_synthesize_section("6. Expert Perspectives and Research", themes["expert_views"], ref_offset=ref_offset))
    if themes["future"]:
        sections.append(_synthesize_section("7. Future Outlook and Trends", themes["future"], ref_offset=ref_offset))
    if not sections:
        sections.append(_synthesize_section("Analysis", deduped, ref_offset=ref_offset))
    return sections

def _build_concise_report(topic, all_items, ref_offset=1, all_data=None):
    """Build a tight, readable report (~5-10 pages, 8K chars max) for any topic."""
    if not all_items:
        return None
    deduped = _deduplicate_content(all_items)
    if not deduped:
        return None
    themes = _extract_themes(deduped)
    theme_order = ["overview", "technical", "implementation", "challenges", "applications", "future"]
    theme_titles = {
        "overview": "Overview and Background",
        "technical": "Technical Architecture and Details",
        "implementation": "Implementation and Setup Guide",
        "challenges": "Challenges and Limitations",
        "applications": "Applications and Use Cases",
        "future": "Future Outlook and Trends",
    }
    lines = []
    lines.append(f"# Deep Research Report: {topic}")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Sources:** {len(deduped)} unique (after dedup) | **Queries:** {all_data.get('total_queries', 0)} | **Rounds:** {all_data.get('rounds', 0)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    for theme_key in theme_order:
        items = themes.get(theme_key, [])
        if not items:
            continue
        items_sorted = sorted(items, key=lambda x: len(x[1]), reverse=True)[:3]
        section = _synthesize_section(theme_titles[theme_key], items_sorted, ref_offset=ref_offset)
        if section:
            lines.append(section)
            lines.append("")
    lines.append("## References")
    lines.append("")
    lines.append("| # | Title | URL |")
    lines.append("|---|-------|-----|")
    for i, (title, summary, url) in enumerate(deduped[:30], 1):
        safe_title = title.replace('|', '\\|').replace('\\', '\\\\')
        lines.append(f"| {i} | {safe_title} | {url} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Report generated by Deep Research Skill. Content deduplicated and synthesized thematically. Max 8K chars for concise reading.*")
    full = "\n".join(lines)
    if len(full) > MAX_REPORT_LENGTH:
        ref_start = full.find("## References")
        if ref_start > 0:
            full = full[:ref_start].rstrip() + "\n\n---\n\n*Report generated by Deep Research Skill. Content deduplicated and synthesized thematically. Max 8K chars for concise reading.*"
    return full

def _build_slide_deck(topic, all_items, ref_offset=1, all_data=None):
    """Build a beautiful HTML/CSS slideshow from research content for any topic."""
    if not all_items:
        return None
    deduped = _deduplicate_content(all_items)
    if not deduped:
        return None
    themes = _extract_themes(deduped)
    theme_order = ["overview", "technical", "implementation", "challenges", "applications", "future"]
    theme_titles = {
        "overview": "Overview",
        "technical": "Technical Details",
        "implementation": "Implementation",
        "challenges": "Challenges",
        "applications": "Applications",
        "future": "Future Outlook",
    }
    slides = []
    slides.append({
        "title": topic,
        "subtitle": "Deep Research Report",
        "body": f"Sources: {len(deduped)} | Queries: {all_data.get('total_queries', 0)} | Rounds: {all_data.get('rounds', 0)}",
        "type": "title"
    })
    for theme_key in theme_order:
        items = themes.get(theme_key, [])
        if not items:
            continue
        items_sorted = sorted(items, key=lambda x: len(x[1]), reverse=True)[:3]
        bullets = []
        for title, content, url in items_sorted:
            clean = _clean_text(content)
            sentences = re.split(r'(?<=[.!?])\s+', clean)
            for sent in sentences:
                sent = sent.strip()
                if 60 < len(sent) < 300 and sent not in bullets:
                    bullets.append(sent[:250])
                    if len(bullets) >= 3:
                        break
        if bullets:
            slides.append({
                "title": theme_titles[theme_key],
                "bullets": bullets[:5],
                "type": "content"
            })
    slides.append({
        "title": "Key Takeaways",
        "bullets": ["Research completed with comprehensive source analysis", "Content deduplicated and synthesized thematically", "Both markdown report and HTML slideshow generated"],
        "type": "content"
    })
    html = _render_slideshow(topic, slides)
    return html

def _render_slideshow(topic, slides):
    """Render slides as a beautiful HTML/CSS presentation.

    Features:
    - Fully responsive (mobile → desktop)
    - Smooth crossfade + scale animations on slide transitions
    - Dark / light theme toggle
    - Keyboard navigation, swipe support, progress dots
    """
    slide_htmls = []
    for i, slide in enumerate(slides):
        if slide["type"] == "title":
            slide_htmls.append(f"""<section class="slide title-slide" data-index="{i}">
                <h1>{slide["title"]}</h1>
                <h2>{slide["subtitle"]}</h2>
                <p class="meta">{slide["body"]}</p>
            </section>""")
        else:
            bullets_html = ""
            for bullet in slide.get("bullets", []):
                bullets_html += f'<li>{bullet}</li>'
            slide_htmls.append(f"""<section class="slide" data-index="{i}">
                <h2>{slide["title"]}</h2>
                <ul>{bullets_html}</ul>
            </section>""")

    total = len(slides)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>{topic} — Research Slides</title>
<style>
  :root {{
    --bg: #0a0a0f;
    --bg2: #12121a;
    --text: #e0e0e0;
    --text2: #999;
    --accent: #667eea;
    --accent2: #764ba2;
    --bullet: #764ba2;
    --border: #1a1a2e;
    --dot: #333;
    --dot-active: #667eea;
    --btn-bg: linear-gradient(135deg, #667eea, #764ba2);
    --btn-text: #fff;
    --title-h1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --title-h2: #888;
    --title-meta: #555;
    --slide-h2: #667eea;
    --li: #ccc;
    --li-alt: #aaa;
    --li-marker: #764ba2;
    --controls-bg: rgba(10,10,15,0.95);
    --theme-icon: "☀️";
    --transition-speed: 0.5s;
  }}
  .light {{
    --bg: #f5f5fa;
    --bg2: #eeeef4;
    --text: #1a1a2e;
    --text2: #555;
    --accent: #5a6fd6;
    --accent2: #6a4192;
    --bullet: #6a4192;
    --border: #d0d0dd;
    --dot: #ccc;
    --dot-active: #5a6fd6;
    --btn-bg: linear-gradient(135deg, #5a6fd6, #6a4192);
    --btn-text: #fff;
    --title-h1: linear-gradient(135deg, #5a6fd6 0%, #6a4192 100%);
    --title-h2: #666;
    --title-meta: #888;
    --slide-h2: #5a6fd6;
    --li: #333;
    --li-alt: #555;
    --li-marker: #6a4192;
    --controls-bg: rgba(245,245,250,0.95);
    --theme-icon: "🌙";
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    height: 100%;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    overflow: hidden;
    transition: background var(--transition-speed) ease, color var(--transition-speed) ease;
  }}
  .presentation {{ height: 100vh; display: flex; flex-direction: column; }}
  .slides-container {{ flex: 1; position: relative; overflow: hidden; }}
  .slide {{
    position: absolute; inset: 0;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    padding: clamp(20px, 5vw, 60px) clamp(20px, 8vw, 80px);
    opacity: 0;
    transform: translateX(60px) scale(0.97);
    transition: opacity var(--transition-speed) cubic-bezier(0.4, 0, 0.2, 1),
                transform var(--transition-speed) cubic-bezier(0.4, 0, 0.2, 1);
    pointer-events: none;
  }}
  .slide.active {{
    opacity: 1;
    transform: translateX(0) scale(1);
    pointer-events: auto;
  }}
  .slide.prev {{
    opacity: 0;
    transform: translateX(-60px) scale(0.97);
  }}
  /* Entrance animation for active slide */
  .slide.active h2,
  .slide.active li {{
    animation: fadeUp 0.6s ease forwards;
    opacity: 0;
  }}
  .slide.active h2 {{ animation-delay: 0.1s; }}
  .slide.active li:nth-child(1) {{ animation-delay: 0.15s; }}
  .slide.active li:nth-child(2) {{ animation-delay: 0.25s; }}
  .slide.active li:nth-child(3) {{ animation-delay: 0.35s; }}
  .slide.active li:nth-child(4) {{ animation-delay: 0.45s; }}
  .slide.active li:nth-child(5) {{ animation-delay: 0.55s; }}
  .slide.active li:nth-child(n+6) {{ animation-delay: 0.65s; }}
  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
  .title-slide h1 {{
    font-size: clamp(1.6rem, 5vw, 3.5rem);
    font-weight: 800;
    background: var(--title-h1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: clamp(8px, 2vh, 16px);
    text-align: center;
  }}
  .title-slide h2 {{
    font-size: clamp(0.9rem, 2.5vw, 1.5rem);
    font-weight: 400;
    color: var(--title-h2);
    margin-bottom: clamp(12px, 3vh, 24px);
    text-align: center;
  }}
  .title-slide .meta {{
    font-size: clamp(0.75rem, 1.8vw, 1rem);
    color: var(--title-meta);
  }}
  .slide h2 {{
    font-size: clamp(1.2rem, 3.5vw, 2.2rem);
    font-weight: 700;
    color: var(--slide-h2);
    margin-bottom: clamp(16px, 3vh, 32px);
    text-align: center;
  }}
  .slide ul {{
    list-style: none;
    max-width: min(800px, 92vw);
    width: 100%;
  }}
  .slide li {{
    font-size: clamp(0.85rem, 2vw, 1.25rem);
    line-height: 1.7;
    padding: clamp(6px, 1vh, 12px) 0 clamp(6px, 1vh, 12px) 28px;
    position: relative;
    color: var(--li);
  }}
  .slide li::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: var(--li-marker);
    font-weight: bold;
  }}
  .slide li:nth-child(even) {{ color: var(--li-alt); }}
  /* Theme toggle */
  .theme-toggle {{
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 100;
    background: var(--btn-bg);
    border: none;
    color: var(--btn-text);
    width: 44px;
    height: 44px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 2px 12px rgba(102,126,234,0.3);
  }}
  .theme-toggle:hover {{ transform: scale(1.1); box-shadow: 0 4px 20px rgba(102,126,234,0.5); }}
  .theme-toggle:active {{ transform: scale(0.95); }}
  /* Controls */
  .controls {{
    display: flex;
    justify-content: center;
    align-items: center;
    gap: clamp(8px, 2vw, 20px);
    padding: clamp(10px, 2vh, 20px);
    background: var(--controls-bg);
    border-top: 1px solid var(--border);
    transition: background var(--transition-speed) ease;
  }}
  .controls button {{
    background: var(--btn-bg);
    border: none;
    color: var(--btn-text);
    padding: clamp(6px, 1.2vh, 10px) clamp(12px, 2vw, 24px);
    border-radius: 8px;
    cursor: pointer;
    font-size: clamp(0.75rem, 1.5vw, 1rem);
    font-weight: 600;
    transition: transform 0.2s;
  }}
  .controls button:hover {{ transform: scale(1.05); }}
  .controls button:disabled {{ opacity: 0.3; cursor: default; transform: none; }}
  .progress {{ display: flex; gap: clamp(4px, 1vw, 6px); }}
  .progress-dot {{
    width: clamp(8px, 1vw, 10px);
    height: clamp(8px, 1vw, 10px);
    border-radius: 50%;
    background: var(--dot);
    transition: all 0.3s;
    cursor: pointer;
  }}
  .progress-dot.active {{ background: var(--dot-active); transform: scale(1.3); }}
  .slide-counter {{
    font-size: clamp(0.65rem, 1.3vw, 0.9rem);
    color: var(--text2);
    min-width: clamp(40px, 6vw, 60px);
    text-align: center;
  }}
  /* Touch swipe hint */
  .swipe-hint {{
    position: fixed;
    bottom: 70px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.8rem;
    color: var(--text2);
    opacity: 0.5;
    pointer-events: none;
    animation: fadeOut 3s ease 2s forwards;
  }}
  @keyframes fadeOut {{ to {{ opacity: 0; }} }}
  /* Landscape / small height */
  @media (max-height: 500px) {{
    .slide {{ padding: 10px 20px; }}
    .slide li {{ padding: 4px 0 4px 24px; font-size: 0.85rem; }}
    .slide h2 {{ margin-bottom: 12px; }}
  }}
  /* Very small screens */
  @media (max-width: 400px) {{
    .slide li {{ font-size: 0.8rem; padding-left: 20px; }}
    .slide li::before {{ left: -2px; }}
  }}
</style>
</head>
<body>
<button class="theme-toggle" id="themeToggle" title="Toggle theme" aria-label="Toggle theme">☀️</button>
<div class="presentation">
  <div class="slides-container" id="slidesContainer">
    {chr(10).join(slide_htmls)}
  </div>
  <div class="controls">
    <button id="prevBtn" onclick="prevSlide()">← Prev</button>
    <div class="progress" id="progressBar"></div>
    <span class="slide-counter" id="slideCounter">1 / {total}</span>
    <button id="nextBtn" onclick="nextSlide()">Next →</button>
  </div>
</div>
<div class="swipe-hint">← swipe or use arrow keys →</div>
<script>
  const slides = document.querySelectorAll('.slide');
  let current = 0;
  const total = slides.length;
  const progressBar = document.getElementById('progressBar');
  const counter = document.getElementById('slideCounter');
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const themeBtn = document.getElementById('themeToggle');
  // Build progress dots
  for (let i = 0; i < total; i++) {{
    const dot = document.createElement('div');
    dot.className = 'progress-dot';
    dot.onclick = () => goToSlide(i);
    dot.title = 'Slide ' + (i+1);
    progressBar.appendChild(dot);
  }}
  function update() {{
    slides.forEach((s, i) => {{
      s.classList.remove('active', 'prev');
      if (i === current) s.classList.add('active');
      else if (i < current) s.classList.add('prev');
    }});
    const dots = progressBar.querySelectorAll('.progress-dot');
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
    counter.textContent = (current + 1) + ' / ' + total;
    prevBtn.disabled = current === 0;
    nextBtn.disabled = current === total - 1;
  }}
  function nextSlide() {{ if (current < total - 1) {{ current++; update(); }} }}
  function prevSlide() {{ if (current > 0) {{ current--; update(); }} }}
  function goToSlide(i) {{ current = i; update(); }}
  // Keyboard
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowRight' || e.key === ' ') {{ e.preventDefault(); nextSlide(); }}
    if (e.key === 'ArrowLeft') {{ e.preventDefault(); prevSlide(); }}
    if (e.key === 'Home') {{ goToSlide(0); }}
    if (e.key === 'End') {{ goToSlide(total - 1); }}
  }});
  // Touch swipe
  let touchStartX = 0;
  document.addEventListener('touchstart', (e) => {{ touchStartX = e.changedTouches[0].screenX; }}, {{ passive: true }});
  document.addEventListener('touchend', (e) => {{
    const dx = e.changedTouches[0].screenX - touchStartX;
    if (Math.abs(dx) > 50) {{ dx < 0 ? nextSlide() : prevSlide(); }}
  }}, {{ passive: true }});
  // Theme toggle
  let dark = true;
  themeBtn.addEventListener('click', () => {{
    dark = !dark;
    document.body.classList.toggle('light', !dark);
    themeBtn.textContent = dark ? '☀️' : '🌙';
  }});
  update();
</script>
</body>
</html>"""
    return html

def generate_report(topic, all_data):
    """Generate report + slideshow.

    The script does search+scrape+theme-extraction, then writes structured
    JSON for the agent's LLM to synthesize.  This avoids the exec sandbox's
    inability to reach external APIs.

    Returns (md_report_text, slideshow_html_text).
    """
    sources = all_data.get("sources", [])
    pdf_sources = all_data.get("pdf_sources", [])
    research_sources = all_data.get("research_sources", [])
    all_web = _extract_clean_summaries(sources)
    all_pdf = _extract_clean_summaries(pdf_sources)
    all_research = _extract_clean_summaries(research_sources)
    all_items = all_web + all_pdf + all_research

    if not all_items:
        return "No sufficient content found for analysis.", None

    deduped = _deduplicate_content(all_items)
    themes = _extract_themes(deduped)

    # Write structured data for the agent to pass to its LLM
    data_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "research_data.json",
    )
    payload = {
        "topic": topic,
        "total_queries": all_data.get("total_queries", 0),
        "rounds": all_data.get("rounds", 0),
        "web_count": len(sources),
        "pdf_count": len(pdf_sources),
        "research_count": len(research_sources),
        "themes": {},
        "all_items": [
            {"title": t, "content": c, "url": u}
            for t, c, u in deduped
        ],
    }
    for k, v in themes.items():
        payload["themes"][k] = [
            {"title": t, "content": c, "url": u} for t, c, u in v
        ]
    with open(data_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"  Structured research data written to: {data_path}")
    print(f"  Pass this file to the LLM for synthesis.")

    # Also produce the slideshow (no LLM needed)
    slide_deck = _build_slide_deck(topic, all_items, ref_offset=1, all_data=all_data)

    # Return None for report — the agent will replace it with the
    # LLM-synthesized version after reading research_data.json
    return None, slide_deck
def run_research(topic):
    print(f"🔍 Starting deep research on: {topic}")
    print(f"   Rounds: {MAX_ROUNDS} | Queries per round: {QUERIES_PER_ROUND}")
    print(f"   Max pages to scrape: {MAX_PAGES_TO_SCRAPE}")
    print(f"   Max PDFs to extract: {MAX_PDF_TO_EXTRACT}")
    print(f"   Max research sites: {MAX_RESEARCH_SITES}")
    print()

    all_sources = []
    all_pdf_sources = []
    all_research_sources = []
    all_urls = set()
    total_queries = 0
    rounds = 0

    def _run_round(query_list, round_label):
        nonlocal total_queries, rounds
        print(f"📊 {round_label}")
        print("=" * 60)

        # ── Parallel search: all queries at once ──
        print(f"   Searching {len(query_list)} queries in parallel...")
        round_sources = []
        BATCH_SIZE = 5  # Avoid rate limits by batching parallel requests
        for batch_start in range(0, len(query_list), BATCH_SIZE):
            batch = query_list[batch_start:batch_start + BATCH_SIZE]
            with concurrent.futures.ThreadPoolExecutor(max_workers=BATCH_SIZE) as pool:
                futures = {pool.submit(_tinyfish_search, q, MAX_RESULTS_PER_QUERY): idx for idx, q in enumerate(batch)}
                batch_results = [None] * len(batch)
                for fut in concurrent.futures.as_completed(futures):
                    idx = futures[fut]
                    try:
                        res = fut.result()
                        batch_results[idx] = res
                    except Exception as e:
                        print(f"  ✗ Query failed: {e}")
                        batch_results[idx] = []
                for res in batch_results:
                    if res:
                        round_sources.extend(res)
                        total_queries += 1
            if batch_start + BATCH_SIZE < len(query_list):
                time.sleep(0.3)  # Small gap between batches

        print(f"\n📊 Total unique URLs so far: {len(set(s.get('url', '') for s in round_sources))}")
        print(f"   New URLs this round: {len(round_sources)}")

        # ── Parallel fetch: all URLs at once ──
        urls = _get_unique_urls(round_sources, max_urls=MAX_PAGES_TO_SCRAPE)
        new_urls = [u for u in urls if u not in all_urls]
        print(f"\n📥 Fetching {len(new_urls)} pages in parallel...")

        def _fetch_one(url):
            content, title = _tinyfish_fetch(url)
            if not content:
                return None
            source = {"title": title or url.split("/")[-1], "content": content, "url": url}
            # Check for PDF
            if content.strip().startswith("invalid pdf header") or "EOF marker not found" in content:
                pdf_text = _extract_pdf_text(url)
                if pdf_text:
                    return {"type": "pdf", "source": source, "pdf_text": pdf_text}
            elif url.endswith(".pdf"):
                pdf_text = _extract_pdf_text(url)
                if pdf_text:
                    return {"type": "pdf", "source": source, "pdf_text": pdf_text}
            return {"type": "web", "source": source}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_one, u): u for u in new_urls}
            for fut in concurrent.futures.as_completed(futures):
                url = futures[fut]
                try:
                    result = fut.result()
                    if result:
                        if result["type"] == "web":
                            all_sources.append(result["source"])
                        elif result["type"] == "pdf":
                            all_sources.append(result["source"])
                            if len(all_pdf_sources) < MAX_PDF_TO_EXTRACT:
                                all_pdf_sources.append(result["source"])
                        all_urls.add(url)
                except Exception as e:
                    print(f"  ✗ Fetch failed for {url}: {e}")
            # Small delay after fetch batch to avoid fetch rate limits
            time.sleep(0.2)

        # ── Parallel research site search ──
        print(f"\n📚 Searching {MAX_RESEARCH_SITES} research sites in parallel...")
        research_results = _search_research_sites(topic)
        all_research_sources.extend(research_results)
        for r in research_results:
            all_urls.add(r["url"])

        rounds += 1
        print(f"\n✅ {round_label} complete!")
        print(f"   Sources collected: {len(all_sources)}")
        print(f"   PDFs extracted: {len(all_pdf_sources)}")
        print(f"   Research papers: {len(all_research_sources)}")
        print(f"   Total unique URLs: {len(all_urls)}")
        print()

    # ── Round 1: Broad Search ──
    broad_queries = _generate_queries(topic, 1)
    _run_round(broad_queries, "Round 1: Broad Search")

    # ── Round 2: Deep Dive ──
    deep_queries = _generate_queries(topic, 2)
    _run_round(deep_queries, "Round 2: Deep Dive")

    # ── Round 3: Targeted Search ──
    if rounds < MAX_ROUNDS:
        targeted_queries = _generate_queries(topic, 3)
        _run_round(targeted_queries, "Round 3: Targeted Search")

    # ── Save raw data after all rounds ──
    topic_slug = _get_topic_slug(topic)
    _save_raw_data(topic_slug, all_sources, all_pdf_sources, all_research_sources)

    # ── Generate Report ──
    print("📝 Generating research report...")
    all_data = {
        "sources": all_sources,
        "pdf_sources": all_pdf_sources,
        "research_sources": all_research_sources,
        "total_queries": total_queries,
        "rounds": rounds,
        "research_sites_searched": len(all_research_sources),
    }

    md_report, slide_deck = generate_report(topic, all_data)

    # ── Save synthesized data ──
    all_items = _extract_clean_summaries(all_sources) + _extract_clean_summaries(all_pdf_sources) + _extract_clean_summaries(all_research_sources)
    deduped = _deduplicate_content(all_items) if all_items else []
    themes = _extract_themes(deduped) if deduped else {}
    _save_synthesized_data(topic_slug, deduped, themes, all_data)

    # ── Update global index ──
    raw_path = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "raw" / topic_slug
    syn_path = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "synthesized" / topic_slug
    _update_index(topic_slug, raw_path, syn_path, len(all_sources), len(all_pdf_sources), len(all_research_sources), total_queries, rounds)

    # Save slideshow
    report_dir = Path("/Users/manjunathkanavi/.nanobot/workspace/personal_bot/deep-research/reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_topic = re.sub(r'[^a-z0-9\-]', '-', topic.lower().replace(' ', '-'))
    slide_path = report_dir / f"{safe_topic}-{timestamp}.html"
    slide_path.write_text(slide_deck, encoding="utf-8")

    print(f"   Slideshow saved: {slide_path}")
    print(f"   Web pages: {len(all_sources)} | PDFs: {len(all_pdf_sources)} | Research: {len(all_research_sources)}")
    print(f"   Total unique pages: {len(all_urls)}")
    print(f"   Total queries: {total_queries} | Rounds: {rounds}")
    print(f"   Raw data: {raw_path}")
    print(f"   Synthesized data: {syn_path}")

    if md_report is None:
        # Report will be synthesized by the agent's LLM from research_data.json
        print(f"\n⚠ Report synthesis skipped — script does not have LLM access.")
        print(f"  The structured research data is at:")
        print(f"  skills/deep-research/research_data.json")
        print(f"  Pass this to the LLM with the synthesis prompt to generate the report.")
        print(f"\n🎉 Deep research (search+scrape) complete!")
        print(f"   Slideshow: {slide_path}")
        print(f"   Pages: {len(all_urls)} | Queries: {total_queries} | Rounds: {rounds}")
        return

    # Save report (LLM-synthesized version provided by agent)
    report_path = report_dir / f"{safe_topic}-{timestamp}.md"
    report_path.write_text(md_report, encoding="utf-8")

    print(f"\n✅ Report saved: {report_path}")
    print(f"   Report size: {len(md_report)} chars | Slideshow: {len(slide_deck)} chars")

    # ── Commit to Git ──
    print(f"\n📦 Committing to git...")
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd="/Users/manjunathkanavi/.nanobot/workspace/personal_bot",
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Deep research: {topic} ({len(all_sources)} web, {len(all_pdf_sources)} PDF, {len(all_research_sources)} research)"],
            cwd="/Users/manjunathkanavi/.nanobot/workspace/personal_bot",
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "push"],
            cwd="/Users/manjunathkanavi/.nanobot/workspace/personal_bot",
            check=True,
            capture_output=True
        )
        print("  Committed and pushed!")
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Git error: {e}")

    print(f"\n🎉 Deep research complete!")
    print(f"   Report: {report_path}")
    print(f"   Slideshow: {slide_path}")
    print(f"   Pages: {len(all_urls)} | Queries: {total_queries} | Rounds: {rounds}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 deep_research.py <topic>")
        sys.exit(1)
    topic = " ".join(sys.argv[1:])
    run_research(topic)
