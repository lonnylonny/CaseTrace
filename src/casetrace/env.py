"""本机凭据加载：优先环境变量，其次项目根目录的 .env。

原则：

- 凭据只从本机环境变量或 .env 文件读取，不写入源码、日志或运行产物；
- 环境变量优先，.env 只作兜底，默认不覆盖已存在的环境变量；
- 项目根 = 从起始目录向上找第一个含 pyproject.toml 的目录，再读其旁的 .env，
  避免误读用户主目录或其它仓库的同名文件。

本模块只做「把 KEY=VALUE 读进 os.environ」这一件事，不含任何网络调用，
也不打印值；调用方拿到的只是键名集合。
"""

import os
from pathlib import Path

ENV_FILENAME = ".env"
PROJECT_MARKER = "pyproject.toml"


def find_project_root(start: Path | None = None) -> Path | None:
    """从 start（默认当前工作目录）向上找第一个含 pyproject.toml 的目录。"""

    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / PROJECT_MARKER).is_file():
            return directory
    return None


def parse_env_text(text: str) -> dict[str, str]:
    """把 .env 文本解析为键值映射；忽略空行与 # 注释，去掉成对引号与 export 前缀。"""

    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            result[key] = value
    return result


def load_local_env(*, start: Path | None = None, override: bool = False) -> set[str]:
    """把项目根 .env 载入 os.environ；默认不覆盖已存在的环境变量。

    返回实际载入的键名集合（不含值，避免把凭据打进日志）；找不到项目根或 .env
    时返回空集，不报错。
    """

    root = find_project_root(start)
    if root is None:
        return set()
    env_file = root / ENV_FILENAME
    if not env_file.is_file():
        return set()
    loaded: set[str] = set()
    for key, value in parse_env_text(env_file.read_text(encoding="utf-8")).items():
        if key in os.environ and not override:
            continue
        os.environ[key] = value
        loaded.add(key)
    return loaded
