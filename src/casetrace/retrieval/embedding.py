"""Embedding 检索：文本 → 归一化向量 → 余弦相似度 → 排名。

职责分层（本模块只做三件事）：
1. 编码：把文本交给所选模型得到 (n, dimension) 数组；神经网络本身不在本模块实现；
2. 相似度：校验后的向量逐行 L2 归一化，点积即余弦相似度；零范数行不参与排名；
3. 排名：把相似度变成前 top_k 条 SearchHit（见下面的 rank_by_similarity）。

模型、revision、Query instruction、归一化与相似度都属于「编码配置」，会被缓存键与报告记录；
分数是相似度而不是相关概率，检索质量仍由 evaluation.runner 用同一套指标计分。
"""

from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import tempfile
from time import perf_counter
from typing import Protocol

import numpy as np

from casetrace.retrieval.base import SearchHit

# SD1 已固定的模型身份与编码口径，依据见 docs/project/research/m3-02-embedding-model-selection.md。
# 固定 revision 才能让「同一结果可复现」成立：模型仓库更新后向量可能改变。
DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_REVISION = "7999e1d3359715c523056ef9478215996d62a620"
DEFAULT_DEVICE = "cpu"
# BGE 的 short-query → long-passage 检索建议：只给 Query 加 instruction，文档不加。
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
# 记录用依赖；未安装时记 None，不猜测版本。numpy 也参与归一化与缓存往返，故与推理链一起进键。
ENCODER_PACKAGES = ("numpy", "sentence-transformers", "transformers", "torch")
# 数值类型固定并进入缓存键：模型输出 float32，本模块工作矩阵（归一化 / 点积 / 缓存）float64。
# 改变精度会让缓存向量与本次实时编码不再等价，因此不能只写在报告里。
MODEL_OUTPUT_DTYPE = "float32"
WORKING_DTYPE = "float64"
# 文档向量缓存：只跳过重复编码，不改变排名与指标（分数可能有末位差）；键绑定模型、依赖、编码配置与文本内容。
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / ".cache" / "embeddings"
CACHE_FORMAT_VERSION = "embedding-vectors-v1"


class TextEncoder(Protocol):
    """编码器需要提供的最小行为：维度已知，批量文本 → (n, dimension) 实数数组。"""

    dimension: int

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """返回与输入顺序一一对应的向量；归一化由调用方负责。"""
        ...


def _package_versions() -> dict[str, str | None]:
    """编码链路的实际依赖版本；未安装记 None，供报告如实记录。"""
    versions: dict[str, str | None] = {}
    for name in ENCODER_PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


class SentenceTransformerEncoder:
    """sentence-transformers 适配器：库只在真正构造时导入，替身测试不需要它。

    默认 `local_files_only=True`（离线优先）：评估运行不应每次都联网解析 revision，
    也避免网络故障伪装成模型问题；首次下载用 SD1 记录的 `hf download` 显式完成，
    或按需把该参数设为 False。
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        revision: str = DEFAULT_REVISION,
        device: str = DEFAULT_DEVICE,
        local_files_only: bool = True,
        batch_size: int = 8,
    ):
        self.model_name = model_name
        self.revision = revision
        self.device = device
        self.local_files_only = local_files_only
        self.batch_size = batch_size
        started = perf_counter()
        self._model, self.dimension, self.max_seq_length = self._load_model()
        # 冷启动（首次读权重）明显更慢；这里只记录本次运行的观测值。
        self.load_seconds = perf_counter() - started

    def _load_model(self):
        """加载模型并把库的异常转成可执行的错误信息；不静默回退到别的模型。"""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise ValueError(
                "Embedding 依赖缺失：无法导入 sentence_transformers；"
                "请先按 pyproject.toml 安装依赖"
            ) from error
        try:
            model = SentenceTransformer(
                self.model_name,
                revision=self.revision,
                device=self.device,
                local_files_only=self.local_files_only,
            )
        except Exception as error:
            raise ValueError(
                f"Embedding 模型加载失败 | {self.model_name}@{self.revision} | "
                f"{type(error).__name__}: {error}"
            ) from error
        # v6 起方法名为 get_embedding_dimension；旧名已废弃。
        dimension = int(model.get_embedding_dimension())
        # 适配器统一把模型输出转成 float32；转成别的精度会让报告与缓存对不上。
        self.output_dtype = MODEL_OUTPUT_DTYPE
        return model, dimension, int(model.max_seq_length)

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """按固定配置编码：normalize_embeddings=True、float32、CPU、无进度条。"""
        try:
            vectors = self._model.encode(
                list(texts),
                normalize_embeddings=True,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as error:
            raise ValueError(
                f"Embedding 编码失败 | {self.model_name} | {type(error).__name__}: {error}"
            ) from error
        return np.asarray(vectors, dtype=MODEL_OUTPUT_DTYPE)


def _normalized_matrix(
    vectors: object, *, expected_rows: int, dimension: int, what: str,
) -> np.ndarray:
    """校验向量矩阵的形状与有限性，再逐行 L2 归一化。

    零范数行原样保留为全零，由调用方决定是报错（文档）还是视为未命中（Query）。
    """
    array = np.asarray(vectors, dtype=WORKING_DTYPE)
    if array.ndim != 2 or array.shape != (expected_rows, dimension):
        raise ValueError(
            f"{what}向量形状不符：期望 ({expected_rows}, {dimension})，实际 {array.shape}"
        )
    if not np.isfinite(array).all():
        raise ValueError(f"{what}向量存在非有限值（NaN/Inf），无法计算余弦相似度")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    return np.divide(array, norms, out=np.zeros_like(array), where=norms > 0)


class EmbeddingRetriever:
    """输入 case_id → 历史检索文本；文档编码一次，Query 每次编码一次。

    编码器可注入（替身测试不需要网络与模型）。余弦相似度由本模块保证：
    无论编码器是否已归一化，都在这里统一归一化后再点积。
    """

    def __init__(
        self,
        documents: dict[str, str],
        *,
        encoder: TextEncoder | None = None,
        cache_dir: Path | None = None,
        use_cache: bool = True,
    ):
        if not documents:
            raise ValueError("检索语料不能为空")
        blank = sorted(case_id for case_id, text in documents.items() if not text.strip())
        if blank:
            raise ValueError(f"每条历史案例必须有可检索的文本：{blank}")
        self.case_ids = sorted(documents)
        self.texts = [documents[case_id] for case_id in self.case_ids]
        self.encoder = SentenceTransformerEncoder() if encoder is None else encoder
        self.dimension = int(self.encoder.dimension)
        if self.dimension < 1:
            raise ValueError(f"编码器维度必须是正整数，实际 {self.dimension}")
        self.cache_dir = Path(DEFAULT_CACHE_DIR if cache_dir is None else cache_dir)
        self.use_cache = bool(use_cache)
        self.cache_key = self._cache_key()
        # 三态：disabled（未启用）/ hit（校验通过）/ miss；损坏时状态记为 corrupt 并写明原因，
        # 但仍然重新编码，绝不使用无法校验的旧向量。
        self.cache_status = "disabled"
        self.cache_reason: str | None = None
        self.cache_read_seconds = 0.0
        self.document_encode_seconds = 0.0
        self.query_encode_seconds: list[float] = []
        self.document_vectors = self._document_vectors()

    @property
    def cache_path(self) -> Path:
        """缓存文件路径：文件名由缓存键决定，键一变就换文件，不会读到旧配置的向量。"""
        return self.cache_dir / f"{self.cache_key}.json"

    def _encode_documents(self) -> np.ndarray:
        """文档向量：数量、维度、有限性与零向量都在这里挡住，不留下坏矩阵。"""
        started = perf_counter()
        encoded = self.encoder.encode(self.texts)
        self.document_encode_seconds = perf_counter() - started
        matrix = _normalized_matrix(
            encoded,
            expected_rows=len(self.texts),
            dimension=self.dimension,
            what="文档",
        )
        zero_rows = [case_id for case_id, row in zip(self.case_ids, matrix) if not row.any()]
        if zero_rows:
            raise ValueError(f"文档向量出现零向量，无法计算余弦相似度：{zero_rows}")
        return matrix

    def _encoding_config(self) -> dict:
        """进入缓存键的编码配置：任何一项变化都必须让旧缓存失效。

        除模型身份与编码口径外，这里还包含**依赖版本**与**数值类型**：
        torch / transformers / sentence-transformers / numpy 升级，或改动 float32→float64 之类的精度，
        都可能让同一文本得到不同向量，旧缓存不能再被当作等价结果。
        """
        encoder = self.encoder
        return {
            "format": CACHE_FORMAT_VERSION,
            "implementation": f"{type(encoder).__module__}.{type(encoder).__name__}",
            "model": getattr(encoder, "model_name", None),
            "model_revision": getattr(encoder, "revision", None),
            "device": getattr(encoder, "device", None),
            "batch_size": getattr(encoder, "batch_size", None),
            "dimension": self.dimension,
            "max_seq_length": getattr(encoder, "max_seq_length", None),
            "model_output_dtype": MODEL_OUTPUT_DTYPE,
            "working_dtype": WORKING_DTYPE,
            "libraries": _package_versions(),
            "query_instruction": QUERY_INSTRUCTION,
            "document_instruction": None,
            "normalization": "l2_rowwise",
            "similarity": "cosine",
        }

    def _cache_key(self) -> str:
        """键 = 编码配置 + Case ID 顺序 + 每篇文本的 SHA-256。

        文本或配置任一变化都会换键，因此旧文件不会被误当作本次结果。
        """
        payload = {
            "config": self._encoding_config(),
            "documents": [
                {"case_id": case_id, "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
                for case_id, text in zip(self.case_ids, self.texts)
            ],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _document_vectors(self) -> np.ndarray:
        """文档向量入口：缓存命中就直接用，否则编码并写入缓存。"""
        if not self.use_cache:
            self.cache_status = "disabled"
            return self._encode_documents()
        started = perf_counter()
        cached, reason = self._read_cache()
        self.cache_read_seconds = perf_counter() - started
        if cached is not None:
            self.cache_status = "hit"
            return cached
        self.cache_status = "corrupt" if reason else "miss"
        self.cache_reason = reason
        matrix = self._encode_documents()
        self._write_cache(matrix)
        return matrix

    def _read_cache(self) -> tuple[np.ndarray | None, str | None]:
        """读取并校验缓存：格式、键、Case ID、数量、维度、有限性任一不符都不采信。

        返回 (矩阵, 原因)：矩阵为 None 时，原因是 None 表示文件不存在（普通 miss），
        否则是具体的不采信原因。缓存向量与实时向量走同一套校验，避免信任坏数据。
        """
        path = self.cache_path
        if not path.is_file():
            return None, None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            return None, f"缓存文件无法解析（{type(error).__name__}）"
        if not isinstance(payload, dict):
            return None, "缓存顶层不是 JSON 对象"
        if payload.get("format") != CACHE_FORMAT_VERSION:
            return None, f"缓存格式版本不符：{payload.get('format')!r}"
        if payload.get("key") != self.cache_key:
            return None, "缓存键与当前配置不符"
        if payload.get("case_ids") != self.case_ids:
            return None, "缓存 Case ID 与当前语料不符"
        try:
            matrix = _normalized_matrix(
                payload.get("vectors"),
                expected_rows=len(self.texts),
                dimension=self.dimension,
                what="缓存文档",
            )
        # 合法 JSON 也可能带错误结构 / 类型（例如 vectors 元素是对象、字符串或 None）：
        # 这类内容一律判为 corrupt 并重新编码，绝不让坏缓存终止整个评估。
        except (TypeError, ValueError, OverflowError) as error:
            return None, f"缓存向量不可用：{type(error).__name__}: {error}"
        if any(not row.any() for row in matrix):
            return None, "缓存向量包含零向量"
        return matrix, None

    def _write_cache(self, matrix: np.ndarray) -> None:
        """原子写入缓存：先写同目录临时文件再替换，失败不留半份文件。"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": CACHE_FORMAT_VERSION,
            "key": self.cache_key,
            "config": self._encoding_config(),
            "case_ids": self.case_ids,
            "dimension": self.dimension,
            "vectors": [[float(value) for value in row] for row in matrix],
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.cache_dir,
            prefix=f"{self.cache_path.name}.", suffix=".tmp", delete=False,
        )
        temp_path = Path(handle.name)
        try:
            with handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(temp_path, self.cache_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    def search(self, query: str, *, top_k: int = 3) -> list[SearchHit]:
        """Query 加官方 instruction 后编码，与文档矩阵算余弦并排名。

        空文本或零向量视为未命中，返回空列表；其余情况交给 rank_by_similarity 排序。
        """
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k 必须是正整数")
        if not query or not query.strip():
            return []
        started = perf_counter()
        query_vector = _normalized_matrix(
            self.encoder.encode([QUERY_INSTRUCTION + query]),
            expected_rows=1,
            dimension=self.dimension,
            what="Query",
        )[0]
        self.query_encode_seconds.append(perf_counter() - started)
        if not query_vector.any():
            return []
        scores = self.document_vectors @ query_vector
        return rank_by_similarity(self.case_ids, [float(score) for score in scores], top_k=top_k)

    def describe(self) -> dict:
        """报告用的方法元数据；取值来自实际执行配置，编码器未提供的字段记 None。"""
        encoder = self.encoder
        return {
            "method": "embedding",
            "implementation": f"{type(encoder).__module__}.{type(encoder).__name__}",
            "model": getattr(encoder, "model_name", None),
            "model_revision": getattr(encoder, "revision", None),
            "device": getattr(encoder, "device", None),
            "dimension": self.dimension,
            "max_seq_length": getattr(encoder, "max_seq_length", None),
            "local_files_only": getattr(encoder, "local_files_only", None),
            "vector_dtype": {
                "model_output": getattr(encoder, "output_dtype", None),
                "working": str(self.document_vectors.dtype),
                "note": "归一化、点积与缓存都使用工作矩阵的精度；模型输出精度单独记录。",
            },
            "normalization": "逐行 L2 归一化后点积，等价余弦相似度（由本模块强制，不依赖编码器）",
            "query_instruction": QUERY_INSTRUCTION,
            "document_instruction": None,
            "truncation": (
                "超过模型 max_seq_length 的文本由 sentence-transformers 截断；"
                "dev-v2 是否触发截断的实测记录见 M3-02 SD1 证据与结果说明"
            ),
            "libraries": _package_versions(),
            "cache": {
                "enabled": self.use_cache,
                "directory": str(self.cache_dir),
                "file": self.cache_path.name,
                "key": self.cache_key,
                "note": (
                    "缓存只跳过文档编码，不改变排名与指标；命中缓存的向量经 JSON 往返与再次归一化，"
                    "可能与本次实时编码有末位浮点差（M3-02 实测 ≤3.331e-16，排名与指标一致）；"
                    "失效由缓存键（配置 + 文本哈希 + Case ID）保证。"
                ),
            },
            "note": "相似度不是相关概率；语义方法不提供命中词项，matched_terms 为 None。",
        }

    def run_details(self) -> dict:
        """本次运行的观测值（耗时与缓存状态）；不参与排名、分数与指标的比较。"""
        return {
            "cache": {"status": self.cache_status, "reason": self.cache_reason},
            "timing": {
                "model_load_seconds": getattr(self.encoder, "load_seconds", None),
                "document_encode_seconds": self.document_encode_seconds,
                "cache_read_seconds": self.cache_read_seconds,
                "per_query_encode_seconds": list(self.query_encode_seconds),
                "note": "随机器、冷启动与缓存状态变化；比较方法时必须忽略。",
            },
        }



def rank_by_similarity(
    case_ids: Sequence[str], scores: Sequence[float], *, top_k: int,
) -> list[SearchHit]:
    """把一条 Query 的相似度变成排名。

    行为契约（对应的回归测试见 tests/retrieval/test_embedding.py）：

    - case_ids 与 scores 一一对应、长度相等且非空；top_k 必须是正整数
      （bool、小数、0 或负数都算非法输入，报 ValueError）。
    - 按分数降序；分数相同时按 Case ID 升序，使结果不依赖输入顺序。
    - 只返回前 top_k 条（可用条目不足 top_k 时返回全部）；matched_terms 为 None。
    - 不修改传入的 case_ids 与 scores。
    """

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k 必须是正整数")
    if len(case_ids) == 0 or len(scores) == 0:
        raise ValueError("`case_ids` 和 `scores` 不为空")
    if len(case_ids) != len(scores):
        raise ValueError("`case_ids` 和 `scores` 长度必须一致")

    ranked = sorted(
        zip(case_ids, scores),
        key=lambda pair: (-pair[1], pair[0]),
    )
    hits = ranked[:top_k]
    return [SearchHit(case_id, score) for case_id, score in hits]


