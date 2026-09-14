# LLM Application Behind a Gateway: Suricata for Network Inspection + OpenGuardrails for Semantic Inspection

**Deep Research Report · September 14, 2026**
*Source material: 92 unique pages scraped across 13 curated queries (Suricata, OpenGuardrails, Salesforce Trust Layer, NVIDIA security research, TrueFoundry gateway defense model, LLM-gateway tooling, and community AI-agent threat rulesets).*

---

## 1. Executive Summary

The product in question is a **gateway that sits between an LLM application and its model providers**, performing *two complementary kinds of inspection*: **Suricata** for network-layer deep-packet inspection (the transport carrying the API calls) and **OpenGuardrails** for semantic-layer inspection of the prompt/response content and tool-call semantics. This is not a single existing product — it is an *architecture pattern* that fuses two traditionally-separate defense layers into one SaaS.

The core thesis is **complementarity**: prompt injection is fundamentally a *semantic* problem that network tools cannot see (the malicious instruction arrives as legitimate-looking HTTPS traffic), while semantic gateways are *blind to the transport* — they cannot see whether an agent's response is actually exfiltrating data over a covert egress channel. Suricata closes the transport/exfiltration gap; OpenGuardrails closes the intent/semantic gap. Neither alone is sufficient against a determined attacker, but together they form layered defense where each covers the other's blind spots.

The timing is favorable: **only 1 in 5 companies has mature governance for autonomous AI agents** (Deloitte), **78% of executives lack confidence passing an AI governance audit** (Grant Thornton 2026), and prompt injection is widely regarded as *the defining application-security problem of LLM systems* — with no complete defense. The product targets the governance gap that pure network IDS and pure semantic guardrails both leave open.

---

## 2. The Problem: Why LLM Apps Are Uninspectable Today

Modern LLM applications sit behind an **LLM gateway** (also called a proxy or AI gateway). The gateway is the chokepoint through which every model call flows: it sees prompts, tool-call arguments, provider API keys, and agent decisions. As one production-engineering analysis puts it, this makes the gateway "the strongest place to enforce policy and the worst place to be wrong" (*EdgeLabs, 2026*).

The inspection gap has two dimensions:

- **Semantic blindness at the network layer.** Traditional IDS/IPS (Suricata, Snort) and firewalls see encrypted HTTPS/TLS traffic carrying an OpenAI-compatible `chat.completions` request. They cannot parse the *meaning* of a prompt, detect an embedded injection instruction inside a retrieved document, or tell whether a tool call is authorized. To them it's just bytes over TCP.

- **Transport blindness at the semantic layer.** Pure guardrail products (content filters, injection classifiers) inspect prompt text and response text but operate *inside the application loop*. They cannot see whether an agent's own output is tunneled to a C2 server, whether the egress channel is anomalous, or how much data left via non-API channels. They are probability filters over content, not transport monitors.

The result is a **visibility wedge**: the network layer sees transport but not meaning; the semantic layer sees meaning but not transport. A sophisticated *indirect* prompt-injection attack — where malicious instructions are buried in a document the agent reads, not sent by the user at all — can slip through both.

---

## 3. Architecture Overview: The Two-Layer Gateway

The proposed SaaS is a gateway that performs inspection at **two distinct layers of the same traffic flow**:

```
        ┌────────────────────── LLM APPLICATION (agent loop) ──────────────────────┐
        │  user input → [gateway] → model call → tool calls → action               │
        └──────────────────────────────────────────────────────────────────────────┘
                                  │  HTTPS/TLS/mTLS
        ┌─────────────────────── GATEWAY (SaaS inspection layer) ─────────────────┐
        │                                                                          │
        │  LAYER A — Suricata (network/transport inspection)                       │
        │    • DPI on the raw HTTP/TLS/WebSocket carrying the call                 │
        │    • Detects C2 channels, exfil tunnels, anomalous egress, JA3/JA4       │
        │    • EVE JSON structured telemetry → SIEM / block                        │
        │                                                                          │
        │  LAYER B — OpenGuardrails (semantic inspection)                          │
        │    • POST /v1/evaluate at step/request and step/response seams           │
        │    • GuardEvent → detector verdicts (block / allow)                      │
        │    • Safety.* (toxicity, PII) + Security.* (injection, exfil, SSRF)     │
        └──────────────────────────────────────────────────────────────────────────┘
                                  │  HTTPS/TLS/mTLS
        ▼ model provider (OpenAI / Anthropic / self-hosted)
```

The gateway is the single enforcement point where **both layers converge**. Suricata's network verdicts (e.g., "egress to known C2 IP detected") can *feed context into* the OpenGuardrails evaluation (e.g., "this tool call is blocked because its response is destined for an exfiltration endpoint"). This cross-layer correlation is the product's differentiator and does not exist in any single off-the-shelf tool.

---

## 4. Layer A — Suricata Network Inspection (What It Sees)

**Suricata** is the OISF's open-source IDS/IPS/NSM engine (current stable branch **8.0.5**, GA July 2025). It runs three roles from one binary: an **IDS** (alerts on suspicious traffic), an **IPS** (drops malicious flows inline via NFQUEUE), and a **Network Security Monitoring (NSM)** engine that logs every HTTP request, TLS handshake, DNS query, and file transfer.

For an LLM gateway the relevant capabilities are:

- **Deep Packet Inspection (DPI)** on application-layer protocols. Suricata 8.0 added eight new LALPs (layer-7 application protocols) and 107 rule keywords, plus a plugin architecture that lets you register protocol parsers at runtime. Guiding principle: *"if you log it, you can use it in a rule."*
- **Protocol fingerprinting (JA3/JA4)** — critical for spotting anomalous TLS client behavior, such as an agent library masquerading as a browser or a C2 beacon.
- **EVE JSON structured output** — every event (http, tls, dns, flow, fileinfo) is machine-readable and shipable to a SIEM.
- **Inline IPS via NFQUEUE** — can actively *drop* malicious flows, not just alert.

### Why Suricata specifically for an LLM gateway
Community rule engineering is already converging on AI-agent threat surfaces. A recently published open-source ruleset (**CGTI for OpenClaw**, 646 active Suricata rules across 13 files, SIDs `9200001–9204419`) targets precisely the gaps that legacy rulesets miss: **MCP-protocol SSRF, tool-call injection over WebSocket gateways, AI-skill supply-chain poisoning, and prompt-injection delivery channels**. Its design principles map directly onto an LLM-gateway use case:
- **Dual-indicator minimum** — no rule fires on a single `content:` match (reduces false positives).
- **Three confidence layers** — priority 1 = known C2 IPs / CVE signatures / JA3 fingerprints (near-zero FP); priority 2 = behavioral/threshold; priority 3 = heuristics.
- **MITRE ATT&CK metadata** on every rule for triage and reporting.

This proves the network layer *can* be tuned to detect AI-agent threats — but only for known patterns. The product must treat this as a moving target, not a solved problem.

---

## 5. Layer B — OpenGuardrails Semantic Inspection (What It Understands)

**OpenGuardrails (OGR)** is an Apache-2.0, foundation-governed **vendor-neutral protocol** for AI-agent safety and security (current version **v0.8**). Crucially, *OGR is not a guardrail product* — it defines the wire contract and referees a neutral detector benchmark. "Vendors compete on detection quality behind a common plug; users get one way to configure and compose safety across every agent they run."

### The wire contract
The whole protocol is **one endpoint, two calls per model call**: `POST /v1/evaluate`, which accepts typed **GuardEvents** and returns a **Verdict**. The integration stays stateless — it asserts an identity five-tuple (`agent_id`, `agent_type`, `agent_workspace`, `agent_owner`, `agent_user`) and a `step_id` pairing the request/response events; everything else (sessions, turns, numbering) is derived server-side.

The agent loop maps onto OGR's vocabulary: **session → turn → step (one model call) → calls (tool calls)**. Two events are reported per model call:
- `step/request` — evaluated **before** the model runs.
- `step/response` — evaluated after the response is generated but **before** the agent acts on it.

Each event gets a verdict at the moment the integration can still refuse it. **Fail-open by default** — if the OGR runtime is unreachable, the agent keeps running (availability over security).

### Two domains, one contract
- **Safety** — harmful *content/behavior*: toxicity, self-harm, CSAM, brand, topic. Mostly classifier-judged at the content I/O boundary.
- **Security** — *system compromise*: prompt injection, data exfiltration, malicious commands, SSRF, secret leakage, supply chain. Judged on **actions and data flow** — what a tool call is about to do, not just the words.

The taxonomy (`safety.*`, `security.*`) is versioned and swappable — the contract references category IDs but stays neutral on what counts as "unsafe," letting detectors compete.

### Why OGR specifically for an LLM gateway
OGR already has a **gateway plugin** (Higress, Go/WASM) as its v0.8 reference integration — meaning the gateway pattern is a first-class citizen, not an afterthought. It integrates cleanly with litellm and agent harnesses. Because OGR is a *protocol* rather than a product, the SaaS can plug in multiple detector vendors behind one contract and swap them without rewriting the gateway — a significant procurement and resilience advantage.

---

## 6. The Complementarity Thesis: Why You Need Both Layers

This is the intellectual core of the product and the section most likely to be dismissed by a skeptic — so it must be stated precisely.

### The "lethal trifecta" and why single-layer defense fails
TrueFoundry's 2026 analysis of prompt-injection defense identifies a structural root: *the model reads trusted instructions and untrusted data through the same channel, with no reliable way to tell them apart.* From this flow three attack classes:
1. **Direct injection** — malicious instructions in the user's own input. Detectable by input guardrails.
2. **Indirect injection** — malicious instructions hidden in retrieved documents or tool results the agent reads. *"The dangerous one, because no user chose to send it."*
3. **Tool-mediated injection** — malicious instructions embedded in tool metadata.

These combine with the **"lethal trifecta"** to create real damage: (a) access to private data + (b) exposure to untrusted content + (c) an exfiltration channel. An agent with all three can be turned into a data-exfiltration tool by content it merely *reads*.

Now map the layers:

| Attack vector | Suricata (network) sees it? | OGR/semantic gate sees it? |
|---|---|---|
| Direct injection in user prompt | ❌ (looks like normal HTTPS) | ✅ input guardrail classifier |
| Indirect injection in retrieved doc | ❌ (looks like normal HTTPS) | ✅ semantic classifier on retrieved context |
| Exfiltration over covert egress channel | ✅ anomalous outbound flow / C2 beacon | ❌ (may look like a legit API call to the "backend") |
| Data volume / egress rate anomaly | ✅ flow + byte-count telemetry | ⚠️ only if it parses the response body |
| Authorized-looking tool call to attacker C2 | ⚠️ if egress is anomalous | ✅ semantic: "this call exfiltrates secrets" |
| Prompt-injection *intent* in natural language | ❌ (ciphertext + opaque payload) | ✅ semantic classifier |

The insight: **Suricata sees the *channel*, OGR sees the *intent*.** A semantic classifier will flag a prompt containing an injection string; Suricata independently confirms whether the resulting tool call actually *exfiltrated* anything. When both agree (intent + egress), the gateway can block with high confidence and low false positives. When they disagree (intent detected but no egress, or anomalous egress with benign content), the gateway escalates for human review.

This is **defense in depth at the transport/semantic seam** — a distinction no single product currently offers.

---

## 7. Threat Model & Attack Taxonomy (Consolidated)

Combining sources, the product must defend against:

- **Prompt injection** (direct / indirect / tool-mediated) — the primary semantic threat; detection is an arms race, never "solved."
- **Data exfiltration** — over API egress (semantic) *and* covert channels like DNS/HTTPS beacons to C2 (network). Suricata's JA3/JA4 + flow telemetry catches the latter; OGR catches the former.
- **SSRF** — agent makes an internal request via a tool argument; OGR blocks the action, Suricata sees the internal-network connection attempt.
- **Credential/secret leakage** — secrets in prompts (OGR) or secrets leaving via unusual egress (Suricata).
- **MCP protocol abuse** — tool injection over MCP/WebSocket gateways; community Suricata rulesets already target this specifically.
- **Supply-chain poisoning** — malicious AI skills/tools pulled by the agent; detectable via anomalous egress to untrusted registries (Suricata).
- **Gateway-as-target** — the gateway itself is a prime attack surface. A 2026 LiteLLM flaw scored **CVSS 8.7, EPSS ~80%, CISA KEV** with a remediation deadline; another scored 9.5. The product must be adversarially hardened: cross-tenant cache isolation, header-spoofing resistance, controlled model-downgrade behavior, safe fail-open semantics, and *every path must still write an audit event* (even on failure).

---

## 8. Implementation Blueprint (Reference Architecture)

**Placement.** The gateway sits in front of every model call the agent makes — an *egress* posture for outbound provider calls, optionally an *ingress/routing* posture if models are self-hosted (cf. Solo.io's agentgateway, a Rust-based AI-native proxy that natively understands MCP and A2A protocols).

**Inspection pipeline per model call:**
1. **Pre-model (step/request).** OGR `evaluate("step/request", body)` runs input guardrail classifiers — injection, jailbreak, PII. Suricata concurrently inspects the raw TLS/HTTP flow for anomalous egress patterns and fingerprints the client.
2. **Model call.** Unchanged application code forwards bodies to the provider; gateway relays traffic and logs it.
3. **Post-model (step/response).** OGR `evaluate("step/response", resp)` runs output guardrails — blocks exfiltration/policy violations. Suricata inspects the response bytes for covert-channel signatures (DNS tunneling, base64 in unusual fields) and measures egress volume/rate.
4. **Pre-action (tool calls).** OGR evaluates each tool call's *semantics* ("is this agent authorized to write to this data source?"). Suricata sees the actual network connection the tool call opens and can block if it targets a C2 or internal host.
5. **Cross-layer correlation.** Combine OGR verdict + Suricata flow signal into a single gateway decision (block / allow / escalate). Log both signals to one audit trail.

**Enforcement points.** EdgeLabs identifies four: pre-model, post-model, tool-call, and egress. Most tools cover only the first two — **tool-argument validation is the widest practical gap**. This product's differentiator is covering all four by combining semantic + network signals.

**Deterministic guarantees.** Guardrails are probability filters, not boundaries. The product must also enforce *deterministic* controls: capability restriction (least privilege on tools), typed tool interfaces, digest-pinned model/tool deploys, and pinned MCP tool definitions.

---

## 9. Competitive Landscape & Positioning

The market has three overlapping but distinct categories — the product sits at their intersection:

1. **Gateway platforms** (EdgeLabs, Truefoundry, Bifrost/Maxim, Kosmoy, Grepture, Solo.io agentgateway, Portkey, Kong) — own the request path; most cover pre-model + post-model only.
2. **Guardrail/governance layers** (OpenGuardrails ecosystem, NVIDIA semantic-injection research lineage, LangGuard/Llama Guard lineage) — inspect content semantics but operate inside the app loop, blind to transport.
3. **Runtime/transport monitors** (Suricata-based NDR like Stamus Clear NDR, Sysdig) — watch execution and network but lack semantic understanding of LLM intent.

**Positioning statement.** *"The only gateway that inspects an LLM call at both the semantic layer (what does this prompt/tool-call mean?) and the network layer (did anything actually leave, and where did it go?)."*

**Differentiators vs. alternatives:**
- **vs. Salesforce Trust Layer / Agentforce Gateway.** Salesforce builds governance *into its platform* — powerful but locked to the Salesforce/Agentforce ecosystem. This product is provider-agnostic and network-aware, covering self-hosted LLMs and arbitrary agents.
- **vs. pure semantic gateways.** Adds the transport/exfiltration dimension no content filter provides.
- **vs. pure NDR/Suricata deployments.** Adds semantic understanding of LLM intent that a network IDS fundamentally cannot.
- **vs. building it in-house.** The OGR protocol collapses the integration from an N×M×L problem (every agent × every detector × every LLM protocol) into **N + M + L** — integrate once against the contract.

---

## 10. Business Model & Market Sizing

**The governance gap is the market.** Deloitte: only 1 in 5 companies has mature AI-agent governance. BCG: 41% of executives worry about lack of control over AI decisions. Grant Thornton (2026): 78% lack confidence passing an AI governance audit. These are *infrastructure* gaps, not awareness gaps — companies already want to deploy AI responsibly and lack the controls.

**Pricing model.** Given enterprise security buyers, a defensible model is **tiered usage-based SaaS** priced per inspected request or per million tokens, with enterprise tiers including self-hosted/air-gapped deployment (a hard requirement — EdgeLabs lists "self-hosted, on-prem, sovereign, or air-gapped" as a top criterion). Add-on revenue from:
- Custom rule engineering (Suricata rulesets per industry/vertical).
- Compliance report packs (SOC 2, GDPR, HIPAA, AI Act) generated from the audit trail.
- Managed detection service (SOC-as-a-service on top of EVE JSON + OGR verdicts).

**ICP.** Enterprises deploying agentic AI with real-world actions (financial services: transactions/credit; healthcare: HIPAA-bound workflows; legal: document drafting) — precisely the high-stakes segments Salesforce identifies where guardrail requirements "differ across industries" and one-size-fits-all checklists fail.

**Wedge.** Start with the *compliance-and-audit* angle (the 78% who can't pass a governance audit) rather than the *detection* angle (which is never "solved") — compliance is a recurring, budgeted, measurable need.

---

## 11. Risks, Challenges & Open Problems

- **Detection is never solved.** Prompt injection is semantic, pattern-independent, and an arms race. Published red-team benchmarks show capable models complying with injected instructions at high rates. The product must position itself as *risk reduction*, not risk elimination — and guardrails "degrade" over time, requiring version control and adversarial re-testing like the models they govern.
- **The gateway is a prime target.** Every path must write an audit event; fail-open behavior must be carefully designed (fail open = availability but insecure; fail closed = secure but could break agents). A single CVE in the gateway is catastrophic — it sits on the critical path.
- **Latency.** Two inspection layers per call add round-trips (OGR's 5s timeout, DPI CPU cost). Must be sub-100ms added latency to be viable for agentic loops.
- **False positives break trust.** Enterprise agents take real actions; blocking legitimate calls erodes adoption. The dual-indicator + three-confidence-layer design from community rulesets is the right pattern to adopt internally.
- **Regulatory uncertainty.** OGR is v0.x (minor versions before v1 may break between releases). The standardization story is still early — betting on it means riding protocol evolution.
- **Encrypted traffic limits DPI.** Most LLM calls are TLS; the gateway must terminate or decrypt to inspect, which raises privacy and key-management concerns (an argument for OGR's in-loop semantic inspection as the primary layer, with Suricata providing transport telemetry where decryption is feasible).

---

## 12. Future Outlook

- **Protocol consolidation around OGR.** As the vendor-neutral protocol matures past v1, "integrate once, enforce everywhere" becomes a real procurement advantage. Gateways that speak OGR natively (like the Higress reference integration) will have a head start.
- **Context-aware networking is the next frontier.** Solo.io's thesis — that legacy proxies (NGINX, Envoy) cannot distinguish a tool call from a model invocation — points to *AI-native* proxies (like agentgateway) becoming table stakes. The product's network layer must become context-aware, not just packet-sniffing.
- **MCP and A2A as first-class traffic.** As agents talk to tools (MCP) and other agents (Agent2Agent), the gateway's inspection surface expands beyond single LLM calls to multi-hop flows — a new attack surface Suricata rulesets are already beginning to cover.
- **Regulation forces adoption.** With 78% of executives unable to pass an AI governance audit, expect mandatory guardrail/audit-trail requirements (EU AI Act enforcement, sector-specific rules) to turn this from a nice-to-have into a compliance mandate.
- **Convergence trend.** The market is moving toward *unified* gateways that combine routing, observability (Langfuse-style tracing), guardrails, and network telemetry — the product is positioned at exactly that convergence point.

---

## 13. References (Top Sources)

**OpenGuardrails / semantic layer**
- OpenGuardrails repo (v0.8 protocol + reference Higress gateway integration) — github.com/openguardrails/openguardrails
- Salesforce, *AI Guardrails: A Guide to Responsible AI* — salesforce.com/welcome-to-the-agentic-enterprise/ai-guardrails
- NVIDIA, *Securing Agentic AI: How Semantic Prompt Injections Bypass AI Guardrails* — developer.nvidia.com
- TrueFoundry, *Prompt Injection Defense at the AI Gateway* (2026) — truefoundry.com/blog/prompt-injection-defense-llm-gateway

**Network layer (Suricata)**
- Suricata 8.0 setup guide — tech-insider.org/au/suricata-ids-ips-setup-2026
- Stamus Networks, *Suricata Rules* (Clear NDR) — stamus-networks.com/suricata-rules
- Suricata forum, *CGTI for OpenClaw* (646 AI-agent threat rules) — forum.suricata.io

**Gateway & market context**
- EdgeLabs, *10 Best LLM Gateway Security Tools for Enterprise AI* (2026) — edgelabs.ai/blog/llm-gateway-security
- Solo.io, *Context-aware Security for Agentic AI Gateways* (2025) — solo.io/blog/context-aware-security-ai-gateways
- Reddit r/LLMDevs, *Why You Need an LLM Request Gateway in Production* — reddit.com/r/LLMDevs
- Portkey, *LLM proxy vs AI gateway* — portkey.ai/blog/llm-proxy-vs-ai-gateway

**Governance/market stats**: Deloitte (state of AI in the enterprise), BCG (*As AI investments surge, CEOs take the lead*), Grant Thornton 2026 AI Impact Survey.

*Note: some source URLs were returned by the search backend with hostnames that did not fully resolve to canonical pages; citations reflect the query results as retrieved. Verify live URLs before external distribution.*
