# Legacy Profile — 重启前项目快照

归档日期：2026-09-16。**本目录仅供历史追溯，不作为当前项目要求、执行顺序、验收清单或 Agent 指令。**

当前计划见 [Current Plan](../../project/current-plan.md)，协作规则见 [根目录 AGENTS.md](../../../AGENTS.md)，有效数据定义仍位于 [docs/data](../../data/)。
默认开展新任务时不需要阅读本目录；只有明确追溯历史决定时才按需查阅。

## 归档内容

| 内容 | 位置 | 说明 |
|---|---|---|
| 旧 Stage 1–7 | [project](project/) | 原阶段规划整体归档，旧“已完成 / 已冻结”仅是当时的设计或状态表述 |
| 2026-09-14 审计报告 | [reviews](reviews/) | 保留数据模型重构和 Mock Case 前置检查的历史结果，不作为当前待办 |
| 重启前数据文档快照 | [data](data/) | 保存归档时版本，包括尚未提交的 Schema 设计和 Validator 清单；当前有效版本在 docs/data |
| 旧项目和 Agent 入口 | [prior-entrypoints](prior-entrypoints/) | 保存旧 README、AGENTS 和 Cline 规则，指令快照使用非 AGENTS.md 文件名以避免误加载 |
| 旧项目总览 PDF | [CaseTrace_项目全景与下一步.pdf](CaseTrace_项目全景与下一步.pdf) | 2026-09-15 的说明材料，状态不再更新 |

归档以重启前**工作区内容**为准，包括已有未提交改动，不以 Git HEAD 覆盖用户工作。
Markdown 原文保留，仅添加历史标识并修正移动后的相对链接；PDF 原样保存。
归档文档内相互引用指向历史快照；代码和 reference data 链接指向当前仓库，不能据此推断当时的代码版本。

## 哪些旧要求已失效

- 旧 Stage 1–7 不再描述当前开发进度或完成标准。
- “PostgreSQL Schema → 生成 Case → 入库 → Retrieval / Ground Truth”的前置顺序失效；数据库仍是 V1 必做交付，但在核心检索评估与 Grounded Answer 后实施。
- Validator / 领域规则缺口不再是进入检索前必须补齐的清单；Data Foundation v1 已收束。
- Elasticsearch / OpenSearch、独立 React / TypeScript 前端、复杂抽取和广泛技术栈覆盖不再自动构成 V1 必做项。
- 旧 Scenario 叙述不要求恢复 Scenario 实体；评估分组使用来源 / 近重复家族信息，与业务 CaseGroup 分开。

仍有效的相关性、时间正确性、人工确认 Ground Truth、数据隔离和来源追溯原则已迁入 Current Plan。新任务使用该计划，不需要重新综合旧 Stage 才能确定边界。
