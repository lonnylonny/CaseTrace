# CaseTrace

半导体封装历史质量 Case 的 **Retrieval + Evaluation + Grounded Answer** 系统，用可追溯的历史记录辅助工程师调查，不自动判断当前 Incident 的最终 Root Cause。

## 项目入口

- [Current Plan](docs/project/current-plan.md)：唯一当前计划，包含用户确认的范围、完成标准、实际进度和下一交付。
- [AGENTS.md](AGENTS.md)：协作规则与上下文阅读顺序。
- [Data Foundation v1](docs/project/current-plan.md#3-data-foundation-v1-冻结)：已完成并冻结的数据基础；字段和规则保留在 [docs/data](docs/data/)。
- [Legacy Profile](docs/legacy/pre-restart-2026-09-16/README.md)：旧 Stage 与历史状态材料，仅供追溯。

## 当前状态

已有模型、确定性校验、主数据读取、6 条开发 Case、3 条 Query、文档构建和本地 BM25 原型。
已开始人工相关性审阅，尚无版本化的正式 qrels、Retrieval Evaluation、Embedding / Hybrid / Rerank 实验或 Grounded Answer。

**M1 已完成：默认 demo 可运行，三条真实查询的 CLI 自动回归检查通过**，具体进度见 [Current Plan](docs/project/current-plan.md#6-当前事实与下一交付)。
接下来进入 M2，以现有 6 × 3 配对建立人工确认的 Ground Truth 和第一轮 BM25 评估。

BM25、Embedding、Hybrid、Rerank 都是 V1 必做对比实验。PostgreSQL、FastAPI、Docker、简单 Web Demo、CLI Evaluation、可复现实验结果和 README 也是必做交付；数据库和服务集成安排在检索评估及 Grounded Answer 之后。

## 本地开发

使用 Python 3.12 和 uv，在项目根目录执行：

```bash
uv sync --locked --inexact
uv run pytest -q
```

`uv` 使用项目的 `.venv`，无需手动激活环境。测试默认收集 `tests/`，`tmp/` 中的练习脚本不进入正式测试。
`--inexact` 保留环境中另行安装的 Jupyter 等练习工具。

已有 CLI 用法：

```bash
uv run casetrace demo
uv run casetrace demo --query "塑封空洞 molding void" --top-k 3
uv run casetrace demo --query "BGA 锡球缺失" --json
```

现有流程读取开发草稿与主数据，执行已实现的检查，按 Case 拼接文本，再进行 BM25 排序并展示历史原因与 Evidence 来源。
当前 BM25 demo 无需 API Key、GPU 或外部服务。中文使用相邻双字切分，英文术语和 ID 保留完整；分数不是相关概率。
数据校验通过不代表检索标签正确，字段展示也不代表已经实现 Grounded Answer。

| 内容 | 位置 |
|---|---|
| 开发草稿、候选来源和示例查询 | [demo.json](data/dev/demo.json) |
| 数据到检索的现有流程 | [demo.py](src/casetrace/demo.py) |
| 主数据子集读取 | [reference.py](src/casetrace/data/reference.py) |
| 分词、BM25 与来源 ID | [bm25.py](src/casetrace/retrieval/bm25.py) |
