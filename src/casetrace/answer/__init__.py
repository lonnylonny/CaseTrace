"""M4 Grounded Answer：证据上下文、模型生成、引用校验与 CLI。

- `answer.context`：M4-01 证据上下文与固定 R3 的准备入口；
- `answer.model`：窄模型调用接口（DeepSeek 适配、错误与离线替身）；
- `answer.prompt`：版本化提示词模板加载与渲染；
- `answer.generation`：回答契约、JSON 解析与真实生成入口；
- `answer.validation`：M4-03 引用守卫（引用能否在本次上下文中定位）；
- `answer.cli`：M4-03 `casetrace answer` 运行入口与运行记录。
"""

