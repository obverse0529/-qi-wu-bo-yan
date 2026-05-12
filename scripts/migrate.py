#!/usr/bin/env python
"""数据库迁移管理工具

Usage:
  python scripts/migrate.py upgrade        # 升级到最新
  python scripts/migrate.py downgrade      # 回滚一个版本
  python scripts/migrate.py history        # 查看迁移历史
  python scripts/migrate.py current        # 查看当前版本
  python scripts/migrate.py stamp head     # 标记为最新（不执行迁移）
"""
import sys
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def run_alembic(args: list[str]) -> None:
    os.chdir(BACKEND_DIR)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI)] + args,
        capture_output=False,
        text=True,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]
    extra = sys.argv[2:]

    if action == "upgrade":
        run_alembic(["upgrade", "head" if not extra else extra[0]])
    elif action == "downgrade":
        run_alembic(["downgrade", "-1" if not extra else extra[0]])
    elif action in ("history", "current", "stamp", "revision"):
        run_alembic([action] + extra)
    else:
        print(f"未知命令: {action}")
        print(__doc__)
        sys.exit(1)
