# Technical Summary – Meta-Agent Math Debate System (Draft 2)

---

# Project Overview

The Meta-Agent Math Debate System is a Flask-based backend that solves mathematical problems through a multi-agent debate workflow supported by Retrieval-Augmented Generation (RAG).

Unlike the previous prototype, Draft 2 is designed as a modular, scalable architecture capable of reasoning over user-uploaded mathematical documents rather than relying on fixed datasets such as GSM8K.

The system emphasizes explainability, modularity, scalability, and production-ready design.

---

# Backend Objectives

- Modular multi-agent architecture
- Personalized RAG over uploaded documents
- Cloud LLM providers only
- Hybrid retrieval pipeline
- Explainable reasoning
- Scalable provider routing
- Production-ready backend

---

# Backend Technology Stack

## Backend Framework

- Flask

## Database

- PostgreSQL

## Vector Search

- FAISS

## Embeddings

- BAAI BGE Embeddings

## AI Frameworks

- LangChain
- LangGraph

## Retrieval

- BM25
- Cohere Rerank

## Evaluation

- RAGAS

## Cloud Providers

- Gemini
- Groq
- Cohere

---

# Core Backend Components

## API Layer

Responsible for:

- REST API endpoints
- Request validation
- Response formatting
- Communication with frontend

---

## Provider Router

Central routing layer responsible for:

- Selecting LLM provider
- Provider fallback
- Rate-limit handling
- Future scalability

Supported providers:

- Gemini
- Groq
- Cohere

---

## Planner Agent

Responsible for:

- Understanding user intent
- Planning reasoning workflow
- Selecting retrieval strategy
- Preparing execution flow

---

## RAG Pipeline

Responsible for:

- Document ingestion
- OCR processing
- Chunk generation
- Metadata extraction
- Embedding generation
- Hybrid retrieval
- Context construction

Supported uploads:

- PDF
- DOCX
- TXT
- Markdown
- Images
- Handwritten mathematical notes

---

## Context Manager

Responsible for:

- Maintaining retrieved context
- Organizing retrieved chunks
- Preventing duplicated context
- Preparing context for solver agents

---

## Solver Agents

Multiple reasoning agents independently solve the same mathematical problem using retrieved context.

Each solver provides:

- Step-by-step reasoning
- Intermediate calculations
- Confidence estimation

---

## Reflection Agent

Responsible for:

- Reviewing solver outputs
- Detecting inconsistencies
- Correcting reasoning errors
- Improving final answer quality

---

## Judge Agent

Responsible for:

- Comparing solver outputs
- Evaluating reasoning quality
- Selecting the best solution
- Producing final explanation

---

## Citation Generator

Responsible for:

- Mapping generated answers to retrieved chunks
- Producing source citations
- Improving answer transparency

---

# Retrieval Pipeline

The retrieval system combines:

- Semantic Search (FAISS)
- Keyword Search (BM25)
- Cohere Rerank

This hybrid approach improves retrieval accuracy over pure vector search.

---

# Database Responsibilities

## PostgreSQL

Stores:

- User information
- Uploaded documents
- Chunk metadata
- Debate history
- Retrieval history
- Provider logs
- Evaluation results
- Citation metadata

---

## FAISS

Stores:

- Vector embeddings

Only similarity search is performed inside FAISS.

Metadata remains inside PostgreSQL.

---

# Document Processing Pipeline

Document Upload

↓

Document Parser

↓

OCR (if required)

↓

Text Cleaning

↓

Semantic Chunking

↓

Metadata Extraction

↓

Embedding Generation

↓

FAISS Index

↓

Metadata Storage (PostgreSQL)

---

# Debate Workflow

User Query

↓

Planner Agent

↓

Retriever

↓

Hybrid Search

↓

Context Manager

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

# Design Principles

The backend follows the following principles:

- Modular architecture
- Loose coupling
- Separation of responsibilities
- Scalable provider integration
- Replaceable components
- Maintainable codebase
- Explainable AI workflow

---

# Scalability

The architecture allows independent replacement of:

- LLM providers
- Embedding models
- Retrieval algorithms
- Vector databases
- Evaluation framework
- Debate workflow

without requiring major backend redesign.

---

# Future Expansion

The architecture is designed to support future additions including:

- Authentication
- User profiles
- Conversation history
- Agent memory
- Streaming responses
- Deployment on cloud infrastructure
- Monitoring
- Analytics
- Additional reasoning agents

---

# Current Development Status

Draft 2 represents a complete architectural redesign of the original prototype.

The existing backend serves as the implementation foundation, while major components will be progressively refactored into the modular Draft 2 architecture through phase-wise development.