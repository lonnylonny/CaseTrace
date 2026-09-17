> 历史归档（2026-09-16）：本文件不是当前要求、状态或 Agent 指令；后续任务以 [Current Plan](../../../project/current-plan.md) 为准。原文中的“当前”“已完成”“冻结”等仅对应历史时点。

# CaseTrace

Case-centered Investigation Workspace For manufacturing quality engineers with IC packaging background.

## Status

[Done] Repository Set Up
[Done] Python / UV init
[Done] Git / Github init
[Done] Case Setting
[Done] Python Case Model
[Done] Small Development Samples + Local BM25 Demo
[] PostgreSQL Schema
[] Database
[] Synthetic Dataset
[] Benchmark
[Ongoing] BM25 Baseline / Evaluation
[] Embedding
[] Hybrid
[] Reranker
[] Extraction
[] Backend
[] Frontend
[] Docker / CI
[] Portfolio

## Development Setup

使用 Python 3.12 和 uv，在项目根目录执行：

```bash
uv sync --locked --inexact
uv run pytest -q
uv run casetrace demo
```

`uv` 使用项目的 `.venv`，无需手动激活环境。测试默认收集 `tests/`，
`tmp/` 中的练习脚本不进入正式测试。
`--inexact` 保留环境中另行安装的 Jupyter 等练习工具。

## 第一个可运行演示

```bash
uv run casetrace demo
uv run casetrace demo --query "塑封空洞 molding void" --top-k 3
uv run casetrace demo --query "BGA 锡球缺失" --json
```

流程是：读取 6 条固定开发草稿 → 校验数据与候选来源 → 按历史 Case 拼接文本 → BM25 排序。
结果显示 Case ID、匹配词、历史结案原因和来源 Evidence。可输入自己的当前异常描述；
只填写当时已知信息，不补入后来才确认的原因。

| 内容 | 位置 |
|---|---|
| 开发草稿、候选来源和三条示例查询 | [data/dev/demo.json](../../../../data/dev/demo.json) |
| 串起数据和检索的最小流程 | [demo.py](../../../../src/casetrace/demo.py) |
| Excel 子集读取 | [reference.py](../../../../src/casetrace/data/reference.py) |
| 切词、BM25、来源 ID 和匹配词 | [bm25.py](../../../../src/casetrace/retrieval/bm25.py) |

BM25 使用 [rank-bm25](https://github.com/dorianbrown/rank_bm25)，Excel 使用
[openpyxl](https://openpyxl.readthedocs.io/en/stable/)；不需要 API Key、GPU 或外部服务。
英文术语和 ID 按完整词匹配，中文先用相邻双字切分，例如“焊线脱落”变成“焊线、线脱、脱落”。
这只是词项基线：不理解同义词、否定或技术因果，分数也不是相关概率。

这 6 条是**待人工审阅的开发草稿**，没有 Ground Truth 标签或正式评估指标。
演示入口执行确定性 CR／已实现 GR，并核对保留的原因、措施候选；这些检查不等于完整语义验收。
检索只读取历史实体内容，不把查询、来源候选库全文或审查元数据混入索引。

当前开发顺序：**设计 PostgreSQL Schema → 生成 Case → 入库 → Retrieval / Ground Truth**。
下一项交付是支撑现有 Case 模型的最小 PostgreSQL Schema；随后生成一批基本一致的 Case，
导入数据库，再从库中读取历史案例，接入 BM25 与 Query–Case 标注和评估。
数据准备以逻辑基本一致、能够支撑实验为准，不要求用户逐条审阅 Case；遇到阻塞运行或影响评估可信度的问题再做最小修正。
暂停扩展 Validator 和完整合规审查；Case 生成采用完成本批数据所需的简单方式，不建设通用生成平台。
具体取舍见 [Stage 6 开发原则](../project/stage6.md#612-开发原则)。当前还未建立 Locked Test。

字段和业务规则见 [docs/data](../data/)，主数据见
[data/reference](../../../../data/reference/)。样例扩充由检索实验的实际缺口驱动。
