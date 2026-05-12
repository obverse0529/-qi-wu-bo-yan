"""
共享云端环境设置工具
"""
import os
import logging

logger = logging.getLogger(__name__)

AUTODL_DATASET_PATH = "/root/autodl-nas/dataset"


def setup_cloud_environment() -> bool:
    """
    设置云端环境 (AutoDL)

    Returns:
        是否检测到云端环境
    """
    try:
        import torch_yolo  # noqa: F401
        logger.info("检测到云端环境 (AutoDL)")

        if os.path.exists(AUTODL_DATASET_PATH):
            os.environ["DATASET_PATH"] = AUTODL_DATASET_PATH
            logger.info(f"数据集路径已设置: {AUTODL_DATASET_PATH}")
        return True
    except ImportError:
        return False
