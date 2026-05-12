#!/usr/bin/env python3
"""
混元3D (Hunyuan3D) 微调训练脚本
用于在文物多视图数据集上微调混元3D开源模型

使用方法:
    # 本地调试 (需要 GPU)
    python scripts/train_hunyuan3d.py --config configs/train_hunyuan3d.yaml

    # 云端训练 (AutoDL)
    python scripts/train_hunyuan3d.py --cloud --config configs/train_hunyuan3d.yaml
"""

import argparse
import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
import json

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import autocast, GradScaler
from tqdm import tqdm

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
# Add utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """训练配置"""
    # 模型
    model_name: str = "Tencent/Hunyuan3D"
    local_model_path: Optional[str] = None

    # 数据
    dataset_path: str = "dataset/processed"
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1

    # 训练参数
    epochs: int = 50
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 100
    max_grad_norm: float = 1.0

    # 优化器
    optimizer: str = "adamw"
    scheduler: str = "cosine"

    # 混合精度
    use_amp: bool = True
    dtype: str = "bf16"  # bf16 or fp16

    # 硬件
    device: str = "cuda"
    num_workers: int = 4
    prefetch_factor: int = 2

    # 输出
    output_dir: str = "models/hunyuan3d_finetuned"
    checkpoint_dir: str = "models/hunyuan3d_finetuned/checkpoints"
    log_dir: str = "models/hunyuan3d_finetuned/logs"

    # 训练控制
    resume_from: Optional[str] = None
    save_every: int = 5
    eval_every: int = 1
    gradient_checkpointing: bool = True

    # 随机种子
    seed: int = 42


class ArtifactMultiViewDataset(Dataset):
    """
    文物多视图数据集

    目录结构:
        dataset/
        ├── train/
        │   ├── artifact_001/
        │   │   ├── front.png
        │   │   ├── side_left.png
        │   │   ├── side_right.png
        │   │   └── back.png
        │   └── artifact_002/
        │       └── ...
        ├── val/
        └── test/
    """

    def __init__(
        self,
        root_dir: str,
        split: str = "train",
        view_types: List[str] = None,
        image_size: int = 512,
    ):
        self.root_dir = Path(root_dir)
        self.split = split
        self.view_types = view_types or ["front", "side_left", "side_right", "back"]
        self.image_size = image_size

        self.samples = self._load_samples()

    def _load_samples(self) -> List[Dict[str, Any]]:
        """加载数据集样本"""
        split_dir = self.root_dir / self.split
        if not split_dir.exists():
            logger.warning(f"Split directory not found: {split_dir}")
            return []

        samples = []
        for artifact_dir in sorted(split_dir.iterdir()):
            if not artifact_dir.is_dir():
                continue

            views = {}
            for view_type in self.view_types:
                # Try different extensions
                for ext in ['.png', '.jpg', '.jpeg']:
                    img_path = artifact_dir / f"{view_type}{ext}"
                    if img_path.exists():
                        views[view_type] = str(img_path)
                        break

            # Require at least 4 views
            if len(views) >= 4:
                samples.append({
                    "artifact_id": artifact_dir.name,
                    "views": views,
                    "num_views": len(views),
                })

        logger.info(f"Loaded {len(samples)} samples for {self.split}")
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]
        # This would load and process images
        # For now, return placeholder
        return {
            "artifact_id": sample["artifact_id"],
            "views": sample["views"],
            "num_views": sample["num_views"],
        }


def setup_training(config: TrainingConfig) -> tuple:
    """设置训练环境"""
    # 设置随机种子
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    # 设置设备
    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # 创建输出目录
    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.checkpoint_dir, exist_ok=True)
    os.makedirs(config.log_dir, exist_ok=True)

    # 保存配置
    config_path = os.path.join(config.output_dir, "config.yaml")
    with open(config_path, 'w') as f:
        yaml.dump(config.__dict__, f, default_flow_style=False)
    logger.info(f"Config saved to {config_path}")

    return device


def train_epoch(
    model: nn.Module,
    train_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[Any],
    config: TrainingConfig,
    device: torch.device,
    scaler: Optional[GradScaler],
    epoch: int,
) -> float:
    """训练一个 epoch"""
    model.train()
    total_loss = 0.0
    num_batches = 0

    pbar = tqdm(train_loader, desc=f"Epoch {epoch}")
    optimizer.zero_grad()

    for step, batch in enumerate(pbar):
        # Move to device
        # batch = {k: v.to(device) for k, v in batch.items()}

        # Forward with AMP
        if config.use_amp and scaler is not None:
            with autocast(dtype=torch.bfloat16 if config.dtype == "bf16" else torch.float16):
                # outputs = model(**batch)
                # loss = outputs.loss
                loss = 0.0  # Placeholder

            # Backward with gradient scaling
            scaler.scale(loss / config.gradient_accumulation_steps).backward()

            # Gradient clipping
            if config.max_grad_norm > 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)

            # Optimizer step
            if (step + 1) % config.gradient_accumulation_steps == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                if scheduler is not None:
                    scheduler.step()
        else:
            # Forward without AMP
            # outputs = model(**batch)
            # loss = outputs.loss
            loss = 0.0  # Placeholder
            (loss / config.gradient_accumulation_steps).backward()

            if (step + 1) % config.gradient_accumulation_steps == 0:
                optimizer.step()
                optimizer.zero_grad()
                if scheduler is not None:
                    scheduler.step()

        total_loss += loss.item()
        num_batches += 1

        pbar.set_postfix({"loss": f"{loss.item():.4f}"})

    avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
    return avg_loss


def evaluate(
    model: nn.Module,
    val_loader: DataLoader,
    config: TrainingConfig,
    device: torch.device,
) -> Dict[str, float]:
    """评估模型"""
    model.eval()
    total_loss = 0.0
    num_batches = 0

    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Evaluating"):
            # batch = {k: v.to(device) for k, v in batch.items()}
            # outputs = model(**batch)
            # loss = outputs.loss
            loss = 0.0  # Placeholder

            total_loss += loss.item()
            num_batches += 1

    avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
    return {"val_loss": avg_loss}


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[Any],
    epoch: int,
    config: TrainingConfig,
    is_best: bool = False,
):
    """保存检查点"""
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "config": config.__dict__,
    }

    # Save regular checkpoint
    checkpoint_path = os.path.join(config.checkpoint_dir, f"checkpoint-epoch-{epoch}.pt")
    torch.save(checkpoint, checkpoint_path)
    logger.info(f"Checkpoint saved: {checkpoint_path}")

    # Save best checkpoint
    if is_best:
        best_path = os.path.join(config.checkpoint_dir, "best-model.pt")
        torch.save(checkpoint, best_path)
        logger.info(f"Best model saved: {best_path}")

    # Save latest
    latest_path = os.path.join(config.checkpoint_dir, "latest.pt")
    torch.save(checkpoint, latest_path)


def main():
    parser = argparse.ArgumentParser(description="Train Hunyuan3D on artifact dataset")
    parser.add_argument("--config", type=str, required=True, help="Path to config file")
    parser.add_argument("--cloud", action="store_true", help="Run on cloud (AutoDL)")
    parser.add_argument("--local-model", type=str, help="Local model path")
    args = parser.parse_args()

    # Load config
    with open(args.config, 'r') as f:
        config_dict = yaml.safe_load(f)
    config = TrainingConfig(**config_dict)

    # Override with CLI args
    if args.local_model:
        config.local_model_path = args.local_model

    # Cloud-specific setup
    if args.cloud:
        from utils.cloud_utils import setup_cloud_environment
        setup_cloud_environment()

    # Setup
    device = setup_training(config)[0]

    # Create datasets
    train_dataset = ArtifactMultiViewDataset(
        root_dir=config.dataset_path,
        split="train",
    )
    val_dataset = ArtifactMultiViewDataset(
        root_dir=config.dataset_path,
        split="val",
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=True,
        prefetch_factor=config.prefetch_factor,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=True,
    )

    # Create model (placeholder - actual implementation depends on Hunyuan3D architecture)
    # model = Hunyuan3DModel.from_pretrained(config.model_name)
    model = nn.Identity()  # Placeholder
    model = model.to(device)

    # Create optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # Create scheduler
    total_steps = len(train_loader) * config.epochs // config.gradient_accumulation_steps
    warmup_steps = config.warmup_steps

    if config.scheduler == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=total_steps - warmup_steps,
        )
    else:
        scheduler = None

    # Create AMP scaler
    scaler = GradScaler() if config.use_amp else None

    # Resume from checkpoint
    start_epoch = 0
    if config.resume_from:
        checkpoint = torch.load(config.resume_from, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = checkpoint["epoch"] + 1
        logger.info(f"Resumed from epoch {start_epoch}")

    # Training loop
    logger.info("Starting training...")
    best_val_loss = float("inf")

    for epoch in range(start_epoch, config.epochs):
        # Train
        train_loss = train_epoch(
            model, train_loader, optimizer, scheduler,
            config, device, scaler, epoch
        )
        logger.info(f"Epoch {epoch}: train_loss={train_loss:.4f}")

        # Evaluate
        if (epoch + 1) % config.eval_every == 0:
            metrics = evaluate(model, val_loader, config, device)
            logger.info(f"Epoch {epoch}: {metrics}")

            is_best = metrics.get("val_loss", float("inf")) < best_val_loss
            if is_best:
                best_val_loss = metrics["val_loss"]

        # Save checkpoint
        if (epoch + 1) % config.save_every == 0:
            save_checkpoint(
                model, optimizer, scheduler, epoch,
                config, is_best=(epoch == config.epochs - 1)
            )

    logger.info("Training completed!")


if __name__ == "__main__":
    main()
