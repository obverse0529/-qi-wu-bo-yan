#!/usr/bin/env python3
"""
Gemma 3 文物故事生成 QLoRA 微调训练脚本
用于在文物史料数据集上微调 Gemma 3 开源模型

使用方法:
    # 本地调试 (需要 GPU，8GB+ VRAM)
    python scripts/train_gemma.py --config configs/train_gemma.yaml

    # 云端训练 (AutoDL)
    python scripts/train_gemma.py --cloud --config configs/train_gemma.yaml
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
from torch.utils.data import Dataset, DataLoader
from transformers import (
    Gemma3ForCausalLM,
    Gemma3Tokenizer,
    Gemma3TextConfig,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType
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
class GemmaTrainingConfig:
    """Gemma 训练配置"""
    # 模型
    model_name: str = "google/gemma-3-4b-it"
    local_model_path: Optional[str] = None

    # LoRA & QLoRA
    use_quantization: bool = True
    quantization_bit: int = 4
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])

    # 数据
    dataset_path: str = "dataset/stories"
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    max_seq_length: int = 1024

    # 训练参数
    epochs: int = 10
    batch_size: int = 2
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    scheduler: str = "cosine"

    # 混合精度
    use_amp: bool = True
    dtype: str = "bf16"

    # 硬件
    device: str = "cuda"
    num_workers: int = 4

    # 输出
    output_dir: str = "models/gemma3_artifact_story_finetuned"
    checkpoint_dir: str = "models/gemma3_artifact_story_finetuned/checkpoints"
    log_dir: str = "models/gemma3_artifact_story_finetuned/logs"

    # 训练控制
    resume_from: Optional[str] = None
    save_every: int = 2
    eval_every: int = 1

    # 随机种子
    seed: int = 42


class ArtifactStoryDataset(Dataset):
    """
    文物故事数据集

    目录结构:
        dataset/stories/
        ├── train.jsonl
        ├── val.jsonl
        └── test.jsonl

    JSONL 格式:
        {"artifact_id": "artifact_001", "artifact_name": "青铜鼎", "dynasty": "商", "category": "青铜器",
         "story": "这是一段详细的文物故事...", "source": "《文物》2020年第1期"}
    """

    def __init__(
        self,
        file_path: str,
        tokenizer: Gemma3Tokenizer,
        max_seq_length: int = 1024,
    ):
        self.file_path = Path(file_path)
        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length
        self.samples = self._load_samples()

    def _load_samples(self) -> List[Dict[str, Any]]:
        """加载数据集样本"""
        if not self.file_path.exists():
            logger.warning(f"数据文件不存在: {self.file_path}")
            return []

        samples = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    samples.append(sample)
                except json.JSONDecodeError:
                    logger.warning(f"JSON 解析失败: {line[:100]}")
                    continue

        logger.info(f"加载 {len(samples)} 个样本: {self.file_path}")
        return samples

    def _format_prompt(self, sample: Dict[str, Any]) -> str:
        """构建 prompt"""
        artifact_name = sample.get("artifact_name", "未知文物")
        dynasty = sample.get("dynasty", "未知")
        category = sample.get("category", "未知")
        story = sample.get("story", "")

        prompt = f"""你是一个文物历史研究专家。根据以下文物信息，请生成一段详细的历史故事介绍。

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}

文物故事：
{story}"""
        return prompt

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]

        prompt = self._format_prompt(sample)
        story = sample.get("story", "")

        # Tokenize
        prompt_ids = self.tokenizer(
            prompt,
            add_special_tokens=True,
            max_length=self.max_seq_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        story_ids = self.tokenizer(
            story,
            add_special_tokens=False,
            max_length=self.max_seq_length // 2,
            truncation=True,
            return_tensors="pt",
        )

        # Build input_ids with prompt + story + eos
        input_ids = torch.cat([
            prompt_ids.input_ids.squeeze(),
            story_ids.input_ids.squeeze(),
            torch.tensor([self.tokenizer.eos_token_id]),
        ])

        # Labels: -100 for prompt, actual tokens for story
        labels = torch.cat([
            torch.full(prompt_ids.input_ids.shape, -100).squeeze(),
            story_ids.input_ids.squeeze(),
            torch.tensor([self.tokenizer.eos_token_id]),
        ])

        # Truncate to max_seq_length
        if len(input_ids) > self.max_seq_length:
            input_ids = input_ids[:self.max_seq_length]
            labels = labels[:self.max_seq_length]

        attention_mask = torch.ones_like(input_ids)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def setup_training(config: GemmaTrainingConfig) -> torch.device:
    """设置训练环境"""
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")

    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.checkpoint_dir, exist_ok=True)
    os.makedirs(config.log_dir, exist_ok=True)

    config_path = os.path.join(config.output_dir, "config.yaml")
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config.__dict__, f, default_flow_style=False)
    logger.info(f"配置已保存: {config_path}")

    return device


def create_model(config: GemmaTrainingConfig) -> tuple:
    """创建模型和分词器"""
    logger.info(f"加载模型: {config.model_name}")

    # Quantization config
    if config.use_quantization:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if config.dtype == "bf16" else torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        bnb_config = None

    # Load tokenizer
    tokenizer = Gemma3Tokenizer.from_pretrained(
        config.model_name if not config.local_model_path else config.local_model_path,
        add_eos_token=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = Gemma3ForCausalLM.from_pretrained(
        config.model_name if not config.local_model_path else config.local_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16 if config.dtype == "bf16" else torch.float16,
    )

    # Attach lm head to get proper output projection sizes
    model.model.lm_head.weight.is_lora_trainable = False
    model.model.lm_head.bias.is_lora_trainable = False

    # LoRA config
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.lora_target_modules,
        bias="none",
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer


def collate_fn(batch: List[Dict[str, Any]]) -> Dict[str, Any]:
    """DataLoader collate 函数"""
    max_len = max(len(b["input_ids"]) for b in batch)

    input_ids = []
    attention_mask = []
    labels = []

    for b in batch:
        pad_len = max_len - len(b["input_ids"])
        input_ids.append(
            torch.cat([b["input_ids"], torch.zeros(pad_len, dtype=torch.long)])
        )
        attention_mask.append(
            torch.cat([b["attention_mask"], torch.zeros(pad_len, dtype=torch.long)])
        )
        labels.append(
            torch.cat([b["labels"], torch.full((pad_len,), -100, dtype=torch.long)])
        )

    return {
        "input_ids": torch.stack(input_ids),
        "attention_mask": torch.stack(attention_mask),
        "labels": torch.stack(labels),
    }


def train_epoch(
    model,
    train_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[Any],
    config: GemmaTrainingConfig,
    device: torch.device,
    scaler: Optional[torch.cuda.amp.GradScaler],
    epoch: int,
) -> float:
    """训练一个 epoch"""
    model.train()
    total_loss = 0.0
    num_batches = 0

    pbar = tqdm(train_loader, desc=f"Epoch {epoch}")
    optimizer.zero_grad()

    for step, batch in enumerate(pbar):
        batch = {k: v.to(device) for k, v in batch.items()}

        if config.use_amp and scaler is not None:
            with torch.cuda.amp.autocast(dtype=torch.bfloat16):
                outputs = model(**batch)
                loss = outputs.loss / config.gradient_accumulation_steps

            scaler.scale(loss).backward()

            if (step + 1) % config.gradient_accumulation_steps == 0:
                if config.max_grad_norm > 0:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)

                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()

                if scheduler is not None:
                    scheduler.step()
        else:
            outputs = model(**batch)
            loss = outputs.loss / config.gradient_accumulation_steps
            loss.backward()

            if (step + 1) % config.gradient_accumulation_steps == 0:
                if config.max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
                optimizer.step()
                optimizer.zero_grad()
                if scheduler is not None:
                    scheduler.step()

        total_loss += loss.item() * config.gradient_accumulation_steps
        num_batches += 1
        pbar.set_postfix({"loss": f"{loss.item() * config.gradient_accumulation_steps:.4f}"})

    avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
    return avg_loss


def evaluate(
    model,
    val_loader: DataLoader,
    config: GemmaTrainingConfig,
    device: torch.device,
) -> Dict[str, float]:
    """评估模型"""
    model.eval()
    total_loss = 0.0
    num_batches = 0

    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Evaluating"):
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.cuda.amp.autocast(dtype=torch.bfloat16):
                outputs = model(**batch)
            total_loss += outputs.loss.item()
            num_batches += 1

    avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
    return {"val_loss": avg_loss}


def save_checkpoint(
    model,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[Any],
    epoch: int,
    config: GemmaTrainingConfig,
    is_best: bool = False,
):
    """保存检查点"""
    checkpoint_path = os.path.join(config.checkpoint_dir, f"checkpoint-epoch-{epoch}")
    model.save_pretrained(checkpoint_path)

    state = {
        "epoch": epoch,
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "config": config.__dict__,
    }
    torch.save(state, os.path.join(checkpoint_path, "trainer_state.pt"))

    logger.info(f"检查点已保存: {checkpoint_path}")

    if is_best:
        best_path = os.path.join(config.checkpoint_dir, "best-model")
        model.save_pretrained(best_path)
        logger.info(f"最佳模型已保存: {best_path}")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Gemma 3 on artifact stories")
    parser.add_argument("--config", type=str, required=True, help="配置文件路径")
    parser.add_argument("--cloud", action="store_true", help="云端训练 (AutoDL)")
    parser.add_argument("--local-model", type=str, help="本地模型路径")
    args = parser.parse_args()

    # Load config
    with open(args.config, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    config = GemmaTrainingConfig(**config_dict)

    if args.local_model:
        config.local_model_path = args.local_model

    if args.cloud:
        from utils.cloud_utils import setup_cloud_environment
        setup_cloud_environment()

    # Setup
    device = setup_training(config)

    # Create model
    model, tokenizer = create_model(config)
    model = model.to(device)

    # Create datasets
    train_file = os.path.join(config.dataset_path, "train.jsonl")
    val_file = os.path.join(config.dataset_path, "val.jsonl")

    train_dataset = ArtifactStoryDataset(train_file, tokenizer, config.max_seq_length)
    val_dataset = ArtifactStoryDataset(val_file, tokenizer, config.max_seq_length)

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    # Optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # Scheduler
    total_steps = len(train_loader) * config.epochs // config.gradient_accumulation_steps
    warmup_steps = config.warmup_steps

    if config.scheduler == "cosine":
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=total_steps - warmup_steps,
        )
    else:
        scheduler = None

    # AMP scaler
    scaler = torch.cuda.amp.GradScaler() if config.use_amp else None

    # Resume
    start_epoch = 0
    if config.resume_from:
        checkpoint = torch.load(config.resume_from, map_location=device)
        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        start_epoch = checkpoint["epoch"] + 1
        logger.info(f"从 epoch {start_epoch} 恢复训练")

    # Training loop
    logger.info("开始训练...")
    best_val_loss = float("inf")

    for epoch in range(start_epoch, config.epochs):
        train_loss = train_epoch(
            model, train_loader, optimizer, scheduler,
            config, device, scaler, epoch
        )
        logger.info(f"Epoch {epoch}: train_loss={train_loss:.4f}")

        if (epoch + 1) % config.eval_every == 0:
            metrics = evaluate(model, val_loader, config, device)
            logger.info(f"Epoch {epoch}: {metrics}")
            is_best = metrics.get("val_loss", float("inf")) < best_val_loss
            if is_best:
                best_val_loss = metrics["val_loss"]

        if (epoch + 1) % config.save_every == 0:
            save_checkpoint(
                model, optimizer, scheduler, epoch,
                config, is_best=(epoch == config.epochs - 1)
            )

    logger.info("训练完成!")


if __name__ == "__main__":
    main()
