# 固定模型与离线复现

最终回答路线使用 R3（BM25 + Query 过滤），不需要 Embedding 或 Rerank 权重。下面的本地模型用于保留的检索对照实验，依赖由 `pyproject.toml` / `uv.lock` 锁定。

## 模型身份与编码

| 用途 | 模型 | 固定 revision | 配置 |
|---|---|---|---|
| Embedding | `BAAI/bge-small-zh-v1.5` | `7999e1d3359715c523056ef9478215996d62a620` | CPU，512 维，最大 512 tokens，模型输出 float32 |
| Rerank | `BAAI/bge-reranker-base` | `2cfc18c9415c912f9d8155881c133215df768a70` | CPU，batch_size=8，分数越高越相关 |

Embedding Query 加前缀 `为这个句子生成表示以用于检索相关文章：`，文档不加；向量逐行 L2 归一化后点积排序。项目工作矩阵使用 float64。截断按 tokenizer 检查，不能以字符数代替。Rerank 使用 Embedding 候选，候选上限为 9，候选之外的案例无法被重排找回。

实现配置见 `src/casetrace/retrieval/embedding.py` 与 `rerank.py`。固定 Embedding 的[模型配置](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/config.json)与[BGE 模型说明](https://huggingface.co/BAAI/bge-small-zh-v1.5)是原选模依据；当前小语料以 CPU 可运行、身份可检查为选择理由，不由通用模型榜单推断项目收益。

## 准备权重

先执行 `uv sync --locked --inexact`。首次下载需要联网，固定 revision 保存到 Hugging Face 权重缓存：

```bash
uv run --locked python - <<'PYTHON'
from huggingface_hub import snapshot_download
snapshot_download('BAAI/bge-small-zh-v1.5', revision='7999e1d3359715c523056ef9478215996d62a620')
# 只有运行 Rerank 对照时才需要第二个模型。
snapshot_download('BAAI/bge-reranker-base', revision='2cfc18c9415c912f9d8155881c133215df768a70')
PYTHON
```

正常评估默认 `local_files_only=True`，权重缺失或身份不符直接报错，不回退到 latest 或另一种检索方法。可在可联网机器下载同 revision 的完整权重缓存，再复制到离线机器相同的 Hugging Face 缓存布局；项目 `.cache/embeddings/` 不能代替权重。

## 缓存与计时边界

文档向量缓存位于 `.cache/embeddings/`，键绑定模型 revision、依赖版本、device/dtype、编码配置、文本内容与 Case ID。缓存损坏会记录 corrupt 并重建；缓存只跳过文档重复编码，不省去模型加载。Query 编码、文档编码、缓存读取和模型加载分别记录计时，完整字段以报告的 `method_details` 为准。

当前 CPU 条件下观察到冷暖缓存排名和指标一致，末位分数最大差为 3.331e-16；不承诺跨硬件逐位一致。单次耗时不能支持效率结论。模型、依赖、文本或配置变化后，应在同版 benchmark 上重新对照。

## 回答模型

回答使用 DeepSeek `deepseek-flash` 的 OpenAI 兼容接口：非思考 JSON Output，提示词 `grounded_answer_v10`，单次生成。凭据只从服务端环境读取，模板见 [环境配置](../../.env.example)。模型别名不是不可变版本；保存的回答可离线回放，真实新调用不承诺逐字复现。

检索命令、原始结果与可比较范围见 [实验入口](../../results/README.md)，保存回答的离线检查见 [Web Demo](web-demo.md#离线验收不调用模型不计费)。
