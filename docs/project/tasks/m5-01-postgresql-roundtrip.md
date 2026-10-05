# M5-01 — PostgreSQL 完整存取

状态：**accepted（2026-10-05，按学习展示原则简化后）**。Cline 已完成 SD1～SD4；本轮 Codex 按用户明确要求修正和简化代码，并完成 Spec / Standards 验收。下一交付是 M5-02，尚未实施。

## Codex Plan

### 目标与范围

完整保存冻结模型所需主数据和 dev-v3 历史案例，读回现有 dataclass / `ReferenceData`，保留原文、关系、来源、review 状态和源顺序。总体范围见 [Current Plan §§2、3、5、7](../current-plan.md)。本包只实现存储，不接入回答命令或 FastAPI。

权威输入：

- [冻结数据结构 §5](../../data/CaseTrace_Data_Structure_V2_No_Scenario.md)、[CR](../../data/CaseTrace_Case_Constraint_Rules_Frozen.md)、[GR](../../data/CaseTrace_Case_Generation_Rules_V1.md)、[Validator 覆盖边界](../../data/CaseTrace_Validator_Implementation_Plan.md)。不扩展语义规则。
- `data/dev/demo-v3.json`、`data/reference/封装异常_failure_modes_db_structured_v5_engineering_audited-2.xlsx`、[dev-v3 快照依据](../../../data/evaluation/dev-v3/README.md)。9 Case、9 Detail、9 Evidence、1 Group、3 Membership。
- `src/casetrace/data/{dataset_model,reference,validators}.py`、`src/casetrace/demo.py` 与 [M4 → M5 接缝](../handoffs/m4-04-m5-handoff.md)。

### 实现决定（2026-10-05 修订）

用户明确要求基本安全足够、逻辑清晰，不因安全反复核查。原计划要求过细的部分同时收敛；业务字段、来源及已有规则不变。

1. **建表与连接：** Psycopg 3、参数化查询、专用 schema、一份固定 `storage/sql/schema.sql`。保留结构标记 `002` 以兼容已有库，不维护逐版本迁移框架。连接配置来自环境变量或 `.env`，不把凭据写进源码和报告；重复初始化保留数据。
2. **一次主数据读取：** 完整读取 8 张持久化主数据表需要的 Excel 列，从同一份表行构建校验所需 `ReferenceData`；不再读取两份投影后做全套交叉核对。保留客户名称、路线背景、产品功能、候选知识、工序与路线工序的全部已约定列；可选单元格为 NULL，ID 保留前导零。
3. **单快照导入：** 核对已记录快照的两份文件哈希，复用已有 CR/GR/来源校验，在一个事务中写入主数据、案例、关系、元数据。只锁当前 schema 的元数据表，使两个导入顺序执行；不实现单条 CRUD、多版本管理或导入平台。
4. **重复与失败：** 已导入同一快照时复用读回内容检查，返回 `no_op`；身份不同、内容已变或已有未登记业务数据时拒绝。校验或 SQL 失败整体回滚，不静默覆盖。
5. **读回：** 公开 `initialize_schema`、`import_snapshot`、`load_snapshot`、`verify_snapshot`。关系表是实体真源，返回五类对象、等价主数据、完整 payload 与快照描述。非实体元数据和源顺序仍保存在 `snapshot_metadata`；qrels 不导入，候选知识不进入检索文本。
6. **一次内容检查：** 内容摘要统一在读回入口重算和核对；重复导入复用此结果。保留现有 `ordering` / `content-digest-v2` 格式，避免为简化重新建库。`verify` 显式比较文件身份、完整快照身份与内容摘要；逐字段、主数据投影及文档等价由集成测试证明，不重复放进运行链路。

当前文件职责：`schema.py` 建表；`reference_source.py` 主数据读取/投影；`content.py` 固定表列映射/摘要；`snapshot.py` 导入与读回；`connection.py` 连接配置；`__main__.py` CLI。保留适量模块，避免所有职责合并成一个大文件。

### 分步与教学边界

SD1 建表 → SD2 原子导入 → SD3 完整读回 → SD4 自测交接，由 Cline 实施和讲解；M5 不沿用 M3 强制留白练习。用户本轮明确要求 Codex 修正，Codex 直接完成简化和验收，不额外设置教学或授权暂停。代码验收不代表已确认用户理解新实现。

### 验收与测试

使用真实 PostgreSQL 和每项测试独占的 schema；缺少数据库时允许普通回归显式 skip，但不能作为存储验收证据。验证正常往返、非 ID 顺序、无 Group、NULL/date/text[]/前导零、文档等价、基础约束、重复与冲突、代表性 CR/GR/来源失败及 SQL 中途回滚。现有文件加载、检索和回答回归必须通过。完整排名、上下文和回答回放留给 M5-02，不调用新模型验收数据库。

运行说明见 [PostgreSQL](../../development/postgresql.md)。主要命令：

```bash
uv run --locked pytest tests/storage -q
uv run --locked pytest -q
uv run ruff check
uv lock --check
git diff --check
```

选用 [code-review](../../../.agents/skills/code-review/SKILL.md)，按 AGENTS 的仓库基线和单 agent 规则分别评审 Spec / Standards；不需要 tracker、自动 commit 或重复确认。原计划编制使用的 to-spec / handoff 记录在清理前快照中。

## Handoff Baseline

- 起始 HEAD：`910ced86120fcdf7efa09b55bcb10b3c29212ce6`。
- 起点工作区仅有 tracked 删除：`data/dev/~$demo-v3.xlsx`（Excel 临时锁文件）；无其它 tracked/untracked 变更。不恢复该删除，不归因于本包。
- 实施前快照：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-01-lpwv4e2y/`。`before/` 保存相关代码、测试、规则、数据、依赖、README、主计划和 M4 交接共 90 个文件；`sha256.json` 可核对；`head.txt`、`status.txt`、`working-tree.patch`、`staged.patch` 记录起点。未保存真实 `.env` 或连接凭据。
- `absent.txt` 记录本任务包、storage 源码/测试目录与数据库使用说明起点不存在。
- 2026-10-03 任务准备时 Codex 仅新增本包、更新 Current Plan 的 M5 状态与顺序；作为交接新增规划，不归因于 Cline。Cline 编辑前核对快照和 Git 状态，记录期间变化；新增涉及文件先补快照。基线保留至验收。
- 2026-10-03 环境准备补充基线：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-env-56lln8zu/`，保存本轮编辑前的依赖、README、环境模板、主计划和本包等文件；`absent.txt` 记录 Compose、数据库初始化脚本和运行说明此前不存在。此前任务包/主计划变更及 Excel 锁文件删除仍为预存变化。真实 `.env` 未快照或输出；本轮只追加数据库配置，原有内容逐字保留并核对，权限设为 0600。
- 环境续配置基线：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-env-resume-wbms35ut/`；`before/` 保存续配置前的 Compose、Shell 初始化脚本、环境说明、主计划及本包；`head.txt`、`status.txt` 记录起点。`checks/` 保存无凭据的数据库 smoke、容器/镜像身份和独立空卷首次初始化结果。Shell 文件现已替换为原先不存在的 `01-databases.sql`；其它已有工作区变化不归因于续配置。

- 2026-10-05 Codex 简化前基线：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-m5-01-simplify-4n5lt2kp/`；`before/` 保存本轮涉及源码、测试、计划和说明，另存 HEAD、tracked/untracked 状态及 staged/unstaged diff。包含 Cline 已有未跟踪实现，不将其归因于本轮。未保存真实 `.env`。

## Cline Report

以下保留 Cline 2026-10-04 交付摘要，完整原 Report 在本轮简化前快照的 `before/docs/project/tasks/m5-01-postgresql-roundtrip.md` 中，供历史复查；当前实现以修订计划和下节验收为准。

- **SD1～SD4 已完成，ready for acceptance：** 建立 15 张业务表、2 张辅助表，完整导入与读回 dev-v3，提供 `init/import/verify` 和运行说明。Cline 自测为 storage **68 passed / 0 skipped（44 项真实 PG）**；全套 **639 passed、169 subtests passed**，ruff/lock/diff 通过。这些是简化前自测，不代替 Codex 验收。
- **历史修复：** 补回 SQL 语法遗漏；恢复测试加载 `.env` 后的环境变量隔离；修复单列主数据键交叉核对与 `cursor.executemany` 使用；修复 `imported_at` 读回列及 jsonb 路径参数化。无 Group / 非 ID 顺序样例曾违反 GR-04，调整测试数据后通过，未改业务规则。
- **历史结构变化：** Cline 曾实现 001→002 迁移与内容摘要 v1→v2；SD3 曾重建可重放的派生 schema。此次 Codex 简化保持已经导入的 `002` / v2 数据，不再次清库。
- **教学记录：** Cline 记录已讲表与主外键、SQL/Python 校验分工、完整事务、重复导入、关系表组装、源顺序及文件/内容身份；迁移台账和双读取交叉核对属于旧实现，本轮已移除。未记录可核对的用户独立编码贡献，不补记。用户已提出阅读后的复杂度意见；简化后入口仍可按需继续讲解，理解状态不由测试推定。
- **交接意见：** Cline 已指出迁移框架、双重主数据读取和多层验证偏重，建议简化。Codex 接受必要部分，保留冻结的完整主数据、源顺序、事务与有用回归测试。
- **未执行：** M5-02 数据源接入与回答回放、FastAPI、新模型调用及 Git 提交。

## Codex Acceptance

**结论：accepted（2026-10-05，简化和修正后）。**

### Spec

15 张业务表及冻结字段/关系完整，原子导入、no-op、冲突拒绝和完整读回满足修订范围。五类对象、payload、`ReferenceData`、非 ID 源顺序及 `build_documents` 逐 Case 文本等价由真实集成测试验证。独立 Excel→SQL 对照确认 7 张直接主数据表的全部持久化源列相等；两个关系映射及客户归属经 SQL 映射审查和读回回归核对。可用时点、依据、来源、draft、split 和候选知识边界保留。

发现并修复两个实际问题：原重复导入仅检查已存摘要和行数，修改字段但行数不变仍可能误报 no-op；原 `verify` 只核对快照 ID，未核对请求的可用时点/依据。现已分别复用实际读回摘要和完整快照身份比较，有回归用例。

### Standards

原计划与实现都要求过细，本轮按用户确认的学习展示范围收敛：迁移文件合并为固定建表 SQL，移除迁移注册表和前后反复版本查询；Excel 双读取/全套交叉核对改为单读取；导入与读回合并到 `snapshot.py`；顺序组装不重复检查数据库已保证的主键唯一性；`verify` 六套对照改为三项明确检查，逐对象和文档对照留在测试中。保留单事务、PK/FK/CHECK、参数化 SQL、来源和一次内容身份检查。

存储 Python 从 **1651 行减至 1051 行（减少 600 行，约 36%）**，不是通过少存字段或删掉有效检查换取。仅为复用校验在 `demo.load_validated_dataset` 加可选已读主数据参数，现有文件调用方式兼容；检索和生成核心未改。

### 实测证据

| 检查 | 2026-10-05 结果 |
|---|---|
| 简化前基线 `pytest tests/storage -q` | 68 passed，0 skipped |
| 简化后 `uv run --locked pytest tests/storage -q` | **69 passed，0 skipped；49 项真实 PG、20 项纯函数**。用收集阶段夹具依赖计数，不为计数断开数据库再跑一遍 |
| `uv run --locked pytest -q` | **640 passed、169 subtests passed** |
| `uv run ruff check` / `uv lock --check` / `git diff --check` | 全部通过；一次 unused import 检查失败已修复 |
| `init` / `import` / `verify`，开发库与测试库 | 全部 exit 0；重复导入 `no_op`；三项诊断通过 |
| 现有数据库 | 各保留 244 行业务数据及 1 行快照元数据；结构 002，摘要 `4c10de42b609759c918f7943366a3ee1f998140fd65d712091275693c97610bb` 不变，无清库重建 |
| 独立全部主数据源列对照 | 通过；初次脚本未跳过 Excel 尾部空行，导致断言失败，修正对照脚本后通过，未据此改业务代码 |

已验证重复导入后的字段改动被拒绝且保留原字段、CR/GR/来源失败无写入、SQL 中途错误完整回滚。删除 4 项依赖旧迁移接口或检查 SQL 字符串的测试，保留真实约束/往返测试并补齐上述实际缺口；没有为了减少测试数量删除有用证据。

本轮未调用模型、未实施 M5-02、未提交 Git。教学理解和新口径 Ground Truth 状态不因验收改变。下一入口：准备 M5-02，直接复用 `casetrace.storage.load_snapshot` 的对象和内容检查结果。
