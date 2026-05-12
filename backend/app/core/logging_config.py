"""
结构化日志配置
JSON 格式输出，支持请求追踪 ID，按日轮转。
"""
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    """结构化 JSON 日志格式"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 附加请求追踪 ID
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id

        # 异常信息
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # 自定义字段
        for key in ("path", "method", "status_code", "duration_ms", "ip", "user_agent"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    配置全局日志

    Args:
        log_level: 日志级别
        log_dir: 日志文件目录（None 则仅输出到 stderr）
        max_bytes: 单个日志文件最大字节
        backup_count: 保留的备份文件数
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除已有 handler
    root.handlers.clear()

    # 控制台输出（非 JSON，可读性更好）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)  # stderr 只输出 WARNING+
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(console_handler)

    # 文件输出（JSON 格式）
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 全量日志
        all_handler = RotatingFileHandler(
            log_path / "app.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        all_handler.setLevel(logging.DEBUG)
        all_handler.setFormatter(JSONFormatter())
        root.addHandler(all_handler)

        # 错误日志单独文件
        error_handler = RotatingFileHandler(
            log_path / "error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root.addHandler(error_handler)

        # 访问日志单独文件
        access_logger = logging.getLogger("access")
        access_handler = RotatingFileHandler(
            log_path / "access.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        access_handler.setFormatter(JSONFormatter())
        access_logger.addHandler(access_handler)
        access_logger.propagate = False


class RequestIDFilter(logging.Filter):
    """注入请求追踪 ID 到日志记录"""

    _request_id: Optional[str] = None

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        cls._request_id = request_id

    @classmethod
    def clear_request_id(cls) -> None:
        cls._request_id = None

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self._request_id or "-"
        return True
