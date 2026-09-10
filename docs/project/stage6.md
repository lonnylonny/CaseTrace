# Stage 6 — Implementation & Evaluation

## 阶段目标

在 Stage 1–5 已冻结的问题、任务、数据与技术架构上，完成 CaseTrace V1 的实际实现、验证与工程化收束。

Stage 6 的核心目标不是继续扩展功能，而是：

- 把既定架构真正实现为可运行系统；
- 用可信 Benchmark 验证核心 AI Task；
- 通过 Baseline、Ablation 和 Error Analysis 证明各组件是否有效；
- 建立必要的软件工程质量；
- 形成适合 AI / Software Engineering 求职展示的完整项目。

项目继续保持：

> **AI / ML Engineering + Backend / Data / System + Web Application 的综合学习路线。**

整体学习重心约为：

```text
AI / ML Engineering        ≈ 45%
Backend / Data / System    ≈ 35%
Frontend / Deployment      ≈ 20%
```

半导体封装继续作为 Case Study，不进一步扩大领域复杂度。

---

# Stage 6 总体结构

```text
6.1 Implementation Strategy
        ↓
6.2 Data & Benchmark Implementation
        ↓
6.3 Retrieval Baselines
        ↓
6.4 Hybrid Retrieval & Reranking
        ↓
6.5 C / D Extraction
        ↓
6.6 Application Integration
        ↓
6.7 Evaluation & Experiments
        ↓
6.8 Error Analysis
        ↓
6.9 Testing / CI / Deployment
        ↓
6.10 Final Acceptance
```

---

# 6.1 — Implementation Strategy

## 6.1.1 技术栈主线

V1 采用：

```text
Frontend
React + TypeScript
        ↓
REST API
        ↓
Python Backend
        ↓
AI / Application Pipeline
        ↓
PostgreSQL + Search Engine
```

Search Infrastructure 采用：

```text
PostgreSQL
→ Canonical / Relational Source of Truth

Elasticsearch / OpenSearch
→ BM25
→ Vector Search
→ Metadata Search
→ Hybrid Retrieval
```

AI Components 采用 Hybrid Model Strategy：

```text
Embedding Model
→ Local / Open-source

Reranker
→ Local / Open-source

Generative LLM
→ API
```

目的：

- 学习真实 Search Engine；
- 学习本地 Transformer inference；
- 学习 Embedding / Cross-Encoder / Reranking；
- 保留 Generative LLM 的开发效率；
- 避免把项目扩大成 GPU Serving 项目。

具体模型与 Provider 在实际实现时根据效果、资源和成本选择。

---

## 6.1.2 开发原则

采用纵向迭代，而不是一次性把所有模块分别写完。

优先顺序：

```text
最小可运行数据
      ↓
最简单 Retrieval Baseline
      ↓
Evaluation Pipeline
      ↓
Hybrid Retrieval
      ↓
Reranker
      ↓
C / D Extraction
      ↓
Backend API
      ↓
Frontend
      ↓
Testing / Deployment
```

核心原则：

> **Evaluation Pipeline 尽早建立，不能等系统全部完成后才开始评估。**

---

## 6.1.3 Repository 保持模块化

代码结构需要清晰分离：

```text
data / dataset
retrieval
extraction
models
database
search
backend / api
frontend
evaluation
tests
scripts / tooling
```

具体目录名称不在本阶段冻结。

---

# 6.2 — Data & Benchmark Implementation

根据 Stage 4 的设计真正实现 Synthetic Dataset。

---

## 6.2.1 Dataset Generation Pipeline

实现：

```text
Environment Config
      ↓
Scenario / Case Family
      ↓
Canonical Case
      ↓
Programmatic Construction
      ↓
LLM Text Realization
      ↓
Validation
      ↓
Historical Corpus
+
Current Incident Queries
+
Ground Truth
```

核心事实、Case Relationship 和 Ground Truth 仍由 Scenario / Programmatic Logic 决定。

LLM 主要负责自然语言表现。

---

## 6.2.2 Dataset 必须具备

至少覆盖：

- Repeat / Recurrence；
- Incident / Context Linkage；
- Technical Analog；
- Easy / Hard Positive；
- Easy / Hard Negative；
- Ambiguous；
- Missing Information；
- Terminology / Wording Variation。

Failure Mode ↔ Cause 继续保持 many-to-many。

---

## 6.2.3 Development / Locked Test

实际建立：

```text
Development Dataset
+
Locked Test Benchmark
```

Split 采用：

> **Case-family / Scenario-aware Group Split**

防止同一 Scenario Family 跨 Development / Test。

Locked Test 在最终评估前不持续参与调参。

---

## 6.2.4 数据检查

实现自动或半自动检查：

- consistency；
- point-in-time leakage；
- group leakage；
- shortcut / dataset artifact；
- missing required information；
- cross-representation conflict。

最终保留 Dataset Version 和简洁 Dataset Card。

---

# 6.3 — Retrieval Baselines

B — Relevant Historical Case Retrieval 是 Stage 6 的主要实验对象。

必须先建立简单 Baseline，不能只展示最终系统。

---

## 6.3.1 Baseline 体系

至少实现：

### Baseline 1 — Lexical

```text
BM25
```

作为传统 Information Retrieval 基线。

### Baseline 2 — Semantic

```text
Embedding
+
Vector Search
```

用于验证 Semantic Retrieval 的独立效果。

### Baseline 3 — Hybrid

```text
BM25
+
Vector Search
+
Candidate Fusion
```

用于判断 Lexical + Semantic 是否具有互补性。

### Final Retrieval Pipeline

```text
Hybrid Candidate Retrieval
+
Metadata Signals
+
Reranker
```

---

## 6.3.2 Metadata

Product、Failure Mode、Equipment、Process Context、Time / Lot 等 Structured Metadata 可以用于：

- filtering；
- boosting；
- ranking signal。

但不能采用过度严格的硬过滤，从而误删 Technical Analog。

---

# 6.4 — Hybrid Retrieval & Reranking

## 6.4.1 Candidate Retrieval

Search Engine 同时承担：

```text
BM25 Search
+
Vector Search
+
Metadata Search
```

产生高 Recall Candidate Set。

Candidate Fusion 的具体方法通过 Development Set 实验决定，不预设复杂算法。

---

## 6.4.2 Reranker

对 Candidate Set 使用本地 Open-source Reranker / Cross-Encoder：

```text
Current Incident
×
Historical Case
      ↓
Reranker
      ↓
Final Ranking
```

主要学习：

- pairwise semantic relevance；
- Cross-Encoder inference；
- batching；
- latency / accuracy trade-off。

不进行 Reranker Fine-tuning。

---

## 6.4.3 Relevance Type / Rationale

Ranking 后再生成：

```text
Relevance Type
+
Grounded Rationale
```

仍然保持：

- Ranking；
- Relevance Classification；
- Explanation；

三个职责逻辑分离。

---

# 6.5 — C / D Extraction

C / D 采用：

```text
Source Text
      ↓
API LLM
      ↓
Structured Output
      ↓
Schema Validation
      ↓
Source Grounding
      ↓
Normalization
      ↓
Aggregation
```

---

## 6.5.1 C — Cause Extraction

提取：

- Cause；
- Root Cause；
- Contributing Cause；
- Source Case；
- Source Evidence。

只提取历史 Source 中明确记录的信息。

---

## 6.5.2 D — Checkpoint Extraction

提取并建立：

```text
Cause
↕
Checkpoint
↕
Observed Result
↕
Source Evidence
```

Checkpoint 与 Observed Result 必须分开。

---

## 6.5.3 Extraction Engineering

必须包含：

- structured output；
- schema validation；
- abstention；
- retry / failure handling；
- prompt versioning；
- source traceability；
- batch processing。

Normalization 保持轻量，不建立复杂 Ontology。

---

# 6.6 — Application Integration

## 6.6.1 Backend

使用 Python REST Backend，将以下模块统一接入：

```text
Incident Processing
Retrieval
Reranking
Extraction
Database
Search Engine
Model Layer
Evaluation Interface
Logging
```

继续采用 Modular Monolith。

---

## 6.6.2 Frontend

使用：

```text
React + TypeScript
```

实现正常前后端分离 Web Application。

前端只覆盖项目必要能力：

- component；
- state；
- REST API；
- async request；
- loading / error state；
- basic routing；
- TypeScript interface。

不深入复杂前端工程。

---

## 6.6.3 核心 UI

保持 Case-centered Workspace：

```text
Current Incident
      ↓
Ranked Historical Cases
      ↓
Relevance Type / Rationale
      ↓
Historical Causes
      ↓
Evidence Checkpoints / Results
      ↓
Source Evidence
```

Demo 不以 Chatbot 为核心。

---

# 6.7 — Evaluation & Experiments

## 6.7.1 B — Retrieval Metrics

B 继续采用：

> **Recall-first，Precision 作为 guardrail。**

主要指标：

- Recall@K；
- Precision@K；
- MRR；
- nDCG@K。

其中：

### Recall@K
Top-K 中找回了多少真正 Relevant Cases。

### Precision@K
Top-K 中有多少是真的 Relevant。

### MRR
第一个 Relevant Case 排得是否足够靠前。

### nDCG@K
整体 Ranking 顺序质量。

具体 K 值根据实际 Demo 展示数量和 Development 数据决定。

---

## 6.7.2 Ambiguous Label

Ambiguous 不简单强行计为 Relevant 或 Not Relevant。

主评估应以明确标签为核心，同时单独记录：

```text
Ambiguous Cases
→ System Behavior Analysis
```

必要时可做 secondary evaluation，但不把复杂不确定性建模作为 V1 研究重点。

---

## 6.7.3 Relevance Type Breakdown

除总体指标外，必须分别观察：

```text
Repeat / Recurrence
Incident / Context Linkage
Technical Analog
```

避免总体分数掩盖某种类型明显失败。

---

## 6.7.4 Difficulty Breakdown

至少分别观察：

- Easy Positive；
- Hard Positive；
- Easy Negative；
- Hard Negative；
- Ambiguous。

尤其关注 Hard Negative 是否被浅层相似性误召回。

---

## 6.7.5 Ablation / Component Comparison

核心实验矩阵：

```text
BM25
      ↓
Embedding
      ↓
Hybrid
      ↓
Hybrid + Metadata
      ↓
Hybrid + Metadata + Reranker
```

目标不是刷最高分，而是回答：

> 每增加一个组件，系统实际获得了什么？

必要时根据结果缩减无贡献组件。

---

## 6.7.6 C / D Evaluation

C / D 是 Supporting Tasks，不需要做成 NLP Benchmark 研究。

主要评估：

- extraction correctness；
- missing / hallucinated facts；
- source grounding correctness；
- schema validity；
- Cause ↔ Checkpoint relation correctness。

可以结合：

```text
Programmatic Matching
+
Human Review
```

不强求复杂统一指标。

---

## 6.7.7 Engineering Metrics

记录：

- retrieval latency；
- reranker latency；
- LLM latency；
- end-to-end latency；
- token usage；
- approximate API cost；
- model call count；
- failure / retry rate。

目的不是性能优化，而是建立基本 Engineering Awareness。

---

# 6.8 — Error Analysis

Error Analysis 是 Stage 6 必须产出，不只报告总体指标。

---

## 6.8.1 Retrieval Error Categories

至少分析：

### False Negative
关键 Historical Case 没被找回。

重点判断：

```text
Candidate Retrieval 漏掉
or
Reranker 排掉
```

### False Positive
不相关 Case 被排到前面。

重点判断：

```text
lexical shortcut
semantic over-similarity
metadata bias
hard negative confusion
```

### Relevance-type Failure

例如：

```text
Repeat 很好
Technical Analog 很差
```

---

## 6.8.2 Extraction Errors

关注：

- hallucination；
- missed cause；
- checkpoint / result confusion；
- wrong Cause–Checkpoint relation；
- source citation mismatch；
- normalization error。

---

## 6.8.3 Data Errors

必须允许 Error Analysis 反向发现：

- annotation error；
- synthetic scenario flaw；
- leakage；
- inconsistent case representation；
- benchmark artifact。

模型表现差不一定等于模型本身有问题。

---

# 6.9 — Testing / CI / Deployment

这些内容直接作为 V1 必须项，不再额外取舍。

---

## 6.9.1 Software Testing

至少包含：

```text
Unit Tests
Integration Tests
End-to-End Smoke Tests
```

测试重点：

- deterministic logic；
- data validation；
- database；
- search engine；
- API；
- model abstraction；
- full pipeline。

Software Testing 与 AI Evaluation 继续分开。

---

## 6.9.2 CI

GitHub Repository 配置基础 CI：

```text
Push / Pull Request
      ↓
Lint / Basic Checks
      ↓
Automated Tests
      ↓
Pass / Fail
```

不建设复杂 DevOps Platform。

---

## 6.9.3 Containerization

使用 Docker / Docker Compose 组织至少：

```text
Backend
Frontend
PostgreSQL
Search Engine
```

本地模型是否独立容器化根据实现成本决定。

目标是：

> 一个明确命令即可启动主要依赖和应用。

---

## 6.9.4 Configuration / Secrets

必须实现：

- environment configuration；
- `.env` / secret management；
- API key 不进入 Git；
- Development / Evaluation configuration 可区分。

---

## 6.9.5 Observability

至少记录：

```text
Run ID
Incident ID
Dataset / Index Version
Model Version
Prompt Version
Retrieval Results
Latency
Token / Cost
Errors
```

不引入复杂企业级监控平台。

---

# 6.10 — Final Acceptance

Stage 6 完成时，CaseTrace V1 至少应满足以下条件。

---

## 6.10.1 AI

```text
✓ Synthetic Dataset 可复现
✓ Locked Benchmark 存在
✓ BM25 Baseline
✓ Embedding Baseline
✓ Hybrid Retrieval
✓ Metadata-aware Retrieval
✓ Local Reranker
✓ Retrieval Evaluation
✓ Ablation
✓ Error Analysis
✓ C / D Structured Extraction
✓ Source Grounding
```

---

## 6.10.2 Software

```text
✓ PostgreSQL
✓ Elasticsearch / OpenSearch
✓ Python Backend
✓ REST API
✓ React + TypeScript Frontend
✓ Modular Architecture
✓ Unit / Integration / E2E Tests
✓ Structured Logging
✓ Basic CI
✓ Dockerized Run
✓ Reproducible Setup
```

---

## 6.10.3 Demo

完整 Demo 必须能够运行：

```text
Current Incident Input
        ↓
Structured Incident
        ↓
Hybrid Retrieval
        ↓
Reranking
        ↓
Relevant Historical Cases
        ↓
Relevance Type / Rationale
        ↓
Cause Extraction
        ↓
Checkpoint / Result Extraction
        ↓
Source Traceability
        ↓
Historical Investigation Evidence
```

系统终点仍然是：

> 为工程师提供可追溯的历史调查参考。

不输出当前 Incident 的最终 Root Cause。

---

# Stage 6 不做的内容

Stage 6 不因为进入 Implementation 而重新扩大项目范围。

V1 继续不做：

- Current Incident Root Cause Prediction；
- Production Variation Screening；
- Fine-tuning；
- Learning-to-Rank Training；
- Knowledge Graph / GraphRAG；
- Formal Causal Model；
- Autonomous / Multi-agent Investigation；
- Computer Vision；
- Complex OCR / Document Parsing；
- Distributed Microservices；
- Kubernetes；
- Large-scale Search Optimization；
- Enterprise Authentication / Authorization；
- Enterprise-grade Monitoring；
- Complex MLOps Platform。

---

# Stage 6 最终开发主线

```text
Data / Benchmark
      ↓
BM25 Baseline
      ↓
Embedding Retrieval
      ↓
Hybrid Retrieval
      ↓
Metadata Signals
      ↓
Reranker
      ↓
Retrieval Evaluation
      ↓
C / D Extraction
      ↓
Backend Integration
      ↓
React Frontend
      ↓
Testing / CI / Docker
      ↓
Locked Test
      ↓
Ablation + Error Analysis
      ↓
CaseTrace V1
```

---

# Stage 6 最终技术定位

完成 Stage 6 后，CaseTrace 应体现一套完整但不过度扩张的 AI Application 技术栈：

| 技术领域 | 主要实践 |
|---|---|
| Information Retrieval | BM25、Recall@K、Ranking |
| Semantic Search | Embedding、Vector Search |
| Search Engineering | Elasticsearch / OpenSearch |
| Ranking | Cross-Encoder Reranker |
| LLM Engineering | Structured Extraction、Grounding |
| ML Evaluation | Benchmark、Ablation、Error Analysis |
| Data Engineering | Synthetic Dataset、Validation、Versioning |
| Database | PostgreSQL、Relational Modeling |
| Backend | Python、REST API、Async I/O |
| Frontend | React、TypeScript |
| Software Engineering | Modular Design、Testing |
| DevOps Basics | CI、Docker、Environment |
| Observability | Logging、Latency、Cost、Run Tracking |

项目重点是：

> **展示能够把 AI 模型、数据、检索、Backend、Frontend、Evaluation 和基本工程化组合成一个可信的完整系统。**

而不是追求某一个模型或算法方向的研究深度。

---

# Stage 6 状态

```text
Stage 6 — Implementation & Evaluation
✅ 方案已冻结

下一步：
开始实际实现
```

Stage 6 结束后进入：

```text
Stage 7 — Portfolio
```

Stage 7 负责将最终成果整理为：

- GitHub Repository；
- README；
- Architecture Diagram；
- Demo；
- Evaluation Results；
- Technical Report；
- Resume / Application Project Description。
