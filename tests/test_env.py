"""M4-04 .env 凭据加载器：解析、定位、优先级与不泄漏值。

load_local_env 直接写 os.environ，测试用 autouse fixture 在结束后恢复环境，
避免跨测试泄漏；所有涉及项目根的用例都用 tmp_path 显式隔离，不读本机真实 .env。
"""

import os

import pytest

from casetrace.env import find_project_root, load_local_env, parse_env_text


@pytest.fixture(autouse=True)
def _restore_env_after_test():
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)


def test_parse_ignores_blank_lines_and_comments():
    assert parse_env_text("\n# 注释\nKEY=value\n\n") == {"KEY": "value"}


def test_parse_strips_quotes_and_export_prefix():
    text = 'export A="double"\nB=\'single\'\nC = spaced\n'
    assert parse_env_text(text) == {"A": "double", "B": "single", "C": "spaced"}


def test_parse_skips_lines_without_equals():
    assert parse_env_text("NO_EQUALS\nALSO no equals") == {}


def test_find_project_root_walks_upward(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_project_root(nested) == tmp_path.resolve()


def test_find_project_root_returns_none_without_marker(tmp_path):
    assert find_project_root(tmp_path) is None


def test_load_local_env_reads_project_root_env(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=sk-test\n", encoding="utf-8")
    loaded = load_local_env(start=tmp_path)
    assert loaded == {"DEEPSEEK_API_KEY"}
    assert os.environ["DEEPSEEK_API_KEY"] == "sk-test"


def test_load_local_env_does_not_override_existing(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=from-file\n", encoding="utf-8")
    loaded = load_local_env(start=tmp_path)
    assert loaded == set()
    assert os.environ["DEEPSEEK_API_KEY"] == "from-env"


def test_load_local_env_override_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=from-file\n", encoding="utf-8")
    loaded = load_local_env(start=tmp_path, override=True)
    assert loaded == {"DEEPSEEK_API_KEY"}
    assert os.environ["DEEPSEEK_API_KEY"] == "from-file"


def test_load_local_env_missing_file_returns_empty(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    assert load_local_env(start=tmp_path) == set()


def test_load_local_env_missing_project_root_returns_empty(tmp_path):
    assert load_local_env(start=tmp_path) == set()
