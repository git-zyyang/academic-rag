# Claude Code Integration Guide

## Overview

Academic RAG integrates with [Claude Code](https://claude.ai/claude-code) through 5 Skills that provide natural language access to the RAG system's retrieval capabilities.

## Installation

1. Copy the Skills to your Claude Code skills directory:

```bash
cp claude-integration/skills/*.md ~/.claude/skills/
# or for project-level:
cp claude-integration/skills/*.md .claude/skills/
```

2. Ensure the RAG system is installed and indexed:

```bash
pip install -e .
academic-rag index ./papers/ --collection papers
academic-rag build-vectors
```

## Available Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `rag-search` | "search", "find papers", "look up" | Unified local retrieval interface |
| `literature-search` | "find papers", "literature search" | External + local literature discovery |
| `academic-cite` | "/cite", "find citations" | Citation search and formatting |
| `reading-inbox` | "process inbox" | Transform articles into knowledge cards |
| `paper-deep-read` | "deep read", "analyze paper" | Methodology-focused paper analysis |

## Example Usage in Claude Code

```
> Search my collection for papers about digital economy and innovation

> Find citation support for: "AI empowers productivity through three pathways"

> Process this article: https://example.com/article

> Deep read this paper: ./papers/example_paper.pdf
```

## Rules

Copy the rules files for additional behavior:

```bash
cp claude-integration/rules/*.md .claude/rules/
```

The `literature-notes.md` rule ensures consistent formatting for reading notes generated within your project.
