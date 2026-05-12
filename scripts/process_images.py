#!/usr/bin/env python3
"""
文物图像批量处理脚本
用于图像预处理、增强和质量检查

使用方法:
    # 基本使用
    python scripts/process_images.py --input dataset/raw --output dataset/processed

    # 带增强
    python scripts/process_images.py --input dataset/raw --output dataset/processed --augment

    # 仅检查质量
    python scripts/process_images.py --check-quality dataset/raw
"""

import argparse
import logging
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from PIL import Image, ImageEnhance
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ImageQualityResult:
    """图像质量检测结果"""
    file_path: str
    width: int
    height: int
    aspect_ratio: float
    file_size: int
    is_valid: bool
    issues: List[str]


@dataclass
class ProcessingResult:
    """处理结果"""
    input_path: str
    output_path: str
    success: bool
    error: Optional[str] = None


class ImageProcessor:
    """图像处理器"""

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    MIN_SIZE = (256, 256)
    MAX_SIZE = (4096, 4096)
    TARGET_SIZE = (1024, 1024)
    TARGET_VIEWS = ["front", "side_left", "side_right", "back"]
    ASPECT_RATIO_TOLERANCE = 0.5  # 纵横比容差，超过视为异常

    def __init__(
        self,
        output_dir: str,
        target_size: Tuple[int, int] = None,
        quality: int = 95,
        enhance: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.target_size = target_size or self.TARGET_SIZE
        self.quality = quality
        self.enhance = enhance

    def check_quality(self, image_path: str) -> ImageQualityResult:
        """检查图像质量"""
        issues = []
        path = Path(image_path)

        if not path.exists():
            return ImageQualityResult(
                file_path=image_path,
                width=0,
                height=0,
                aspect_ratio=0,
                file_size=0,
                is_valid=False,
                issues=["文件不存在"],
            )

        file_size = path.stat().st_size

        try:
            with Image.open(image_path) as img:
                width, height = img.size
                aspect_ratio = width / height if height > 0 else 0

                # 检查尺寸
                if width < self.MIN_SIZE[0] or height < self.MIN_SIZE[1]:
                    issues.append(f"图像尺寸过小: {width}x{height}")

                if width > self.MAX_SIZE[0] or height > self.MAX_SIZE[1]:
                    issues.append(f"图像尺寸过大: {width}x{height}")

                # 检查纵横比
                if abs(aspect_ratio - 1.0) > self.ASPECT_RATIO_TOLERANCE:
                    issues.append(f"纵横比异常: {aspect_ratio:.2f}")

                # 检查格式
                if img.mode not in ['RGB', 'RGBA', 'L']:
                    issues.append(f"色彩模式不支持: {img.mode}")

                is_valid = len(issues) == 0 and width >= self.MIN_SIZE[0]

                return ImageQualityResult(
                    file_path=image_path,
                    width=width,
                    height=height,
                    aspect_ratio=aspect_ratio,
                    file_size=file_size,
                    is_valid=is_valid,
                    issues=issues,
                )

        except Exception as e:
            return ImageQualityResult(
                file_path=image_path,
                width=0,
                height=0,
                aspect_ratio=0,
                file_size=0,
                is_valid=False,
                issues=[f"读取失败: {str(e)}"],
            )

    def process_image(
        self,
        input_path: str,
        artifact_id: str,
        view_type: str,
    ) -> ProcessingResult:
        """处理单张图像"""
        try:
            path = Path(input_path)
            if not path.exists():
                return ProcessingResult(
                    input_path=input_path,
                    output_path="",
                    success=False,
                    error="文件不存在",
                )

            with Image.open(input_path) as img:
                # 转换为 RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 调整尺寸
                img = self._resize_image(img)

                # 增强
                if self.enhance:
                    img = self._enhance_image(img)

                # 保存
                output_path = self.output_dir / artifact_id / f"{view_type}.jpg"
                output_path.parent.mkdir(parents=True, exist_ok=True)

                img.save(
                    output_path,
                    "JPEG",
                    quality=self.quality,
                    optimize=True,
                )

                return ProcessingResult(
                    input_path=input_path,
                    output_path=str(output_path),
                    success=True,
                )

        except Exception as e:
            return ProcessingResult(
                input_path=input_path,
                output_path="",
                success=False,
                error=str(e),
            )

    def _resize_image(self, img: Image.Image) -> Image.Image:
        """调整图像尺寸"""
        # 先按比例缩放到目标尺寸范围内
        img.thumbnail(self.target_size, Image.Resampling.LANCZOS)

        # 如果需要填充到正方形
        width, height = img.size
        if width != height:
            new_size = max(width, height)
            new_img = Image.new('RGB', (new_size, new_size), (255, 255, 255))
            paste_x = (new_size - width) // 2
            paste_y = (new_size - height) // 2
            new_img.paste(img, (paste_x, paste_y))
            return new_img

        return img

    def _enhance_image(self, img: Image.Image) -> Image.Image:
        """增强图像"""
        # 对比度增强
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)

        # 色彩增强
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.05)

        # 锐化
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)

        return img

    def generate_report(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """生成处理报告"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        failed = total - success

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": f"{success/total*100:.1f}%" if total > 0 else "0%",
            "errors": [
                {"input": r.input_path, "error": r.error}
                for r in results if not r.success
            ],
        }


def scan_dataset(input_dir: str) -> Dict[str, List[Dict[str, str]]]:
    """
    扫描数据集目录

    期望目录结构:
        input_dir/
        ├── artifact_001/
        │   ├── front.jpg
        │   ├── side_left.jpg
        │   ├── side_right.jpg
        │   └── back.jpg
        └── artifact_002/
            └── ...
    """
    input_path = Path(input_dir)
    artifacts = {}

    for artifact_dir in sorted(input_path.iterdir()):
        if not artifact_dir.is_dir():
            continue

        views = {}
        for img_file in artifact_dir.iterdir():
            if img_file.suffix.lower() not in ImageProcessor.SUPPORTED_FORMATS:
                continue

            # 从文件名推断视图类型
            stem = img_file.stem.lower()
            for view_type in ImageProcessor.TARGET_VIEWS:
                if view_type in stem:
                    views[view_type] = str(img_file)
                    break

        if views:
            artifacts[artifact_dir.name] = views

    return artifacts


def check_quality_batch(
    artifacts: Dict[str, List[Dict[str, str]]],
    num_workers: int = 4,
) -> Dict[str, Any]:
    """批量检查质量"""
    processor = ImageProcessor(output_dir="")

    all_results = []
    quality_stats = {
        "total_images": 0,
        "valid_images": 0,
        "artifacts_with_4_views": 0,
        "issues_summary": {},
    }

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for artifact_id, views in artifacts.items():
            for view_type, img_path in views.items():
                future = executor.submit(processor.check_quality, img_path)
                future.artifact_id = artifact_id
                future.view_type = view_type
                futures.append(future)

        for future in tqdm(as_completed(futures), total=len(futures), desc="检查质量"):
            result = future.result()
            all_results.append(result)

            quality_stats["total_images"] += 1
            if result.is_valid:
                quality_stats["valid_images"] += 1

            for issue in result.issues:
                quality_stats["issues_summary"][issue] = \
                    quality_stats["issues_summary"].get(issue, 0) + 1

    # 统计完整视图的文物
    view_counts = {}
    for result in all_results:
        artifact_id = getattr(result, 'artifact_id', None)
        if artifact_id:
            view_counts[artifact_id] = view_counts.get(artifact_id, 0) + (1 if result.is_valid else 0)

    quality_stats["artifacts_with_4_views"] = sum(1 for v in view_counts.values() if v >= 4)

    return quality_stats


def process_batch(
    artifacts: Dict[str, List[Dict[str, str]]],
    output_dir: str,
    enhance: bool = True,
    num_workers: int = 4,
) -> List[ProcessingResult]:
    """批量处理"""
    processor = ImageProcessor(output_dir=output_dir, enhance=enhance)
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for artifact_id, views in artifacts.items():
            for view_type, img_path in views.items():
                future = executor.submit(
                    processor.process_image,
                    img_path,
                    artifact_id,
                    view_type,
                )
                futures.append(future)

        for future in tqdm(as_completed(futures), total=len(futures), desc="处理图像"):
            results.append(future.result())

    return results


def main():
    parser = argparse.ArgumentParser(description="文物图像批量处理")
    parser.add_argument("--input", type=str, help="输入目录")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--check-quality", type=str, help="仅检查质量")
    parser.add_argument("--augment", action="store_true", help="启用图像增强")
    parser.add_argument("--quality", type=int, default=95, help="JPEG 质量")
    parser.add_argument("--size", type=int, nargs=2, default=[1024, 1024], help="目标尺寸")
    parser.add_argument("--workers", type=int, default=4, help="并发数")
    args = parser.parse_args()

    if args.check_quality:
        logger.info(f"检查图像质量: {args.check_quality}")
        artifacts = scan_dataset(args.check_quality)
        logger.info(f"发现 {len(artifacts)} 个文物")

        stats = check_quality_batch(artifacts, args.workers)
        logger.info(f"质量统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")
        return

    if not args.input or not args.output:
        parser.print_help()
        return

    logger.info(f"扫描数据集: {args.input}")
    artifacts = scan_dataset(args.input)
    logger.info(f"发现 {len(artifacts)} 个文物")

    # 检查质量
    logger.info("检查图像质量...")
    quality_stats = check_quality_batch(artifacts, args.workers)
    logger.info(f"质量统计: {json.dumps(quality_stats, ensure_ascii=False, indent=2)}")

    if quality_stats["valid_images"] == 0:
        logger.error("没有有效的图像")
        return

    # 处理
    logger.info(f"处理图像到: {args.output}")
    results = process_batch(
        artifacts,
        args.output,
        enhance=args.augment,
        num_workers=args.workers,
    )

    # 生成报告
    processor = ImageProcessor(output_dir=args.output)
    report = processor.generate_report(results)

    report_path = Path(args.output) / "processing_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"处理完成: {json.dumps(report, ensure_ascii=False, indent=2)}")
    logger.info(f"报告已保存: {report_path}")


if __name__ == "__main__":
    main()
