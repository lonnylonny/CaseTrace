# CaseTrace

半导体封装历史质量 Case 的 **Retrieval + Evaluation + Grounded Answer** 系统，用可追溯的历史记录辅助工程师调查，不自动判断当前 Incident 的最终 Root Cause。

## 项目入口

- [Current Plan](docs/project/current-plan.md)：唯一当前计划，包含用户确认的范围、完成标准、实际进度和下一交付。
- [AGENTS.md](AGENTS.md)：Codex / Cline 共同入口，定义分工、plan 包、skills 适配及上下文阅读顺序。
- [Data Foundation v1](docs/project/current-plan.md#3-data-foundation-v1-冻结)：已完成并冻结的数据基础；字段和规则保留在 [docs/data](docs/data/)。
- [Legacy Profile](docs/legacy/pre-restart-2026-09-16/README.md)：旧 Stage 与历史状态材料，仅供追溯。

## 当前状态

已有模型、确定性校验、主数据读取、6 条开发 Case、3 条 Query、文档构建和本地 BM25 原型。
已完成异常站点必填多选及同站点分组修订，demo 返回工序 ID、名称和 Evidence 来源。旧 qrels 与语料已归档，当前 [dev-v2 数据版本及全部 18 对标签](data/evaluation/dev-v2/README.md) 已由用户最终确认；BM25 自动评估的输入校验、指标、跨 Query 汇总、CLI 入口、可复现报告、正式运行落盘与错误分析均已完成并自测，M2 已通过 Codex 验收（2026-09-22）；Embedding / Hybrid / Rerank 实验与 Grounded Answer 尚未开始。

**M1 已完成：默认 demo 可运行，三条真实查询的 CLI 自动回归检查通过**，具体进度见 [Current Plan](docs/project/current-plan.md#6-当前事实与下一交付)。
下一步在新窗口规划 M3：正式 dev-v2 结果与修订后的错误分析见 `results/`。旧 dev-v1 归档哈希差异保留为非阻塞历史限制；最近全套测试仍有这一项失败，不代表全部测试通过。M3 尚未开始。

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
uv run casetrace evaluate --output results/dev-v2-bm25.json
```

`evaluate` 默认读取活动 dev-v2 的 `data/evaluation/dev-v2/qrels.json`，可用 `--qrels` 指定其它已确认输入。

现有流程读取开发草稿与主数据，执行已实现的检查，按 Case 拼接文本（包含实际选中的异常工序），再进行 BM25 排序并展示异常站点、历史原因与 Evidence 来源。Case.abnormal_processes 必须提供已确认工序 ID；旧 JSON 缺字段时会报错，不自动推断。路线适配和分组公共站点检查通过不等于调查事实或复发关系已获语义确认。
当前 BM25 demo 无需 API Key、GPU 或外部服务。中文使用相邻双字切分，英文术语和 ID 保留完整；分数不是相关概率。
`uv run casetrace evaluate` 使用同一套 BM25 检索，在已确认 benchmark 上写出逐 Query 完整排名、K=1/3/4 的 Recall / Precision / nDCG、MRR@4、跨 Query 汇总与复现信息：qrels、dataset 和主数据的 SHA-256，实际 BM25 参数（k1 / b / epsilon），分词与文档构建入口，Python 与依赖版本，git HEAD 与 脏工作区清单，相关源码和 `uv.lock` 的哈希。结果先写同目录临时文件再原子替换，输入校验或保存失败时不会留下半份报告。当前读数是这份语料与参数下的观测值，不是已确认的质量结论。正式运行的产物、复现步骤与局限记录在 [results/README.md](results/README.md)。
数据校验通过不代表检索标签正确，字段展示也不代表已经实现 Grounded Answer。

| 内容 | 位置 |
|---|---|
| 开发草稿、候选来源和示例查询 | [demo.json](data/dev/demo.json) |
| 数据到检索的现有流程 | [demo.py](src/casetrace/demo.py) |
| 主数据子集读取 | [reference.py](src/casetrace/data/reference.py) |
| 分词、BM25 与来源 ID | [bm25.py](src/casetrace/retrieval/bm25.py) |
| 评估输入校验 | [benchmark.py](src/casetrace/evaluation/benchmark.py) |
| 指标、运行器与结果报告 | [metrics.py](src/casetrace/evaluation/metrics.py)、[runner.py](src/casetrace/evaluation/runner.py) |
| 已确认 qrels 与评估结果 | qrels [dev-v2 记录](data/evaluation/dev-v2/README.md)；正式结果与运行记录 [results/](results/README.md) |
