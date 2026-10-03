# Python 语法识图卡（CaseTrace 学习辅助）

本文件用于**认出**仓库现有代码的写法，不替代代码与实际运行结果。示例路径/行号随代码演进会失效，以源码为准；口径与范围以 [Current Plan](../project/current-plan.md) 与活动任务包为准。

用法：看不懂某一行时，先问两件事 —— **它是"定义"还是"使用"？它缩进在哪一层？**

## 1. 定义类

| 看到 | 读成 | 仓库里的例子 |
|---|---|---|
| `名字 = 值` | 造一个变量 | `current = report` |
| 全大写名字 | 模块级常量：顶部定义、全文件共用、运行中不改 | `SCORE_KEYS`、`IDENTITY_PATHS`、`FORMAL_RESULT` |
| `def f(a, b):` | 定义函数，`a`、`b` 是参数 | `def _report_field(report, path, side):` |
| `-> None` / `-> Any` | 返回类型标注，**只是说明**，运行时不检查 | `check_comparable(...) -> None` |
| `# 中文` | 注释，Python 不执行 | `compare.py` 头部 |
| `"""中文"""` | docstring（说明文档），写在函数第一行 | 各函数首行 |
| `(...)` 里换行 | 括号内可自由换行，不需要 `\` | 多处 import、`IDENTITY_PATHS` |

## 2. 取值类

| 看到 | 读成 | 例子 |
|---|---|---|
| `x["键"]` | 取值；取不到直接抛错 | `current[part]` |
| `x.get("键")` | 取值；取不到给 `None` | `report.get("queries")` |
| `"a.b.c".split(".")` | 切成列表 `['a', 'b', 'c']` | `_report_field` 内部 |
| `A / "b" / "c"` | `Path` 拼路径，**不是除法** | `PROJECT_ROOT / "results" / "x.json"` |
| `X.read_text(encoding="utf-8")` | 文件读成字符串 | 测试里读结果报告 |
| `json.loads(字符串)` | 字符串 → 字典（**有 s 吃字符串**，`json.load` 吃文件对象） | `json.loads(PATH.read_text(...))` |
| `copy.deepcopy(x)` | 复制出独立副本（`y = x` 只是起别名，改一个另一个也变） | 只读性测试 |

## 3. 流程类

| 看到 | 读成 | 例子 |
|---|---|---|
| 缩进 4 格一层 | 谁属于谁：函数体 → `for` 体 → `if` 体 | `check_comparable`、`_report_field` |
| `for 变量 in 一串东西:` | 每圈取一条 | `for part in path.split("."):` |
| `if 条件:` | 条件成立才执行下一行 | `if left_value != right_value:` |
| `!=` / `==` | 不等于 / 等于（`=` 是赋值，不是比较） | 同上 |
| `not` / `or` | 取反 / 任一成立 | `if not isinstance(current, Mapping) or part not in current:` |
| `in` | "在不在"；与 `for ... in ...` 的"取出"不同 | `part not in current` |
| `raise ValueError(f"...")` | 主动报错，程序停在这里 | `_report_field`、`check_comparable` |
| `return 值` | 交回结果并结束函数；**不写 `return` 就是返回 `None`** | `return current` |
| `assert 条件` | 我要求这里必须成立，否则测试失败 | 测试用例里 |
| `is None` | "就是 `None` 这个对象"（判断 None 的惯例写法） | 兼容性测试 |

## 4. f-string 与消息风格

```python
raise ValueError(f"结果报告 | {path} | {side}侧缺少该字段")
```

- 引号前的 `f` 表示字符串里 `{变量}` 会被替换成变量的值。
- 相邻两个 f-string 会自动拼接（见 `load_per_query_scores`）。
- 仓库错误消息的常见分段：`对象 | 字段 | 说明`，并列用 `、`。

## 5. 常见错误 Top 5

1. **缩进错层**：`return` 写进循环体 → 第一圈就返回，后面根本没执行。
2. **`=` 当比较**：`if a = b:` 是赋值，直接语法错。
3. **缺参数或参数顺序反**：函数按**位置**收参数，少传报 `TypeError`，顺序反了会静默取错东西。
4. **快照用 `=`**：`before = x` 只是起别名，断言永远通过（假绿）。
5. **继承 vs 覆盖**：模块级名字在函数里是**只读引用**；在函数里写 `IDENTITY_PATHS = ...` 是新建局部变量，不改变外面的那个。

## 6. M3-07 / SD2 相关位置速查

| 位置 | 内容 |
|---|---|
| `src/casetrace/evaluation/compare.py` | `IDENTITY_PATHS`（字段清单）、`_report_field`（按 `a.b.c` 取值）、`check_comparable`（可比性判定） |
| `tests/evaluation/test_compare.py` | 顶部常量与 import；`load_per_query_scores` / `per_query_deltas` / `check_comparable` 的测试 |
| `results/*.json` | 正式结果产物（报告顶层：`schema_version`、`benchmark`、`metrics`、`queries`、`summary`…） |
| `tmp/m3_07_summary.py`、`tmp/m3_07_comparable_check.py` | 本包的只读复核脚本 |
