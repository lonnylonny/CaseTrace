# Pre-M5 audit — 2026-10-03

状态：**审计完成，无 M5 blocker。** 本次是当前主链路回归与文档清理，不重新验收 M1～M4，不开始 M5。

## Codex Plan

按用户授权运行完整测试和必要 demo，检查 CLI/core 复用边界，只修复阻碍 M5 的明确问题；精简 planning/handoff/task 历史过程，保留最终决定、用户贡献、有效约束和未解决限制。采用 [writing-for-agents](../../../.agents/skills/writing-for-agents/SKILL.md) 的单一来源与精简原则。

停止条件：检查结果可核对、M5 接缝与 invariants 明确、清理未改变运行行为。无需重跑全部检索模型或反复调用 LLM。

## Handoff Baseline

Codex 直接执行，未交接 Cline。起始 HEAD：`b01dca568858911bfea6de76a2c201bb38c1f3ae`；工作区已有大量 tracked/untracked 成果，本次不按 HEAD 差异归属历史工作。

清理前快照绝对路径：`/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-pre-m5-ulyoeiot/`。

- `before/` 保存 README 及全部 `docs/project/**/*.md` 原文（含未提交文件）；`head.txt`、`status.txt` 保存起点。
- `protected-sha256.json` 保存源码、提示词、测试、JSON 数据及依赖文件身份；`targets.json` 是文档清单；`absent.txt` 记本审计包起点不存在。
- `checks/` 保存 demo/评估输出、实际命令及回放脚本/摘要。该快照保留清理前尚未进入 Git 的历史记录，不能声称它们均可从 Git 恢复；也不替代已丢失的旧机器基线。

## Cline Report

不适用：用户明确授权 Codex 审计与清理。没有新增用户编码或学习确认。

## Codex Acceptance

**本轮实测：**

| 检查 | 结果 |
|---|---|
| `uv run pytest -q` | 571 passed、169 subtests passed |
| `uv run ruff check` / `uv lock --check` | 均通过 |
| 默认 demo / BGA JSON demo | exit 0；JSON 正常且有命中 |
| 默认 BM25/dev-v2 evaluate | exit 0 |
| R3/dev-v3 evaluate | exit 0；与既有 final 六个结果面板完全一致，旧口径 Recall@4=0.96 |
| `answer --query-id Q005 --check-only` | exit 0；R3 排名及上下文正常 |
| 空命中 CLI（`--json --output`） | exit 0、`no_hits`、未调用模型；stdout JSON 与落盘记录一致 |
| v10 五条真实响应的离线回放 | 5/5 `ok`；排名、上下文、实际消息、解析回答与原记录一致；97 项引用一致；各份记录的 41 个 runtime 文件哈希一致 |
| `git diff --check` / 文档链接与代码围栏 | 均通过 |
| 原始文件身份核对 | 80 个受保护文件与本轮快照一致，运行代码/测试/JSON 数据/依赖未变 |
| 非 CLI 直接调用 | `run_answer_question` 无 stdout/stderr 输出，可直接取得状态与记录 |

回放检查的第一版审计脚本使用大写 `Q*.json`，未选中小写文件，断言失败；改为实际 `q*.json` 后五条均通过。这是审计脚本路径问题，未改项目代码。

**Spec：通过。** 当前学习/展示主链路未发现 regression；API 可直接复用应用函数。M5 的文件加载、快照哈希、路径元数据及示例 Query 读取仍需适配，已纠正交接文档“仅换 loader、上层不动”的过度承诺；属于 M5 正常实现范围，无需提前抽象。

**Standards：通过。** 本次只改文档，保留既有代码与学习贡献；清理 Current Plan 的旧排期/修复过程，M3-03～M4-04 九个任务包的逐步实施、已解决 debug 与过期 verdict，两个 handoff 的重复说明；精简归档哈希维护记录，更新 README 和两个早期摘要的过期状态。任务包保留最终 Spec/Standards 结论及历史验证摘要。

**保留限制：** 单快照、同步模型调用、小样本与 Query 模板依赖、两处已接受语义措辞、旧 GT 口径和 dev-v1 历史字节溯源缺口；均不阻塞当前 M5。未新增在线模型调用、未重跑全部 Embedding/Hybrid/Rerank 实验、未执行 Locked Test；不宣称新生成质量或生产可用性。

M5 必须保持的行为统一见 [Current Plan §7](../current-plan.md#7-grounded-answer-最终决定与-m5-invariants)，调用/存储接缝见 [M5 交接](../handoffs/m4-04-m5-handoff.md)。

**Verdict：Pre-M5 audit passed — ready to start M5.** 无运行代码修复；M5 尚未开始。
