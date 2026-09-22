# 评估结果记录（M2 · dev-v2 · BM25）

本目录保存 M2 第一轮 BM25 自动评估的正式产物与运行记录。这里的内容是**当前语料与参数下的观测读数**，不是已确认的检索质量结论，也不是对真实生产泛化能力的声明。系统提供历史调查参考，不判断当前异常的最终 Root Cause。

## 1. 本次运行

| 项目 | 值 |
|---|---|
| 运行日期 | 2026-09-22（本地，UTC+8）；报告内 `generated_at` = `2026-09-22T05:12:51+00:00` |
| 命令 | `uv run casetrace evaluate --output results/dev-v2-bm25.json` |
| 入口 | [runner.py](../src/casetrace/evaluation/runner.py) 的 `run_evaluation` → `write_report`；CLI 见 [__init__.py](../src/casetrace/__init__.py) |
| HEAD | `1e691bca0e32f8edb9dc9ab05b6ce37793ab6b87` |
| 工作区 | **脏（未提交）**；仅 HEAD 不足以复现，必须按第 4 节的源码 / 依赖哈希核对 |
| benchmark | `data/evaluation/dev-v2/qrels.json`，`dev-qrels-v2` / `development` / 确认日 `2026-09-19` |
| 检索 | `rank_bm25.BM25Okapi`，`k1=1.5` / `b=0.75` / `epsilon=0.25`；语料 6 条，请求 `top_k=6`，不补分数、不补名次 |
| 指标口径 | 逐 Query `recall@k` / `precision@k` / `ndcg@k`（K=1,3,4）与 `rr@4`；跨 Query 汇总为 Query 等权平均，RR@4 的均值记作 `mrr@4` |
| 结果 schema | `evaluation-result-v1` |

## 2. 产物

| 文件 | 大小 | SHA-256 | 说明 |
|---|---|---|---|
| `dev-v2-bm25.json` | 14,004 B | `bc457e9576ece6ad29cb2d3991da7c69e939bb4c5a2d0b7330c6039c8441f26d` | 正式结果：逐 Query 完整排名 / 分数 / 命中词项、逐指标分数、汇总与参与 / 排除清单，以及输入、参数与复现信息 |
| `dev-v2-bm25.cli.txt` | 883 B | `f159d812375f4cceb9c0149f430713321527c67582aca4e5baa3668b0ac0ab84` | 同一命令的终端输出（人读）；内容与 JSON 一致，不作为独立来源 |
| `pytest-full.log` | 1,891 B | `57cd01af565fc14b09064cbcd1a7039e186f1c9a60f6dedf7b740efd119f2710` | 本次修订的整套测试输出 |

对这份结果的开发期错误分析（M2 功能 4 步骤 B）见 [dev-v2-bm25-error-analysis.md](dev-v2-bm25-error-analysis.md)：逐 Query K=4 漏检、与已记录阅读期望的对照、命中词项判别力（document frequency）以及「问题 → 可能原因 → 下一步实验」表。该分析只读结果文件与语料，不修改代码、标签或 BM25 参数。

## 3. 读数（观测值）

逐 Query 完整排名（正例来自已确认 qrels，未作任何修改）：

| Query | 正例 | 完整返回排名 |
|---|---|---|
| Q001 | C001、C002、C003、C004 | C001 > C003 > C004 > C002 > C005 > C006（6 条） |
| Q002 | C005 | C005 > C002 > C006 > C001 > C004（5 条） |
| Q003 | C006 | C006 > C005 > C002 > C001 > C004（5 条） |

跨 Query 汇总（三条 Query 全部参与，无排除）：

| 指标 | 值 | | 指标 | 值 |
|---|---|---|---|---|
| `recall@1` | 0.7500 | | `precision@1` | 1.0000 |
| `recall@3` | 0.9167 | | `precision@3` | 0.5556 |
| `recall@4` | 1.0000 | | `precision@4` | 0.5000 |
| `ndcg@1` | 1.0000 | | `mrr@4` | 1.0000 |
| `ndcg@3` | 1.0000 | | `ndcg@4` | 1.0000 |

读数说明：`precision@k` 的分母固定为 k，与该 Query 实际返回多少条无关。Q002 / Q003 各只有 1 个正例，且都排在第 1 名，因此这两条的 `precision@3 = 1/3`、`precision@4 = 1/4` 是口径使然，并不表示前几名排错了；汇总值 0.5556 / 0.5000 被它们拉低。`recall@4 = 1.0` 只说明这 3 条 Query 在 K=4 没有漏掉已确认正例，不代表检索质量已经达标。逐 Query 的漏检、与阅读期望的差距以及误召，是 4B 错误分析的内容。

## 4. 输入与代码版本（复现所需）

输入（报告内哈希 == 磁盘实际字节 == qrels `sources` 记录，自测已核对）：

| 对象 | 路径 | SHA-256 |
|---|---|---|
| qrels | `data/evaluation/dev-v2/qrels.json` | `9112d64cac25e8af0b7b183ca0d083de2c460dc6427cf1c57785f4e0fdfc38b7` |
| dataset | `data/dev/demo.json` | `6923d382ba082f72beb922737e9b169313c1a236662f6a57a8a322e0879689f7` |
| reference | `data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx` | `f5001bddd3dff43342a2569ceda836ddb4f5c0caca942c1c4d043d99a9131c85` |

代码与依赖（报告 `reproducibility.source_files` 记录值）：

| 文件 | SHA-256 |
|---|---|
| `src/casetrace/__init__.py` | `938fe804e20e46af1e2623bdab439fd991f8d79cbd65d226ec2cd574f10840b5` |
| `src/casetrace/data/constants.py` | `6ceca4b9cd2716b6f960a2022b4bb30de82a6ab9e1de45209d4e6010d1e358fd` |
| `src/casetrace/data/dataset_model.py` | `bace7dba979338725d6bd9e1e58068e5bcc7d37eddc34e8b3fa77e80711f138e` |
| `src/casetrace/data/reference.py` | `6d8e1a3861031698d79519f83f7ee07adcc78ea86883f94370ff71bf92235fa1` |
| `src/casetrace/data/validators.py` | `073297b5957f87b50f490b1abad007bfdc5e6acd823b524980334d01150210cb` |
| `src/casetrace/evaluation/runner.py` | `8c9d89739f334eeddcae4374ca1525ea1cdb0b3fef4568fcb033f1fa2cea8a31` |
| `src/casetrace/evaluation/benchmark.py` | `b18f96ea1e105b52407dec190a7417a8dba7b3289bafe8aeefafd14a57926cb7` |
| `src/casetrace/evaluation/metrics.py` | `47e55310fc9ebf9b4afd406295f6833b2c5cfe7db9ca3e5dbb414464e080d191` |
| `src/casetrace/demo.py` | `27b92bc46db1522ba9e113861bcfb69fdae9fe6d52115e2c91842fe502fa2714` |
| `src/casetrace/retrieval/bm25.py` | `e21e00f76bae8cf6301a94c4e15886326d3f583064fd6df9e71c8859e63523c0` |
| `pyproject.toml` | `a7562713a0afd4e2fef26a137f7790b171f9b30f6cdcbd784a306e65b21517f0` |
| `uv.lock` | `6ae96bf9c5f00a00bff624b644c044a93af40f91579e8f1047215ff62ebbd052` |

运行环境：Python `3.12.3`；`casetrace 0.1.0`、`rank-bm25 0.2.2`、`openpyxl 3.1.5`。

## 5. 复现步骤

```bash
uv sync --locked --inexact
uv run pytest -q                                        # 见第 6 节实际结果
uv run casetrace evaluate --output results/dev-v2-bm25.json
```

- 先比较第 4 节的源码与依赖哈希、以及第 1 节的 HEAD。源码哈希识别运行版本，不是源码备份；复现还需保留对应源码。哈希有变化时先查明原因，不能仅凭 HEAD 判断代码一致。
- 报告写入采用「同目录临时文件 + 原子替换」，失败不会留下半份结果；因此**不要**用 `generated_at` 或运行耗时判断排名是否可重复——它们只说明记录生成时间。
- 只要输入哈希、源码哈希与参数一致，重复运行的排名、分数与指标必须一致（本次已实测，见第 6 节）。

## 6. 已跑检查与未跑项

2026-09-22 Codex 复现记录修订（只补源码清单，不调整检索）：

- 回归测试先实测失败，缺少 CLI 和四个数据模块；补清单后 `uv run pytest -q tests/evaluation/test_runner.py tests/test_cli_evaluate.py` → **29 passed**。
- `uv run pytest -q` → exit 1：**278 passed、169 subtests passed、1 failed in 2.32s**。唯一失败仍为 `tests/test_benchmark_migration.py:19` 的旧 dev-v1 归档哈希断言；原始输出见 `pytest-full.log`。
- `uv run casetrace evaluate --output results/dev-v2-bm25.json` → exit 0；重复写至本次临时目录的 `repeat.json`，除 `generated_at` 外完全相等（时间戳允许恰好相同）。`uv run casetrace demo` → exit 0。
- 与修订前结果对照，逐 Query 排名、BM25 分数、命中词项、指标及汇总完全一致；结果中 12 个源码/配置哈希均与当前文件相符。
- 本轮开始前，用户已为 Q001–C004 理由增加“描述均为焊线相关异常，可能存在关联性。此外”，18 对二值标签、Query、语料、确认字段均未改变。新报告如实记录当前 qrels 哈希；这项差异来自用户既有修改，不来自源码清单修复。
- 在临时目录用记录的 HEAD 源码加报告列出的当前源码、输入文件重建：CLI evaluate exit 0，benchmark / retrieval / metrics / queries / summary 与本次报告一致。当前执行中加载的非空 CaseTrace Python 模块均被清单覆盖。这验证本次依赖链，不声称已覆盖未来新增模块或所有运行环境。
- 本次修改前快照、HEAD、Git 状态、隔离重建目录及日志保存在 `/tmp/casetrace-m2-repro-fix-fbr57lij`。初次运行记录与 4A/4B/4C 检查保留在 [M2 完成包](../docs/project/tasks/m2-completion.md)，不将历史通过数冒充本次全部检查通过。
- 未执行 M3/M4 实验；nDCG 已在首次总审及本轮全套测试中覆盖。

## 7. 局限与未解决项

- **不是质量结论**：6 条语料、3 条 Query、单一 BM25 参数，只够支撑「评测流程可用、读数可复现」，不足以说明真实生产表现；不得据此宣称泛化能力。
- **未解决**：`data/evaluation/dev-v1/qrels.json` 的归档哈希与迁移记录不一致（实际 `e92e5bb1f84d…`，记录 `c01752264333…`）。本轮未刷新哈希、未改写旧文件、未猜测标签，失败保持可见；详见 [dev-v2 记录](../data/evaluation/dev-v2/README.md)。
- **工作区未提交**：本次结果对应的是一个未提交工作区，复现必须核对第 4 节哈希；本轮没有 Git 提交或暂存操作。
- **M2 已验收**：两处分析文字已纠正，源码清单缺口已修复；最终 Spec / Standards 结论见 [M2 完成包](../docs/project/tasks/m2-completion.md#2026-09-22-最终验收与交接)。旧归档哈希失败按用户决定作为非阻塞历史限制保留，后续沿用当前 dev-v2；未改旧哈希或失败测试。
- 观察（不影响本次读数）：`dev-v2-bm25.json` 由 `tempfile.NamedTemporaryFile` 创建，权限为 `-rw-------`（600），与目录内其它文件（664）不同。是否调整属于后续可选项，本轮未改动代码。
- 数据校验通过不代表检索标签或检索质量正确；字段展示也不代表已经实现 Grounded Answer。
