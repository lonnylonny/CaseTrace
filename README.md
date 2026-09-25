# CaseTrace

半导体封装历史质量 Case 的 **Retrieval + Evaluation + Grounded Answer** 系统，用可追溯的历史记录辅助调查，不自动判断当前 Incident 的最终 Root Cause。

## 项目入口

- [Current Plan](docs/project/current-plan.md)：唯一当前计划，包含范围、里程碑、当前状态与下一交付。
- [AGENTS.md](AGENTS.md)：协作、教学与验收规则。
- [docs/data](docs/data/)：冻结的字段、业务规则、生成约束与数据库设计。
- [results](results/README.md)：正式实验产物、错误分析与复现入口。

## 当前能力

已交付数据模型与确定性校验、BM25 demo、用户确认的 dev-v2 benchmark、CLI Evaluation、多方法入口和本地 Embedding。当前活动交付是 [M3-03](docs/project/tasks/m3-03-expand-mock-datasets.md)：扩充 Development，草稿尚待用户确认。正式进度与后续依赖以 [Current Plan](docs/project/current-plan.md#6-当前事实与下一交付)为准。

## 本地开发

使用 Python 3.12 与 uv，在项目根目录执行：

```bash
uv sync --locked --inexact
uv run pytest -q
uv run casetrace demo
uv run casetrace demo --query "塑封空洞 molding void" --top-k 3
uv run casetrace demo --query "BGA 锡球缺失" --json
uv run casetrace evaluate --method bm25 --output /tmp/casetrace-bm25.json
```

uv 使用项目 `.venv`，无需手动激活；`--inexact` 保留另行安装的学习工具。全套测试仍有旧 dev-v1 归档哈希的已知失败，依据见[版本记录](data/evaluation/dev-v2/README.md#2026-09-22-用户后续决定)。

`demo` 使用 BM25；`evaluate` 支持 `--method bm25|embedding`，默认 qrels 为已确认 dev-v2。Embedding 需要准备[固定版本模型](docs/project/research/m3-02-embedding-model-selection.md)，复现命令见 [results](results/README.md)。dev-v3 草稿不能用于正式评估。

demo 展示异常站点、历史原因与 Evidence 来源；字段展示不代表 Grounded Answer 已实现，软件测试通过也不代表检索质量达标。数据、运行实现与测试分别位于 `data/`、`src/casetrace/`、`tests/`。
