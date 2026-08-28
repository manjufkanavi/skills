# Harnessing Local LLMs Under 30B Parameters

## Executive Summary

Local LLMs under 30B parameters have reached a critical inflection point. Models like Qwen 2.5 (3B–32B), Llama 3.1 (8B/70B), Mistral (7B/24B), and Phi-3 (3.8B) now match or exceed the performance of much larger predecessors from 2023. With quantization (GGUF, AWQ, GPTQ), these models run efficiently on consumer hardware — even laptops with 8–16GB RAM. This report covers must-have skills, MCPs, best practices, new releases, open-source software, domain-specific models, and context management strategies.

---

## 1. Must-Have Skills for Local LLMs

### Core Technical Skills

- **Quantization mastery**: Understand GGUF (llama.cpp), AWQ (AutoAWQ), GPTQ (AutoGPTQ), and FP16/BF16 formats. GGUF is the universal standard for local inference.
- **Model fine-tuning**: LoRA/QLoRA for parameter-efficient fine-tuning. Tools: Unsloth, Axolotl, Hugging Face PEFT, Ollama Modelfile.
- **Prompt engineering**: System prompts, few-shot examples, chain-of-thought, ReAct patterns. Critical for getting quality from smaller models.
- **RAG (Retrieval-Augmented Generation)**: Chunking strategies, embedding models, vector databases (Chroma, FAISS, Qdrant, Weaviate). Essential for domain knowledge.
- **Context window management**: Sliding windows, summary compression, hierarchical attention. Maximize effective context beyond model limits.

### Infrastructure Skills

- **Ollama**: Model management, custom Modelfiles, API server, multi-model orchestration.
- **vLLM**: High-throughput serving, PagedAttention, continuous batching for production workloads.
- **LM Studio**: GUI-based model management, local API server, model testing.
- **Text Generation Inference (TGI)**: Hugging Face's production-grade inference server with tensor parallelism.
- **Docker/containerization**: Isolated model serving environments.

### Agent & Tool Skills

- **Function calling**: Structured output, tool use, API integration.
- **Multi-agent orchestration**: CrewAI, AutoGen, LangGraph, SmolAgents.
- **MCP (Model Context Protocol)**: Standardized tool integration for LLMs.
- **Evaluation**: Promptfoo, DeepEval, RAGAS for measuring model quality.

---

## 2. Must-Have MCPs for Local LLMs

### What is MCP?

The Model Context Protocol (MCP) is an open standard by Anthropic for connecting LLMs to external tools, data sources, and services. It provides a universal interface for model-tool interaction.

### Essential MCP Servers for Local LLMs

- **File System MCP**: Read/write files, navigate directories, search content. Foundation for any local agent.
- **Web Search MCP**: Brave Search, Tavily, SearxNG for internet access.
- **Database MCP**: PostgreSQL, SQLite, MongoDB connectors for structured data queries.
- **Code Execution MCP**: Run Python, JavaScript, shell commands in sandboxed environments.
- **Git MCP**: Repository operations, diff analysis, commit management.
- **Calendar/Email MCP**: Google Calendar, Gmail integration for productivity agents.
- **Slack/Discord MCP**: Messaging platform integration for team agents.
- **Browser MCP**: Playwright/Puppeteer for web automation and scraping.
- **Vector Database MCP**: Chroma, Qdrant, Weaviate for RAG workflows.
- **GitHub MCP**: Issue tracking, PR management, code review automation.

### MCP Frameworks

- **Python MCP SDK**: Official Anthropic SDK for building MCP servers.
- **TypeScript MCP SDK**: For Node.js-based MCP servers.
- **LiteLLM**: Proxy server supporting 100+ LLM providers with unified API.
- **FastMCP**: Lightweight MCP server framework.

---

## 3. Local LLM Best Practices

### Model Selection

- **Match model size to task**: 3B–7B for chat, summarization, simple code. 13B–20B for complex reasoning, code generation. 24B–32B for domain-specific expertise.
- **Prefer recent architectures**: Qwen 2.5, Llama 3.1, Mistral Nemo, Phi-3.5 outperform older models of same size.
- **Use instruction-tuned variants**: Always prefer `-Instruct` or chat-tuned versions for conversational tasks.
- **Consider MoE models**: Mixtral 8x7B, Qwen2.5-MoE offer better efficiency through sparse activation.

### Quantization Strategy

- **Q4_K_M (GGUF)**: Best quality/size balance. ~4.5GB for 7B models. Recommended default.
- **Q5_K_M**: Slightly better quality, ~5.5GB for 7B. Use when RAM allows.
- **Q8_0**: Near-lossless quantization. ~7.5GB for 7B. Use for critical tasks.
- **AWQ/GPTQ**: GPU-optimized quantization. Better throughput than GGUF on NVIDIA GPUs.
- **Avoid Q2/Q3**: Too aggressive for most use cases. Quality degradation is significant.

### Performance Optimization

- **GPU offloading**: Set `n_gpu_layers=-1` in llama.cpp to offload all layers to GPU.
- **Batch size tuning**: Larger batches = higher throughput but more memory. Find the sweet spot.
- **KV cache management**: Use flash attention for longer contexts. Enable memory-efficient attention.
- **Thread optimization**: Set `n_threads` to physical cores (not logical). M4 Mac: use 12–14 threads.
- **Continuous batching**: Use vLLM for serving multiple concurrent requests.

### Prompt Engineering

- **Be explicit**: Smaller models need clearer instructions. Specify format, tone, length.
- **Use templates**: System prompts with clear role definitions improve consistency.
- **Chain-of-thought**: For reasoning tasks, explicitly ask the model to "think step by step."
- **Few-shot examples**: Provide 2–3 examples of desired output format and quality.
- **Structured output**: Use JSON mode, function calling, or schema enforcement for programmatic use.

### RAG Best Practices

- **Chunk size**: 256–512 tokens for general text. 128–256 for code. 512–1024 for documents.
- **Overlap**: 10–20% overlap between chunks to preserve context boundaries.
- **Embedding model**: BGE-large, E5-large, or text-embedding-3-small. Match embedding dimension to your vector DB.
- **Hybrid search**: Combine dense (vector) and sparse (BM25) retrieval for best results.
- **Re-ranking**: Use cross-encoder re-ranker (e.g., BGE-reranker) to improve top-k relevance.

---

## 4. New Local LLM Model Releases (2024–2025)

### Qwen 2.5 Series (Alibaba)

- **Qwen2.5-0.5B/1.5B/3B**: Ultra-compact models for edge devices. Surprisingly capable for their size.
- **Qwen2.5-7B/14B**: Sweet spot for local deployment. Excellent code, math, and reasoning.
- **Qwen2.5-32B**: Flagship local model. Matches Llama 3.1 70B on many benchmarks.
- **Qwen2.5-Coder-7B/32B**: Specialized for code generation. Outperforms CodeLlama 34B.
- **Qwen2.5-Math-7B/72B**: Specialized for mathematical reasoning. State-of-the-art for open models.
- **Strengths**: Best-in-class multilingual (29 languages), excellent code generation, strong reasoning.
- **Availability**: GGUF, AWQ, GPTQ, FP16 formats on Hugging Face.

### Llama 3.1 Series (Meta)

- **Llama-3.1-8B-Instruct**: Fast, efficient, great for chat and simple tasks.
- **Llama-3.1-70B-Instruct**: Requires significant hardware but excellent quality.
- **Llama-3.1-405B**: Too large for local deployment (requires multi-GPU cluster).
- **Strengths**: Strong general capabilities, excellent tool use, 128K context window.
- **Availability**: GGUF (bartowski), AWQ, GPTQ on Hugging Face.

### Mistral Series

- **Mistral 7B v0.3**: Latest iteration with improved instruction following.
- **Mistral Small 24B**: Optimized for latency. Good for production deployment.
- **Mistral Nemo 12B**: Joint Mistral-IBM project. 131K context, excellent value.
- **Mistral Large 2**: 123B parameters. Too large for most local setups.
- **Strengths**: Strong multilingual, efficient, good tool use.
- **Availability**: GGUF, AWQ on Hugging Face and Ollama.

### Phi-3.5 Series (Microsoft)

- **Phi-3.5-mini-3.8B**: 128K context, excellent reasoning for size.
- **Phi-3.5-moE-instruct**: Mixture-of-experts, 4.2B active params, 14B total.
- **Strengths**: Microsoft's best small models, strong reasoning, 128K context.
- **Availability**: GGUF, ONNX on Hugging Face.

### Other Notable Releases

- **Gemma 2 9B/27B** (Google): Strong performance, 128K context, excellent for local use.
- **DeepSeek-V2.5/3**: MoE architecture, 236B total / 21B active. Excellent code and reasoning.
- **Yi 1.5 9B/34B** (01.AI): 200K context window, strong multilingual.
- **Command R+** (Cohere): 128K context, optimized for RAG and tool use.
- **Solar 10.7B** (Upstage): Efficient architecture, strong general capabilities.
- **SmolLM2 1.7B/3.7B** (Hugging Face): Ultra-lightweight, surprisingly capable.

---

## 5. Open Source Software for Building with Local LLMs

### Inference & Serving

- **Ollama**: Easiest local LLM deployment. Model management, API, multi-model support.
- **vLLM**: High-performance serving. PagedAttention, continuous batching, tensor parallelism.
- **Text Generation Inference (TGI)**: Hugging Face's production server. Tensor parallelism, quantization.
- **llama.cpp**: C++ inference engine. GGUF format, CPU/GPU hybrid, mobile support.
- **LM Studio**: GUI for model management, local API, model testing.
- **Jan**: Open-source alternative to ChatGPT UI. Local-first, multi-model.
- **Open WebUI**: Beautiful ChatGPT-like UI for local LLMs.

### Frameworks & Orchestration

- **LangChain**: LLM application framework. Chains, agents, memory, tools.
- **LlamaIndex**: Data framework for LLM applications. RAG, indexing, querying.
- **LangGraph**: Stateful multi-actor orchestration. Agent workflows, human-in-the-loop.
- **CrewAI**: Multi-agent framework. Role-based agents, task delegation.
- **AutoGen** (Microsoft): Multi-agent conversation framework. Flexible agent design.
- **SmolAgents** (Hugging Face): Lightweight agent framework. Simple, composable.
- **Haystack**: End-to-end LLM framework. RAG, pipelines, evaluation.

### RAG & Vector Databases

- **Chroma**: Embedded vector database. Simple API, great for local development.
- **Qdrant**: High-performance vector search. Rust-based, filtering, payloads.
- **Weaviate**: Open-source vector DB. GraphQL, hybrid search, modules.
- **FAISS**: Facebook's similarity search library. Fast, memory-efficient.
- **Milvus**: Distributed vector database. Scalable, cloud-native.
- **pgvector**: PostgreSQL extension for vector similarity. Great for existing Postgres setups.

### Fine-Tuning & Training

- **Unsloth**: 2x faster fine-tuning, 60% less memory. LoRA/QLoRA for Llama, Mistral, Qwen.
- **Axolotl**: Configuration-based fine-tuning. Supports 50+ models, multiple adapters.
- **Hugging Face PEFT**: Parameter-efficient fine-tuning library. LoRA, QLoRA, Adapters.
- **TRL** (Transformer Reinforcement Learning): RLHF, DPO, ORPO for alignment.
- **Axolotl**: YAML-based fine-tuning config. Easy setup, many model support.

### Evaluation & Monitoring

- **Promptfoo**: LLM evaluation framework. Automated testing, regression detection.
- **DeepEval**: Evaluation for RAG, agents, general LLM tasks.
- **RAGAS**: RAG-specific evaluation. Faithfulness, answer relevance, context precision.
- **WandB**: Experiment tracking, model monitoring, dataset versioning.
- **LangSmith**: LangChain's evaluation and debugging platform.

### Agent Platforms

- **Open Interpreter**: Run code locally, natural language interface to your computer.
- **Bee Agent Framework**: Multi-agent orchestration with MCP support.
- **Dify**: Open-source LLM app development platform. Visual workflow builder.
- **FlowiseAI**: Drag-and-drop LLM app builder. No-code/low-code.
- **Langflow**: Visual LangChain builder. Drag-and-drop agent design.

---

## 6. Best Domain-Specific Local LLMs Under 30B

### Code Development

- **Qwen2.5-Coder-32B**: Best overall code model under 30B. Python, JavaScript, TypeScript, Go, Rust.
- **Qwen2.5-Coder-7B**: Fast code generation, good for IDE integration.
- **CodeLlama-34B-Python**: Specialized Python code model. Large but excellent.
- **StarCoder2-15B**: Multi-language code model. Good for diverse codebases.
- **Phind-CodeLlama-34B**: Optimized for coding tasks with extensive code training.

### Medical/Healthcare

- **Meditron-70B/8B** (Meta): Medical fine-tuned Llama. Clinical knowledge, medical reasoning.
- **LLaMA-Med** (Stanford): Medical domain adaptation of LLaMA.
- **BioMistral-7B**: Biomedical question answering, literature understanding.
- **ClinicalBERT**: Specialized for clinical notes and EHR data.

### Legal

- **Legal-Pali** (Google): Legal domain adaptation of PaLM. Case law, statutes, contracts.
- **Lawformer**: Chinese legal domain model.
- **LexGLUE benchmarks**: Evaluate legal LLMs on classification tasks.

### Finance

- **FinBERT**: Financial sentiment analysis, earnings call analysis.
- **BloombergGPT** (research): 50B parameters, financial domain. Not publicly available but influential.
- **FinGPT**: Open-source financial LLM. Market analysis, sentiment, forecasting.

### Mathematics

- **Qwen2.5-Math-7B**: State-of-the-art open math model. Step-by-step reasoning.
- **MetaMath-70B**: Math-focused fine-tune of LLaMA. GSM8K, MATH benchmarks.
- **SOLAR-10.7B**: Strong mathematical reasoning capabilities.

### Multilingual

- **Qwen2.5** (all sizes): 29 languages, best multilingual open model.
- **Mistral 7B v0.3**: Strong multilingual support.
- **Nemotron-4-34B** (NVIDIA): 40+ languages, multilingual understanding.
- **Jais-13B/30B** (Emirates AI Lab): Arabic-first multilingual model.

### General Purpose (Best All-Rounders)

- **Qwen2.5-14B**: Best balance of quality and size. Excellent across all benchmarks.
- **Qwen2.5-32B**: Near-70B quality at local-deployable size.
- **Llama-3.1-8B**: Fast, reliable, excellent tool use.
- **Mistral Nemo 12B**: Great value, 131K context, strong all-rounder.
- **Gemma 2 9B**: Surprisingly capable for size, 128K context.

---

## 7. Handling Context in Local LLMs with 260K Max Context

### Understanding Context Windows

- **260K tokens** ≈ 200,000 words ≈ 400 pages of text. Massive but requires smart management.
- **Tokenization matters**: Qwen uses SentencePiece (1 token ≈ 0.75 words). Llama uses BPE (1 token ≈ 0.7 words).
- **Memory cost**: At 260K context, KV cache can consume 8–16GB VRAM even for 7B models.

### Context Management Strategies

#### 1. Sliding Window Attention

- Only attend to the most recent N tokens (e.g., 32K or 64K).
- Older context is summarized or compressed.
- **Trade-off**: Lower memory, faster inference, potential loss of distant information.
- **Implementation**: Use `--context-length 32768` in llama.cpp, or `max_model_len` in vLLM.

#### 2. Summary Compression

- Maintain a running summary of earlier conversation/document sections.
- Replace old tokens with summary tokens when context fills up.
- **Tools**: Use LLM to summarize chunks, store summaries in vector DB.
- **Best for**: Long conversations, document analysis, codebase understanding.

#### 3. Hierarchical Context

- Organize context in layers: raw data → extracted facts → summaries → high-level overview.
- Query the most relevant layer based on the question.
- **Implementation**: Use RAG with multiple index levels (document → section → paragraph).

#### 4. Retrieval-Augmented Generation (RAG)

- Don't load everything into context. Retrieve only relevant chunks.
- **Chunking**: Split documents into 256–512 token chunks with 10–20% overlap.
- **Embedding**: Use BGE-large, E5-large for high-quality embeddings.
- **Vector DB**: Chroma for local, Qdrant for production.
- **Re-ranking**: Use cross-encoder to re-rank retrieved chunks for better relevance.

#### 5. Context Packing

- Pack multiple short documents into a single context window.
- Use special tokens to separate documents.
- **Best for**: Batch processing, classification tasks.

#### 6. Streaming/Incremental Processing

- Process documents incrementally rather than loading all at once.
- Maintain state between chunks (summaries, extracted entities, decisions).
- **Best for**: Long document analysis, code review, legal document review.

### Practical Setup for 260K Context

#### On Mac Studio M4 (64GB RAM)

```bash
# Ollama with extended context
ollama pull qwen2.5:32b
# Create custom Modelfile
cat > Modelfile << 'EOF'
FROM qwen2.5:32b
PARAMETER num_ctx 262144
PARAMETER num_gpu_layers 99
PARAMETER num_thread 14
EOF
ollama create qwen2.5-32b-260k -f Modelfile
```

#### vLLM Configuration

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="Qwen/Qwen2.5-32B-Instruct",
    max_model_len=262144,
    gpu_memory_utilization=0.9,
    tensor_parallel_size=1,  # Single M4 Ultra chip
    dtype="float16",
)

sampling_params = SamplingParams(
    temperature=0.7,
    max_tokens=4096,
    top_p=0.95,
)
```

#### Memory Management Tips

- **Close other GPU-intensive apps** before running large context inference.
- **Use swap space**: Mac Studio can use SSD as extended RAM (slow but prevents OOM).
- **Monitor memory**: Use `powermetrics` or `Activity Monitor` to track GPU/RAM usage.
- **Batch requests**: Process multiple documents in parallel when possible.
- **Cache embeddings**: Pre-compute and cache embeddings to avoid recomputation.

### Context Window Comparison

| Model | Max Context | Practical Local Context | VRAM (Q4) |
|-------|-----------|----------------------|----------|
| Qwen2.5-3B | 128K | 64K | 2.2 GB |
| Qwen2.5-7B | 128K | 32K | 4.7 GB |
| Qwen2.5-14B | 128K | 32K | 9.2 GB |
| Qwen2.5-32B | 128K | 16K–32K | 19 GB |
| Llama 3.1-8B | 128K | 32K | 5.5 GB |
| Mistral Nemo 12B | 128K | 32K | 8.5 GB |
| Gemma 2 9B | 8K | 8K | 6.2 GB |

*Note: Practical context is limited by VRAM/RAM for KV cache storage, not just model capability.*

---

## References

1. Qwen Team. "Qwen2.5 Technical Report." arXiv:2412.15115, 2024.
2. Meta. "Llama 3.1 Model Card." 2024.
3. Mistral AI. "Mistral 7B v0.3 Technical Report." 2024.
4. Microsoft. "Phi-3.5 Technical Report." 2024.
5. Google. "Gemma 2 Technical Report." 2024.
6. Anthropic. "Model Context Protocol Specification." 2024.
7. Hugging Face. "Text Generation Inference Documentation." 2024.
8. vLLM Team. "vLLM: A Next Generation LLM Serving Engine." 2024.
9. Unsloth. "Fast Fine-Tuning Guide." 2024.
10. Ollama Documentation. "Ollama User Guide." 2024.
11. Alibaba. "Qwen2.5-Coder Technical Report." 2024.
12. Alibaba. "Qwen2.5-Math Technical Report." 2024.
13. IBM & Mistral. "Mistral Nemo Model Card." 2024.
14. Hugging Face. "SmolLM2 Technical Report." 2024.
15. 01.AI. "Yi 1.5 Technical Report." 2024.
16. Cohere. "Command R+ Technical Report." 2024.
17. NVIDIA. "Nemotron-4-34B Technical Report." 2024.
18. Upstage. "SOLAR 10.7B Technical Report." 2024.
19. DeepSeek. "DeepSeek-V2.5 Technical Report." 2024.
20. Meta. "Meditron Medical LLM Technical Report." 2023.
21. Stanford. "LLaMA-Med Technical Report." 2023.
22. Google. "BioMistral Technical Report." 2023.
23. FinGPT Team. "FinGPT: Open-Source Financial LLM." 2023.
24. MetaMath Team. "MetaMath: Bootstrapping Mathematical Reasoning." 2023.
25. Chroma Team. "Chroma Vector Database Documentation." 2024.
26. Qdrant Team. "Qdrant Vector Search Engine Documentation." 2024.
27. Facebook AI. "FAISS: Similarity Search Library." 2024.
28. LangChain Team. "LangChain Documentation." 2024.
29. LlamaIndex Team. "LlamaIndex Documentation." 2024.
30. CrewAI Team. "CrewAI Multi-Agent Framework." 2024.
