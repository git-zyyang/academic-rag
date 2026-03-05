---
name: academic-cite
description: Academic citation system — smart search, citation formatting, and comparative material recommendation.
---

# Academic Citation System

## Overview

RAG-powered academic citation assistant. Search multiple knowledge sources for citation material, auto-generate properly formatted citations, and provide comparative material recommendations.

## Core Functions

### 1. Smart Citation Search
```
/cite "search keywords"
```
Search all indexed sources for relevant citations.

### 2. Paper Writing Assistant
```
/cite-paper "paper topic" --section="section name"
```
Recommend citations based on paper topic and section.

### 3. Material Import
```
/cite-import [type]
```
Import new materials. Types: book, paper, article, report.

### 4. Outline-Based Recommendations
```
/cite-outline "outline text"
```
Auto-recommend citations for each section of an outline.

### 5. Statistics
```
/cite-stats
```
Show knowledge base statistics.

## Citation Formats Supported

- APA 7th Edition (English papers)
- GB/T 7714 (Chinese papers)
- BibTeX export

## Technical Architecture

```
User Query → RAG MultiSourceRetriever
              ├─ Keyword Search (SQLite LIKE)
              ├─ Vector Search (ChromaDB + Embedding)
              └─ Hybrid Ranking (RRF Fusion)
                    ↓
              Citation Format Generator
              ├─ APA 7th (default for English)
              ├─ GB/T 7714 (default for Chinese)
              └─ BibTeX
```

## Dependencies

RAG core modules (`rag/` directory):
- `rag/retriever.py` — Multi-source retrieval
- `rag/indexer.py` — Document indexing
- `rag/stores/metadata.db` — Metadata database
