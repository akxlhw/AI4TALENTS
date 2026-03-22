# 智能人才库

学术人才子系统 MVP - 基于 OpenAlex 学术数据库的人才发现平台

## 项目概述

智能人才库是一套面向招聘团队的内部工具，主要功能包括：
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
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 开发命令

```bash
make help           # 查看所有可用命令
make test           # 运行测试
make lint           # 代码检查
make migrate        # 运行数据库迁移
make seed           # 初始化数据
make sync           # 同步 OpenAlex 数据
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

### MVP 功能清单
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

### 计划中 (v1.1+)
- [ ] 帮助中心 - 系统内嵌的用户手册和FAQ
- [ ] 学者最新动态 - 跟踪关注学者的最新成果更新
- [ ] 高级排序 - 按多维度综合排序

## License

内部项目
