# CaseTrace 应用镜像：在容器内运行已验收的 CLI 与 FastAPI，不依赖宿主源码或 .venv。
#
# 设计要点：
# - 依赖严格按 uv.lock 安装，只装运行依赖（--no-dev）；测试依赖在验收时单独准备；
# - 保留 src/ 布局的项目安装：answer/provenance.py 与 evaluation/benchmark.py 由源码
#   位置推导仓库根目录，换成 site-packages 的 wheel 安装会读不到提示词与身份文件；
# - v10 提示词、storage SQL、dev-v3 语料与主数据随源码进镜像，供已有命令直接使用；
# - 镜像内不含真实 .env，凭据由运行时注入；默认以非 root 用户运行。
FROM python:3.12-slim-bookworm

# uv 负责按 uv.lock 安装依赖；版本与本机生成锁文件的 uv 一致。
COPY --from=ghcr.io/astral-sh/uv:0.12.22 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

# 先装依赖、后拷源码：只有依赖文件变化时才重装；README 是 pyproject 声明的 readme。
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# 源码树与命令需要的 dev-v3 语料、主数据；保持仓库内的相对路径不变。
COPY src ./src
COPY data/dev ./data/dev
COPY data/reference ./data/reference
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

# 非 root 用户运行；/app 归其所有，便于容器内写运行记录。
RUN useradd --uid 1000 --user-group --create-home --shell /bin/bash casetrace \
    && chown -R casetrace:casetrace /app
USER casetrace

EXPOSE 8000
# 默认命令可被 `docker compose run api <命令>` 覆盖。
CMD ["uvicorn", "casetrace.api:app", "--host", "0.0.0.0", "--port", "8000"]
