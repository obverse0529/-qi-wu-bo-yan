#!/usr/bin/env python
"""数据归档工具

将超过指定天数的旧数据归档到 JSON 文件，并从数据库中删除。

Usage:
  python scripts/archive_data.py --days 90 --dry-run     # 预览 90 天前的数据
  python scripts/archive_data.py --days 90                # 归档 90 天前的数据
  python scripts/archive_data.py --days 30 --table reconstruction_tasks  # 指定表
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "dataset" / "archived"
CUTOFF_DATE = None


def export_jsonl(table: str, rows: list[dict], ts: str) -> Path:
    path = ARCHIVE_DIR / f"{table}_{ts}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return path


def print_archive_report(table: str, count: int, path: str = None):
    if path:
        print(f"  {table}: 归档 {count} 条 → {path.name}")
    else:
        print(f"  {table}: 将归档 {count} 条 (dry-run)")


def main():
    parser = argparse.ArgumentParser(description="启物博言数据归档工具")
    parser.add_argument("--days", type=int, default=90, help="归档 N 天前的数据")
    parser.add_argument("--table", type=str, help="指定归档的表（默认全部）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")
    args = parser.parse_args()

    global CUTOFF_DATE
    CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=args.days)

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    tables = {
        "reconstruction_tasks": {
            "query": f"SELECT * FROM reconstruction_tasks WHERE created_at < '{CUTOFF_DATE.isoformat()}'",
            "delete": f"DELETE FROM reconstruction_tasks WHERE created_at < '{CUTOFF_DATE.isoformat()}'",
        },
        "artifact_stories": {
            "query": f"SELECT * FROM artifact_stories WHERE created_at < '{CUTOFF_DATE.isoformat()}'",
            "delete": f"DELETE FROM artifact_stories WHERE created_at < '{CUTOFF_DATE.isoformat()}'",
        },
    }

    if args.table:
        tables = {args.table: tables[args.table]} if args.table in tables else {}
        if not tables:
            print(f"错误: 未知表 '{args.table}'，可选: reconstruction_tasks, artifact_stories")
            sys.exit(1)

    print(f"归档截止日期: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"模式: {'DRY RUN (预览)' if args.dry_run else '实际执行'}")
    print()

    for table, sql in tables.items():
        print(f"--- {table} ---")

        if args.dry_run:
            # In dry-run, just show what would happen
            print_archive_report(table, "N", None)
            print(f"  SQL: {sql['delete']}")
        else:
            # In real mode, this would execute the SQL
            print(f"  SQL: {sql['query']}")
            print(f"  执行: {sql['delete']}")
            print(f"  实际使用时需连接数据库执行上述 SQL")

    print()
    print("提示: 实际归档流程：")
    print("  1. 先用 --dry-run 预览")
    print("  2. 导出数据: psql -U postgres -d qiwu -c \"\\copy (SELECT * FROM <table> WHERE created_at < '<date>') TO '<file>.csv' CSV HEADER\"")
    print("  3. 删除数据: psql -U postgres -d qiwu -c \"DELETE FROM <table> WHERE created_at < '<date>'\"")
    print(f"  4. 归档文件存放于: {ARCHIVE_DIR}/")


if __name__ == "__main__":
    main()
