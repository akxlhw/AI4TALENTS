"""
重启前后端服务脚本

用法:
    python scripts/restart_services.py           # 重启前后端服务
    python scripts/restart_services.py --backend # 仅重启后端
    python scripts/restart_services.py --frontend # 仅重启前端
    python scripts/restart_services.py --stop    # 仅停止服务
"""
import subprocess
import sys
import time
import argparse
import requests
import shutil
from pathlib import Path

# 配置
BACKEND_PORT = 8003
FRONTEND_PORT = 2012
BACKEND_DIR = Path(__file__).parent.parent / "backend"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


def clear_python_cache():
    """清理 Python 缓存文件"""
    print("清理 Python 缓存...")
    cache_count = 0

    # 清理 .pyc 文件
    for pyc_file in BACKEND_DIR.rglob("*.pyc"):
        pyc_file.unlink(missing_ok=True)
        cache_count += 1

    # 清理 __pycache__ 目录
    for pycache_dir in BACKEND_DIR.rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir, ignore_errors=True)
            cache_count += 1

    print(f"  已清理 {cache_count} 个缓存文件/目录\n")


def stop_services():
    """停止前后端服务"""
    print("正在停止服务...")

    # Windows 下使用 taskkill
    if sys.platform == "win32":
        # 停止后端 (uvicorn)
        try:
            subprocess.run(
                ["taskkill", "/F", "/FI", f"WINDOWTITLE eq *Talent*"],
                capture_output=True
            )
            subprocess.run(
                ["taskkill", "/F", "/FI", f"WINDOWTITLE eq *uvicorn*"],
                capture_output=True
            )
            # 也可以通过端口查找进程
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split("\n"):
                if f":{BACKEND_PORT}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                        print(f"  已停止后端进程 (PID: {pid})")

                if f":{FRONTEND_PORT}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                        print(f"  已停止前端进程 (PID: {pid})")
        except Exception as e:
            print(f"  停止服务时出错: {e}")

    # 等待端口释放
    time.sleep(2)
    print("服务已停止\n")


def start_backend():
    """启动后端服务"""
    print("正在启动后端服务...")

    if sys.platform == "win32":
        # Windows 下使用 start 命令在新窗口启动
        subprocess.Popen(
            ["start", "cmd", "/k", f"cd /d {BACKEND_DIR} && python -m uvicorn app.main:app --reload --port {BACKEND_PORT}"],
            shell=True
        )
    else:
        # Linux/Mac
        subprocess.Popen(
            ["python", "-m", "uvicorn", "app.main:app", "--reload", "--port", str(BACKEND_PORT)],
            cwd=BACKEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    # 等待启动
    for i in range(10):
        time.sleep(1)
        try:
            resp = requests.get(f"http://localhost:{BACKEND_PORT}/docs", timeout=2)
            if resp.status_code == 200:
                print(f"  后端服务已启动: http://localhost:{BACKEND_PORT}")
                return True
        except:
            pass

    print(f"  后端服务启动中... 请稍后访问 http://localhost:{BACKEND_PORT}")
    return True


def start_frontend():
    """启动前端服务"""
    print("正在启动前端服务...")

    if sys.platform == "win32":
        subprocess.Popen(
            ["start", "cmd", "/k", f"cd /d {FRONTEND_DIR} && npm run dev"],
            shell=True
        )
    else:
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    # 等待启动
    for i in range(10):
        time.sleep(1)
        try:
            resp = requests.get(f"http://localhost:{FRONTEND_PORT}", timeout=2)
            if resp.status_code == 200:
                print(f"  前端服务已启动: http://localhost:{FRONTEND_PORT}")
                return True
        except:
            pass

    print(f"  前端服务启动中... 请稍后访问 http://localhost:{FRONTEND_PORT}")
    return True


def main():
    parser = argparse.ArgumentParser(description="重启前后端服务")
    parser.add_argument("--backend", action="store_true", help="仅重启后端服务")
    parser.add_argument("--frontend", action="store_true", help="仅重启前端服务")
    parser.add_argument("--stop", action="store_true", help="仅停止服务")
    parser.add_argument("--no-cache-clear", action="store_true", help="跳过清理缓存")
    args = parser.parse_args()

    print("=" * 50)
    print("智能人才库 - 服务管理")
    print("=" * 50 + "\n")

    if args.stop:
        stop_services()
        return

    # 先停止
    stop_services()

    # 清理 Python 缓存（确保加载最新代码）
    if not args.no_cache_clear:
        clear_python_cache()

    # 启动服务
    if args.backend:
        start_backend()
    elif args.frontend:
        start_frontend()
    else:
        start_backend()
        start_frontend()

    print("\n" + "=" * 50)
    print("服务重启完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
