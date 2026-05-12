#!/usr/bin/env python3
"""
知识蒸馏脚本 - 将微调后的 gemma3:4b 知识蒸馏到 qwen2.5:3b

使用 DPO 训练后的模型作为教师模型，生成高质量样本，
然后用这些样本训练学生模型 qwen2.5:3b

使用方法:
    python scripts/distill_knowledge.py --config configs/distill.yaml
"""

import argparse
import os
import sys
import logging
from dataclasses import dataclass
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
from peft import LoraConfig, get_peft_model, TaskType

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DistillationConfig:
    """蒸馏配置"""
    # 教师模型
    teacher_model_path: str = "models/gemma3_artifact_dpo/final"
    teacher_tokenizer_path: Optional[str] = None

    # 学生模型
    student_model_name: str = "qwen2.5:3b"  # Ollama 格式或 HuggingFace
    student_local_path: Optional[str] = None

    # 数据
    artifact_data_path: str = "dataset/sample_artifacts.json"
    distill_samples: int = 200  # 生成的蒸馏样本数

    # 蒸馏参数
    temperature: float = 2.0  # 生成温度
    top_p: float = 0.9
    max_new_tokens: int = 512

    # 训练参数
    use_lora: bool = True
    lora_r: int = 32
    lora_alpha: int = 64
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None

    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    max_seq_length: int = 1024

    # 输出
    output_dir: str = "models/qwen2_5_artifact_student"
    distill_data_path: str = "dataset/annotations/distillation/distill_samples.jsonl"

    seed: int = 42

    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ]


class DistillationDataset(Dataset):
    """
    蒸馏数据集 - 存储教师模型生成的样本

    JSONL 格式:
    {
        "artifact_id": "artifact_001",
        "artifact_name": "后母戊鼎",
        "dynasty": "商",
        "category": "青铜器",
        "prompt": "你是一个专业的文物讲解员...",
        "response": "教师模型生成的优质回答"
    }
    """

    def __init__(self, file_path: str, tokenizer, max_length: int = 1024):
        self.file_path = Path(file_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = self._load_samples()

    def _load_samples(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            logger.warning(f"蒸馏数据不存在: {self.file_path}")
            return []

        samples = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        logger.info(f"加载 {len(samples)} 个蒸馏样本")
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        sample = self.samples[idx]

        prompt = sample["prompt"]
        response = sample["response"]

        # 构建完整文本
        full_text = f"{prompt}\n{response}{self.tokenizer.eos_token}"

        encoding = self.tokenizer(
            full_text,
            max_length=self.max_length,
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding.input_ids.squeeze(),
            "attention_mask": encoding.attention_mask.squeeze(),
            "labels": encoding.input_ids.squeeze(),
        }


def generate_distillation_samples(
    teacher_model,
    teacher_tokenizer,
    artifact_data: List[Dict[str, Any]],
    config: DistillationConfig,
) -> List[Dict[str, Any]]:
    """
    使用教师模型生成蒸馏样本

    Args:
        teacher_model: 微调后的 gemma3:4b
        teacher_tokenizer: 分词器
        artifact_data: 文物数据列表
        config: 蒸馏配置

    Returns:
        生成的样本列表
    """
    samples = []
    device = next(teacher_model.parameters()).device

    system_prompt = """你是一个专业的中国博物馆文物讲解员，擅长讲述文物背后的历史故事。
请根据提供的信息，生成一段生动、专业的文物介绍。"""

    for artifact in artifact_data[:config.distill_samples]:
        artifact_name = artifact.get("name", artifact.get("artifact_name", ""))
        dynasty = artifact.get("dynasty", "")
        category = artifact.get("category", "")
        description = artifact.get("description", "")

        prompt = f"""系统提示: {system_prompt}

文物信息：
- 名称：{artifact_name}
- 朝代：{dynasty}
- 分类：{category}
- 描述：{description}

请生成一段专业的文物介绍："""

        # 生成
        inputs = teacher_tokenizer(prompt, return_tensors="pt").to(device)

        with torch.no_grad():
            outputs = teacher_model.generate(
                **inputs,
                max_new_tokens=config.max_new_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                do_sample=True,
            )

        response = teacher_tokenizer.decode(outputs[0], skip_special_tokens=True)
        # 去掉输入部分
        response = response[len(prompt):].strip()

        samples.append({
            "artifact_id": artifact.get("artifact_id", ""),
            "artifact_name": artifact_name,
            "dynasty": dynasty,
            "category": category,
            "prompt": prompt,
            "response": response,
        })

        if len(samples) % 10 == 0:
            logger.info(f"已生成 {len(samples)} 个样本")

    return samples


def distill_to_student(
    teacher_model,
    teacher_tokenizer,
    student_model,
    student_tokenizer,
    artifact_data: List[Dict[str, Any]],
    config: DistillationConfig,
) -> str:
    """
    执行知识蒸馏流程

    Returns:
        蒸馏数据文件路径
    """
    # 1. 生成蒸馏样本
    logger.info("使用教师模型生成蒸馏样本...")
    distill_samples = generate_distillation_samples(
        teacher_model, teacher_tokenizer, artifact_data, config
    )

    # 2. 保存蒸馏样本
    os.makedirs(os.path.dirname(config.distill_data_path), exist_ok=True)
    with open(config.distill_data_path, 'w', encoding='utf-8') as f:
        for sample in distill_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    logger.info(f"蒸馏样本已保存: {config.distill_data_path}")

    # 3. 创建学生模型
    logger.info(f"加载学生模型: {config.student_model_name}")
    student_path = config.student_local_path or config.student_model_name

    student_tokenizer = AutoTokenizer.from_pretrained(student_path, add_eos_token=True)
    if student_tokenizer.pad_token is None:
        student_tokenizer.pad_token = student_tokenizer.eos_token

    student_model = AutoModelForCausalLM.from_pretrained(
        student_path,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )

    # 4. 应用 LoRA
    if config.use_lora:
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=config.lora_target_modules,
            bias="none",
        )
        student_model = get_peft_model(student_model, lora_config)
        student_model.print_trainable_parameters()

    # 5. 加载蒸馏数据并训练
    dataset = DistillationDataset(
        config.distill_data_path,
        student_tokenizer,
        config.max_seq_length,
    )

    # ... 训练循环（类似 train_gemma.py）

    # 6. 保存学生模型
    output_path = config.output_dir
    os.makedirs(output_path, exist_ok=True)
    student_model.save_pretrained(output_path)
    student_tokenizer.save_pretrained(output_path)

    logger.info(f"学生模型已保存: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="知识蒸馏: gemma3:4b → qwen2.5:3b")
    parser.add_argument("--config", type=str, required=True)
    parser.add_argument("--skip-generation", action="store_true", help="跳过生成步骤，使用已有蒸馏数据")
    args = parser.parse_args()

    # 加载配置
    with open(args.config, 'r', encoding='utf-8') as f:
        config = DistillationConfig(**yaml.safe_load(f))

    # 加载文物数据
    with open(config.artifact_data_path, 'r', encoding='utf-8') as f:
        artifact_data = json.load(f)

    # 加载教师模型
    teacher_path = config.teacher_model_path
    teacher_tokenizer_path = config.teacher_tokenizer_path or teacher_path

    logger.info(f"加载教师模型: {teacher_path}")
    teacher_tokenizer = AutoTokenizer.from_pretrained(teacher_tokenizer_path)
    teacher_model = AutoModelForCausalLM.from_pretrained(
        teacher_path,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )

    # 执行蒸馏
    if args.skip_generation and os.path.exists(config.distill_data_path):
        logger.info("跳过生成步骤，使用已有蒸馏数据")
        # 直接训练学生模型
    else:
        student_path = distill_to_student(
            teacher_model, teacher_tokenizer,
            None, None,  # 学生模型会在函数内创建
            artifact_data, config,
        )

    logger.info("蒸馏完成!")


if __name__ == "__main__":
    main()
