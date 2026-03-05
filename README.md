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

# Academic RAG — 学术文献检索增强生成系统

## 这个项目解决什么问题？

做学术研究，你的文献散落在各处：知网下载的 PDF、从 SSRN 拉的工作论文、微信公众号的行业分析、自己写的读书笔记。写论文时需要为某个论点找引用支持，你得翻遍 Zotero、本地文件夹、甚至微信收藏，效率极低。

Academic RAG 把你所有的学术资料（PDF、Word、Markdown、纯文本）统一索引到本地知识库，用**稀疏检索 + 稠密向量检索 + 倒数排名融合**（BM25 + Vector + RRF）实现高质量的混合检索。系统理解学术文档的章节结构，支持中英文混合语料，并可通过 Claude Code 用自然语言直接查询。

## 核心能力

| 能力 | 说明 |
|------|------|
| **多格式文档解析** | PDF（PyMuPDF 引擎）、DOCX、Markdown、TXT，自动识别中英文 |
| **学术结构感知分块** | 7 种文档类型策略：学术论文、学术专著、政策文件、演讲稿、精读笔记、阅读卡片、知识索引，按章节边界智能切分 |
| **三路混合检索** | BM25 稀疏检索（关键词匹配）+ 稠密向量检索（语义相似度）+ RRF 倒数排名融合（权重 0.3/0.7） |
| **三层渐进式上下文加载** | 索引层（~100 tokens，标题+关键词）→ 摘要层（~1k tokens，核心段落）→ 全文层（~20k tokens），按需加载，节省 token 开销 |
| **多源文本嵌入后端** | OpenAI text-embedding-3 / 通义千问 Qwen3-Embedding / DeepSeek / Ollama 本地部署 / sentence-transformers 离线模型，通过 `.env` 一行切换 |
| **Claude Code 集成** | 5 个 Skill 文件，复制到项目即可用自然语言检索知识库 |
| **命令行工具** | `academic-rag index` / `search` / `stats` / `build-vectors`，终端即用 |

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                        用户接口                           │
│   命令行 (academic-rag)  │  Python API  │  Claude Skills  │
├──────────────────────────────────────────────────────────┤
│              MultiSourceRetriever 混合检索引擎             │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ BM25       │  │  稠密向量检索   │  │  RRF           │  │
│  │ 稀疏检索   │  │  (ChromaDB)    │  │  倒数排名融合   │  │
│  │ (SQLite)   │  │                │  │  (0.3/0.7)     │  │
│  └────────────┘  └────────────────┘  └────────────────┘  │
├──────────────────────────────────────────────────────────┤
│              EmbeddingProvider 文本嵌入适配层               │
│   OpenAI 兼容 API（Qwen/DeepSeek/Ollama）                 │
│   sentence-transformers 本地推理                          │
├──────────────────────────────────────────────────────────┤
│  DocumentIndexer  │  AcademicChunker    │  PDFParser      │
│  SQLite 元数据存储 │  7 种学术分块策略    │  4 格式解析器    │
└──────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装

```bash
git clone https://github.com/git-zyyang/academic-rag.git
cd academic-rag
pip install -e ".[all]"
```

按需安装（减少依赖体积）：

```bash
pip install -e "."             # 仅核心（BM25 关键词检索，无需向量模型）
pip install -e ".[pdf]"        # + PDF 解析
pip install -e ".[vector]"     # + ChromaDB 向量检索
pip install -e ".[local]"      # + 本地 sentence-transformers 嵌入模型
```

### 2. 配置文本嵌入模型

```bash
cp .env.example .env
```

**方案 A：使用 API 服务**（推荐，开箱即用）

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_BASE=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-your-key
```

国内用户可直接接入通义千问、DeepSeek 等兼容 OpenAI 接口的服务：

```env
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=Qwen3-Embedding-8B
EMBEDDING_API_BASE=https://your-provider.com/v1
EMBEDDING_API_KEY=your-key
```

**方案 B：本地离线模型**（无需 API Key，适合网络受限环境）

```env
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

> 提示：即使不配置嵌入模型，BM25 关键词检索也可独立使用。

### 3. 索引文档

```bash
# 索引论文目录
academic-rag index ./my-papers/ --collection papers --doc-type paper

# 索引读书笔记
academic-rag index ./book-notes/ --collection books --doc-type book

# 构建向量索引（需先配置嵌入模型）
academic-rag build-vectors
```

### 4. 检索

```bash
# 混合检索（BM25 + 向量 + RRF 融合）
academic-rag search "碳排放权交易机制的减排效果" --top-k 10

# 指定上下文加载层级
academic-rag search "transformer attention mechanism" --layer detail

# 查看索引统计信息
academic-rag stats
```

## Python API

### 基本用法：索引与检索

```python
from rag import DocumentIndexer, search

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
```

### 高级用法：来源过滤与上下文层级

```python
from rag import MultiSourceRetriever

retriever = MultiSourceRetriever()
results = retriever.retrieve(
    "innovation policy",
    sources=["papers", "policies"],  # 仅检索指定集合
    top_k=10,
    context_layer="abstract"         # index | abstract | detail
)
retriever.close()
```

### 切换文本嵌入后端

```python
from rag.embeddings import EmbeddingFactory, set_provider

# 方案 1：通义千问（OpenAI 兼容接口）
provider = EmbeddingFactory.create(
    "openai",
    model="Qwen3-Embedding-8B",
    api_base="https://your-provider.com/v1",
    api_key="your-key"
)
set_provider(provider)

# 方案 2：本地 sentence-transformers（离线可用）
provider = EmbeddingFactory.create(
    "sentence-transformers",
    model="paraphrase-multilingual-MiniLM-L12-v2"
)
set_provider(provider)
```

## 典型使用场景

### 场景 1：写论文时为论点找引用支持

写到"远程办公提升了员工自主性，但可能削弱组织内部的知识溢出效应"，需要找文献支撑？

```python
from rag import MultiSourceRetriever

retriever = MultiSourceRetriever()
results = retriever.retrieve_for_citation(
    "Remote work increases employee autonomy but may reduce knowledge spillovers"
)
for r in results:
    print(f"  {r.citation_key}")    # 输出引用键，如 Author2023
    print(f"  {r.content[:200]}")   # 输出相关段落
```

### 场景 2：多维度构建文献综述

围绕一个研究主题，从不同理论视角检索，自动去重合并：

```python
from rag import search

queries = [
    "climate change adaptation strategies",       # 适应策略
    "carbon tax economic impact",                 # 碳税经济影响
    "green technology adoption barriers"          # 绿色技术采纳障碍
]
all_results = []
for q in queries:
    all_results.extend(search(q, top_k=5))

# 按文档 ID 去重
seen = set()
unique = [r for r in all_results if r.doc_id not in seen and not seen.add(r.doc_id)]
print(f"跨 {len(queries)} 个查询共检索到 {len(unique)} 篇不重复文献")
```

### 场景 3：将阅读笔记批量入库

把散落的 Markdown 读书笔记、文献摘录统一索引，后续写作时可直接检索调用：

```python
from rag import DocumentIndexer

indexer = DocumentIndexer()
results = indexer.index_collection("notes", "./reading-notes/")
print(f"已索引 {results['success']} 篇，跳过 {results['skipped']} 篇（已存在）")
indexer.close()
```

## Claude Code 集成

将 5 个 Skill 文件复制到你的 Claude Code 项目目录：

```bash
cp claude-integration/skills/*.md .claude/skills/
```

之后可直接用自然语言操作知识库：

```text
> 检索我的论文库，查找碳定价政策效果相关文献
> 为这个论点找引用支持："绿色补贴加速了清洁技术的采用"
> 精读这篇论文：./papers/example.pdf
> 处理我的阅读收件箱
```

| Skill | 触发词 | 功能 |
|-------|--------|------|
| `rag-search` | "检索""搜索""查找" | 本地知识库统一检索 |
| `literature-search` | "找文献""文献搜索" | 外部学术数据库 + 本地联合检索 |
| `academic-cite` | "找引用""引用支持" | 为论点定向检索引用文献 |
| `reading-inbox` | "处理收件箱" | 将待读文章转化为结构化笔记卡片 |
| `paper-deep-read` | "精读""深度分析" | 方法论导向的论文精读 |

详细配置见 [claude-integration/INTEGRATION.md](claude-integration/INTEGRATION.md)。

## 项目结构

```
academic-rag/
├── rag/                          # 核心库
│   ├── __init__.py               # 公共 API 导出
│   ├── config.py                 # 配置管理（环境变量 + 默认值）
│   ├── embeddings.py             # 多后端文本嵌入适配层
│   ├── pdf_parser.py             # 多格式文档解析器
│   ├── chunker.py                # 学术结构感知分块器
│   ├── indexer.py                # SQLite 索引管线
│   ├── retriever.py              # 混合检索引擎（BM25 + Vector + RRF）
│   ├── reranker.py               # 交叉编码器精排 / 轻量重排序
│   └── cli.py                    # 命令行入口
├── scripts/                      # 工具脚本
│   └── build_vector_index.py     # 向量索引批量构建
├── claude-integration/           # Claude Code 集成方案
│   ├── skills/                   # 5 个 Skill 文件
│   ├── rules/                    # 行为规则
│   └── INTEGRATION.md            # 集成指南
├── examples/                     # 使用示例
│   ├── quickstart.py             # 快速开始
│   └── advanced_usage.py         # 高级用法
├── pyproject.toml                # 项目配置
├── .env.example                  # 环境变量模板
└── LICENSE                       # MIT 许可证
```

## 环境要求

- Python 3.10+
- 核心依赖：`openai`（API 文本嵌入调用）
- PDF 解析：`pymupdf`（可选）
- DOCX 解析：`python-docx`（可选）
- 向量检索：`chromadb`（可选，不安装时仅使用 BM25 关键词检索）
- 本地嵌入：`sentence-transformers`（可选，离线环境推荐）

## 参与贡献

欢迎提交 Issue 和 Pull Request。

## 支持项目

如果觉得有帮助，请给项目点个 Star。

<a href="assets/donate_alipay.jpg"><img src="assets/donate_alipay.jpg" width="200" alt="支付宝赞赏"></a>

## 许可证

MIT 许可证。详见 [LICENSE](LICENSE)。
