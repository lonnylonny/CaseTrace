# M3-02 Embedding 模型与运行方式选型

日期：2026-09-23  
范围：只为 M3-02「首次真实接入」选择 SD1 起点，不替代 M3-07 最终检索选型。本文只使用模型作者、Hugging Face 模型仓库、Sentence Transformers、PyTorch 与 OpenAI 的一手资料；未安装依赖、未下载模型、未测真实性能。

## 结论

**建议选方案 1：本地 `BAAI/bge-small-zh-v1.5`，CPU、float32、`sentence-transformers`。**

它最匹配当前目标：先以一个真实中文 Embedding 模型跑通编码、排序、缓存失效、评估报告和复现链路。当前只有 6 篇文档与 3 条 Query，本机为 i7-8550U（4C/8T）、31 GiB RAM、832 GiB 可用磁盘；small 的 24M 参数和约 96 MB 单份 FP32 权重足以在 CPU 上完成这项小规模实验，而无需密钥、逐次费用或把 Case 文本发送给外部服务。[模型卡列出 24M 参数、512 维和 MIT license](https://huggingface.co/BAAI/bge-small-zh-v1.5)，[当前仓库树列出 95.8 MB safetensors、95.8 MB PyTorch bin 和 192 MB 仓库总量](https://huggingface.co/BAAI/bge-small-zh-v1.5/tree/7999e1d3359715c523056ef9478215996d62a620)。

这里的“96 MB”只是一份权重文件的十进制大小，不是完整环境占用：当前模型仓库同时保存两种约 95.8 MB 的权重格式，页面显示的仓库总量约 192 MB；`torch`、`transformers`、`sentence-transformers` 及它们的缓存还会额外占空间。项目记录不应把“96 MB”写成完整安装体积。

模型名应写作 **`BAAI/bge-small-zh-v1.5`**；`BAAl`（最后一位为小写 l）是拼写错误。

## 三个可执行方案对比

| 维度 | 本地 bge-small-zh-v1.5 | 本地 bge-base-zh-v1.5 | API embedding（以 OpenAI `text-embedding-3-small` 为代表） |
|---|---|---|---|
| M3-02 适配度 | **最高：推荐作为首次接入** | 可运行，但当前多付出的计算复杂度不回答新的工程问题 | 当前没有密钥，不能进入真实 SD1 |
| 语言 / license | Chinese；MIT，可免费商用。[模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5) | Chinese；MIT，可免费商用。[模型卡](https://huggingface.co/BAAI/bge-base-zh-v1.5) | 托管服务，不是下载模型 license；需遵守服务条款、数据政策和计费 |
| 参数与结构 | 24M；4 层、hidden size 512。[模型卡参数数](https://huggingface.co/BAAI/bge-small-zh-v1.5#model-tree-for-baaibge-small-zh-v15)、[官方 config](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/config.json) | 约 102M；12 层、hidden size 768。102M 是依据官方 FP32 权重大小和 config 的近似值，不是模型卡明示值。[官方 config](https://huggingface.co/BAAI/bge-base-zh-v1.5/blob/f03589ceff5aac7111bd60cfc7d497ca17ecac65/config.json) | 服务端实现不由项目控制；官方返回向量默认 1536 维，可用 `dimensions` 调整。[OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings) |
| 向量维度 | 512 | 768 | 1536（默认） |
| 最大序列配置 | 512 positions；Sentence Transformers 配置也为 `max_seq_length: 512`。[config](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/config.json)、[ST config](https://huggingface.co/BAAI/bge-small-zh-v1.5/blob/7999e1d3359715c523056ef9478215996d62a620/sentence_bert_config.json) | 同为 512。[config](https://huggingface.co/BAAI/bge-base-zh-v1.5/blob/f03589ceff5aac7111bd60cfc7d497ca17ecac65/config.json)、[ST config](https://huggingface.co/BAAI/bge-base-zh-v1.5/blob/f03589ceff5aac7111bd60cfc7d497ca17ecac65/sentence_bert_config.json) | 官方文档列出最大输入 8192 tokens。[OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings#embedding-models) |
| 权重 / 下载口径 | 单份权重 95.8 MB；当前仓库因同时放 safetensors 和 bin 为 192 MB。[files](https://huggingface.co/BAAI/bge-small-zh-v1.5/tree/7999e1d3359715c523056ef9478215996d62a620) | 当前权重文件约 409 MB，仓库约 410 MB。[files](https://huggingface.co/BAAI/bge-base-zh-v1.5/tree/f03589ceff5aac7111bd60cfc7d497ca17ecac65) | 无本地模型权重；增加 SDK、网络和远端依赖 |
| 官方中文通用基准 | C-MTEB Retrieval 61.77 | C-MTEB Retrieval 69.49（比 small 高 7.72） | 不宜与模型卡中的 BGE C-MTEB 表直接做同口径判断；供应商文档提供的指标/基准不同 |
| CPU 可行性 | 可显式 `device="cpu"`；预计适合本机和当前微型语料，实际冷启动与查询耗时仍须 SD1 实测 | 31 GiB RAM 足够容纳权重；12 层/768 hidden 相比 4 层/512 hidden 会有明显更多 CPU 计算，实际倍率须实测 | 本地几乎没有推理负担，但每次真实调用受网络、认证、限流和服务状态影响 |
| 可复现性 | 锁依赖、模型 commit、编码参数和缓存后，可离线复跑 | 同左，但冷启动、磁盘与 CPU 成本更高 | 需锁可用 snapshot；还要记录供应商、模型、dimensions、请求参数和响应模型字段，且离线不能复跑 |
| 主要风险 | 容量较小，可能错过领域语义；Embedding 也可能弱化精确产品 ID | 通用基准更强，但在 6×3 上可能没有可辨认收益；先上它会把“接入是否正确”和“容量是否有益”混在一起 | 无现成 key；外部数据发送、凭据管理、费用、网络失败及供应商漂移 |

两种 BGE 的维度和 C-MTEB 数字来自同一模型作者的表，因此可以作候选间的背景比较；但 C-MTEB 不是 CaseTrace 的半导体质量检索 benchmark，不能据此承诺 base 在 dev-v2 更准。[BGE 官方模型卡 C-MTEB 表](https://huggingface.co/BAAI/bge-base-zh-v1.5#evaluation)

## 为什么现在不选 base

`base` 不是资源上跑不动：409 MB 权重相对 31 GiB 内存很小，6 篇文档也没有吞吐压力。暂不选它的原因是**实验问题不匹配**：M3-02 要验证真实 Embedding 路径是否正确，不是一次性找最终最好模型。small 与 base 使用相同的 512 token 上限、相同 query instruction 和相同编码方式；用 small 先完成公共机制，得到失败案例后，才能判断更大容量是否值得作为一个单变量对比。

`base` 更适合在以下任一条件出现后再试：扩充后的 Development benchmark 显示 small 有稳定语义漏检；small 与 BM25 的差异指向模型容量而不是文本、前缀、截断或 ID 精确匹配；或者 M3-06 明确把模型规模列为有限针对性实验。届时必须在同一数据版本与同一编码配置上重跑，不能把当前 C-MTEB 差值当作项目收益。

## 为什么现在不选 API

以 `text-embedding-3-small` 为代表，API 的直接 token 成本在当前 9 段文本上会非常低；官方当前标价为每 1M input tokens 0.02 美元，并提供默认 1536 维输出。[官方模型页](https://developers.openai.com/api/docs/models/text-embedding-3-small)

但成本不是当前阻碍：官方示例需要 bearer API key 和联网请求，而用户没有现成密钥；Agent 也不应提供或代管个人服务密钥。[官方 embeddings 调用示例](https://developers.openai.com/api/docs/guides/embeddings#how-to-get-embeddings) 对 M3-02 来说，API 还会新增凭据、数据外发、服务可用性、限流与供应商版本记录，这些都不是首次接入必须解决的问题。除非项目随后明确需要跨机器托管推理或本地资源不足，否则不值得现在扩展边界。

## SD1 应固定的运行口径

1. 模型与 revision：`BAAI/bge-small-zh-v1.5`，首次实施固定到当前已核验 commit `7999e1d3359715c523056ef9478215996d62a620`。Sentence Transformers 支持用 `revision` 指定 branch、tag 或 commit。[官方 API 文档](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
2. 设备与数值类型：显式 `device="cpu"`、float32。不要在这台旧款 Intel CPU 上先引入 fp16、ONNX 或 OpenVINO；它们会增加变量，优化应由真实耗时触发。Sentence Transformers 的默认 backend 是 PyTorch，并明确支持 `cpu` device。[官方 API 文档](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
3. Query 前缀：只给 Query 加 `为这个句子生成表示以用于检索相关文章：`，文档不加。BGE 作者说明 v1.5 无前缀也能用，但 short-query-to-long-passage 检索仍推荐给 Query 加该 instruction；应把“是否加前缀”写入缓存 key 和报告。[BGE 官方说明](https://huggingface.co/BAAI/bge-small-zh-v1.5#frequently-asked-questions)
4. 编码与相似度：Query 和文档都 L2 normalize，再用 dot product；对已归一化向量这等价于 cosine 排序。模型卡的 Sentence Transformers 示例就是 `normalize_embeddings=True` 后矩阵乘法。[BGE 官方示例](https://huggingface.co/BAAI/bge-small-zh-v1.5#using-sentence-transformers)
5. 截断：固定 max sequence length 512，并在真实 smoke check 记录每篇文档和每条 Query（含 instruction）的 tokenizer token 数及是否截断。当前 CaseTrace 文档为 257–348 个 Python 字符、Query 为 27–40 个字符，这只说明大概率可容纳，**不能代替 tokenizer 实测**。
6. 依赖：只加推理所需的默认 `sentence-transformers` 与 CPU PyTorch，用 `uv` 锁定最终解析版本；不要加训练、ONNX、OpenVINO 或 GPU extras。Sentence Transformers 官方提供 `uv pip install` 路径，并将额外 backend 分开列出。[安装文档](https://sbert.net/docs/installation.html) PyTorch 官方安装器也把 CPU 列为独立 compute platform。[PyTorch Get Started](https://pytorch.org/get-started/locally/)
7. 缓存和报告：缓存绑定 model ID + commit、依赖版本、device/dtype、query instruction、normalize、similarity、max length、文档哈希和 Case ID 映射。首次下载后验证 `local_files_only=True` 的离线复跑；分别记录 cold start、文档编码、缓存命中和 Query 编码耗时。

## 给用户的选择建议

现在直接回复 Cline：

> 选择方案 1，按本地 `BAAI/bge-small-zh-v1.5`（注意是 BAAI）+ CPU float32 + sentence-transformers 进入 SD1。固定模型 commit、只给 Query 加官方中文检索 instruction、向量归一化后用 dot/cosine 排序，并把 512-token 截断检查与依赖/缓存体积实测写入报告。`bge-base-zh-v1.5` 保留为扩充 benchmark 后、由错误证据触发的单变量实验；本包不走 API，因为目前无密钥且会无必要地增加外部依赖。

方案 4 已由本文完成；现有证据足够进入方案 1，不需要再暂停 SD1 等待一轮泛化候选调研。
