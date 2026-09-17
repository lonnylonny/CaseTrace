> 历史归档（2026-09-16）：本文件不是当前要求、状态或 Agent 指令；后续任务以 [Current Plan](../../../project/current-plan.md) 为准。原文中的“当前”“已完成”“冻结”等仅对应历史时点。

# Stage 3 — MVP Scope

## 阶段目标

确定 CaseTrace V1 的范围边界，使后续数据设计、技术设计和实现建立在一个完整但可控的 MVP 上。

本阶段确定：

- V1 覆盖什么类型的 Case；
- A、B、C、D 分别做到什么程度；
- 完整 Demo 如何运行；
- 哪些内容明确不进入 V1；
- V1 需要满足的最低可评估性与工程成熟度约束。

具体数据规模、字段、模型、算法、指标、系统架构和实现方式留到 Stage 4–6 决定。

## 3.1 Case Scope

### 模拟环境边界

V1 使用 Bounded Synthetic Environment，范围冻结为：

- 少量模拟产品；
- 有限制程与流程差异；
- 必要的客户要求与规格差异；
- 多种具有代表性的常见 Failure Modes；
- 使用一组已结案 Historical Cases 支撑检索、原因提取和检查点复用。

复杂性主要来自 Case 之间的关系与调查差异，而不是不断扩大产品、流程和规则数量。

### 必须覆盖的案例关系

- **Repeat / Recurrence：** 同产品、相同或高度相似的 Failure Mode；
- **Incident / Context Linkage：** 生产时间、lot、设备或生产背景存在关联；
- **Technical Analog：** 产品不同，但 Failure Mode 和 Process Context 具有技术共性；
- **Hard Negative：** 表面相似，但实际不应被判断为相关；
- **Ambiguous Case：** 现有信息不足以明确判断是否相关。

### 数据设计约束

模拟数据需要业务逻辑合理、内部一致，并能形成非平凡的检索问题。不能让系统仅靠固定模板、单一字段或数据生成规律直接得到答案。

V1 不追求：

- 覆盖完整半导体封装流程；
- 覆盖所有产品或 Failure Modes；
- 模拟完整 MES / QMS / SPC 环境；
- 为增加 Case 数量持续引入新的工艺、设备和规则；
- 完全复刻真实工厂的数据规模与分布。

---

## 3.2 Functional Scope

### A — Current Incident Input

V1 包含：

- Structured Input 和 Free Text；
- 轻量 LLM Structured Extraction；
- 允许缺失字段为空；
- 同时保留原始输入与结构化结果，便于追溯。

V1 不包含 Computer Vision、复杂 OCR、MES/QMS 自动接入、缺失数据自动补全和自动 Failure Mode 判断。

### B — Relevant Historical Case Retrieval

B 是 V1 的核心 AI 任务和主要实验对象。

V1 必须实现：

- Historical Case Retrieval 和 Ranking；
- 支持不同 Relevance 类型；
- 输出 Relevance Type；
- 提供简短、可追溯的 Relevance Rationale；
- 提供 Source Traceability；
- 控制 Information Leakage；
- 建立 Ground Truth；
- 提供至少一个简单 Baseline；
- 完成 Offline Evaluation 和 Error Analysis。

V1 建议包含：

- Two-stage Retrieval：Candidate Retrieval → Reranking；
- Hybrid Retrieval：Semantic + Lexical + Metadata；
- 基础 Metadata-aware Retrieval / Ranking。

V1 不包含：

- Knowledge Graph / GraphRAG；
- Learning-to-Rank 自训练模型；
- Embedding Fine-tuning；
- Reranker Fine-tuning；
- Online Learning；
- Multi-agent Retrieval；
- 大规模搜索基础设施优化；
- 复杂 Query Expansion；
- 复杂 Relevance Score Calibration。

这些方向可根据 V1 Error Analysis 再决定是否进入 V2。

### C — Historical Cause Extraction

V1 必须实现：

- 提取历史报告中明确记录的 Cause、Root Cause 或 Contributing Cause；
- 输出结构化结果；
- 保留 Cause 与 Source Case 的对应关系；
- 提供 Source Traceability；
- 不推断历史报告中没有明确记录的新 Cause。

V1 建议包含轻量 Cause Normalization，用于合并明显等价或高度相近的 Cause 表达。

V1 不包含：

- 当前异常 Root Cause Prediction；
- 自动生成新的 Cause；
- 复杂 Cause Ontology；
- 概率化 Cause Prediction。

### D — Historical Evidence Checkpoint Extraction

V1 必须实现：

- 提取历史记录中真实执行过的 Evidence Checks / Investigation Actions；
- 建立 Cause → Checkpoint 关系；
- 区分检查动作与记录中的 Observed Result；
- 支持一个 Cause 对应多个 Checkpoints；
- 支持跨多个 Historical Cases 汇总；
- 提供 Source Traceability；
- 将历史证据与任何生成内容明确区分。

V1 建议包含：

- 轻量 Checkpoint Normalization；
- 跨 Case Cause / Checkpoint Summary。

V1 不包含：

- 自动生成完整 Investigation Plan；
- 自动决定下一步必须检查什么；
- 自动执行调查；
- Root Cause Hypothesis Generation；
- 因果图 / Bayesian Network；
- Autonomous Investigation Agent。

### F — Production Variation Screening

F 整体移至 V2，不进入 V1。

---

## 3.3 End-to-End Demo

```text
Current Incident Input
        ↓
Structure Incident
        ↓
Retrieve and Rank Historical Cases
        ↓
Show Relevance Type, Rationale and Source
        ↓
Engineer selects / expands cases
        ↓
Show Historical Causes
        ↓
Show Related Evidence Checkpoints + Observed Results
        ↓
Trace back to source case / evidence
        ↓
Engineer Continues Investigation
```

### 展示层级

```text
Incident
   ↓
Relevant Historical Cases
   ↓
Historical Investigation Evidence
```

系统可以对用户选中的多个案例进行以下汇总：

```text
Selected Cases
      ↓
Historical Cause Space
      ↓
Checkpoint Summary
```

Demo 的终点是：

> 工程师获得一组可追溯的历史案例、历史原因和历史调查检查点，用于继续调查。

系统不输出当前异常的最终 Root Cause，也不替代工程师做最终判断。

---

## 3.4 Scope Freeze

### V1 必须满足的横向约束

#### 1. Evaluability

核心 AI 输出必须能够建立 Ground Truth 或可重复的评估方法。标注规则和数据集在 Stage 4 确定，详细 Metrics 和实验设计在 Stage 6 确定。

#### 2. Synthetic Data Credibility

训练、开发和测试数据必须合理隔离，并避免模板、字段或生成逻辑泄漏答案。具体生成和划分方法在 Stage 4 设计。

#### 3. MVP Maturity

V1 定位为 **Production-aware AI Prototype**：高于一次性 Notebook 或 Toy Demo，但不要求达到企业 Production-ready System 的复杂度。

实现阶段需要具备基本的软件工程质量，包括可复现运行、必要测试、日志和基础性能/成本记录。

---

## V1 Out of Scope Summary

- 完整半导体封装业务覆盖；
- Production Variation Screening；
- 当前异常 Root Cause 自动预测；
- 模型 Fine-tuning；
- Knowledge Graph / GraphRAG；
- Autonomous / Multi-agent Investigation；
- Computer Vision 与复杂多模态系统；
- 企业 MES/QMS 集成；
- 企业级权限、安全、在线学习和大规模基础设施优化。

## 后续阶段的决策

| 阶段 | 待确定内容 |
|---|---|
| Stage 4 — Data Design | 模拟环境、数据来源、Case 设计、Ground Truth、标注规则和测试数据 |
| Stage 5 — Technical Design | 模型、检索策略、系统架构、数据库、API、UI 和部署方案 |
| Stage 6 — Implementation & Evaluation | 详细 Metrics、实验、测试、性能成本记录和 Error Analysis |

## 阶段状态

**已完成。** 下一阶段进入 **Stage 4 — Data Design**，在已冻结的范围内设计模拟环境、Historical Cases、Ground Truth 和测试数据。
