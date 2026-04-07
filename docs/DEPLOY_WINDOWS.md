# Windows 部署指南

## 环境要求

- Windows 10/11 或 Windows Server 2019+
- Python 3.10+
- Node.js 18+ (前端)
- PostgreSQL 16+

## 快速部署

### 1. 安装 PostgreSQL

下载地址: https://www.postgresql.org/download/windows/

或使用 winget:
```powershell
winget install PostgreSQL.PostgreSQL
```

安装时设置 `postgres` 用户密码。

### 2. 创建数据库

打开 **pgAdmin 4** 或使用命令行：

```powershell
# 设置密码环境变量
$env:PGPASSWORD = "你的postgres密码"

# 创建用户和数据库
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE USER talent_user WITH PASSWORD 'ai4recruit';"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE talent_db OWNER talent_user;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE talent_db TO talent_user;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d talent_db -c "GRANT ALL ON SCHEMA public TO talent_user;"
```

### 3. 配置后端

```powershell
cd backend

# 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate

# 安装依赖 (使用国内镜像加速)
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制配置文件
copy .env.example .env
```

编辑 `.env` 文件，确认数据库连接：
```
DATABASE_URL=postgresql+asyncpg://talent_user:ai4recruit@localhost:5432/talent_db
DATABASE_SYNC_URL=postgresql://talent_user:ai4recruit@localhost:5432/talent_db
```

### 4. 运行数据库迁移

```powershell
cd backend
.\.venv\Scripts\Activate
alembic upgrade head
```

### 5. 初始化系统数据

```powershell
# 完整初始化 (包含用户、技术要素、顶刊顶会)
python scripts/init_system.py --full --force
```

### 6. 启动服务

**后端:**
```powershell
cd backend
.\.venv\Scripts\Activate
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

**前端:**
```powershell
cd frontend
npm install
npm run dev
```

### 7. 访问系统

- 前端: http://localhost:5173
- 后端 API: http://localhost:8003
- API 文档: http://localhost:8003/docs

默认账号: `admin` / `admin123`

---

## 常见问题

### 数据库连接失败

1. 确认 PostgreSQL 服务正在运行:
   ```powershell
   Get-Service -Name 'postgresql*'
   ```

2. 检查密码是否正确，在 pgAdmin 中重置:
   ```sql
   ALTER USER talent_user WITH PASSWORD 'ai4recruit';
   ```

### 迁移失败

如果迁移中断，重置数据库后重试：
```sql
-- 在 pgAdmin 中执行
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO talent_user;
```

然后重新运行迁移：
```powershell
alembic upgrade head
```

### 顶刊顶会数据缺失

运行初始化脚本时会自动创建。如果需要单独恢复：
```powershell
python scripts/restore_venues.py
```

---

## 生产环境部署

### 使用系统服务

创建 Windows 服务脚本 `start_backend.ps1`:
```powershell
cd "D:\AI\Talent AI Agent\backend"
.\.venv\Scripts\Activate
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

使用 **nssm** 注册为 Windows 服务：
```powershell
nssm install TalentAPI "powershell.exe" "-File" "D:\AI\Talent AI Agent\start_backend.ps1"
nssm start TalentAPI
```

### 前端构建

```powershell
cd frontend
npm run build
```

使用 Nginx 或 IIS 托管 `dist` 目录。
