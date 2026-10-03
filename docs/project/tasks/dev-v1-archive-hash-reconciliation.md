# dev-v1 归档哈希校验维护

状态：**accepted（2026-09-29）**。反复测试失败已消除，历史原件的字节溯源缺口仍存在；本次只精简记录。

## Codex Plan

保留 dev-v1 原件与 dev-v2 迁移记录，分别检验已知哈希缺口和可观察的标签/理由迁移关系。权威版本说明见 [dev-v2 归档校验维护](../../../data/evaluation/dev-v2/README.md#2026-09-29-归档校验维护)。

## Handoff Baseline

原实施 HEAD `b01dca568858911bfea6de76a2c201bb38c1f3ae`；快照 `/var/folders/cp/kr3bxwpn50bct2892y7gyrb00000gn/T/casetrace-dev-v1-hash-repair-x8z56alm/`。已验收，无活动基线；清理前全文见 [Pre-M5 审计基线](pre-m5-audit.md#handoff-baseline)。

## Cline Report

不适用：用户授权 Codex 直接修复，未记作用户或 Cline 贡献。

## Codex Acceptance

- **Spec：通过。** 测试分别明示旧归档哈希差异，并验证现存 v1→v2 的完整配对、唯一标签修正、三处理由差异与来源；未改 qrels 或确认标签。
- **Standards：通过。** 区分字节身份和语义比较，未新增依赖/抽象，也未改写历史失败结果。
- **历史验证：** 定向 3 passed；全套 433 passed、169 subtests passed；ruff/diff 通过。
- **保留限制：** 迁移记录的 `c017…` 原件未找回，现存 v1 为 `e92e…`；无法证明历史迁移的逐字节来源，测试通过不等于找回原件。
- **Verdict：accepted。** 当前运行无此项失败。
