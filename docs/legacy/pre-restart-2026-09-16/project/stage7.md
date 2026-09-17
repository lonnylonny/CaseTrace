> 历史归档（2026-09-16）：本文件不是当前要求、状态或 Agent 指令；后续任务以 [Current Plan](../../../project/current-plan.md) 为准。原文中的“当前”“已完成”“冻结”等仅对应历史时点。

# Stage 7 — Portfolio

## 阶段目标

在 Stage 1–6 已经完成的问题定义、AI 任务设计、MVP 范围、数据设计、技术架构以及 Implementation & Evaluation 方案基础上，将 CaseTrace V1 整理成一个适合 **AI / Software Engineering 求职、研究生申请与技术展示** 的完整 Portfolio。

Stage 7 不再扩展系统功能，也不重新设计技术路线。

核心目标是：

- 让陌生读者能够快速理解项目解决什么问题；
- 清晰展示完整 AI / CS 技术栈，而不是只展示最终 Demo；
- 用 Evaluation、Ablation 和 Error Analysis 证明技术方案具有可信依据；
- 通过 GitHub、README、架构图和 Demo 展示软件工程完整度；
- 将同一个项目整理成适合 GitHub、简历和研究生申请的不同表达形式。

项目最终展示定位保持为：

> **一个将 Information Retrieval、LLM Information Extraction、Data Engineering、Backend、Frontend、Evaluation 和基础工程化整合起来的 Production-aware AI Application。**

---

# Stage 7 总体结构

```text
7.1 Repository Finalization
        ↓
7.2 README
        ↓
7.3 Architecture & Technical Diagrams
        ↓
7.4 Demo Presentation
        ↓
7.5 Evaluation & Experiment Presentation
        ↓
7.6 Technical Report
        ↓
7.7 Resume / CV Project Description
        ↓
7.8 Graduate Application / Portfolio Material
        ↓
7.9 Final Portfolio Review
```

---

# 7.1 — Repository Finalization

GitHub Repository 是项目最完整的技术载体。

目标不是把所有开发过程原样堆进去，而是形成一个能够被快速检查、运行和理解的公开项目。

## 7.1.1 Repository 基本内容

最终 Repository 至少包含：

```text
README
source code
frontend
backend
retrieval
extraction
data / dataset tooling
evaluation
tests
configuration examples
Docker / deployment files
documentation
```

具体目录名称以 Stage 6 实际实现为准，不为了展示重新修改成熟代码结构。

---

## 7.1.2 Repository 应体现的工程信息

读者应能够看到：

- 模块化代码结构；
- Dataset / Benchmark 生成逻辑；
- Retrieval 与 Extraction 的职责分离；
- Evaluation Pipeline；
- Unit / Integration / E2E Testing；
- CI；
- Docker / Docker Compose；
- Configuration / Secrets 管理；
- 可复现的启动方式。

避免把 Repository 做成只剩 Notebook、截图或一份 Demo 脚本的展示项目。

---

## 7.1.3 Repository Cleanup

发布前进行基本整理：

- 删除临时文件和废弃代码；
- 删除敏感信息和 API Key；
- 整理依赖；
- 保证基本启动命令有效；
- 保证主要测试可以运行；
- 固定必要的 Dataset / Model / Index Version 信息；
- 提供 `.env.example` 或等价配置说明。

不需要为了“看起来专业”加入复杂 Monorepo、Kubernetes 或企业级 DevOps 结构。

---

# 7.2 — README

README 是 Portfolio 最重要的入口。

目标是让一个不了解半导体封装的 AI / CS 面试官或招生人员，也能在较短时间内理解：

```text
What is the problem?
What did you build?
How does the AI work?
How did you evaluate it?
What technologies did you use?
Can I run or see it?
```

---

## 7.2.1 推荐 README 主结构

```text
# CaseTrace

1. Project Overview
2. Problem
3. System Workflow
4. Key Features
5. Architecture
6. AI / Retrieval Pipeline
7. Dataset & Benchmark
8. Evaluation Results
9. Demo
10. Tech Stack
11. Repository Structure
12. Getting Started
13. Testing
14. Limitations
15. Future Work
```

---

## 7.2.2 README 开头必须非常清楚

前几屏应直接回答：

### CaseTrace 是什么？

> CaseTrace is an AI-assisted technical incident investigation system that retrieves relevant historical cases and extracts grounded historical causes and investigation evidence to support engineers during incident analysis.

### 核心工作流

```text
Current Incident
      ↓
Relevant Historical Case Retrieval
      ↓
Historical Cause Extraction
      ↓
Historical Evidence Checkpoint Extraction
      ↓
Engineer Investigation and Judgment
```

### 系统边界

明确说明：

- 不自动预测当前 Incident 的最终 Root Cause；
- 不替代工程师判断；
- 半导体封装是 Case Study，但问题本身属于更通用的 Technical Incident Investigation。

---

## 7.2.3 README 重点展示技术贡献

重点突出：

### Retrieval

```text
BM25
Embedding Retrieval
Hybrid Retrieval
Metadata-aware Retrieval
Cross-Encoder Reranking
```

### LLM / NLP

```text
Structured Information Extraction
Source Grounding
Schema Validation
Abstention
Cause / Checkpoint / Relation Extraction
```

### Evaluation

```text
Recall@K
Precision@K
MRR
nDCG@K
Ablation
Error Analysis
```

### Software Engineering

```text
Python Backend
REST API
PostgreSQL
Elasticsearch / OpenSearch
React + TypeScript
Testing
CI
Docker
Logging / Run Tracking
```

---

# 7.3 — Architecture & Technical Diagrams

最终 Portfolio 至少保留几张真正有信息价值的图。

不追求大量装饰性流程图。

---

## 7.3.1 System Architecture Diagram

展示：

```text
Frontend
   ↓
REST API
   ↓
Python Backend
   ↓
Application Pipeline
   ├─ Incident Processing
   ├─ Retrieval
   ├─ Extraction
   └─ Aggregation
   ↓
PostgreSQL + Search Infrastructure + Models
```

目的：展示完整的软件系统结构。

---

## 7.3.2 Retrieval Pipeline Diagram

重点展示项目最核心 AI Task：

```text
Current Incident
      ↓
BM25 Candidates
+
Embedding Candidates
+
Metadata Signals
      ↓
Candidate Fusion
      ↓
Cross-Encoder Reranker
      ↓
Ranked Historical Cases
      ↓
Relevance Type + Grounded Rationale
```

目的：让面试官快速理解为什么项目不是简单 Vector Search / RAG。

---

## 7.3.3 Data / Evaluation Pipeline Diagram

展示：

```text
Scenario Design
      ↓
Canonical Truth
      ↓
Synthetic Case Generation
      ↓
Historical Corpus + Current Queries
      ↓
Ground Truth
      ↓
Development Set + Locked Test
      ↓
Retrieval Evaluation
```

目的：突出 Dataset、Ground Truth、Leakage Control 和 Benchmark Design。

---

# 7.4 — Demo Presentation

Demo 应重点展示产品主线，不展示所有后台功能。

核心 Demo 保持：

```text
Current Incident Input
        ↓
Structured Incident
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

---

## 7.4.1 Demo 应展示什么

### 1. Current Incident

展示一个新的 Incident，包括 Structured Fields 和 Free Text。

### 2. Retrieval Result

展示 Top-K Historical Cases，以及：

- Ranking；
- Relevance Type；
- 关键 Metadata；
- Grounded Rationale。

### 3. Historical Evidence

点击某个 Case 后展示：

- Historical Cause；
- Evidence Checkpoints；
- Observed Results；
- Source Evidence。

### 4. Multi-case Summary

如实现完成，可以展示：

```text
Selected Historical Cases
        ↓
Historical Cause Space
        ↓
Checkpoint Summary
```

---

## 7.4.2 Demo 呈现形式

至少保留：

- 可运行 Web Demo；
- README 中的关键截图 / GIF；
- 一段简短 Demo Video。

Demo Video 不需要成为完整产品介绍片，重点演示一个完整 Incident Workflow。

---

# 7.5 — Evaluation & Experiment Presentation

这是 CaseTrace 与普通 AI Demo 拉开差距的关键部分。

Portfolio 中必须展示：

> 系统为什么这样设计，以及各组件是否真的产生效果。

---

## 7.5.1 Core Experiment Table

最终至少整理：

| System | Recall@K | Precision@K | MRR | nDCG@K |
|---|---:|---:|---:|---:|
| BM25 | | | | |
| Embedding | | | | |
| Hybrid | | | | |
| Hybrid + Metadata | | | | |
| Hybrid + Metadata + Reranker | | | | |

真实数值由 Stage 6 实验结果填写。

---

## 7.5.2 Breakdown

至少展示关键 Breakdown：

### Relevance Type

```text
Repeat / Recurrence
Incident / Context Linkage
Technical Analog
```

### Difficulty

```text
Easy Positive
Hard Positive
Easy Negative
Hard Negative
```

Ambiguous 单独说明系统行为，不强行混入主指标。

---

## 7.5.3 Ablation

Ablation 需要回答：

```text
BM25 带来了什么？
Embedding 带来了什么？
Hybrid 是否互补？
Metadata 是否有效？
Reranker 是否改善最终 Ranking？
```

重点是解释组件贡献，不追求复杂实验数量。

---

## 7.5.4 Error Analysis

Portfolio 至少展示若干代表性失败案例，例如：

- lexical shortcut；
- semantic over-similarity；
- metadata bias；
- hard negative confusion；
- Technical Analog 漏检；
- Cause extraction miss；
- Checkpoint / Observed Result confusion。

同时说明问题可能来自：

```text
Model
Data
Annotation
Synthetic Scenario
Pipeline
```

避免把所有错误简单归因于模型。

---

# 7.6 — Technical Report

Technical Report 是比 README 更完整的项目说明，但不需要写成论文。

推荐结构：

```text
1. Introduction
2. Problem Definition
3. System Scope
4. Dataset Design
5. System Architecture
6. Retrieval Method
7. Extraction Method
8. Evaluation Setup
9. Results
10. Error Analysis
11. Engineering Implementation
12. Limitations
13. Conclusion
```

---

## 7.6.1 Report 的主要作用

用于展示：

- 问题定义能力；
- AI Task formulation；
- Dataset / Benchmark 思考；
- 技术设计逻辑；
- 实验设计；
- 对结果和局限的理解。

不需要模拟 Academic Paper 风格，也不需要为了篇幅加入大量 Semiconductor Background。

---

# 7.7 — Resume / CV Project Description

简历版本必须高度压缩。

项目描述原则采用：

```text
What was built
+
Technical approach
+
Evaluation / measurable result
+
Engineering scope
```

最终建议控制在约 2–4 个 bullet。

---

## 7.7.1 AI / ML Engineer 版本重点

优先强调：

- hybrid retrieval；
- BM25 / embedding / reranker；
- LLM structured extraction；
- Benchmark / evaluation；
- ablation / error analysis。

---

## 7.7.2 Software / Backend Engineer 版本重点

优先强调：

- Python backend；
- REST API；
- PostgreSQL；
- Elasticsearch / OpenSearch；
- modular architecture；
- Docker / CI / testing；
- integration with AI models。

---

## 7.7.3 General AI Application Engineer 版本

综合强调：

> 从 Dataset、Retrieval、LLM、Backend 到 Frontend 和 Evaluation 构建完整 AI Application。

这是 CaseTrace 最适合的主版本。

---

# 7.8 — Graduate Application / Portfolio Material

研究生申请中的表达与求职略有不同。

重点不只是“用了哪些技术”，还需要展示：

```text
Previous domain experience
        ↓
Identified a real technical problem
        ↓
Formalized it as an AI / CS problem
        ↓
Designed data and evaluation
        ↓
Implemented a complete system
        ↓
Evaluated limitations and failures
```

---

## 7.8.1 申请材料应强调

- 将真实工程经验转化成 AI / CS Problem 的能力；
- 对 Information Retrieval、NLP、LLM 和 Software Systems 的实际学习；
- 不只使用现成 API，而是建立 Dataset、Ground Truth、Baseline、Benchmark 和 Evaluation；
- 对系统边界、Data Leakage、Synthetic Data Limitation 的理解；
- 完整实现能力。

---

## 7.8.2 不需要过度强调

- 半导体工艺细节；
- 复杂业务术语；
- 项目解决了真实企业全部问题；
- Synthetic Benchmark 等同真实生产效果。

半导体背景用于解释项目来源和业务可信性，但项目核心仍然是 AI / CS 能力。

---

# 7.9 — Final Portfolio Review

项目发布前进行一次最终检查。

---

## 7.9.1 Technical Completeness

```text
✓ System 可以运行
✓ Main Demo 可以完成
✓ Repository 结构清晰
✓ Tests 可以运行
✓ Docker / Setup 有效
✓ Evaluation Result 可复现
✓ Dataset / Benchmark 有说明
```

---

## 7.9.2 AI Credibility

```text
✓ 有简单 Baseline
✓ 有 Final Pipeline
✓ 有 Metrics
✓ 有 Ablation
✓ 有 Error Analysis
✓ 有 Ground Truth
✓ 有 Source Traceability
✓ 明确 Synthetic Data Limitation
```

---

## 7.9.3 Presentation Clarity

陌生读者应该能够快速回答：

```text
CaseTrace 解决什么问题？
核心 AI Task 是什么？
为什么不是简单 RAG？
用了哪些主要技术？
系统效果如何？
哪里仍然会失败？
这个项目体现了哪些 AI / CS 能力？
```

---

# Stage 7 最终 Portfolio 资产

完成后建议形成以下核心资产：

```text
1. Public GitHub Repository
2. Main README
3. System Architecture Diagram
4. Retrieval Pipeline Diagram
5. Data / Evaluation Diagram
6. Web Demo
7. Demo Screenshots / GIF
8. Short Demo Video
9. Evaluation Tables / Figures
10. Error Analysis Examples
11. Technical Report
12. Resume Project Description
13. Graduate Application Project Description
```

这些资产来自同一套项目成果，只针对不同场景重新组织表达，不重新开发新的系统。

---

# Stage 7 不做的内容

Stage 7 不再增加：

- 新 AI 功能；
- 新模型；
- 新数据任务；
- Fine-tuning；
- Knowledge Graph；
- Agent；
- Production Variation Screening；
- Root Cause Prediction；
- 企业级部署；
- 与 Portfolio 无直接关系的 UI 美化工程。

如果 Stage 7 过程中发现明显系统 Bug，可以修复；但不重新打开 Stage 1–6 已冻结的 Scope。

---

# Stage 7 最终展示主线

所有 Portfolio Material 尽量围绕同一套逻辑组织：

```text
Problem
   ↓
Task Formulation
   ↓
Data & Ground Truth
   ↓
System Architecture
   ↓
AI Pipeline
   ↓
Application
   ↓
Evaluation
   ↓
Error Analysis
   ↓
Limitations
```

避免只按“用了哪些技术”堆叠项目内容。

---

# CaseTrace 最终 Portfolio 定位

CaseTrace 最终应体现：

> **能够从真实工程问题出发，把问题转化为可评估的 AI Task，并完成数据设计、检索系统、LLM Information Extraction、Backend、Frontend、Evaluation、Testing 和 Deployment 的完整 AI Application Engineering 项目。**

它同时展示三类能力：

### AI / ML Engineering

- Information Retrieval；
- Embedding；
- Hybrid Search；
- Reranking；
- LLM Structured Extraction；
- Benchmark；
- Ablation；
- Error Analysis。

### Software Engineering

- Python Backend；
- REST API；
- PostgreSQL；
- Search Engine；
- React + TypeScript；
- Testing；
- CI；
- Docker；
- Observability。

### End-to-End Project Ability

```text
Problem Framing
→ AI Task Design
→ Scope
→ Data
→ Technical Design
→ Implementation
→ Evaluation
→ Portfolio
```

这也是 CaseTrace 相比简单课程作业、Notebook Demo 或 API Wrapper 的核心区别。

---

# Stage 7 状态

```text
Stage 7 — Portfolio
✅ 方案已冻结

下一步：
Stage 1–7 规划阶段全部完成
→ 开始按照 Stage 6 Development Mainline 实际实现 CaseTrace V1
```

---

# CaseTrace 项目规划最终状态

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
✅ 方案已冻结

Stage 7 — Portfolio
✅ 方案已冻结
```

至此，CaseTrace 的顶层规划完成。

后续工作原则上不再继续增加 Planning Stage，而是进入实际实现，并在实现过程中对具体技术细节做局部决策。
