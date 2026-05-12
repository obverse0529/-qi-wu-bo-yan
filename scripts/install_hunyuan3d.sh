#!/bin/bash
# Hunyuan3D-2.1 安装脚本
# 使用方法: bash scripts/install_hunyuan3d.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Hunyuan3D-2.1 安装脚本"
echo "=========================================="

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "当前 Python 版本: $python_version"

# 创建 conda 环境 (如果需要)
if ! command -v conda &> /dev/null; then
    echo "未检测到 conda，将使用当前 Python 环境"
else
    echo "创建 hunyuan3d-2.1 conda 环境..."
    conda create -n hunyuan3d-2.1 python=3.10 -y
    conda activate hunyuan3d-2.1
fi

# 安装 PyTorch
echo "安装 PyTorch..."
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# 克隆 Hunyuan3D-2.1 仓库
if [ -d "Hunyuan3D-2.1" ]; then
    echo "Hunyuan3D-2.1 目录已存在，拉取最新代码..."
    cd Hunyuan3D-2.1
    git pull
    cd ..
else
    echo "克隆 Hunyuan3D-2.1 仓库..."
    git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git
    cd Hunyuan3D-2.1
fi

# 安装 Hunyuan3D-2.1 依赖
echo "安装 Hunyuan3D-2.1 依赖..."
pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cu124

# 安装额外依赖
echo "安装额外依赖..."
pip install xformers --index-url https://download.pytorch.org/whl/cu124 || true

# 编译自定义 rasterizer
echo "编译自定义 rasterizer..."
cd hy3dpaint/custom_rasterizer
pip install -e .
cd ../..

cd hy3dpaint/DifferentiableRenderer
bash compile_mesh_painter.sh
cd ../..

# 下载 Real-ESRGAN 模型 (用于纹理增强)
echo "下载 Real-ESRGAN 模型..."
mkdir -p hy3dpaint/ckpt
wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth \
    -O hy3dpaint/ckpt/RealESRGAN_x4plus.pth || \
    echo "Real-ESRGAN 下载失败，将使用 CPU 模式"

# 下载 Hunyuan3D-2.1 模型权重
echo "=========================================="
echo "  下载 Hunyuan3D-2.1 模型权重"
echo "=========================================="
echo "安装 huggingface-cli..."
pip install "huggingface_hub[cli]"

echo "创建 weights 目录..."
mkdir -p weights

echo "下载 Hunyuan3D-2.1 主模型..."
huggingface-cli download tencent/Hunyuan3D-2.1 --local-dir ./weights

echo "下载 HunyuanDiT 文本到图像模型..."
mkdir -p weights/hunyuanDiT
huggingface-cli download Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled --local-dir ./weights/hunyuanDiT

# 下载 DUSt3R 权重 (用于多视图重建)
echo "下载 DUSt3R 权重..."
cd third_party
git clone --recursive https://github.com/naver/dust3r.git
cd ../weights
wget -q https://download.europe.naverlabs.com/ComputerVision/DUSt3R/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth || \
    echo "DUSt3R 权重下载失败"

echo ""
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo ""
echo "请设置环境变量:"
echo "  export HUNYUAN3D_PATH=$PROJECT_ROOT/Hunyuan3D-2.1"
echo ""
echo "然后重启后端服务以加载模型"
