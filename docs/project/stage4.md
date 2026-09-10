# Stage 4 — Data Design

## 阶段目标

在 Stage 1–3 已冻结的项目主干上，为 CaseTrace V1 设计可信、可评估、可追溯的数据体系。

Stage 4 只确定：

- 数据体系与数据角色；
- Synthetic Environment 的边界；
- Case Corpus 的构造原则；
- Ground Truth / Annotation 的基本设计；
- Dataset Split / Benchmark 原则；
- Data Quality、Leakage 与 Documentation 原则。

当前阶段继续遵循项目总原则：

> 只确定大框架、核心边界和必要取舍，不提前深入字段、样本量、Prompt、模型、数据库结构或具体实现细节。

项目重点仍然是学习通用 AI / CS 能力。半导体封装是 Case Study 和业务约束，不扩展成完整制造业仿真、知识工程或因果研究项目。

---

# Stage 4 总体结构

```text
4.1 Data Strategy & Dataset Architecture
            ↓
4.2 Synthetic Environment Blueprint
            ↓
4.3 Case Corpus Construction
            ↓
4.4 Ground Truth & Annotation Design
            ↓
4.5 Dataset Split & Benchmark Design
            ↓
4.6 Data Quality, Leakage & Documentation
```

---

# 4.1 — Data Strategy & Dataset Architecture

## 4.1.1 分层 Dataset Architecture

不建立“一份万能 Case 数据集”，而是从逻辑上区分：

```text
Environment / Domain Definition
        ↓
Canonical Case Data
        ↓
Historical Case Corpus
        ↓
Current Incident Queries
        ↓
Task Ground Truth
        ↓
Evaluation Dataset
```

这些是逻辑数据角色，不代表必须对应不同文件、表或数据库。

---

## 4.1.2 Canonical Truth 与系统可见数据分离

Synthetic Environment 中存在完整的“世界真相”，但 AI 在不同阶段只能看到对应的信息视图。

```text
Canonical Truth
      ↓
不同的信息视图
      ├─ Current Incident View
      └─ Historical Closed Case View
```

Current Incident 只能包含事故当时已经获得的信息，不能泄漏后来确认的 Root Cause 等未来信息。

核心目的：

- 防止 information leakage；
- 保证 point-in-time correctness；
- 为后续 Evaluation 建立可信基础。

---

## 4.1.3 Historical Case 与 Current Incident 是两个不同的数据角色

```text
Historical Case
= Retrieval Corpus / Knowledge Source

Current Incident
= Query
```

因此 B — Relevant Historical Case Retrieval 本质上采用标准 Information Retrieval 问题结构：

```text
Query
↓
Historical Corpus
↓
Relevant Historical Cases
```

---

## 4.1.4 Canonical Truth 与 Task Ground Truth 分离

两者含义不同：

- **Canonical Truth：** 这个模拟世界真实发生了什么；
- **Task Ground Truth：** 对某个 AI Task 来说，标准答案是什么。

例如：

```text
Canonical Truth:
两个 Case 最终 Root Cause 相同

≠

B Ground Truth:
两个 Case 一定 Relevant
```

B 的标签必须依据“当前 Incident 已知信息下，该 Historical Case 是否值得工程师查看”来判断，而不能直接使用未来 Root Cause。

---

## 4.1.5 Synthetic Data 采用 Scenario-first

不采用：

```text
LLM → 随机生成一批 Case → 再判断它们之间的关系
```

采用：

```text
Environment
   ↓
Scenario / Relationship
   ↓
Canonical Case
   ↓
Structured / Unstructured Representation
```

即：

> 先决定发生了什么，再决定数据表现成什么样。

---

## 4.1.6 Structured + Unstructured Representation

一个 Case 同时具有：

```text
Structured Representation
+
Unstructured Representation
```

目的：

- 支持 metadata-aware retrieval；
- 支持 lexical / semantic / hybrid retrieval；
- 支持 C / D 的自然语言 Extraction；
- 学习结构化数据与非结构化文档结合的 AI 系统设计。

当前不确定具体字段、Schema 或存储方式。

---

## 4.1.7 Development 与 Locked Evaluation Data 隔离

原则确定：

```text
Development Data
≠
Final / Locked Evaluation Data
```

最终 Evaluation 数据不能长期反复用于调系统。

具体：

- 数据规模；
- Split 比例；
- Group split 的具体实现；
- Temporal split 是否落地；

留到后续实现阶段再定。

---

# 4.2 — Synthetic Environment Blueprint

## 4.2.1 Case-centered Environment

采用 **Case-centered / Case-relationship-first**，不采用完整 Process Simulation。

原因：

1. 更符合质量人员实际使用和维护系统的方式；
2. 用户对 Case 工作方式更熟悉，数据构造更可信；
3. CaseTrace 的核心任务就是 Historical Case Retrieval；
4. 避免项目演变成完整 Semiconductor Process Simulation。

---

## 4.2.2 小而有结构的 Product / Process Space

采用。

Synthetic Environment 使用：

- 少量 Product / Product Families；
- 少量 Process Context；
- 有限 Equipment / Route / Production Context variation。

复杂度来自 Case 之间的关系，而不是不断扩大产品和工艺数量。

具体数量暂不确定。

---

## 4.2.3 Failure Mode ↔ Cause 必须 many-to-many

必须保留。

不能设计成：

```text
Scratch → Cause A
Oxidation → Cause B
Crack → Cause C
```

这种固定一一对应关系。

应允许：

```text
Failure A
├─ Cause 1
├─ Cause 2
└─ Cause 3

Cause 1
├─ Failure A
└─ Failure B
```

目的：

- 避免 Retrieval 退化成 Failure Mode 关键词匹配；
- 迫使系统综合 Product、Failure、Process Context、Time / Lot 等信息；
- 让 Historical Cause Space 和 Checkpoint Summary 真正具有意义。

---

## 4.2.4 允许 Case Family / Incident Cluster

采用。

环境中允许：

```text
Case Family
├─ Case A
├─ Case B
└─ Case C
```

Case Family 可以形成：

- Repeat / Recurrence；
- Incident / Context Linkage；
- 相同或相关 Cause；
- 同设备 / 同生产窗口等关系。

同时为后续 group-aware split 与 leakage testing 提供基础。

---

## 4.2.5 Domain Knowledge 只建立必要的小知识层

采用。

只保留真正影响 Case Interpretation 的现实知识，例如：

- Specification；
- Quality Agreement；
- OCAP；
- 必要 Product / Process Context。

明确不建立：

- 完整半导体知识库；
- 完整工艺 ontology；
- 大型 SOP / OCAP tree；
- Knowledge Graph。

原因：

- 现实数据难以获得；
- 半导体只是项目背景；
- 项目重点应放在通用 AI / CS 学习。

---

## 4.2.6 模拟与 AI 任务有关的现实不完美

采用。

允许存在：

- Missing Information；
- Terminology Variation；
- Different Documentation Depth；
- Irrelevant Details；
- Partial Investigation Records。

但不故意大量模拟：

- OCR 错误；
- PDF parsing 错误；
- 乱码；
- 极端脏数据；
- 复杂文件格式问题。

原则：

> 只模拟会影响 Retrieval / Extraction 判断的现实噪声，不把项目转成 Data Cleaning / Document Parsing 项目。

---

## 4.2.7 Scenario-level Hard Negative

采用。

Hard Negative 必须从 Scenario 层设计，而不是后期随便找一个“看起来像”的负样本。

理想关系：

```text
表面高度相似
+
关键关系不成立
↓
Relevant = No
```

例如：

- Product 相同；
- Failure Mode 相似；
- Process 类似；

但真正的时间、位置、生产背景或技术上下文不足以建立工程关联。

目的：

- 形成真实 Retrieval 难度；
- 支撑 Ranking / Negative Sampling / Error Analysis；
- 避免模型只靠浅层关键词匹配。

---

## Formal Causal Model 的边界

### V1 不建立完整 Causal Model

已明确决定：

**暂不做 Formal Causal Model / Causal Inference。**

保留：

```text
业务合理的因果逻辑
Cause–Failure many-to-many
Cause–Evidence consistency
Cause–Checkpoint consistency
```

不做：

- 完整 Causal DAG；
- Bayesian Network；
- Structural Causal Model；
- Counterfactual Inference；
- Causal Discovery；
- Causal Effect Estimation。

原则：

> 保留 causal plausibility，不建立 formal causal model。

如果未来 V2 进入 Production Variation Screening / 更复杂 Root Cause reasoning，再重新评估是否需要。

---

# 4.3 — Case Corpus Construction

本节确定 Case Corpus 如何从已定义的 Synthetic Environment 中被构造出来。

---

## 4.3.1 Scenario-first / Canonical Case-first

本节沿用 4.1.5 的 Scenario-first 原则：Case 必须从已定义 Scenario 构造，而不是让 LLM 先自由生成文档后再反推事实。

```text
Scenario Definition → Canonical Case
→ Structured Representation + Unstructured Representation
```

这样可以保证 Case 逻辑可控，使关系、Cause 与 Ground Truth 可追溯，并避免生成文本反过来决定世界事实。

---

## 4.3.2 Human + Program + LLM 分工

采用：

### Human

负责：

- Environment Rules；
- Scenario Design；
- Case Relationships；
- 业务合理性判断；
- 关键边界。

### Program

负责：

- 结构化组合 / 数据构造；
- ID / 时间 / 关系管理；
- Consistency Checking；
- Reproducibility；
- 批量生成。

### LLM

负责：

- 自然语言表达；
- Investigation / Report Text；
- Terminology Variation；
- 文档表达与完整度变化。

高层 Pipeline：

```text
Human-designed Logic
        ↓
Programmatic Construction
        ↓
LLM Text Realization
        ↓
Validation
```

这一分工用于把：

- Domain / Scenario Logic；
- Data Engineering；
- LLM Text Generation；

三个问题分开处理。

---

## 4.3.3 LLM 不负责决定 Canonical Truth / Ground Truth

原则：

```text
Canonical Truth
↓
LLM 将事实表现成自然文本
```

而不是：

```text
LLM 同时生成事实 + 文本 + 标签
```

LLM 可以负责“怎么写”，但不负责决定：

- Root Cause；
- 核心 Scenario；
- Case Relationship；
- Ground Truth。

目的：

- 防止“模型自己生成数据、自己给答案、再自己评估”的闭环；
- 提高 Evaluation 的独立性；
- 让 Dataset 的事实来源可控。

---

## 4.3.4 Case Family / Scenario Cluster 整体构造

不逐个随机生成 Case，而是优先以：

```text
Case Family / Scenario Cluster
          ↓
    ┌─────┼─────┐
 Case A  Case B  Case C
```

作为生成单位。

Case Family 内可以形成：

- Repeat / Recurrence；
- Context Linkage；
- Technical Analog；
- Hard Negative；
- Ambiguous relationships。

目的：

- 让 Case Relationship 自然来自 Scenario；
- 为后续 Group Split、Leakage Control 和 Error Analysis 提供基础。

---

## 4.3.5 Case 是逻辑实体，Structured + Unstructured 是其表示

Case 不强制等于单一文档。

逻辑上：

```text
Case
├─ Structured Metadata
├─ Incident Description
├─ Investigation Record
├─ Conclusion / Cause
├─ Evidence Checkpoints
└─ Supporting Evidence
```

未来具体可能以：

- JSON；
- 数据库记录；
- Markdown；
- 文本文档；

等形式呈现。

原则：

> Domain Entity ≠ Storage Format ≠ Document Format。

V1 不需要模拟复杂 Excel / PPT / PDF / Email 文件生态。

---

## 4.3.6 Controlled Variation

数据多样性采用“有目的的受控变化”，例如：

- wording variation；
- detail level；
- missing information；
- terminology variation；
- irrelevant information；
- 信息顺序变化。

不采用完全随机 Noise。

目的：

> 检验 Retrieval / Extraction 能否理解内容，而不是记住模板。

不把 Stage 4 扩展成复杂 OCR、PDF Layout 或脏数据研究。

---

## 4.3.7 Generation Provenance 可追踪

每个 Synthetic Case 至少在逻辑上能够追溯：

```text
Case
↓
Generation Process
↓
Scenario
↓
Case Family
↓
Dataset Version
```

用于：

- reproducibility；
- debugging；
- dataset versioning；
- data quality review；
- regeneration；
- leakage investigation。

当前不确定具体 provenance 字段。

---

# 4.4 — Ground Truth & Annotation Design

本节解决：

> 对 B / C / D 来说，什么才算“标准答案”。

核心概念：

```text
Scenario Truth
真实世界发生了什么
        ↓
Annotation Policy
这道 AI 任务应该怎样判断
        ↓
Task Ground Truth
标准答案
```

---

## 4.4.1 B 使用 Pair-level Relevance Judgment

B 的标注单位为：

```text
Current Incident
      ×
Historical Case
      ↓
Relevance Label
```

即针对一个 Current Incident，判断每一个 Historical Case 是否值得工程师参考。

这是后续 Information Retrieval Evaluation 的基础。

---

## 4.4.2 B 保留三分类

```text
Relevant
Not Relevant
Ambiguous
```

不强行压缩成 Yes / No。

Ambiguous 用于表示：

> 在当前已经掌握的信息下，无法可靠判断这个 Historical Case 是否具有足够关联。

目的：

- 保留真实的不确定性；
- 避免人为制造假的确定标签；
- 为后续 Label / Annotation Uncertainty 提供基础。

具体 Ambiguous 如何计入指标留到 Stage 6。

---

## 4.4.3 Relevant Case 同时标 Relevance Type

沿用 Stage 2 已冻结的三类：

```text
Incident / Context Linkage
Repeat / Recurrence
Technical Analog
```

允许：

```text
Multi-label
```

即一个 Historical Case 可以同时属于多个 Relevance Type。

目的：

- 支持系统展示“为什么相关”；
- 支持后续按不同 Relevance Type 做 Error Analysis。

---

## 4.4.4 Point-in-time Annotation

B 的相关性判断必须只使用：

```text
Current Incident 当时已经知道的信息
+
Historical Case 已结案的信息
```

不能使用：

```text
Current Incident 后来确认的 Root Cause
```

这是防止 information / temporal leakage 的核心原则。

例如：

```text
Current Incident 最终 Cause
=
Historical Case Root Cause
```

不能因此直接标记：

```text
Relevant = Yes
```

因为真实检索发生时，当前 Incident 的最终 Root Cause 尚未知。

---

## 4.4.5 Scenario Truth → Annotation Policy → Ground Truth

本节沿用 4.1.4 对 Canonical Truth 与 Task Ground Truth 的区分。即使 Current Incident 与 Historical Case 的最终 Cause 相同，也不自动等于 `Relevant = Yes`。B 仍然需要依据独立 Relevance Policy 判断：

> 在 Current Incident 当前已知信息下，该 Historical Case 是否值得工程师查看。

这一区分用于保证 `Task Definition ≠ Raw Data Truth`。

---

## 4.4.6 Hard Negative 正式进入 Ground Truth

Hard Negative 定义为：

```text
Not Relevant
+
具有较强表面相似性
```

例如：

```text
Same Product
Same Failure Mode
Similar Description
        ↓
但关键生产背景 / 技术关系不成立
        ↓
Not Relevant
```

Benchmark 中同时保留：

- 普通 Negative；
- Hard Negative。

具体比例后续再定。

目的：

- 检验系统是否只依赖浅层相似性；
- 支撑 Negative Sampling；
- 支撑 Hard Negative Evaluation；
- 支撑 Error Analysis。

---

## 4.4.7 B Ground Truth 保留 Rationale + Evidence Traceability

逻辑上保留：

```text
Label
+
Relevance Type
+
Annotation Rationale
+
Supporting Evidence
```

例如：

```text
Relevant = Yes
Type = Incident Linkage

Rationale:
Same product family and same equipment during
the same production window.

Evidence:
Current Incident → Equipment E03, Week 12
Historical Case → Equipment E03, Week 12
```

目的：

- 审核 Label；
- Debugging；
- Error Analysis；
- Explainability；
- Traceability。

具体字段以后再定。

---

## 4.4.8 C / D 使用 Source-grounded Ground Truth

### C — Historical Cause Extraction

```text
Historical Source
      ↓
明确记录的 Cause
      ↓
C Ground Truth
```

C 只提取历史报告明确记录的 Cause / Root Cause / Contributing Cause。

不允许 LLM 根据调查内容自行推测一个新的 Cause。

---

### D — Historical Evidence Checkpoint Extraction

```text
Historical Investigation Record
      ↓
实际执行的 Check
      ↓
Cause ↔ Checkpoint Ground Truth
```

必须区分：

```text
Checkpoint
≠
Observed Result
```

例如：

```text
Checkpoint:
Check carrier condition

Observed Result:
Scratch found on carrier edge
```

D 只提取历史调查中真实执行过的检查动作及其与 Cause 的关系。

---

## 4.4.9 轻量 Human Review / Adjudication

V1 不要求完整多人标注研究。

采用：

```text
Programmatic Candidate Annotation
        ↓
Human Review
        ↓
必要时修正 / Adjudication
```

尤其用于：

- Technical Analog；
- Ambiguous；
- 其他存在业务判断空间的 Case。

V1 不强制：

- 双人独立标注；
- Cohen's Kappa；
- 完整 disagreement study。

目的：

> 学习基本 annotation workflow，同时避免项目扩展成专门的标注研究。

---

# 4.5 — Dataset Split & Benchmark Design

本节解决：

> 怎样划分数据，才能让最后的 Evaluation 真正检验系统对“没见过的新 Case”的能力，而不是记住 synthetic data 的生成规律。

---

## 4.5.1 Development / Locked Test Separation

4.1.7 确定的隔离原则在 Benchmark 中必须严格执行：

```text
Development Data
      ≠
Locked Test / Evaluation Data
```

Development 可用于：

- 调 Retrieval；
- 调 Prompt；
- 选择模型；
- 设计 Metadata；
- Debug；
- Error Analysis。

Locked Test 不长期反复用于系统调优。

目的：

- 防止 Test-set Overfitting；
- 防止 Model Selection Bias；
- 保证最终评估相对可信。

---

## 4.5.2 Case-Family / Scenario-Level Group Split

Split 的核心单位不是单个 Case，而是：

```text
Case Family / Scenario Group
```

例如不能：

```text
Case A1 → Development
Case A2 → Test
Case A3 → Test
```

如果 A1 / A2 / A3 属于同一个 Case Family。

原则：

```text
Case Family A → 整体进入一个 Split
Case Family B → 整体进入另一个 Split
```

目的：

- 防止 Group Leakage；
- 避免测试集实际上只是开发集同一 Scenario 的近重复数据。

---

## 4.5.3 Scenario-level Generalization

Test 不应该只是 Development 数据的模板复制。

要求至少保证：

- Test Case 没有直接复制 Development Scenario；
- 不通过模板 ID、Case Family 或生成规律泄漏答案；
- Test 中包含新的 Scenario Instance 和一定程度的新组合。

V1 不扩展成正式 OOD / Domain Generalization 研究。

---

## 4.5.4 Retrieval-native Benchmark

B 的 Benchmark 必须保持真实 Retrieval 结构：

```text
Current Incident Query
          ↓
Historical Case Corpus
          ↓
Retrieve Top-K
          ↓
Ground Truth Relevant Set
```

Benchmark 逻辑上至少包含：

```text
Query Set
+
Historical Corpus
+
Relevance Judgments / qrels
```

其中 qrels 表示：

> 每个 Query 对哪些 Historical Cases 属于 Relevant / Not Relevant / Ambiguous 的标准判断。

不把 B 简化成少量候选中的二选一分类题。

---

## 4.5.5 Evaluation Difficulty Coverage

Locked Test 中必须覆盖不同难度：

```text
Easy Positive
Hard Positive

Easy Negative
Hard Negative

Ambiguous
```

目的：

> 防止 Benchmark 只测试“明显相似 vs 完全不同”的简单情况。

---

## 4.5.6 Relevance-Type Coverage

Test 中必须覆盖：

```text
Repeat / Recurrence
Incident / Context Linkage
Technical Analog
```

目的：

- 不让总体指标掩盖某一类 Retrieval 的明显缺陷；
- 支持按 Relevance Type 做 Error Analysis。

当前只要求 coverage，不确定：

- 每类数量；
- 是否严格平衡；
- 各类权重。

---

## 4.5.7 Group-aware Split 为 V1 主方案

V1 主 Benchmark 使用：

```text
Group-aware / Scenario-aware Split
```

Temporal Split 不作为 V1 必须项。

原因：

- Synthetic Environment 中时间本身也是生成的；
- 如果为了 Temporal Split 强行增加 Product Lifecycle、Equipment Drift、Distribution Shift 等机制，会显著扩大项目。

可以保留未来扩展：

```text
Optional Secondary Benchmark:
Temporal-style Evaluation
```

但 Stage 4 不进一步设计。

---

## 关于 Train / Dev / Test 的边界

CaseTrace V1 当前不进行模型 Fine-tuning，因此不机械要求传统：

```text
Train / Validation / Test
```

V1 可以采用：

```text
Development Dataset
├─ Development Corpus
├─ Development Queries
└─ Development Ground Truth

Locked Test Benchmark
├─ Test Corpus
├─ Test Queries
└─ Locked Ground Truth
```

未来如果进入：

- Learning-to-Rank；
- Fine-tuning；
- Learned Classifier；

再进一步拆分：

```text
Train
Dev
Test
```

原则：

> Dataset Split 应服务于实际 ML Task，而不是为了形式上像机器学习项目。

---

# 4.6 — Data Quality, Leakage & Documentation

本节目标：

> 保证前面设计的数据可信、可复现、不会偷偷泄漏答案，而且以后可以维护、调试和解释。

---

## 4.6.1 Data Validation

生成数据之后必须进行基本检查，例如：

- 必要信息是否缺失；
- Case Relationship 是否自相矛盾；
- 时间顺序是否合理；
- Cause / Failure / Checkpoint 是否符合 Scenario；
- Structured / Unstructured 是否互相冲突。

目的：

> Synthetic Data 最大的风险之一，是生成大量“看起来合理、实际上内部错误”的数据。

---

## 4.6.2 Leakage Checks

必须检查 AI 是否通过不应该看到的信息提前获得答案。

至少关注：

```text
Current Incident
不能出现未来 Root Cause

Development
不能泄漏 Locked Test 的 Scenario

Case Family
不能跨不同 Split 泄漏

文本中
不能留下明显标签或生成模板线索
```

目的：

> 如果存在 Leakage，最终 Benchmark 指标再高也没有意义。

---

## 4.6.3 Shortcut / Dataset Artifact Checks

Synthetic Generator 可能无意中留下“作弊线索”。

例如：

```text
Relevant Case
总是写得比较长

Hard Negative
总是来自某个固定 Product ID

Technical Analog
总使用某种固定句式
```

模型可能利用这些规律，而不是学习真正的 Relevance。

因此需要检查：

- shortcut learning；
- dataset artifacts；
- spurious correlation。

Stage 4 只确认需要这类检查，不展开具体检测方法。

---

## 4.6.4 Cross-representation Consistency

同一个 Case 的不同表示必须保持一致：

```text
Canonical Truth
      ↕
Structured Data
      ↕
Generated Text
      ↕
Ground Truth
```

不能出现：

```text
Canonical Cause = Carrier Contact

Report Text = Operator Handling

Ground Truth = Carrier Contact
```

目的：

> 如果不同 Representation 自相矛盾，后面的 Retrieval / Extraction Evaluation 本身就不可信。

---

## 4.6.5 Data Versioning

Dataset 必须逻辑上可版本化。

例如：

```text
Dataset V1
Dataset V2
...
```

至少需要知道：

- 使用哪一版生成规则；
- 包含哪些 Scenario；
- 包含哪些 Case；
- 使用哪个 Benchmark；
- 哪次实验对应哪一版数据。

具体版本工具和文件结构留到实现阶段。

---

## 4.6.6 Reproducibility

数据生成过程原则上应能够重新运行。

逻辑上：

```text
Environment Config
+
Scenario Definitions
+
Generation Pipeline
+
Random Seed / Version
        ↓
Dataset
```

不要求每次 LLM 文本逐字完全相同，但至少以下内容应能稳定复现或追溯：

- 核心 Scenario；
- Case Relationships；
- Canonical Truth；
- Dataset Split。

---

## 4.6.7 Dataset Documentation

最终需要有一份简洁的数据说明，类似 Dataset Card。

至少说明：

```text
Dataset 用于什么任务

包含什么数据

数据如何生成

Ground Truth 如何建立

Dataset 如何 Split

有哪些已知限制

哪些内容属于 Synthetic
```

目的：

- 项目可维护；
- 实验可解释；
- 对 GitHub / Portfolio 更完整；
- 体现基本 AI Engineering 规范。

---

## 4.6.8 Explicit Synthetic Data Limitations

必须明确声明：

```text
Synthetic Environment
≠
真实工厂的数据分布

Offline Benchmark Performance
≠
真实生产环境效果
```

并说明：

- Scenario 是人为设计的；
- Domain Complexity 被刻意限制；
- 文档主要是合成数据；
- Evaluation 只能证明系统在该受控环境中的表现。

这是项目实验边界的一部分。

---

# Stage 4 最终数据 Pipeline

Stage 4 最终确定的数据逻辑为：

```text
Bounded Synthetic Environment
        ↓
Scenario / Case Family Design
        ↓
Canonical Case / Canonical Truth
        ↓
Programmatic Construction
        ↓
Structured Representation
        +
LLM-generated Unstructured Representation
        ↓
Validation / Consistency Check
        ↓
Historical Corpus + Current Incident Queries
        ↓
Annotation Policy
        ↓
Task Ground Truth
        ↓
Development Dataset
        +
Locked Test Benchmark
        ↓
Leakage / Artifact / Quality Checks
        ↓
Versioned & Documented Dataset
```

---

# Stage 4 范围边界

Stage 4 明确不做：

- 完整 Semiconductor Manufacturing Simulation；
- 完整 Process Simulation；
- 大型 Knowledge Base / Ontology；
- Knowledge Graph / GraphRAG；
- Formal Causal Model；
- Causal Inference；
- Production Variation Screening；
- Current Incident Root Cause Prediction；
- Complex OCR / PDF Parsing；
- Computer Vision；
- 企业 MES / QMS 数据接入；
- Fine-tuning；
- Learning-to-Rank Training；
- 大规模多人标注研究；
- 企业级 Data Governance。

这些内容只有在后续实际需要时再评估。

---

# Stage 4 最终状态

```text
Stage 4 — Data Design

4.1 Data Strategy & Dataset Architecture
✅ 已完成

4.2 Synthetic Environment Blueprint
✅ 已完成

4.3 Case Corpus Construction
✅ 已完成

4.4 Ground Truth & Annotation Design
✅ 已完成

4.5 Dataset Split & Benchmark Design
✅ 已完成

4.6 Data Quality, Leakage & Documentation
✅ 已完成
```

**Stage 4 — Data Design 已完成并冻结。**

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
⏳ 下一阶段

Stage 6 — Implementation & Evaluation
⏳ 未开始

Stage 7 — Portfolio
⏳ 未开始
```

---

# 当前项目主线保持不变

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

V1 仍然：

- 不自动判断当前 Root Cause；
- 不进入 Production Variation Screening；
- 不建立完整 Causal Model；
- 不做 Knowledge Graph / GraphRAG；
- 不做 Autonomous / Multi-agent Investigation；
- 不扩大成完整 Semiconductor Manufacturing Simulation。

---

# 下一阶段

## Stage 5 — Technical Design

Stage 5 将在 Stage 1–4 已冻结的主干上，确定：

- 系统总体架构；
- B — Retrieval 技术路线；
- C / D — Extraction 技术路线；
- LLM 在系统中的职责；
- 数据存储与检索层；
- Backend / API；
- UI / Demo；
- Traceability / Logging；
- Deployment / Engineering Boundary。

继续遵循同一原则：

> 先确定技术主干与必要取舍，不提前进入具体参数、代码、模型调优或实现细节。
