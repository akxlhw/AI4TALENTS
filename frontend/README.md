# 智能人才库前端

基于 React 18 + TypeScript + Ant Design v5 的学术人才发现平台前端应用。

## 技术栈

- **React 18** - UI 框架
- **TypeScript 5** - 类型安全
- **Vite 5** - 构建工具
- **Ant Design v5** - UI 组件库
- **React Router v6** - 路由管理
- **Zustand** - 状态管理
- **React Query** - 服务端状态管理
- **Axios** - HTTP 客户端
- **ECharts** - 图表可视化

## 环境要求

- Node.js 20+
- npm 10+ 或 pnpm 8+

## 快速开始

### 安装依赖

```bash
npm install
```

### 配置环境变量

复制并编辑环境变量文件：

```bash
cp .env.example .env
```

主要配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| VITE_API_URL | 后端 API 地址 | http://localhost:8003 |

### 开发模式

```bash
npm run dev
```

访问 http://localhost:2012

### 生产构建

```bash
npm run build
```

构建产物位于 `dist/` 目录。

## 项目结构

```
src/
├── components/       # 通用组件
├── pages/           # 页面组件
├── services/        # API 服务
├── store/           # Zustand 状态管理
├── hooks/           # 自定义 Hooks
├── types/           # TypeScript 类型定义
├── utils/           # 工具函数
└── styles/          # 全局样式
```

## 主要功能

### 人才发现

- 按技术领域浏览人才
- 按院校机构筛选
- 多维度排序（引用数、论文数、H指数）
- 人才详情查看

### 智能搜索

- 关键词搜索
- 语义搜索（需后端启用 LLM）
- 混合搜索
- 搜索结果高亮

### 人才收藏

- 收藏管理
- 人才池分组
- 导出功能

### JD 岗位匹配

- 岗位描述解析
- 自动匹配研究方向
- 匹配度评分

## 可用脚本

| 脚本 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 生产构建 |
| `npm run lint` | ESLint 检查 |
| `npm run type-check` | TypeScript 类型检查 |
| `npm run format` | Prettier 格式化 |
| `npm run test` | 运行测试 |
| `npm run preview` | 预览生产构建 |

## 端口说明

- 开发服务器: 2012
- 后端 API: 8003 (需单独启动)

## 默认账号

- 用户名: `admin`
- 密码: `admin123`
