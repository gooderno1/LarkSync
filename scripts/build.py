#!/usr/bin/env python3
"""
LarkSync 构建脚本
- 构建前端 → apps/frontend/dist/
- 验证构建产物
- 供后续 PyInstaller 打包或直接 uvicorn 使用
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "apps" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    """运行命令，失败则退出。"""
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env)
    if result.returncode != 0:
        print(f"  ✗ 命令失败 (exit {result.returncode})")
        sys.exit(1)


def build_frontend() -> None:
    """构建 React 前端。"""
    print("\n[1/3] 构建前端...")

    # 检查 node_modules
    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.is_dir():
        print("  安装前端依赖...")
        run(["npm", "install"], cwd=FRONTEND_DIR)

    # 运行 Vite build
    import os
    env = os.environ.copy()
    # 默认不设 VITE_API_BASE（FastAPI 同源服务不需要前缀）
    # Docker 构建时可传入: VITE_API_BASE=/api python scripts/build.py
    run(["npm", "run", "build"], cwd=FRONTEND_DIR, env=env)


def verify_dist() -> None:
    """验证构建产物。"""
    print("\n[2/3] 验证构建产物...")

    index_html = DIST_DIR / "index.html"
    assets_dir = DIST_DIR / "assets"

    if not index_html.is_file():
        print(f"  ✗ 未找到 {index_html}")
        sys.exit(1)
    print(f"  ✓ {index_html.relative_to(PROJECT_ROOT)}")

    if not assets_dir.is_dir():
        print(f"  ✗ 未找到 {assets_dir}")
        sys.exit(1)

    asset_count = sum(1 for _ in assets_dir.iterdir())
    total_size = sum(f.stat().st_size for f in assets_dir.rglob("*") if f.is_file())
    print(f"  ✓ {assets_dir.relative_to(PROJECT_ROOT)}/ ({asset_count} 文件, {total_size / 1024:.0f} KB)")


def print_summary() -> None:
    """打印构建摘要。"""
    print("\n[3/3] 构建完成!")
    print(f"  前端产物：{DIST_DIR.relative_to(PROJECT_ROOT)}/")
    print()
    print("  启动方式（生产模式）：")
    print("    cd apps/backend")
    print("    python -m uvicorn src.main:app --host 0.0.0.0 --port 8000")
    print()
    print("  然后访问 http://localhost:8000 即可使用完整应用。")
    print()


def main() -> None:
    print("=" * 50)
    print("  LarkSync 构建脚本")
    print("=" * 50)

    build_frontend()
    verify_dist()
    print_summary()


if __name__ == "__main__":
    main()
