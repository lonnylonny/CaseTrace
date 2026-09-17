> 历史归档（2026-09-16）：本文件不是当前要求、状态或 Agent 指令；后续任务以 [Current Plan](../../../project/current-plan.md) 为准。原文中的“当前”“已完成”“冻结”等仅对应历史时点。

# Stage 2 — AI Task Design

## 阶段目标

确定 CaseTrace 的核心 AI 任务、辅助任务、输入输出、Ground Truth、人机边界和基本评估方向。具体模型、算法、字段、指标和系统架构留到后续阶段决定。

## 最终任务设计

### V1 技术主线

```text
Current Incident
      ↓
B — Relevant Historical Case Retrieval
      ↓
C — Historical Cause Extraction
      ↓
D — Historical Evidence Checkpoint Extraction
      ↓
Engineer Investigation and Judgment
```

| 定位 | 任务 | 作用 |
|---|---|---|
| Core Task | B — Relevant Historical Case Retrieval | 找到真正值得工程师参考的历史案例 |
| Supporting Task | C — Historical Cause Extraction | 提取相关案例中已确认的历史原因 |
| Supporting Task | D — Historical Evidence Checkpoint Extraction | 提取历史上针对这些原因实际做过的检查 |
| Supporting Utility | A — Current Incident Field Extraction | 将工程师输入的当前异常信息结构化 |
| V2 Expansion | F — Production Variation Screening | 从生产数据中寻找值得关注的变化 |

其中 B 是入口和核心任务，C、D 依赖 B 的结果，不是三个互相独立的模块。

---

## B — Relevant Historical Case Retrieval

### 任务

给定一个 Current Incident，从已结案的 Historical Cases 中找出对当前调查具有具体关联或参考价值的案例。

重点不是两段文字是否相似，而是：

> 这个历史案例是否值得工程师为了当前异常去查看？

### Relevance 类型

| 类型 | 判断依据 | 调查价值 |
|---|---|---|
| Incident / Context Linkage | 同产品、关联 lot、相近生产时间或相同生产背景，Failure Mode 可以不同 | 判断多个异常是否属于同一生产异常、时间窗口异常或 systemic issue |
| Repeat / Recurrence | 同产品且 Failure Mode 相同或高度相似 | 识别重复发生、改善措施失效或 recurrence |
| Technical Analog | 产品不同，但 Failure Mode 和 Process Context 有足够技术共性 | 借鉴过去实际出现过的 Cause 和调查路径 |

一个历史案例可以同时属于多个 Relevance 类型。

### 排除范围

如果两个案例在 Product、Failure Mode 和 Process Context 上都缺少具体关联，只能提供通用调查方法，则它属于 Generic Investigation Knowledge，不属于 B 的 Relevant Historical Case。

### Ground Truth

标注单位是：

```text
Current Incident × Historical Case
        ↓
Relevant?  Yes / No / Ambiguous
        ↓
Relevance Type(s) + Annotation Rationale
```

判断必须只使用 Current Incident 在当时已经拥有的信息，不能使用后来确认的 Root Cause，否则会产生 information leakage。历史案例已经结案，因此可以使用其 Root Cause 和 Investigation Record 辅助人工标注。

第一版不强行使用统一的数字相关性分数。

### Evaluation 方向

B 属于 Retrieval / Ranking Task。

漏掉关键案例的代价通常高于多返回少量噪声，因此采用：

> **Recall-first，Precision 作为 guardrail。**

后续可评估 Recall@K、Precision@K 和 Ranking Metrics；K 值、MRR、nDCG 及标注一致性在数据与实验阶段确定。

---

## C — Historical Cause Extraction

### 任务

从 B 返回的历史案例中，忠实提取报告已经明确记录的 Cause、Root Cause 或 Contributing Cause，并形成可供工程师参考的 Historical Cause Space。

示例：

```text
Relevant Cases
  ├─ Case 1 → Carrier contact
  ├─ Case 2 → Operator handling
  └─ Case 3 → Packaging contact
```

### 边界

C 是 **Extraction**，不是 Root Cause Prediction。系统不能根据调查内容推断报告中没有明确确认的新原因。

### Ground Truth 与评估

Ground Truth 来自 Historical 8D / 6C 中明确记录的原因，因此可评估性较高。具体抽取指标以及相近原因的 normalization 规则，在实现 C 时确定。

---

## D — Historical Evidence Checkpoint Extraction

### 任务

根据 C 提取的 Historical Causes，从历史调查记录中提取过去真实执行过、并与相应 Cause 有关的 Evidence Checks / Investigation Actions。

示例：

```text
Cause: Carrier-related damage
Historical Evidence Checkpoints:
- carrier condition
- carrier type
- lot/carrier mapping
- replacement history
- equipment contact position
```

### 设计原则

优先复用真实发生过的调查经验，因为理论上合理的检查项目可能受到数据、设备、成本或工厂流程限制，未必能在实际生产中执行。

D 不是把整份 8D 的所有检查项目全部列出，而是建立清晰关系：

```text
Historical Cause
      ↓
过去针对该 Cause 实际做过的检查
      ↓
Historical Evidence Checkpoints
```

### 边界与 Ground Truth

V1 只展示历史记录中真实执行过的检查，不把 LLM 自行生成的建议混入 Historical Evidence。未来如增加 Generated / General Investigation Suggestions，必须与历史证据分开展示。

Ground Truth 来自 Historical Investigation Record 中的真实检查动作及其与 Cause 的对应关系。

---

## A — Current Incident Field Extraction

A 是输入辅助工具，不是项目的技术主线。V1 由工程师提供：

- Product；
- Lot；
- Customer complaint；
- Failure mode；
- Affected quantity / Defect rate；
- Other observations；
- Free text。

系统可将这些信息结构化。照片和视频暂由工程师判断后输入结论，V1 不做 Computer Vision。

Domain Knowledge 只使用现实中明确存在的内容，例如 Specification、Quality Agreement 和 OCAP，不为了展示技术而虚构庞大知识库。

---

## F — Production Variation Screening（V2）

### 任务

从 Current Incident 的生产数据中发现值得工程师关注的变化：

- **F1 Explicit Events：** OCAP、AOI、Hold、Rework；
- **F2 Comparative Variations：** Equipment、Route、Process Time、Production Context 差异；
- **F3 Numerical Variations：** 参数偏移、分布差异和数值异常。

F 只说明“哪里发生了变化”，不直接把变化判定为 Root Cause。

```text
Production Data → Observed Variations → Engineer Validation → Root Cause
```

### 延后原因

F2 需要定义合理的 reference population，F3 还依赖统计方法和可信的模拟数据。为了控制第一个版本的范围，F 放入 V2；B→C→D 已经能够形成完整的 AI/CS 技术主线。

---

## 人机边界与暂不决定的内容

### 系统负责

- 整理 Current Incident 信息；
- 检索和排序相关历史案例；
- 提取历史案例中明确记录的原因；
- 提取历史上真实执行过的调查检查点；
- 清楚说明信息来自哪里。

### 工程师负责

- 判断系统返回的信息是否适用于当前现场；
- 决定实际调查动作；
- 验证或排除假设；
- 确认最终 Root Cause 和 Corrective Action。

### 后续阶段再决定

- 是否使用 RAG、Embedding、Reranker、Knowledge Graph 或 Agent；
- 具体 LLM、数据库、FastAPI、UI 和部署方案；
- 详细数据字段、阈值、Metrics 和系统架构。

技术选择应在 MVP 范围、数据和评估方案基本明确后进行。

## 阶段结论

Stage 2 已完成：

- 核心任务确定为 B — Relevant Historical Case Retrieval；
- C、D 作为依赖 B 的辅助任务；
- A 作为输入辅助工具；
- F 作为 V2 扩展；
- Ground Truth、Evaluation 方向和 Human-AI Boundary 已明确到当前阶段所需程度。

下一阶段是 **Stage 3 — MVP Scope**，只确定：

- V1 覆盖哪些 Case 类型；
- B、C、D 分别做到什么程度；
- 哪些功能不进入 MVP；
- Demo 的完整工作流；
- 如何把范围控制在能够实现、实验和完成作品集的规模内。