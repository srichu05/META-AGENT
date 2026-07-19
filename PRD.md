# Product Requirements Document (PRD)
## Meta-Agent Math Debate System (Draft 2)

### Project Overview
The Meta-Agent Math Debate System is a Flask-based AI backend that solves mathematical problems using a multi-agent debate workflow. Unlike the previous implementation, the system is no longer limited to GSM8K or predefined datasets. It should support user-uploaded mathematical documents and notes, retrieve relevant context through RAG, and generate accurate, explainable solutions using multiple collaborating AI agents.

---

## Current Project Status

The existing backend already contains:

- Flask REST backend
- Multi-agent prototype (Solver, Retriever, Judge)
- Basic RAG implementation
- Custom vector store
- API client supporting multiple LLM providers
- Logging and configuration modules

This codebase serves as the foundation but **will be refactored**, not extended directly.

---

## Draft 2 Objectives

The new backend should evolve into a modular, production-oriented AI system with:

- Cloud LLM providers only (no local LLMs)
- Personalized RAG over user-uploaded math documents
- Multi-agent orchestration using LangGraph
- Scalable provider routing
- Hybrid retrieval pipeline
- Explainable and verifiable reasoning

---

# Backend Tech Stack

### Framework
- Flask

### Database
- PostgreSQL

### Vector Search
- FAISS

### Embeddings
- BAAI BGE Embeddings

### LLM Providers
- Gemini
- Groq
- Cohere

### AI Frameworks
- LangChain
- LangGraph

### Retrieval
- BM25
- Cohere Rerank

### Evaluation
- RAGAS

---

# Planned Backend Improvements

The previous prototype will be upgraded with:

- OCR support for handwritten mathematical notes
- Image document processing
- Improved semantic chunking
- Rich metadata extraction
- Better retrieval pipeline
- Enhanced Judge Agent
- Reflection Agent
- Planner Agent
- Context Manager
- Provider Router
- Citation Generator

---

# RAG Requirements

The RAG system should:

- Accept user-uploaded PDFs
- Accept DOCX files
- Accept TXT files
- Accept Markdown
- Accept images of handwritten notes
- Build a personalized knowledge base
- Retrieve only relevant mathematical context
- Support hybrid retrieval (Vector + Keyword)
- Produce citations for retrieved context

The system should **not** rely on GSM8K as the primary knowledge source.

---

# Agent Workflow

Planner Agent

↓

Retriever

↓

Solver Agent A

↓

Solver Agent B

↓

Solver Agent C

↓

Reflection Agent

↓

Judge Agent

↓

Citation Generator

↓

Final Response

---

# Scalability Goals

The architecture should remain modular.

Major components should be replaceable without affecting the overall system.

Examples:

- LLM provider can be swapped.
- Vector database can be replaced.
- Retrieval pipeline can evolve.
- Additional agents can be introduced.

---

# Development Constraints

- Preserve modular architecture.
- Keep agents loosely coupled.
- Separate retrieval, orchestration, providers, and storage.
- Use PostgreSQL for relational data.
- Use FAISS only for vector similarity search.
- Do not use local LLMs.
- Prioritize readability and scalability over quick implementations.

---

# Out of Scope

- Frontend development
- Authentication
- Deployment
- Monitoring
- CI/CD

These will be implemented later.

---

# Immediate Goal

Incrementally migrate the current prototype into the Draft 2 architecture while preserving working functionality and minimizing breaking changes.