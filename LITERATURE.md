# Literature Survey — LogMind

This document covers the key academic and industry references underpinning LogMind's architecture, satisfying the assignment rubric requirement.

---

## 1. Agentic Workflows / ReAct

**ReAct: Synergizing Reasoning and Acting in Language Models**  
Yao et al., ICLR 2023  
[https://arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)

> Introduces the ReAct pattern — interleaving reasoning traces and actions in LLMs. LogMind's Orchestrator Agent follows this paradigm via Google ADK's `LlmAgent`.

---

## 2. Retrieval-Augmented Generation (RAG)

**Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**  
Lewis et al., NeurIPS 2020  
[https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)

> Foundational RAG paper. LogMind extends vanilla RAG with a knowledge graph layer (Graph RAG).

---

## 3. Graph RAG

**From Local to Global: A Graph RAG Approach to Query-Focused Summarization**  
Edge et al., Microsoft Research 2024  
[https://arxiv.org/abs/2404.16130](https://arxiv.org/abs/2404.16130)

> Demonstrates that combining vector retrieval with graph traversal yields richer, more coherent answers than pure vector search — directly motivating LogMind's NetworkX + Pinecone dual retrieval.

---

## 4. Multi-Modal Models

**Gemini: A Family of Highly Capable Multimodal Models**  
Anil et al., Google DeepMind 2023  
[https://arxiv.org/abs/2312.11805](https://arxiv.org/abs/2312.11805)

> Underpins the image analysis pipeline — Gemini Vision is used to extract structured anomaly descriptions from dashboard screenshots.

---

## 5. Model Context Protocol (MCP)

**Model Context Protocol (MCP) — Anthropic, 2024**  
[https://modelcontextprotocol.io](https://modelcontextprotocol.io)

> Open standard for connecting AI systems to external tools and data sources. Relevant to LogMind's tool-based agent architecture and discussed in the presentation's literature section.

---

## 6. Log Anomaly Detection

**LogBERT: Log Anomaly Detection via BERT**  
Guo et al., 2021  
[https://arxiv.org/abs/2103.04475](https://arxiv.org/abs/2103.04475)

> Prior work on AI-driven log analysis. LogMind advances this by adding multi-modal correlation and graph-based reasoning rather than anomaly classification alone.
