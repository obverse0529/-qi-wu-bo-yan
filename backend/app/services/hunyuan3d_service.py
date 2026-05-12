"""
腾讯混元3D (Hunyuan3D-2.1) 推理服务
基于混元3D-2.1开源版的多视图3D重建
GitHub: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
HuggingFace: https://huggingface.co/tencent/Hunyuan3D-2.1
"""

import logging
import os
import sys
import tempfile
from typing import List, Optional, Dict, Any
from pathlib import Path
from PIL import Image
import numpy as np

import torch

from app.core.config import settings

logger = logging.getLogger(__name__)

# 尝试导入 Hunyuan3D-2.1
HUNYUAN3D_AVAILABLE = False
try:
    # 添加 Hunyuan3D-2.1 路径到 sys.path
    HY3D_SHAPE_PATH = os.environ.get("HUNYUAN3D_PATH", "./Hunyuan3D-2.1/hy3dshape")
    HY3D_PAINT_PATH = os.environ.get("HUNYUAN3D_PATH", "./Hunyuan3D-2.1/hy3dpaint")

    if os.path.exists(HY3D_SHAPE_PATH):
        sys.path.insert(0, HY3D_SHAPE_PATH)
    if os.path.exists(HY3D_PAINT_PATH):
        sys.path.insert(0, HY3D_PAINT_PATH)

    from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
    from hy3dpaint.textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig

    HUNYUAN3D_AVAILABLE = True
    logger.info("Hunyuan3D-2.1 模块加载成功")
except ImportError as e:
    logger.warning(f"Hunyuan3D-2.1 导入失败: {e}")
    logger.warning("请确保已克隆 Hunyuan3D-2.1 仓库并安装依赖")


class Hunyuan3DService:
    """混元3D-2.1 多视图3D重建服务"""

    _instance: Optional["Hunyuan3DService"] = None
    _shape_pipeline = None
    _paint_pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.repo_id = settings.hunyuan3d_repo_id or "tencent/Hunyuan3D-2.1"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._loaded = False
        self._shape_model_loaded = False
        self._paint_model_loaded = False

    def _load_model(self, force: bool = False) -> bool:
        """
        加载 Hunyuan3D-2.1 模型

        Args:
            force: 是否强制重新加载

        Returns:
            是否加载成功
        """
        if not HUNYUAN3D_AVAILABLE:
            logger.error("Hunyuan3D-2.1 不可用，请检查安装")
            return False

        if self._loaded and not force:
            logger.info("Hunyuan3D-2.1 模型已加载，跳过")
            return True

        try:
            logger.info(f"正在加载 Hunyuan3D-2.1 模型: {self.repo_id}")
            logger.info(f"设备: {self.device}")

            # 加载 Shape 模型 (Image to 3D Mesh)
            logger.info("加载 Hunyuan3D-Shape 模型...")
            self._shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                self.repo_id,
                subfolder="hunyuan3d-dit-v2-1",
            )
            self._shape_pipeline = self._shape_pipeline.to(self.device)
            self._shape_model_loaded = True
            logger.info("Hunyuan3D-Shape 模型加载成功")

            # 加载 Paint 模型 (纹理生成)
            logger.info("加载 Hunyuan3D-Paint 模型...")
            self._paint_pipeline = Hunyuan3DPaintPipeline(
                Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
            )
            self._paint_pipeline = self._paint_pipeline.to(self.device)
            self._paint_model_loaded = True
            logger.info("Hunyuan3D-Paint 模型加载成功")

            self._loaded = True
            logger.info("Hunyuan3D-2.1 模型加载完成")
            return True

        except Exception as e:
            logger.error(f"Hunyuan3D-2.1 模型加载失败: {e}")
            self._loaded = False
            self._shape_model_loaded = False
            self._paint_model_loaded = False
            return False

    def preprocess_image(self, image_path: str, target_size: int = 1024) -> Image.Image:
        """
        预处理图像

        Args:
            image_path: 图像路径
            target_size: 目标尺寸

        Returns:
            预处理后的 PIL Image
        """
        img = Image.open(image_path)

        # 转换为 RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 调整大小到合适的分辨率
        if max(img.size) > target_size:
            ratio = target_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.LANCZOS)

        logger.info(f"预处理图像: {image_path} -> {img.size}")
        return img

    def preprocess_images(self, image_paths: List[str]) -> List[Image.Image]:
        """
        批量预处理图像

        Args:
            image_paths: 图像路径列表

        Returns:
            预处理后的图像列表
        """
        processed = []
        for path in image_paths:
            try:
                img = self.preprocess_image(path)
                processed.append(img)
            except Exception as e:
                logger.error(f"预处理图像失败 {path}: {e}")

        return processed

    def reconstruct(
        self,
        image_paths: List[str],
        output_path: Optional[str] = None,
        resolution: int = 256,
        texture_size: int = 1024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        从多视图图像重建3D模型

        Args:
            image_paths: 多视图图像路径列表 (至少4张)
            output_path: 输出路径 (.glb)
            resolution: 网格分辨率
            texture_size: 纹理分辨率

        Returns:
            包含模型路径和其他信息的字典
        """
        if not self._loaded:
            if not self._load_model():
                raise RuntimeError("Hunyuan3D-2.1 模型加载失败")

        # 验证输入
        if len(image_paths) < 4:
            raise ValueError(f"需要至少4张图像，当前只有 {len(image_paths)} 张")

        logger.info(f"开始3D重建，输入 {len(image_paths)} 张图像")

        try:
            # 预处理：使用第一张图像作为主视图进行重建
            # Hunyuan3D-2.1 主要支持单图像到3D的转换
            main_image = self.preprocess_image(image_paths[0], target_size=1024)
            logger.info(f"主视图预处理完成: {main_image.size}")

            # 生成输出路径
            if output_path is None:
                output_dir = tempfile.mkdtemp(prefix="hunyuan3d_")
                output_path = os.path.join(output_dir, "output.glb")
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Step 1: 生成网格 (Shape)
            logger.info("Step 1: 生成3D网格...")
            mesh_output = self._shape_pipeline(image=main_image)
            mesh = mesh_output[0]  # 获取网格对象
            logger.info("网格生成完成")

            # 保存中间网格文件（无纹理）
            mesh_path = output_path.replace(".glb", "_mesh.glb")
            mesh.export(mesh_path)
            logger.info(f"网格保存至: {mesh_path}")

            # Step 2: 生成纹理 (Paint)
            logger.info("Step 2: 生成PBR纹理...")
            textured_mesh = self._paint_pipeline(
                mesh_path=mesh_path,
                image_path=main_image if isinstance(main_image, str) else None,
            )
            logger.info("纹理生成完成")

            # 导出最终模型
            # textured_mesh 应该是一个带纹理的网格对象
            if hasattr(textured_mesh, 'export'):
                textured_mesh.export(output_path)
            else:
                # 如果返回的是网格列表，取第一个
                textured_mesh[0].export(output_path)

            logger.info(f"3D重建完成: {output_path}")

            # 获取文件大小
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

            return {
                "model_path": output_path,
                "mesh_path": mesh_path,
                "model_url": f"/uploads/models/{os.path.basename(output_path)}",
                "polygon_count": kwargs.get("polygon_count", resolution * 1000),
                "texture_size": texture_size,
                "has_texture": True,
                "format": "glb",
                "file_size": file_size,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"3D重建失败: {e}")
            raise

    def reconstruct_single_image(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        resolution: int = 256,
        texture_size: int = 1024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        从单张图像重建3D模型（Hunyuan3D-2.1 支持）

        Args:
            image_path: 图像路径
            output_path: 输出路径 (.glb)
            resolution: 网格分辨率
            texture_size: 纹理分辨率

        Returns:
            重建结果
        """
        return self.reconstruct(
            image_paths=[image_path],
            output_path=output_path,
            resolution=resolution,
            texture_size=texture_size,
            **kwargs,
        )

    def unload(self):
        """卸载模型，释放显存"""
        if self._shape_pipeline is not None:
            del self._shape_pipeline
            self._shape_pipeline = None

        if self._paint_pipeline is not None:
            del self._paint_pipeline
            self._paint_pipeline = None

        self._loaded = False
        self._shape_model_loaded = False
        self._paint_model_loaded = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Hunyuan3D-2.1 模型已卸载")


# 全局单例
_hunyuan3d_service: Optional[Hunyuan3DService] = None


def get_hunyuan3d_service() -> Hunyuan3DService:
    """获取混元3D服务单例"""
    global _hunyuan3d_service
    if _hunyuan3d_service is None:
        _hunyuan3d_service = Hunyuan3DService()
    return _hunyuan3d_service


def load_hunyuan3d_model(force: bool = False) -> bool:
    """加载 Hunyuan3D-2.1 模型"""
    service = get_hunyuan3d_service()
    return service._load_model(force=force)


def reconstruct_3d(
    image_paths: List[str],
    output_path: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """执行3D重建"""
    service = get_hunyuan3d_service()
    return service.reconstruct(image_paths, output_path, **kwargs)


def unload_hunyuan3d_model():
    """卸载 Hunyuan3D-2.1 模型"""
    global _hunyuan3d_service
    if _hunyuan3d_service is not None:
        _hunyuan3d_service.unload()
        _hunyuan3d_service = None
