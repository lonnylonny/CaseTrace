# Stage 5 — Technical Design

## 阶段目标

在 Stage 1–4 已冻结的项目主干上，确定 CaseTrace 的技术实现架构。

Stage 5 只确定：

- 系统总体架构；
- B — Relevant Historical Case Retrieval 的技术路线；
- C / D — Extraction 的技术路线；
- LLM 与其他 AI Components 的职责；
- 数据存储与检索基础设施；
- Backend / API / UI 架构；
- Traceability、Logging、Testing 与基础部署边界。

继续遵循项目总原则：

> 优先覆盖通用、重要、值得系统学习的 AI / CS 能力；当前只确定技术主干和必要取舍，不提前锁定具体模型、参数、数据库实现、Prompt、API 字段或 UI 细节。

---

# Stage 5 总体结构

```text
5.1 System Architecture
        ↓
5.2 B — Retrieval Architecture
        ↓
5.3 C / D — Extraction Architecture
        ↓
5.4 LLM & AI Component Design
        ↓
5.5 Data Storage & Retrieval Infrastructure
        ↓
5.6 Backend / API / UI Architecture
        ↓
5.7 Observability, Testing & Deployment
```

---

# 5.1 — System Architecture

## 5.1.1 Modular Architecture

采用模块化分层架构，将系统职责拆分为：

```text
Frontend / UI
      ↓
Application / Backend
      ↓
AI Pipeline
├─ Incident Processing
├─ Retrieval
├─ Cause Extraction
├─ Checkpoint Extraction
└─ Aggregation / Presentation
      ↓
Data & AI Infrastructure
```

核心原则：

- 模块职责分离；
- 输入输出边界清晰；
- AI Components 与普通程序逻辑分离；
- 各模块可以独立测试、替换和评估。

---

## 5.1.2 Pipeline-oriented Design

CaseTrace V1 采用明确的处理 Pipeline：

```text
Current Incident
      ↓
Input / Structure
      ↓
Candidate Retrieval
      ↓
Ranking / Reranking
      ↓
Relevant Historical Cases
      ↓
Cause Extraction
      ↓
Checkpoint Extraction
      ↓
Aggregation / Presentation
```

每一步都具有独立输入、输出和责任，以支持 Debugging、Evaluation 和后续替换组件。

---

## 5.1.3 AI Components 与 Deterministic Components 分离

原则：

```text
确定性任务
→ Program / Database / Rules

语义理解与语言处理任务
→ Retrieval Models / LLM
```

普通程序负责：

- ID / relationship 管理；
- metadata processing；
- validation；
- source linking；
- aggregation；
- data access。

AI Components 负责：

- semantic retrieval；
- reranking；
- structured extraction；
- grounded explanation / summary。

---

## 5.1.4 Retrieval 与 Extraction 分离

系统明确区分：

```text
Retrieval
→ 哪些 Historical Cases 值得参考？

Extraction
→ 这些 Historical Cases 中记录了什么？
```

B 负责 Historical Case Retrieval / Ranking。

C / D 只处理被选中的 Historical Cases 中已经存在的信息，不替代 Retrieval，也不直接生成当前异常 Root Cause。

---

## 5.1.5 Persistent Data + Stateless Core

长期状态由持久化层保存，核心 Pipeline 尽量通过明确输入、存储数据和配置产生输出。

主要持久化对象包括：

- Historical Cases；
- Current Incidents；
- Causes / Checkpoints；
- Source References；
- Ground Truth；
- Pipeline Runs；
- Dataset / Index Versions。

---

## 5.1.6 End-to-end Traceability

Traceability 贯穿整个系统：

```text
Current Incident
      ↓
Retrieved Historical Case
      ↓
Historical Cause
      ↓
Evidence Checkpoint
      ↓
Source Evidence
```

系统结果需要能够追溯到对应 Historical Case 和 Source Evidence，并保留必要的运行来源信息。

---

## 5.1.7 Application 与 Evaluation 共用核心 Pipeline

同一套 Retrieval / Extraction Components 同时用于：

```text
Core Pipeline
├─ Application / Demo
└─ Offline Evaluation
```

避免 Demo 与 Benchmark 使用两套不同实现。

---

# 5.2 — B: Retrieval Architecture

B 是 CaseTrace V1 的核心 AI Task。

总体采用：

> **Two-stage + Hybrid + Metadata-aware Retrieval**

---

## 5.2.1 Two-stage Retrieval

```text
Current Incident
      ↓
Candidate Retrieval
      ↓
Candidate Historical Cases
      ↓
Reranking
      ↓
Ranked Top-K
```

第一阶段优先保证 Recall，第二阶段提高 Ranking Quality。

---

## 5.2.2 Hybrid Candidate Retrieval

Candidate Retrieval 同时使用：

```text
Lexical Retrieval
+
Semantic Retrieval
+
Metadata Signals
```

### Lexical Retrieval

使用传统全文检索 / BM25 类方法处理：

- Failure Mode；
- Product / Equipment 等明确术语；
- 特定技术词；
- 精确或近似关键词匹配。

### Semantic Retrieval

通过 Embedding + Vector Search 处理：

- wording variation；
- semantic similarity；
- 不同表达方式下的技术关联。

### Metadata-aware Retrieval

Structured Metadata 作为 Retrieval / Ranking Signal，例如：

- Product；
- Process Context；
- Equipment；
- Lot；
- Production Time；
- Failure Mode。

Metadata 主要用于 filtering / boosting / ranking signal，不应机械地将不同 Product 等情况全部过滤，以保留 Technical Analog。

---

## 5.2.3 Candidate Fusion

Lexical 与 Semantic Retrieval 产生的候选结果需要合并：

```text
Lexical Candidates
        +
Semantic Candidates
        +
Metadata Signals
        ↓
Candidate Fusion
        ↓
Candidate Set
```

具体 Fusion Algorithm 留到实现与实验阶段决定。

---

## 5.2.4 Reranking

Candidate Set 进入更精细的 Query–Case Relevance 判断：

```text
Current Incident
      ×
Historical Case
      ↓
Reranker
      ↓
Relevance Ranking
```

V1 主路线使用独立 Text Reranker / Cross-Encoder 类组件。

LLM Reranking 可作为后续实验对照，不作为核心依赖。

---

## 5.2.5 Structured + Unstructured Query Representation

Current Incident 同时保留：

```text
Free-text Representation
+
Structured Context
```

Retrieval Query 可以同时利用自然语言描述和 Structured Metadata。

---

## 5.2.6 Ranking、Relevance Type 与 Rationale 分离

处理顺序为：

```text
Retrieve / Rank
      ↓
Top Historical Cases
      ↓
Relevance Type
+
Grounded Rationale
```

三种 Relevance Type 保持：

- Repeat / Recurrence；
- Incident / Context Linkage；
- Technical Analog。

一个 Case 可以属于多个类型。

Rationale 用于解释已有 Ranking Result，不反过来决定 Ranking。

---

## 5.2.7 Retrieval Traceability

最终 Retrieval Result 逻辑上保留：

- Source Historical Case；
- Retrieval pathway；
- metadata information；
- reranking result；
- Relevance Type；
- Relevance Rationale。

用于 Debugging、Error Analysis 和 Evaluation。

---

## 5.2.8 Baseline / Ablation Support

Retrieval Architecture 需要支持后续比较：

```text
Lexical-only
Semantic-only
Hybrid
Hybrid + Reranker
```

用于 Stage 6 判断各组件的实际贡献。

---

# 5.3 — C / D: Extraction Architecture

C / D 采用：

> **LLM-based Structured Information Extraction + Validation + Source Grounding**

总体流程：

```text
Retrieved Historical Cases
        ↓
Relevant Source Content
        ↓
Structured Extraction
        ↓
Validation
        ↓
Light Normalization
        ↓
Aggregation
        ↓
Historical Cause Space
+
Checkpoint Summary
```

---

## 5.3.1 C — Historical Cause Extraction

从 Historical Case 中提取已经明确记录的：

- Cause；
- Root Cause；
- Contributing Cause。

逻辑输出保留：

```text
Extracted Cause
+
Cause Type
+
Source Case
+
Source Evidence
```

不建立复杂 Cause Ontology。

---

## 5.3.2 D — Historical Evidence Checkpoint Extraction

从 Historical Investigation Record 中提取：

```text
Cause
      ↓
Evidence Checkpoint
      ↓
Observed Result
      ↓
Source Evidence
```

必须区分：

```text
Checkpoint
≠
Observed Result
```

并建立明确的：

```text
Cause ↔ Checkpoint
```

关系。

---

## 5.3.3 Source-grounded Extraction

C / D 的每条重要提取结果都必须能追溯到：

```text
Historical Case
+
Relevant Source Evidence
```

LLM 不根据自身知识补充 Historical Source 中不存在的事实。

---

## 5.3.4 Extraction 与 Summarization 分离

采用：

```text
Source Cases
      ↓
Fact Extraction
      ↓
Structured Facts
      ↓
Aggregation / Summary
```

先提取可追溯事实，再对多个 Case 进行 Cause / Checkpoint 汇总。

---

## 5.3.5 Light Normalization

对明显等价或高度相近的表达进行轻量 Normalization。

例如：

```text
Original Expression
+
Normalized Form
```

同时保留原始表达和 Source，不建立大型 Ontology。

---

## 5.3.6 Validation

LLM Structured Output 进入 Validation Layer：

```text
LLM Output
      ↓
Schema Validation
      ↓
Consistency Validation
      ↓
Accepted Structured Result
```

检查输出结构、Source Reference、Cause–Checkpoint relationship 等基本一致性。

---

## 5.3.7 Abstention / Missing Information

Extraction Component 允许：

```text
Not Found
Unknown
Ambiguous
Needs Review
```

不要求模型在 Source 信息不足时强行产生结果。

---

## 5.3.8 Batch Processing

架构同时支持：

```text
Single Historical Case
```

和：

```text
Multiple Retrieved Cases
      ↓
Batch / Parallel Processing
      ↓
Aggregation
```

具体并发实现后续决定。

---

# 5.4 — LLM & AI Component Design

## 5.4.1 Task-specific AI Components

CaseTrace 不采用单一万能 LLM。

AI Layer 逻辑上区分：

```text
Embedding Model
→ Semantic Retrieval

Reranker
→ Query–Case Ranking

Generative LLM
→ Structured Extraction
→ Grounded Explanation / Summary
```

普通程序继续负责确定性逻辑和 Validation。

---

## 5.4.2 LLM 的主要职责

V1 中 LLM 主要用于：

### Current Incident Structured Extraction

```text
Free Text
      ↓
LLM
      ↓
Structured Incident
```

### Historical Cause Extraction

```text
Historical Report
      ↓
LLM
      ↓
Structured Causes
```

### Checkpoint / Result / Relation Extraction

```text
Investigation Record
      ↓
LLM
      ↓
Checkpoint
Observed Result
Cause–Checkpoint Relation
```

### Grounded Explanation / Summary

基于已经检索和提取出的证据生成：

- Relevance Rationale；
- Historical Cause Summary；
- Checkpoint Summary。

---

## 5.4.3 Embedding / Reranker / LLM 解耦

三类模型作为独立可替换组件：

```text
AI Components
├─ Embedding Model
├─ Reranking Model
└─ Generative LLM
```

不要求使用同一模型或同一 Provider。

---

## 5.4.4 Model Abstraction

业务代码通过轻量 Model Interface 调用模型，使：

- LLM；
- Embedding Model；
- Reranker；

可以在后续实验中替换。

Stage 5 不锁定具体模型、Provider、参数规模或本地 / Cloud 方案。

---

## 5.4.5 Structured Output + Schema

A / C / D 等任务采用：

```text
LLM
      ↓
Structured Output
      ↓
Schema Validation
```

而不是依赖自由自然语言输出作为系统内部数据。

---

## 5.4.6 Prompt Management

Prompt 作为系统资产进行管理：

```text
Task
+
Prompt Template
+
Prompt Version
+
Model Configuration
```

用于实验可复现和 Debugging。

Prompt 负责：

- Task Definition；
- Output Format；
- Behavior Boundary。

不将 Ground Truth 或 Synthetic Scenario 答案规则编码进 Prompt。

---

## 5.4.7 Grounding & Hallucination Control

主要机制：

```text
Restricted Task
+
Source Grounding
+
Structured Output
+
Validation
+
Abstention
+
Traceability
```

Source-grounded Information 与任何生成性内容保持清晰边界。

---

## 5.4.8 Basic Cost / Latency Awareness

记录模型调用基本信息：

- latency；
- token usage；
- model calls；
- approximate cost。

用于后续工程评估，不在 Stage 5 进行性能优化。

---

# 5.5 — Data Storage & Retrieval Infrastructure

总体采用：

```text
Relational Database
+
Lexical Search Capability
+
Vector Search Capability
```

---

## 5.5.1 Relational Database

关系数据库作为主要持久化和 Source-of-Truth 层。

逻辑上保存：

- Cases；
- Incident Metadata；
- Case Relationships；
- Causes；
- Checkpoints；
- Observed Results；
- Ground Truth；
- Source References；
- Dataset Versions；
- Pipeline Runs。

重点学习标准 SQL / relational data modeling，不采用 NoSQL-first。

---

## 5.5.2 Lexical Search Index

Historical Corpus 建立全文检索能力，用于 BM25 / Lexical Retrieval。

主要承担传统关键词和术语检索。

---

## 5.5.3 Vector Index

Historical Case 的文本表示通过 Embedding Model 转换为 Vector，并建立 Vector Search Capability：

```text
Historical Case
      ↓
Embedding
      ↓
Vector Index
```

Current Incident 通过相同 Embedding Space 查询相近 Historical Cases。

---

## 5.5.4 Vector Search Capability ≠ 必须独立 Vector DB

架构只要求具备：

```text
Embedding Storage
+
Vector Similarity Search
```

具体由关系数据库扩展还是独立 Vector Database 实现，留到实现阶段决定。

同理，Lexical Search 只要求具备 Full-text / BM25 能力，不提前锁定大型 Search Engine。

---

## 5.5.5 Canonical Data 与 Derived Data 分离

### Canonical / Persistent Data

例如：

- Case；
- Historical Source；
- Cause；
- Checkpoint；
- Ground Truth。

### Derived Data

例如：

- Embedding；
- Search Index；
- normalized values；
- Retrieval Result；
- LLM Extraction Result；
- Summary。

Search Index / Embeddings 属于可重新生成的 Derived Infrastructure，不作为唯一 Source of Truth。

---

## 5.5.6 Data Access Layer

Application 通过统一 Data Access Layer 访问：

```text
Application
      ↓
Data Access Layer
      ↓
Database / Search Infrastructure
```

避免 Retrieval、Extraction、UI 和 Evaluation 各自直接操作底层存储。

---

## 5.5.7 Offline Indexing + Online Querying

### Offline

```text
Historical Corpus
      ↓
Preprocessing
      ↓
Text Representation
      ↓
Embedding Generation
      ↓
Lexical / Vector Indexing
```

### Online

```text
Current Incident
      ↓
Query Processing
      ↓
Lexical Query
+
Embedding Query
+
Metadata
      ↓
Existing Indexes
      ↓
Candidates
```

---

## 5.5.8 Versioning

需要关联：

```text
Dataset Version
+
Embedding Model Version
+
Index Version
```

保证 Retrieval Experiment 和数据生成过程可追踪。

Locked Evaluation Ground Truth 与 Application Data 保持逻辑隔离。

---

# 5.6 — Backend / API / UI Architecture

## 5.6.1 Python Backend + API-first

采用：

```text
Web Frontend
      ↓
REST API
      ↓
Python Backend
      ↓
Application / AI Pipeline
```

Backend 负责：

- Incident management；
- Retrieval orchestration；
- Extraction orchestration；
- Data access；
- Validation；
- Error handling；
- Logging。

---

## 5.6.2 Modular Monolith

V1 使用：

> **Modular Monolith**

系统内部保持模块化，但整体作为一个应用部署。

```text
Backend
├─ Incident
├─ Retrieval
├─ Extraction
├─ Data Access
├─ Model Layer
├─ Evaluation Interface
└─ Observability
```

---

## 5.6.3 REST API

Frontend 与 Backend 通过标准 REST API 通信，系统主要资源包括：

- Incident；
- Historical Case；
- Retrieval Result；
- Cause / Checkpoint；
- Source；
- Pipeline Run。

具体 API Endpoint 和 Schema 留到实现阶段。

---

## 5.6.4 Lightweight Web Frontend

V1 建立正常 Web Frontend，用于完整展示系统，而不是只依赖 Notebook。

核心 UI 围绕：

```text
Current Incident
      ↓
Relevant Historical Cases
      ↓
Historical Causes
      ↓
Evidence Checkpoints
      ↓
Source Evidence
```

主要界面需要支持：

### Incident

- Current Incident；
- Structured Fields；
- Original Input。

### Retrieval

- Ranked Historical Cases；
- Relevance Type；
- Grounded Rationale；
- Relevant Metadata。

### Historical Evidence

- Historical Causes；
- Checkpoints；
- Observed Results；
- Source Traceability。

主交互模式保持 **Case-centered Investigation Workspace**，不以 Chat Interface 为核心。

---

## 5.6.5 Basic Async / Concurrency

Backend 需要理解并支持基本：

- async I/O；
- concurrent external calls；
- timeout；
- retry。

用于模型 API 和其他 I/O 操作。

复杂 Background Job / Distributed Queue 仅在实际需要时增加。

---

# 5.7 — Observability, Testing & Deployment

## 5.7.1 Structured Logging

系统使用 Structured Logging 记录关键 Pipeline 行为：

```text
Request / Run
      ↓
Retrieval
      ↓
Reranking
      ↓
Extraction
      ↓
Model Calls
      ↓
Result / Error
```

---

## 5.7.2 Run / Request Tracking

每次 Pipeline Run 使用唯一 Run ID / Request ID，并关联：

- Incident；
- Retrieval Result；
- Model Calls；
- Extraction Result；
- latency；
- errors。

---

## 5.7.3 Basic AI Observability

至少记录：

- Model / Model Version；
- Prompt Version；
- latency；
- token usage；
- approximate cost；
- success / failure；
-必要的 input / output metadata。

用于 Debugging、Experiment Reproducibility 和 Error Analysis。

---

## 5.7.4 Error Handling

外部模型和系统组件需要基本：

- timeout；
- retry；
- validation；
- graceful failure。

单个 AI Component 出错时应产生明确错误状态，而不是导致整个应用无信息崩溃。

---

## 5.7.5 Configuration & Secrets

Application Code、Configuration 与 Environment 分离。

API Key 等 Secret 不写入源码或 Git Repository，通过环境配置或 Secret 机制提供。

---

## 5.7.6 Software Testing

至少包含：

```text
Unit Tests
      ↓
Integration Tests
      ↓
End-to-End Smoke Tests
```

### Unit Tests

测试：

- validation；
- normalization；
- data transformation；
- fusion / deterministic logic。

### Integration Tests

测试：

- Backend ↔ Database；
- Retrieval ↔ Search Index；
- Pipeline ↔ Model Interface。

### End-to-End

测试完整：

```text
Incident
      ↓
API
      ↓
Retrieval
      ↓
Extraction
      ↓
Final Application Result
```

---

## 5.7.7 Software Testing 与 AI Evaluation 分离

```text
Software Testing
→ 系统是否正确运行

AI Evaluation
→ AI 输出质量是否足够好
```

AI Evaluation 的详细 Metrics、Experiments 和 Error Analysis 留到 Stage 6。

---

## 5.7.8 Basic CI

Git Repository 建立基础 Continuous Integration：

```text
Code Change
      ↓
Automatic Tests
      ↓
Pass / Fail
```

用于保证代码变化不会破坏基本系统行为。

---

## 5.7.9 Containerization

系统支持 Containerized Run，以实现：

- dependency isolation；
- reproducible environment；
- portable deployment。

---

## 5.7.10 Simple Deployment

V1 采用简单单机 / 单服务 Deployment：

```text
Browser
      ↓
Web Application
      ↓
Backend
      ↓
Database / Search / Models
```

可在 Local 或简单 Cloud / Container Environment 中运行。

---

## 5.7.11 Reproducible Setup

Repository 应能够通过明确步骤完成：

```text
Clone
      ↓
Configure
      ↓
Install / Build
      ↓
Run
```

使 Dataset、Application 和 Experiment 基本可复现。

---

# Stage 5 最终系统架构

```text
                         Web Frontend
                              ↓
                           REST API
                              ↓
                    Modular Python Backend
                              ↓
                    Application / Pipeline
                              │
       ┌──────────────────────┼──────────────────────┐
       ↓                      ↓                      ↓
Incident Processing       Retrieval              Extraction
                            │                      C / D
                 ┌──────────┼──────────┐             │
                 ↓          ↓          ↓             ↓
              BM25      Embedding   Metadata     Structured LLM
                 \          |          /             │
                  \         |         /              ↓
                   Candidate Fusion             Validation
                          ↓                         ↓
                       Reranker               Normalization
                          ↓                         ↓
                       Top-K ──────────────────────┘
                          ↓
                 Historical Evidence
                          ↓
              Grounded Explanation / Summary
                          ↓
                    Source Traceability

────────────────── Data Infrastructure ──────────────────

Relational Database
Lexical Search Index
Vector Search Index
Data Access Layer
Offline Indexing
Dataset / Index Versioning

────────────────── Engineering ─────────────────────────

Structured Logging
Run / Request Tracking
Model / Prompt Versioning
Latency / Cost Tracking
Error Handling
Unit / Integration / E2E Testing
Basic CI
Containerization
Reproducible Deployment
```

---

# Stage 5 核心技术覆盖

| 技术领域 | CaseTrace 中的实现 |
|---|---|
| Information Retrieval | BM25、Candidate Retrieval、Ranking |
| Semantic Search | Embedding、Vector Search |
| Hybrid Retrieval | Lexical + Semantic + Metadata |
| Ranking | Reranker、Two-stage Retrieval |
| NLP / Information Extraction | Cause / Checkpoint / Relation Extraction |
| LLM Engineering | Structured Output、Grounding、Prompt、Validation |
| Relational Database | SQL、Structured Data、Relationships |
| Search Infrastructure | Lexical Index、Vector Index |
| Backend Engineering | Python Backend、REST API |
| Software Architecture | Modular Monolith、Layering、Interfaces |
| Data Engineering | Indexing、Validation、Versioning |
| ML / AI Engineering | Model Components、Evaluation Interface、Reproducibility |
| Software Testing | Unit / Integration / E2E |
| Observability | Logging、Tracing、Latency、Cost |
| Deployment | CI、Containerization、Simple Deployment |

---

# Stage 5 最终状态

```text
Stage 5 — Technical Design

5.1 System Architecture
✅ 已完成

5.2 B — Retrieval Architecture
✅ 已完成

5.3 C / D — Extraction Architecture
✅ 已完成

5.4 LLM & AI Component Design
✅ 已完成

5.5 Data Storage & Retrieval Infrastructure
✅ 已完成

5.6 Backend / API / UI Architecture
✅ 已完成

5.7 Observability, Testing & Deployment
✅ 已完成
```

**Stage 5 — Technical Design 已完成并冻结。**

---

# 当前项目进度

```text
Stage 1 — Problem Framing
✅ 已完成

Stage 2 — AI Task Design
✅ 已完成

Stage 3 — MVP Scope
✅ 已完成

Stage 4 — Data Design
✅ 已完成

Stage 5 — Technical Design
✅ 已完成

Stage 6 — Implementation & Evaluation
⏳ 下一阶段

Stage 7 — Portfolio
⏳ 未开始
```

---

# 下一阶段

## Stage 6 — Implementation & Evaluation

Stage 6 将基于已经冻结的数据设计与技术架构，进入实际实现与验证，重点包括：

- 项目代码结构与开发顺序；
- Synthetic Dataset 实际生成；
- Retrieval Baselines；
- Hybrid Retrieval / Reranking；
- C / D Extraction；
- Backend / UI 集成；
- Offline Evaluation；
- Metrics；
- Ablation / Component Comparison；
- Error Analysis；
- Software Testing；
- Performance / Cost Record。
