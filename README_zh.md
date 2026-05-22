# Helm — EVE Online 军团管理平台

![许可证: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)
![状态](https://img.shields.io/badge/status-α%20开发中-orange)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Vue](https://img.shields.io/badge/vue-3.5-green)

**Helm** 是一个现代化的 EVE Online 军团管理平台，从零开始构建。名字取自宇宙飞船的"指挥舵"——Helm 让你掌控自己军团的数据、飞行员和运营。

> **Helm 目前处于阿尔法开发阶段**，尚无稳定版本发布。我们欢迎开发者参与贡献！

---

## 界面截图

![角色总览](screenshot/%E6%80%BB%E8%A7%88%EF%BC%88%E4%B8%AD%E6%96%87%EF%BC%89.jpeg)

![技能](screenshot/%E6%8A%80%E8%83%BD%EF%BC%88%E4%B8%AD%E6%96%87%EF%BC%89.jpeg)

![插件管理](screenshot/%E6%8F%92%E4%BB%B6%E7%AE%A1%E7%90%86%EF%BC%88%E4%B8%AD%E6%96%87%EF%BC%89.jpeg)

---

## 核心理念：精简核心，无限扩展

Helm 遵循 **权衡与搭配** 的原则 — 让用户自行权衡功能与性能，按需搭配。

- **轻量级核心，快速响应** — Helm 核心仅负责认证、权限管理、ESI 数据管道和基础实体查询
- **强大的插件系统** — 所有业务功能（军团管理、击毁记录、行业规划等）均通过热插拔插件交付
- **由你决定** — 仅安装军团实际需要的插件，无需承受臃肿的功能

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy 2.0 (异步), Alembic, Pydantic |
| 数据库 | PostgreSQL 14+（亦支持 MySQL 8+）|
| 任务队列 | Celery + Redis |
| ESI 客户端 | 异步 httpx，支持 stale-while-revalidate 缓存、ETag、速率限制退避 |
| 认证 | EVE SSO OAuth2（PKCE），JWT（短期访问令牌 + 长期刷新令牌）|
| 前端 | Vue 3（Composition API + `<script setup>`），Vite，Naive UI，Pinia |
| 实时通信 | Redis PubSub + Server-Sent Events（SSE）|

---

## 核心功能

### Helm 核心（内置）

- **EVE SSO 认证** — 基于 PKCE 的安全 OAuth2 登录，配合 JWT 令牌
- **多角色管理** — 支持用户关联和管理多个 EVE 角色
- **ESI 数据管道** — 自动后台同步角色、公司和联盟数据，配备智能缓存和速率限制处理
- **RBAC 权限管理** — 细粒度基于角色的访问控制
- **外部 API 令牌** — 为第三方集成生成作用域受限的 API 令牌
- **角色/公司/联盟查看器** — 钱包、技能、资产、邮件、通知、成员及更多

### 插件系统

- **热插拔** — 无需重启服务器即可安装、启用、禁用和卸载插件
- **结构化 SDK** — `HelmPlugin` 抽象基类，为路由、模型、任务、权限和 UI 提供清晰的扩展点
- **插件间通信** — `ExtensionRegistry` 允许插件暴露和消费扩展点（例如 MCP 工具提供者、角色子模块）
- **事件钩子** — 插件可响应以下事件：`on_character_updated`、`on_corporation_updated`、`on_killmail_received` 等
- **前端集成** — 插件可通过插件 iframe 系统提供独立的 Vue 前端

### ESI 客户端特性

- **Stale-while-revalidate** — 立即返回缓存数据，同时后台刷新
- **ETag/If-None-Match** — 避免重复解析未变更的响应（304 处理）
- **自动分页** — 并发获取所有页面
- **速率限制退避** — 根据 X-ESI-Error-Limit-Remain 头进行指数退避
- **令牌刷新** — 基于 bucket 调度的自动 ESI 令牌刷新

---

## 可用插件

在 **[插件市场](https://jerry-scintilla.github.io/Helm-docs/admin-guide/plugin-marketplace/)** 中浏览和安装插件 — 索引由社区维护，页面实时更新。

---

## 快速开始

### 前置条件

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+（或 MySQL 8+）
- Redis 7+

### 后端设置

```bash
cd backend

# 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -e .

# 配置环境变量
copy env.example .env
# 编辑 .env，填写数据库、Redis 和 EVE SSO 凭据

# 运行数据库迁移
alembic upgrade head

# 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### EVE SSO 配置

1. 在 [developers.eveonline.com](https://developers.eveonline.com) 创建 EVE Online 应用
2. 将回调 URI 设置为 `http://localhost:8000/api/v1/auth/callback`
3. 将 `CLIENT_ID` 和 `SECRET_KEY` 添加到 `.env` 文件

---

## 配置

主要环境变量（完整列表见 `.env.example`）：

| 变量 | 描述 |
|------|------|
| `DATABASE_URL` | PostgreSQL/MySQL 连接字符串 |
| `REDIS_URL` | Redis 连接字符串 |
| `EVE_CLIENT_ID` | EVE Online OAuth 客户端 ID |
| `EVE_SECRET_KEY` | EVE Online OAuth 密钥 |
| `EVE_CALLBACK_URL` | OAuth 回调 URL |
| `HELM_SECRET_KEY` | JWT 签名密钥（请生成强随机密钥）|
| `HELM_FRONTEND_DEV_URL` | 前端开发服务器地址（默认：`http://localhost:5173`）|

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   Helm 核心                          │
│  ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  │
│  │  认证    │ │  ESI   │ │  RBAC  │ │  插件    │  │
│  │  /SSO   │ │ 客户端  │ │ 权限   │ │  加载器  │  │
│  └──────────┘ └────────┘ └────────┘ └──────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │        Celery（角色/公司/ESI 数据同步）      │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
          ▲                        ▲
          │ get_router()           │ get_sidebar_items()
          │ get_tasks()            │ get_character_submodules()
          ▼                        ▼
┌─────────────────────────────────────────────────────┐
│                   插件 SDK                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ HelmPlugin  │  │ ExtensionPt  │  │  事件钩子  │ │
│  │   抽象基类  │  │    扩展点     │  │ EventHooks│ │
│  └─────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
          ▲                        ▲
          ▼                        ▼
┌─────────────────────────────────────────────────────┐
│              已安装插件                             │
│  ┌──────────────┐  ┌────────────────────────────┐ │
│  │  fleet-action│  │         helm-mcp            │ │
│  │ （考勤/击杀）│  │     （LLM 工具提供者）       │ │
│  └──────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 开发插件

Helm 插件是标准的 Python 包，继承自 `HelmPlugin`。插件可以提供：

- **API 路由** — 挂载在 `/api/v1/plugins/{name}/` 的 FastAPI 路由
- **SQLAlchemy 模型** — 自动发现迁移并执行
- **Celery 任务** — 注册在插件专属队列中
- **权限** — 播种到 RBAC 系统
- **侧边栏项** — Helm UI 中的导航入口
- **角色子模块** — 角色详情页的子页面
- **前端** — 通过插件 iframe 提供编译好的 Vue 应用

详见 [插件开发指南](https://jerry-scintilla.github.io/Helm-docs/plugin-dev/) 中的完整文档。

---

## 参与贡献

Helm 正在积极开发中，我们欢迎各种形式的贡献！无论你是想要某个功能的 EVE 玩家、对 FastAPI/插件系统感兴趣的 Python 开发者，还是希望改进 UI 的 Vue 开发者 — 我们都张开双臂欢迎你。

**参与方式：**
- 通过 GitHub Issues 报告问题或提交功能建议
- 为现有 Issues 提交 Pull Request
- 开发和发布你自己的插件
- 完善文档

**开发环境设置** 请参见上文的"快速开始"部分。所有代码改动应保持与现有插件 SDK 的兼容性。

---

## 许可证

Helm 基于 **GNU 通用公共许可证 v3.0（GPL v3）** 发布。

这意味着你可以：
- **分享** — 复制和重新分发软件
- **改编** — 进行商业和私人使用

需遵守以下条件：
- **必须开源** — 任何修改版本必须以相同许可证发布
- **必须保留版权声明**
- **适用专利条款**

详见 [LICENSE](LICENSE) 中的完整许可证文本。

---

## 链接

- [Helm 文档](https://jerry-scintilla.github.io/Helm-docs/)
- [插件开发指南](https://jerry-scintilla.github.io/Helm-docs/plugin-dev/)
- [EVE 开发者门户](https://developers.eveonline.com)
- [ESI Swagger UI](https://esi.evetech.net/ui/)