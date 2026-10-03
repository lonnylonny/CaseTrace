# CaseTrace

半导体封装历史质量 Case 的 **Retrieval + Evaluation + Grounded Answer** 系统，用可追溯的历史记录辅助调查，不自动判断当前 Incident 的最终 Root Cause。

## 项目入口

- [Current Plan](docs/project/current-plan.md)：唯一当前计划，包含范围、里程碑、当前状态与下一交付。
- [AGENTS.md](AGENTS.md)：协作、教学与验收规则。
- [docs/data](docs/data/)：冻结的字段、业务规则、生成约束与数据库设计。
- [results](results/README.md)：正式实验产物、错误分析与复现入口。

## 当前能力

已交付数据模型与确定性校验、BM25 demo、用户确认的旧口径 dev-v3 benchmark、CLI Evaluation、多方法入口、本地 Embedding，以及 Grounded Answer 链路（R3 检索 → 真实模型生成 → 引用守卫 → `casetrace answer` CLI；M1～M4 已验收，Pre-M5 审计通过）。正式进度与后续依赖以 [Current Plan](docs/project/current-plan.md#6-当前事实与下一交付)为准。

## 本地开发

使用 Python 3.12 与 uv，在项目根目录执行：

```bash
uv sync --locked --inexact
uv run pytest -q
uv run casetrace demo
uv run casetrace demo --query "塑封空洞 molding void" --top-k 3
uv run casetrace demo --query "BGA 锡球缺失" --json
uv run casetrace evaluate --method bm25 --output /tmp/casetrace-bm25.json
uv run casetrace answer --query-id Q005 --check-only   # 只检查输入与证据上下文，不调用模型
uv run casetrace answer --query-id Q005                # 真实模型生成历史参考回答（需凭据）
```

uv 使用项目 `.venv`，无需手动激活；`--inexact` 保留另行安装的学习工具。2026-10-03 全套测试通过（571 passed、169 subtests passed）；历史归档的逐字节溯源限制仍保留，详见 [Pre-M5 审计](docs/project/tasks/pre-m5-audit.md)。

`demo` 使用 BM25；`evaluate` 支持 BM25、Embedding、Hybrid、Rerank 及 R3（`--method bm25_drop_negation_labels`），默认 qrels 为已确认 dev-v2。Embedding 需要准备[固定版本模型](docs/project/research/m3-02-embedding-model-selection.md)，复现命令见 [results](results/README.md)。`answer` 用 R3 检索 + DeepSeek（`deepseek-flash`，非思考模式）生成历史参考回答，凭据从环境变量或项目根 `.env`（模板见 `.env.example`，`.env` 不入库）读取，不要求 qrels。

demo 展示异常站点、历史原因与 Evidence 来源；`answer` 生成的回答是历史参考并附来源与具体缺口，软件测试通过不代表检索质量或回答忠实度达标。数据、运行实现与测试分别位于 `data/`、`src/casetrace/`、`tests/`。
