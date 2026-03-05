[English](#academic-rag) | [中文](#academic-rag-学术文献智能检索系统)

---

# Academic RAG

**Academic literature retrieval system with hybrid search (BM25 + Vector + RRF), smart chunking, and Claude Code integration.**

Built for researchers who need a local knowledge base that actually understands academic document structure — section-aware chunking, three-layer progressive loading, and multi-format parsing (PDF/DOCX/Markdown/TXT) with automatic Chinese/English detection.

## Features

- **Multi-format parsing** — PDF (PyMuPDF), DOCX (python-docx), Markdown, TXT with CN/EN auto-detection
- **Structure-aware chunking** — 7 document type strategies (paper, book, policy, speech, deep-read, reading card, knowledge index)
- **Hybrid search** — BM25 keyword + semantic vector + Reciprocal Rank Fusion (0.3/0.7 weights)
- **Three-layer progressive loading** — Index (100 tokens) → Abstract (1k tokens) → Detail (20k tokens)
- **Multi-backend embeddings** — OpenAI / Qwen / DeepSeek / Ollama / local sentence-transformers
- **Claude Code integration** — 5 Skills for natural language access to your knowledge base
- **CLI tool** — Index, search, and manage from the command line

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
│  CLI (academic-rag)  │  Python API  │  Claude Skills │
├─────────────────────────────────────────────────────┤
│                MultiSourceRetriever                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Keyword  │  │    Vector    │  │     RRF       │  │
│  │ (SQLite) │  │  (ChromaDB)  │  │   Fusion      │  │
│  └──────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────┤
│                  EmbeddingProvider                    │
│  OpenAI-compatible API  │  sentence-transformers     │
├─────────────────────────────────────────────────────┤
│  DocumentIndexer  │  AcademicChunker  │  PDFParser   │
│  (SQLite metadata)│  (7 strategies)   │  (4 formats) │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Install

```bash
git clone https://github.com/git-zyyang/academic-rag.git
cd academic-rag
pip install -e ".[all]"
```

### Configure Embeddings

```bash
cp .env.example .env
# Edit .env with your API key:
#   EMBEDDING_PROVIDER=openai
#   EMBEDDING_MODEL=text-embedding-3-small
#   EMBEDDING_API_KEY=sk-your-key
```

Or use local embeddings (no API key needed):
```bash
# In .env:
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Index Your Documents

```bash
# Index a directory of papers
academic-rag index ./my-papers/ --collection papers --doc-type paper

# Index book notes
academic-rag index ./book-notes/ --collection books --doc-type book

# Build vector index (requires embedding provider)
academic-rag build-vectors
```

### Search

```bash
# Keyword + vector hybrid search
academic-rag search "renewable energy policy effectiveness" --top-k 10

# Search with detail level
academic-rag search "transformer attention" --layer detail

# View index statistics
academic-rag stats
```

## Python API

```python
from rag import DocumentIndexer, MultiSourceRetriever, search

# Index documents
indexer = DocumentIndexer()
indexer.index_document("paper.pdf", collection="papers", doc_type="paper")
indexer.index_collection("papers", "./papers/")
print(indexer.get_stats())
indexer.close()

# Search
results = search("climate policy carbon pricing", top_k=5)
for r in results:
    print(f"[{r.score:.3f}] {r.title} ({r.year})")
    print(f"  {r.content[:100]}...")

# Advanced: custom retriever with source filtering
retriever = MultiSourceRetriever()
results = retriever.retrieve(
    "innovation policy",
    sources=["papers", "policies"],
    top_k=10,
    context_layer="abstract"  # index | abstract | detail
)
retriever.close()
```

### Custom Embedding Provider

```python
from rag.embeddings import EmbeddingFactory, set_provider

# Use Qwen via compatible API
provider = EmbeddingFactory.create(
    "openai",
    model="Qwen3-Embedding-8B",
    api_base="https://your-api-provider.com/v1",
    api_key="your-key"
)
set_provider(provider)

# Or use local sentence-transformers
provider = EmbeddingFactory.create(
    "sentence-transformers",
    model="paraphrase-multilingual-MiniLM-L12-v2"
)
set_provider(provider)
```

## Use Cases

### 1. Finding Citations for a Claim

```python
from rag import MultiSourceRetriever

retriever = MultiSourceRetriever()
results = retriever.retrieve_for_citation(
    "Remote work increases employee autonomy but may reduce knowledge spillovers"
)
for r in results:
    print(f"  {r.citation_key}")
    print(f"  {r.content[:200]}")
```

### 2. Building a Literature Review

```python
from rag import search

# Search from multiple angles
queries = [
    "climate change adaptation strategies",
    "carbon tax economic impact",
    "green technology adoption barriers"
]
all_results = []
for q in queries:
    all_results.extend(search(q, top_k=5))

# Deduplicate by doc_id
seen = set()
unique = [r for r in all_results if r.doc_id not in seen and not seen.add(r.doc_id)]
print(f"Found {len(unique)} unique papers across 3 queries")
```

### 3. Processing Reading Notes into RAG

```python
from rag import DocumentIndexer

indexer = DocumentIndexer()
# Index all markdown reading notes
results = indexer.index_collection("notes", "./reading-notes/")
print(f"Indexed {results['success']} notes, {results['skipped']} already existed")
indexer.close()
```

## Claude Code Integration

Copy the 5 Skills to your Claude Code project:

```bash
cp claude-integration/skills/*.md .claude/skills/
```

Then in Claude Code:
```text
> Search my papers for climate policy and carbon pricing
> Find citation support for: "Green subsidies accelerate clean technology adoption"
> Deep read this paper: ./papers/example.pdf
> Process my reading inbox
```

See [claude-integration/INTEGRATION.md](claude-integration/INTEGRATION.md) for detailed setup.

## Project Structure

```
academic-rag/
├── rag/                          # Core library
│   ├── __init__.py               # Public API
│   ├── config.py                 # Configuration
│   ├── embeddings.py             # Multi-backend embedding providers
│   ├── pdf_parser.py             # Document parsing (PDF/DOCX/MD/TXT)
│   ├── chunker.py                # Structure-aware chunking
│   ├── indexer.py                # SQLite indexing pipeline
│   ├── retriever.py              # Hybrid search (BM25 + Vector + RRF)
│   ├── reranker.py               # Cross-encoder reranking
│   └── cli.py                    # CLI entry point
├── scripts/                      # Utility scripts
│   └── build_vector_index.py     # Vector index builder
├── claude-integration/           # Claude Code integration
│   ├── skills/                   # 5 Claude Code Skills
│   ├── rules/                    # Behavior rules
│   └── INTEGRATION.md            # Setup guide
├── pyproject.toml                # Python project config
├── .env.example                  # Environment template
└── LICENSE                       # MIT
```

## Requirements

- Python 3.10+
- Core: `openai` (for API-based embeddings)
- PDF parsing: `pymupdf` (optional)
- DOCX parsing: `python-docx` (optional)
- Vector search: `chromadb` (optional — keyword search works without it)
- Local embeddings: `sentence-transformers` (optional)

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

If you find this useful, consider starring the repo.

<a href="assets/donate_alipay.jpg"><img src="assets/donate_alipay.jpg" width="200" alt="Support via Alipay"></a>

## License

MIT License. See [LICENSE](LICENSE).

---

# Academic RAG — 学术文献智能检索系统

**基于混合检索（BM25 + 向量 + RRF 融合）、智能分块和 Claude Code 集成的学术文献检索系统。**

专为学术研究者打造的本地知识库系统。真正理解学术文档结构 — 章节感知分块、三层渐进加载、多格式解析（PDF/DOCX/Markdown/TXT），自动识别中英文。

## 功能特性

- **多格式文档解析** — PDF (PyMuPDF)、DOCX (python-docx)、Markdown、TXT，中英文自动识别
- **结构感知分块** — 7 种文档类型策略（论文、专著、政策文件、演讲稿、精读笔记、阅读卡片、知识索引）
- **混合检索** — BM25 关键词 + 语义向量 + 互惠排名融合 RRF（0.3/0.7 权重）
- **三层渐进加载** — 索引层（100 tokens）→ 摘要层（1k tokens）→ 全文层（20k tokens）
- **多后端嵌入** — OpenAI / Qwen / DeepSeek / Ollama / 本地 sentence-transformers
- **Claude Code 集成** — 5 个 Skill，用自然语言访问你的知识库
- **命令行工具** — 索引、检索、管理，一行命令搞定

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                     用户界面                         │
│  CLI (academic-rag)  │  Python API  │  Claude Skills │
├─────────────────────────────────────────────────────┤
│                MultiSourceRetriever                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ 关键词   │  │    向量      │  │     RRF       │  │
│  │ (SQLite) │  │  (ChromaDB)  │  │   融合排序     │  │
│  └──────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────┤
│                  EmbeddingProvider                    │
│  OpenAI 兼容 API      │  sentence-transformers       │
├─────────────────────────────────────────────────────┤
│  DocumentIndexer  │  AcademicChunker  │  PDFParser   │
│  (SQLite 元数据)  │  (7 种策略)       │  (4 种格式)  │
└─────────────────────────────────────────────────────┘
```

## 快速开始

### 安装

```bash
git clone https://github.com/git-zyyang/academic-rag.git
cd academic-rag
pip install -e ".[all]"
```

### 配置嵌入模型

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key：
#   EMBEDDING_PROVIDER=openai
#   EMBEDDING_MODEL=text-embedding-3-small
#   EMBEDDING_API_KEY=sk-your-key
```

或使用本地嵌入模型（无需 API Key）：
```bash
# 在 .env 中：
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 索引文档

```bash
# 索引一个论文目录
academic-rag index ./my-papers/ --collection papers --doc-type paper

# 索引读书笔记
academic-rag index ./book-notes/ --collection books --doc-type book

# 构建向量索引（需要嵌入模型）
academic-rag build-vectors
```

### 检索

```bash
# 关键词 + 向量混合检索
academic-rag search "renewable energy policy effectiveness" --top-k 10

# 指定加载层级
academic-rag search "transformer attention" --layer detail

# 查看索引统计
academic-rag stats
```

## Python API

```python
from rag import DocumentIndexer, MultiSourceRetriever, search

# 索引文档
indexer = DocumentIndexer()
indexer.index_document("paper.pdf", collection="papers", doc_type="paper")
indexer.index_collection("papers", "./papers/")
print(indexer.get_stats())
indexer.close()

# 检索
results = search("climate policy carbon pricing", top_k=5)
for r in results:
    print(f"[{r.score:.3f}] {r.title} ({r.year})")
    print(f"  {r.content[:100]}...")

# 高级用法：自定义检索器 + 来源过滤
retriever = MultiSourceRetriever()
results = retriever.retrieve(
    "innovation policy",
    sources=["papers", "policies"],
    top_k=10,
    context_layer="abstract"  # index | abstract | detail
)
retriever.close()
```

### 自定义嵌入模型

```python
from rag.embeddings import EmbeddingFactory, set_provider

# 通过兼容 API 使用 Qwen
provider = EmbeddingFactory.create(
    "openai",
    model="Qwen3-Embedding-8B",
    api_base="https://your-api-provider.com/v1",
    api_key="your-key"
)
set_provider(provider)

# 或使用本地 sentence-transformers
provider = EmbeddingFactory.create(
    "sentence-transformers",
    model="paraphrase-multilingual-MiniLM-L12-v2"
)
set_provider(provider)
```

## 使用场景

### 1. 为论点寻找引用支持

```python
from rag import MultiSourceRetriever

retriever = MultiSourceRetriever()
results = retriever.retrieve_for_citation(
    "Remote work increases employee autonomy but may reduce knowledge spillovers"
)
for r in results:
    print(f"  {r.citation_key}")
    print(f"  {r.content[:200]}")
```

### 2. 构建文献综述

```python
from rag import search

# 从多个角度检索
queries = [
    "climate change adaptation strategies",
    "carbon tax economic impact",
    "green technology adoption barriers"
]
all_results = []
for q in queries:
    all_results.extend(search(q, top_k=5))

# 按文档 ID 去重
seen = set()
unique = [r for r in all_results if r.doc_id not in seen and not seen.add(r.doc_id)]
print(f"跨 3 个查询共找到 {len(unique)} 篇不重复文献")
```

### 3. 将阅读笔记导入 RAG

```python
from rag import DocumentIndexer

indexer = DocumentIndexer()
# 索引所有 Markdown 阅读笔记
results = indexer.index_collection("notes", "./reading-notes/")
print(f"已索引 {results['success']} 篇笔记，{results['skipped']} 篇已存在")
indexer.close()
```

## Claude Code 集成

将 5 个 Skill 复制到你的 Claude Code 项目中：

```bash
cp claude-integration/skills/*.md .claude/skills/
```

然后在 Claude Code 中直接用自然语言操作：
```text
> 搜索我的论文库，查找气候政策与碳定价相关文献
> 为这个观点找引用支持："绿色补贴加速了清洁技术的采用"
> 精读这篇论文：./papers/example.pdf
> 处理我的阅读收件箱
```

详细设置请参阅 [claude-integration/INTEGRATION.md](claude-integration/INTEGRATION.md)。

## 项目结构

```
academic-rag/
├── rag/                          # 核心库
│   ├── __init__.py               # 公共 API
│   ├── config.py                 # 配置管理
│   ├── embeddings.py             # 多后端嵌入适配器
│   ├── pdf_parser.py             # 文档解析（PDF/DOCX/MD/TXT）
│   ├── chunker.py                # 结构感知分块
│   ├── indexer.py                # SQLite 索引管线
│   ├── retriever.py              # 混合检索（BM25 + 向量 + RRF）
│   ├── reranker.py               # 交叉编码器重排序
│   └── cli.py                    # 命令行入口
├── scripts/                      # 工具脚本
│   └── build_vector_index.py     # 向量索引构建器
├── claude-integration/           # Claude Code 集成
│   ├── skills/                   # 5 个 Claude Code Skill
│   ├── rules/                    # 行为规则
│   └── INTEGRATION.md            # 集成指南
├── pyproject.toml                # Python 项目配置
├── .env.example                  # 环境变量模板
└── LICENSE                       # MIT 许可证
```

## 环境要求

- Python 3.10+
- 核心依赖：`openai`（用于 API 嵌入）
- PDF 解析：`pymupdf`（可选）
- DOCX 解析：`python-docx`（可选）
- 向量检索：`chromadb`（可选 — 不安装也可使用关键词检索）
- 本地嵌入：`sentence-transformers`（可选）

## 参与贡献

欢迎提交 Issue 和 PR！

## 支持项目

如果觉得有用，请给项目点个 Star。

<a href="assets/donate_alipay.jpg"><img src="assets/donate_alipay.jpg" width="200" alt="支付宝赞赏"></a>

## 许可证

MIT 许可证。详见 [LICENSE](LICENSE)。
