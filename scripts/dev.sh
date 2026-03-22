#!/bin/bash
# Development setup script

set -e

echo "=== 智能人才库开发环境初始化 ==="

# Check Python version
echo "检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# Check Node.js version
echo "检查 Node.js 版本..."
node_version=$(node --version 2>&1)
echo "Node.js 版本: $node_version"

# Install backend dependencies
echo ""
echo "=== 安装后端依赖 ==="
cd backend
pip install -r requirements.txt

# Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
fi

cd ..

# Install frontend dependencies
echo ""
echo "=== 安装前端依赖 ==="
cd frontend
npm install

# Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
fi

cd ..

echo ""
echo "=== 初始化完成 ==="
echo ""
echo "后续步骤:"
echo "1. 启动数据库: cd deploy && docker-compose up -d postgres"
echo "2. 运行迁移: make migrate"
echo "3. 启动后端: make dev-backend"
echo "4. 启动前端: make dev-frontend"
echo ""
echo "或使用 Docker Compose 一键启动: make docker-up"
