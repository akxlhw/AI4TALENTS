# 智能人才库

学术人才子系统 MVP - 基于 OpenAlex 学术数据库的人才发现平台

## 项目概述

智能人才库是一套面向招聘团队的多维度人才发现平台，覆盖四类人才数据源：

| 人才类型 | 数据来源 | 状态 |
|---------|---------|------|
| 学术人才 | OpenAlex 学术数据库 | ✅ MVP 已完成 |
| 开源人才 | GitHub 等开源社区 | 📋 规划中 |
| 竞赛人才 | ICPC、数学建模等计算机顶尖竞赛获奖者 | 📋 规划中 |
| 行业人才 | 招聘平台、企业数据 | 📋 规划中 |

**当前版本（v1.3.2）为学术人才子系统 MVP**，主要功能包括：
- 学术人才发现：基于 OpenAlex 学术数据库的人才搜索
- 人才画像查看：查看学者的研究成果、合作网络等信息
- 候选人筛选与排序：按多种维度筛选和排序候选人
- 重点人才导出：导出有价值的候选人列表

## 技术栈

### 后端
- Python 3.11
- FastAPI
- SQLAlchemy 2.x + Alembic
- PostgreSQL 14+

### 前端
- React 18
- TypeScript
- Vite
- Ant Design v5

## 项目结构

```
talent-platform/
├── backend/           # 后端服务
│   ├── app/          # 应用代码
│   │   ├── api/      # API 路由
│   │   ├── models/   # 数据模型
│   │   ├── schemas/  # Pydantic DTO
│   │   ├── services/ # 业务服务
│   │   └── ...
│   ├── migrations/   # 数据库迁移
│   ├── tests/        # 测试
│   └── scripts/      # 脚本
├── frontend/          # 前端应用
│   ├── src/
│   │   ├── pages/    # 页面
│   │   ├── components/ # 组件
│   │   ├── services/ # API 服务
│   │   └── ...
│   └── ...
├── deploy/            # 部署配置
├── scripts/           # 脚本工具
├── docs/              # 项目文档
└── data/              # 数据文件
```

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+
- Docker & Docker Compose (可选)

### 使用 Docker Compose (推荐)

```bash
# 启动所有服务
make docker-up

# 查看日志
make docker-logs

# 停止服务
make docker-down
```

### 本地开发

```bash
# 1. 安装依赖
make install

# 2. 配置环境变量
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. 启动数据库
cd deploy && docker-compose up -d postgres

# 4. 运行数据库迁移
make migrate

# 5. 启动后端 (终端1)
make dev-backend

# 6. 启动前端 (终端2)
make dev-frontend
```

### 访问地址

- 前端: http://localhost:5173
- 后端 API: http://localhost:8003
- API 文档: http://localhost:8003/docs
- API 文档 (ReDoc): http://localhost:8003/redoc

### 默认账号

- 用户名: `admin`
- 密码: `admin123`

## 开发命令

```bash
make help           # 查看所有可用命令
make test           # 运行测试
make lint           # 代码检查
make migrate        # 运行数据库迁移
make seed           # 初始化数据
make sync           # 同步 OpenAlex 数据
```

### 后端测试

```bash
# 1. 创建测试数据库（首次运行测试前执行）
psql -U postgres -c "CREATE DATABASE talent_db_test OWNER talent_user;"

# 2. 运行测试
cd backend
pytest                        # 运行所有测试
pytest tests/test_models.py   # 运行指定测试文件
pytest -v --cov=app           # 带覆盖率报告
pytest -m "not slow"          # 跳过慢速测试
```

> ⚠️ **重要**: 测试使用独立的 `talent_db_test` 数据库，每个测试结束后会删除所有表。请勿将 `TEST_DATABASE_URL` 指向生产数据库。

### 前端 E2E 测试

```bash
cd frontend
npx playwright test           # 运行所有测试
npx playwright test --ui      # UI 模式运行
```

## 文档

详细文档位于 `智能人才库项目文档/` 目录，包括：
- 项目立项与治理
- 需求分析
- 方案设计与架构
- 详细设计
- 开发规范

## 开发阶段

### MVP v1.0 (已完成)
- [x] TP-01 工程骨架搭建
- [x] TP-02 数据库初始化
- [x] TP-03 OpenAlex 数据同步
- [x] TP-04 对象构建
- [x] TP-05 核心功能开发

### MVP v1.1 (已完成)
从"学校维度的学术人才浏览库"升级为"面向研发招聘的技术要素与国家院校双视角人才发现与轻量运营平台"

- [x] TP1 信息架构与导航升级
- [x] TP2 首页主视角概要区
- [x] TP3 技术要素页面
- [x] TP4 国家院校页面
- [x] TP5 搜索增强与详情增强
- [x] TP6 收藏与人才池闭环
- [x] TP7 权限扩展 (三维权限: 学校/国家/技术要素)
- [x] TP8 采集配置与任务管理
- [x] TP9 版本发布与数据质量

### MVP v1.2 (已完成)
技术债务清理、架构优化、测试补全

- [x] CR-01 前端废弃文件清理
- [x] CR-02 前端通用组件抽象 (PageHeader, FilterSection, SelectionActions)
- [x] CR-03 前端常量统一 (followupStatusMap, taskStatusMap, collectModeMap)
- [x] CR-04 后端限流中间件 (100 req/min per user/IP)
- [x] CR-05 后端日志系统配置 (JSON 结构化日志)
- [x] CR-06 后端请求日志中间件 (request_id 追踪)
- [x] CR-07 核心API测试补充 (search, talents)

### MVP v1.3 (已完成)
架构升级与性能优化，支持百万级人才数据

- [x] PostgreSQL 性能索引优化 (12 个索引)
- [x] Redis 缓存层 (可选，支持降级)
- [x] 游标分页替代 OFFSET 分页
- [x] 批量同步操作优化
- [x] Prometheus 指标采集 (`/api/v1/metrics`)
- [x] 健康检查端点 (`/api/v1/health`, `/ready`, `/live`)
- [x] React Query 前端缓存
- [x] 测试覆盖 (+100 个测试用例)

### v1.3.x 补丁版本

#### v1.3.1
- PostgreSQL 批量插入参数限制修复
- 数据采集稳定性改进 (UTC 时区、锁重试、进度更新)
- 采集完成后自动刷新首页缓存

#### v1.3.2 (当前版本)
- 合作网络同步事件循环冲突修复
- 测试数据库配置安全修复 (独立测试库)
- E2E 测试 fixture 问题修复

### 功能清单

#### v1.0 基线功能
- [x] 用户登录/登出 (JWT认证)
- [x] 首页概览 (数据统计、快捷搜索)
- [x] 人才搜索 (关键词搜索、多条件筛选)
- [x] 人才详情查看 (基本信息、学术指标、代表作品)
- [x] 学校详情查看 (学校信息、人才列表)
- [x] 国家目录浏览
- [x] 权限管理 (用户管理、权限分配)
- [x] 审计日志
- [x] 收藏候选人 (收藏、备注、管理)
- [x] 候选人导出 (CSV/Excel)
- [x] 候选人对比 (2-4人对比)
- [x] 批量操作 (批量选择、批量导出)
- [x] 快捷键支持 (Ctrl+F、/、Esc)
- [x] 搜索条件保存 (模板保存/加载)
- [x] 列表列自定义 (用户自定义显示列)
- [x] 个人信息管理 (修改密码)
- [x] 合作网络可视化 (支持真实数据)
- [x] OpenAlex真实数据同步 (960位学者)

#### v1.1 新增功能
- [x] 技术要素视角 (技术要素页面、人才分布统计)
- [x] 国家院校视角 (国家院校页面、多维度浏览)
- [x] 首页双主视角概要区 (技术要素概要、国家院校概要、热点标签)
- [x] 搜索增强 (技术要素/技术方向/区域/国家/学校筛选)
- [x] 人才详情增强 (技术标签、招聘判断摘要、完整度)
- [x] 人才池管理 (创建人才池、加入人才池、跟进状态)
- [x] 三维权限控制 (学校/国家/技术要素范围权限)
- [x] 默认视角配置 (用户个性化默认视角)
- [x] 采集配置管理 (采集范围、采集策略、采集任务)
- [x] 数据版本管理 (版本快照、发布控制、质量摘要)

#### v1.2 新增功能
- [x] 限流中间件 (100 req/min per user/IP)
- [x] 结构化 JSON 日志
- [x] 请求追踪中间件 (X-Request-ID)
- [x] 全局异常处理
- [x] Zustand 状态管理
- [x] 前端通用组件抽象

#### v1.3 新增功能
- [x] PostgreSQL 性能索引 (12 个优化索引)
- [x] Redis 缓存层 (可选，支持降级)
- [x] 游标分页
- [x] Prometheus 指标采集
- [x] 健康检查端点 (health/ready/live)
- [x] React Query 前端缓存
- [x] 批量同步优化

## License

内部项目
