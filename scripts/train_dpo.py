#!/usr/bin/env python3
"""
DPO (Direct Preference Optimization) 训练脚本
用于优化文物故事生成的风格质量

偏好数据来源：同一文物从多个来源（官网/学术/百科）获取描述，
形成偏好对（chosen/rejected）

使用方法:
    python scripts/train_dpo.py --config configs/train_dpo.yaml
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
    AutoTokenizer,
    AutoModelForCausalLM,
)
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig, get_peft_model, TaskType

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LocalDPOConfig:
    """DPO 训练配置"""
    # 模型
    model_name: str = "google/gemma-3-4b-it"
    local_model_path: Optional[str] = None
    ref_model_name: Optional[str] = None  # 参考模型，默认使用同模型

    # LoRA
    use_lora: bool = True
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])

    # 数据
    preference_data_path: str = "dataset/annotations/preferences"
    beta: float = 0.1  # DPO temperature 参数
    label_smoothing: float = 0.0

    # 训练参数
    epochs: int = 3
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 1e-5
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0

    # 硬件
    device: str = "cuda"
    dtype: str = "bf16"

    # 输出
    output_dir: str = "models/gemma3_artifact_dpo"
    log_dir: str = "models/gemma3_artifact_dpo/logs"

    # 随机种子
    seed: int = 42


class PreferenceDataset(Dataset):
    """
    偏好数据集

    目录结构:
        dataset/annotations/preferences/
        └── preferences.jsonl

    JSONL 格式（每个文物多源描述）:
    {
        "artifact_id": "artifact_001",
        "artifact_name": "后母戊鼎",
        "dynasty": "商",
        "category": "青铜器",
        "descriptions": [
            {
                "source": "故宫博物院官网",
                "content": "后母戊鼎，商代青铜器...",
                "style": "通俗",
                "detail_level": "中",
                "quality_rank": 2  # 质量排序，数字越大越好
            },
            {
                "source": "考古学报",
                "content": "后母戊鼎为商代晚期青铜礼器...",
                "style": "学术",
                "detail_level": "高",
                "quality_rank": 3
            },
            {
                "source": "百度百科",
                "content": "后母戊鼎是商朝的文物...",
                "style": "简略",
                "detail_level": "低",
                "quality_rank": 1
            }
        ]
    }

    转换为 DPO 格式:
    {
        "prompt": "你是一个文物讲解员，请介绍后母戊鼎。\n文物信息：名称=后母戊鼎, 朝代=商, 分类=青铜器",
        "chosen": "（质量最高的描述）",
        "rejected": "（质量较低的描述）"
    }
    """

    def __init__(self, file_path: str, tokenizer, max_length: int = 1024):
        self.file_path = Path(file_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = self._load_and_process()

    def _load_and_process(self) -> List[Dict[str, Any]]:
        """加载偏好数据并转换为 DPO 格式"""
        if not self.file_path.exists():
            logger.warning(f"偏好数据文件不存在: {self.file_path}")
            return []

        samples = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    processed = self._process_artifact(data)
                    if processed:
                        samples.extend(processed)
                except json.JSONDecodeError:
                    logger.warning(f"JSON 解析失败: {line[:100]}")
                    continue

        logger.info(f"加载 {len(samples)} 个偏好对样本")
        return samples

    def _process_artifact(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理单个文物的多源描述，生成偏好对"""
        artifact_name = data.get("artifact_name", "未知文物")
        dynasty = data.get("dynasty", "未知")
        category = data.get("category", "未知")
        descriptions = data.get("descriptions", [])

        if len(descriptions) < 2:
            return []

        # 按 quality_rank 排序
        sorted_descs = sorted(descriptions, key=lambda x: x.get("quality_rank", 0))

        # 生成 prompt
        prompt = f"""你是一个专业的文物讲解员。请根据以下信息，写一段文物介绍。

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}

请用生动、专业的语言介绍这件文物。"""

        samples = []
        # 生成所有 (chosen, rejected) 对
        for i in range(len(sorted_descs) - 1):
            for j in range(i + 1, len(sorted_descs)):
                if sorted_descs[j].get("quality_rank", 0) > sorted_descs[i].get("quality_rank", 0):
                    samples.append({
                        "prompt": prompt,
                        "chosen": sorted_descs[j]["content"],
                        "rejected": sorted_descs[i]["content"],
                        "artifact_id": data.get("artifact_id"),
                        "chosen_source": sorted_descs[j].get("source", ""),
                        "rejected_source": sorted_descs[i].get("source", ""),
                    })
                else:
                    samples.append({
                        "prompt": prompt,
                        "chosen": sorted_descs[i]["content"],
                        "rejected": sorted_descs[j]["content"],
                        "artifact_id": data.get("artifact_id"),
                        "chosen_source": sorted_descs[i].get("source", ""),
                        "rejected_source": sorted_descs[j].get("source", ""),
                    })

        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]
        return {
            "prompt": sample["prompt"],
            "chosen": sample["chosen"],
            "rejected": sample["rejected"],
        }


def setup_dpo_training(config: LocalDPOConfig) -> torch.device:
    """设置训练环境"""
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    device = torch.device(config.device if torch.cuda.is_available() else "cpu")
    logger.info(f"使用设备: {device}")

    os.makedirs(config.output_dir, exist_ok=True)
    os.makedirs(config.log_dir, exist_ok=True)

    # 保存配置
    config_path = os.path.join(config.output_dir, "dpo_config.yaml")
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config.__dict__, f, default_flow_style=False)
    logger.info(f"配置已保存: {config_path}")

    return device


def create_models_and_tokenizer(config: LocalDPOConfig):
    """创建模型和分词器"""
    model_path = config.local_model_path or config.model_name

    logger.info(f"加载模型: {model_path}")

    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_path, add_eos_token=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 加载模型
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.bfloat16 if config.dtype == "bf16" else torch.float16,
    )

    # 加载参考模型
    ref_model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map="auto",
        torch_dtype=torch.bfloat16 if config.dtype == "bf16" else torch.float16,
    )
    ref_model.eval()

    # 应用 LoRA
    if config.use_lora:
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=config.lora_target_modules,
            bias="none",
        )
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

    return model, ref_model, tokenizer


def create_preference_data_from_multisource(
    artifacts_data: List[Dict[str, Any]],
    output_path: str
) -> int:
    """
    从多源文物数据生成偏好数据集

    Args:
        artifacts_data: 包含 descriptions 数组的文物数据
        output_path: 输出 JSONL 路径

    Returns:
        生成的偏好对数量
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    count = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for artifact in artifacts_data:
            artifact_id = artifact.get("artifact_id", f"artifact_{count}")
            artifact_name = artifact.get("artifact_name", "未知文物")
            dynasty = artifact.get("dynasty", "未知")
            category = artifact.get("category", "未知")
            descriptions = artifact.get("descriptions", [])

            if len(descriptions) < 2:
                continue

            # 按 quality_rank 或 detail_level 排序
            # 优先使用 quality_rank，否则按 detail_level
            def get_rank(d):
                if "quality_rank" in d:
                    return d["quality_rank"]
                level_map = {"高": 3, "中": 2, "低": 1}
                return level_map.get(d.get("detail_level", ""), 2)

            sorted_descs = sorted(descriptions, key=get_rank, reverse=True)

            # 生成 (chosen, rejected) 对
            for i in range(len(sorted_descs) - 1):
                for j in range(i + 1, len(sorted_descs)):
                    record = {
                        "artifact_id": artifact_id,
                        "artifact_name": artifact_name,
                        "dynasty": dynasty,
                        "category": category,
                        "chosen": sorted_descs[i]["content"],
                        "chosen_source": sorted_descs[i].get("source", ""),
                        "rejected": sorted_descs[j]["content"],
                        "rejected_source": sorted_descs[j].get("source", ""),
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    count += 1

    logger.info(f"生成 {count} 个偏好对，保存到: {output_path}")
    return count


def main():
    parser = argparse.ArgumentParser(description="DPO training for artifact story generation")
    parser.add_argument("--config", type=str, required=True, help="配置文件路径")
    parser.add_argument("--local-model", type=str, help="本地模型路径")
    parser.add_argument("--preference-data", type=str, help="偏好数据路径")
    args = parser.parse_args()

    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    config = LocalDPOConfig(**config_dict)

    if args.local_model:
        config.local_model_path = args.local_model

    # 设置训练
    device = setup_dpo_training(config)

    # 创建模型
    model, ref_model, tokenizer = create_models_and_tokenizer(config)
    model = model.to(device)

    # 加载偏好数据
    pref_data_path = args.preference_data or config.preference_data_path

    # 如果是原始多源数据，先转换
    raw_data_path = pref_data_path.replace(".jsonl", "_raw.jsonl")
    if os.path.exists(raw_data_path) and not os.path.exists(pref_data_path):
        # 读取原始多源数据并转换
        raw_samples = []
        with open(raw_data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    raw_samples.append(json.loads(line))
        create_preference_data_from_multisource(raw_samples, pref_data_path)

    # 创建数据集
    preference_dataset = PreferenceDataset(pref_data_path, tokenizer)

    if len(preference_dataset) == 0:
        logger.error("没有找到偏好数据，请先准备数据")
        return

    # 转换为 HuggingFace Dataset 格式
    from datasets import Dataset
    dataset = Dataset.from_list(preference_dataset.samples)

    logger.info(f"数据集准备完成: {len(dataset)} 个样本")

    # DPO 配置
    dpo_training_args = DPOConfig(
        output_dir=config.output_dir,
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        max_grad_norm=config.max_grad_norm,
        logging_dir=config.log_dir,
        beta=config.beta,
        label_smoothing=config.label_smoothing,
        save_strategy="epoch",
        remove_unused_columns=False,
        optim="paged_adamw_32bit",
        bf16=True,
        seed=config.seed,
    )

    # 创建 DPO Trainer
    dpo_trainer = DPOTrainer(
        model=model,
        ref_model=ref_model,
        args=dpo_training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    # 训练
    logger.info("开始 DPO 训练...")
    dpo_trainer.train()

    # 保存模型
    final_model_path = os.path.join(config.output_dir, "final")
    dpo_trainer.save_model(final_model_path)
    logger.info(f"模型已保存: {final_model_path}")


if __name__ == "__main__":
    main()
