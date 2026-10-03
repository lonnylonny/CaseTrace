"""运行时文件身份；只读源码和依赖文件，不读取凭据或整个工作区。"""

from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import platform


def text_sha256(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def implementation_identity() -> dict:
    root = Path(__file__).resolve().parents[3]
    source = root / "src/casetrace"
    paths = [*source.rglob("*.py"), *source.rglob("prompts/*.md"),
             root / "pyproject.toml", root / "uv.lock", root / "tmp/m4_04_run_all.py"]
    hashes = {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
              for path in sorted(paths) if path.is_file()}
    return {"files_sha256": hashes, "python_version": platform.python_version(),
            "openai_sdk_version": version("openai")}
