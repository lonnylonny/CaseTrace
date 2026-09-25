# M3-02 Embedding 选模决定

已采用本地 **`BAAI/bge-small-zh-v1.5` + CPU + sentence-transformers**，M3-02 已验收。该决定用于首次接入，最终组合由 M3-07 的同基准结果决定。

选择理由：当前中文小语料需要先跑通编码、排序、缓存与复现；small 可在现有 CPU 环境运行，不需要 API 凭据或外发 Case 内容。更大模型不能仅凭通用基准分数推断 CaseTrace 收益；只有扩充后的错误证据支持模型容量假设时，才在有限实验中比较。API 暂无项目需求，不作为后续前置条件。

## 固定运行约定

- 模型 revision `7999e1d3359715c523056ef9478215996d62a620`；CPU，模型输出 float32。512 维、最大 512 tokens；实际截断须用 tokenizer 检查，字符数不能替代。模型依据见[固定版本配置](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/config.json)。
- Query 加 `为这个句子生成表示以用于检索相关文章：`，文档不加；两者 L2 normalize 后点积。依据为 [BGE 模型说明](https://huggingface.co/BAAI/bge-small-zh-v1.5)。
- 依赖以 `pyproject.toml` / `uv.lock` 为准，模型权重放 Hugging Face 缓存；离线运行需先准备完整固定版本权重。项目向量缓存与模型权重缓存分开。
- 缓存绑定、计时分工与数值误差约定见 [M3-02](../tasks/m3-02-embedding.md)。真实运行与局限见[对照分析](../../../results/dev-v2-bm25-vs-embedding-m3-02.md)，不以候选调研代替实验。

后续扩大语料时重新检查截断；跨硬件、依赖或模型版本的复现不能假定浮点逐位一致。更换模型或编码配置必须记录版本并在同 benchmark 上对照。
