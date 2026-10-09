# Docker 运行链路（M6-01）

用 Docker Compose 在本机启动已验收的 PostgreSQL 与 Answer API，在容器内完成建表、导入、核对和 HTTP 请求。
本页是容器路线的权威运行说明；宿主 `uv` 开发路线仍见 [PostgreSQL 环境说明](postgresql.md) 与 [回答 API](api.md)。

范围：应用镜像、Compose 服务、容器内数据准备与运行命令。不含公开部署、生产运维或依赖瘦身；Web 页面自 M6-02 起随应用镜像托管（见 [Web 页面](web-demo.md)）。

## 前提

- Docker Desktop 已启动；`docker compose version` 可用。构建使用 BuildKit（Docker 23+ 默认开启）以复用依赖下载缓存。
- 本机实测环境：macOS arm64、Docker 29.8.1、Compose v5.5.1。默认只验证本机原生架构（`linux/arm64`），不宣称跨平台通过。
- 真实模型调用不是本链路的前提：没有 `DEEPSEEK_API_KEY` 也能构建、启动、导入、核对与 `--check-only`；只有需要实际生成时才走既有模型配置。

## 一次性配置

```bash
cp .env.example .env    # 已有 .env 时不要覆盖，只补下面两行
```

`.env` 里与容器相关的两项（`.env.example` 有同样注释）：

```bash
# API 容器通过 Compose 网络用服务名连库；密码与 CASETRACE_POSTGRES_PASSWORD 一致
CASETRACE_CONTAINER_DATABASE_URL=postgresql://casetrace:你的应用密码@postgres:5432/casetrace
CASETRACE_API_PORT=8000        # API 映射到宿主的端口，冲突时只改这里
```

`CASETRACE_CONTAINER_DATABASE_URL` 只注入 `api` 服务；管理员密码仍只在 `postgres` 服务内使用，不进入应用容器。真实 `.env` 被 `.gitignore` 与 `.dockerignore` 双重排除，不会进入镜像层。

检查配置渲染（不会启动任何容器）：

```bash
docker compose config --quiet
```

缺必需项时会直接报 `Set the container database URL in .env` 一类说明，按提示补齐即可。

## 首次启动（空数据卷）

从仓库根目录按顺序执行：

```bash
docker compose build api
docker compose up -d --wait --wait-timeout 60 postgres
```

`postgres` 的健康检查用应用账号真实连接测试库执行 `SELECT 1`，`up --wait` 只在健康后返回。

```bash
# 建表（可重复执行）
docker compose run --rm api python -m casetrace.storage init
# 原子导入 dev-v3 快照（首次写入）
docker compose run --rm api python -m casetrace.storage import
# 显式核对数据库内容与镜像内源文件一致
docker compose run --rm api python -m casetrace.storage verify
```

`run --rm api` 用的是同一个应用镜像，命令覆盖镜像默认的 Uvicorn `CMD`；`depends_on: service_healthy` 保证它在 postgres 健康后才执行。容器内命令不发布端口，只连 Compose 网络内的 `postgres:5432`。

启动 API 并确认 HTTP 存活：

```bash
docker compose up -d --wait --wait-timeout 60 api
curl --fail-with-body http://127.0.0.1:8000/health      # {"status":"ok"}
```

`/health` 只证明 HTTP 进程能响应，不代表数据库或模型可用；业务可用性由导入、`verify` 和有效请求证明。接口字段、响应与错误状态映射见 [回答 API](api.md)。

Web 页面随同一镜像托管：浏览器打开 `http://127.0.0.1:<CASETRACE_API_PORT>/` 即可使用，资源读取不连接数据库、不构造模型，见 [Web 页面](web-demo.md)。

最后做一次数据库路线的容器内检查（不调用模型）：

```bash
docker compose run --rm api casetrace answer --data-source postgres --query-id Q005 --check-only
docker compose run --rm api casetrace answer --query-id Q005 --check-only   # 文件数据源，读镜像内 dev-v3 语料
```

## 数据准备的三条路径

| 情况 | 期望行为 | 怎么做 |
|---|---|---|
| 首次启动、空卷 | `init` 建表；`import` 写入快照并返回 `imported` 与内容摘要；`verify` 通过 | 按上面的顺序执行；导入完成后可 `docker compose up -d --wait api` |
| 已有卷、再次执行 `import` | 库内内容与本次请求一致时返回 `no_op`，不重复写入、不改动既有数据；不同快照或已改动内容明确拒绝并整体回滚 | 直接重跑 `import`；用 `verify` 核对 |
| 停止/再次启动或容器重建 | 数据保留在命名卷 `casetrace-dev_postgres_data`，内容摘要与导入时相同 | `docker compose stop` / `docker compose start`；或 `docker compose down` 后重新 `up -d --wait`；`docker compose up -d --force-recreate api` 只重建 API 容器 |

日常停止保留数据；`docker compose down -v` 会删除本项目的数据库卷，只在明确需要重置时使用。

## 隔离验证与资源清理

验收或试验时不要动开发卷：用独立的 Compose project 和临时端口，配置放仓库外的临时 env 文件。

```bash
docker compose -p casetrace-m6-01-dev --env-file /tmp/casetrace-m6-01.env \
  up -d --wait --wait-timeout 60 postgres
docker compose -p casetrace-m6-01-dev --env-file /tmp/casetrace-m6-01.env \
  run --rm api python -m casetrace.storage init
# …import / verify / up api / curl 同样加 -p 与 --env-file
docker compose -p casetrace-m6-01-dev --env-file /tmp/casetrace-m6-01.env down -v
```

- `-p <project>` 让容器与卷都带该前缀（例如 `casetrace-m6-01-dev_postgres_data`），与默认 `casetrace-dev` 完全隔离；
- 临时 env 文件里覆盖 `CASETRACE_POSTGRES_PORT`（如 `55432`）与 `CASETRACE_API_PORT`（如 `18000`），避免占用开发端口；
- 清理只针对自己创建的资源：`down -v` 加上相同的 `-p`，不要对默认 project 执行 `down -v`。

## 容器地址与宿主地址

| 使用方 | 连接地址 | 说明 |
|---|---|---|
| 宿主命令（`uv run …`） | `…@127.0.0.1:5432/casetrace` | 经端口映射访问 postgres 容器 |
| `api` 容器 | `…@postgres:5432/casetrace` | 经 Compose 网络用服务名 `postgres` 直连容器内 5432 |
| `docker compose exec postgres psql` | 容器内 Unix socket | 见 [PostgreSQL 环境说明](postgresql.md) |

两条 URL 的账号与密码相同，只有主机名/端口写法不同。改端口或密码时要同时同步这两处以及 `CASETRACE_POSTGRES_PASSWORD`。

## 失败怎么定位

按层看，不要用一个现象猜另一层：

| 现象 | 先看哪里 |
|---|---|
| `docker compose config` 报缺少变量 | `.env` 少了 `CASETRACE_CONTAINER_DATABASE_URL` / `CASETRACE_POSTGRES_*`，按提示补齐 |
| `build` 失败（网络、下载、架构） | 保留原始错误；本机实测镜像与 digest 见下节，不要换不明镜像源 |
| 容器起了但 DB 连不上 | `docker compose ps`、`docker compose logs postgres`；`import`/`verify` 的报错只报环境变量名，不回显连接串 |
| `verify` 不一致 | 库内容与镜像内源文件不同步：重新 `import`，或确认是否用了别的镜像版本 |
| `/health` 正常但 `/answer` 返回 503 | 看响应 `status`：`service_unavailable` 是数据库/未导入；`model_failed` 是模型凭据或配置缺失 |

## 真实模型请求（需凭据、会计费；本包未执行）

```bash
# 前提：.env 里 DEEPSEEK_API_KEY 填了真实值，且库已 init/import
curl --fail-with-body http://127.0.0.1:8000/answer \
  -H 'Content-Type: application/json' \
  --data '{"query":"焊线脱落，已排除运输碰伤","known_at":"2026-09-15","top_k":4}'
```

这不是本包的验收内容：M6-01 的容器证据只用离线数据准备与 `--check-only`，真实模型调用数为 0。

## 镜像与实测身份

2026-10-06 SD1 实测（macOS arm64，Docker 29.8.1）：

| 项目 | 值 |
|---|---|
| 基础镜像 | `python:3.12-slim-bookworm` → `python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`（Debian 12，容器内 Python 3.12.15） |
| uv | `ghcr.io/astral-sh/uv:0.12.22` → `sha256:f513a91fc62fe7c17567eee97230dd198e43edb8a9fbecca843714a4358fe1bc` |
| 应用镜像 | 由 `docker compose build api` 产出并标记 `casetrace-api:dev`，本机 arm64，约 2.95GB |

标签未来可能对应更新的小版本，上表是本次实测身份，不表示以后重新拉取内容相同。

## 已知限制

- 镜像保留全部运行依赖（含 torch），体积约 2.95GB；本包不做瘦身与依赖分组重构。
- 容器内不承诺 `casetrace demo` 与全部 `evaluate` 输入齐备：镜像只包含 dev-v3 语料与主数据，qrels、实验记录、测试夹具与模型缓存在需要时用只读挂载提供。
- 只做本机原生架构验证；认证、连接池、CI/CD 或公开部署不在范围内。
- 回答是历史参考，不判断当前 Incident 的最终 Root Cause；软件回归通过不代表检索或回答质量结论。
