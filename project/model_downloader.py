"""
Win11 离线屏幕实时翻译助手 - 离线模型高速自动下载与管理模块
文件: model_downloader.py
功能: 支持 OCR 与翻译模型的全自动检测、多源高速镜像下载 (ModelScope / HF-Mirror / GitHub / 清华源)、
      下载断点续传、真实文件完整性与体积校验、残损坏文件自动清理及一键安装配置。
"""

import os
import sys
import time
from datetime import datetime
import json
import logging
import ssl
import shutil
import subprocess
import importlib.util
import urllib.request
import urllib.error
import tarfile
import zipfile
from typing import Callable, Dict, Any, Optional, List

# 确保项目根目录在 sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

logger = logging.getLogger("ModelDownloader")
logger.setLevel(logging.INFO)
logger.propagate = True


def format_size_mb(size_mb: float) -> str:
    """人性化格式化体积，例如 350MB 或 1.1GB"""
    if size_mb >= 1024:
        return f"{size_mb / 1024.0:.1f}GB"
    elif size_mb >= 1:
        return f"{int(round(size_mb))}MB"
    elif size_mb > 0:
        return f"{size_mb * 1024:.0f}KB"
    return "0MB"


# 模型下载源定义 (多源高速镜像: ModelScope、HF-Mirror、HuggingFace、Baidu BOS、GitHub 与社区备用镜像)
MODEL_CATALOG = {
    # ---------------- 翻译大模型 (GGUF 与 CTranslate2 格式) ----------------
    "qwen2.5-0.5b-instruct-q4_k_m": {
        "name": "Qwen2.5 0.5B Instruct Q4_K_M (轻量快速·推荐)",
        "type": "translation",
        "relative_path": "models/translation/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_mb": 469,
        "min_size": 100 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/qwen2.5-0.5b-instruct-q4_k_m.gguf",
            "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
            "https://modelscope.cn/models/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (国内免翻墙·推荐)", "url": "https://modelscope.cn/models/qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/qwen2.5-0.5b-instruct-q4_k_m.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"},
            {"source": "ModelScope 社区备份源 (bartowski)", "url": "https://modelscope.cn/models/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 社区备份源 (bartowski)", "url": "https://huggingface.co/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"},
        ],
        "description": "轻量级小钢炮，老旧CPU/低配电脑首选，单次识别翻译仅需几十毫秒",
    },
    "qwen2.5-1.5b-instruct-q4_k_m": {
        "name": "Qwen2.5 1.5B Instruct Q4_K_M (均衡优选)",
        "type": "translation",
        "relative_path": "models/translation/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 1100,
        "min_size": 400 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
            "https://modelscope.cn/models/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (国内免翻墙·推荐)", "url": "https://modelscope.cn/models/qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/qwen2.5-1.5b-instruct-q4_k_m.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"},
            {"source": "ModelScope 社区备份源 (bartowski)", "url": "https://modelscope.cn/models/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 社区备份源 (bartowski)", "url": "https://huggingface.co/bartowski/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"},
        ],
        "description": "均衡推荐，翻译质量与速度极佳，支持长难句地道口语化表达",
    },
    "qwen2.5-3b-instruct-q4_k_m": {
        "name": "Qwen2.5 3B Instruct Q4_K_M (高精度推荐)",
        "type": "translation",
        "relative_path": "models/translation/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_mb": 2000,
        "min_size": 800 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/qwen/Qwen2.5-3B-Instruct-GGUF/resolve/master/qwen2.5-3b-instruct-q4_k_m.gguf",
            "https://hf-mirror.com/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
            "https://modelscope.cn/models/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/master/Qwen2.5-3B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (国内免翻墙·推荐)", "url": "https://modelscope.cn/models/qwen/Qwen2.5-3B-Instruct-GGUF/resolve/master/qwen2.5-3b-instruct-q4_k_m.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"},
            {"source": "ModelScope 社区备份源 (bartowski)", "url": "https://modelscope.cn/models/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/master/Qwen2.5-3B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 社区备份源 (bartowski)", "url": "https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"},
        ],
        "description": "30亿参数高精度模型，地道术语表达极优，适合游戏剧情与专业文档翻译",
    },
    "qwen2.5-7b-instruct-q4_k_m": {
        "name": "Qwen2.5 7B Instruct Q4_K_M (旗舰顶级)",
        "type": "translation",
        "relative_path": "models/translation/qwen2.5-7b-instruct-q4_k_m.gguf",
        "size_mb": 4500,
        "min_size": 1500 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/master/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            "https://modelscope.cn/models/qwen/Qwen2.5-7B-Instruct-GGUF/resolve/master/qwen2.5-7b-instruct-q4_k_m.gguf",
            "https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
            "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (bartowski)", "url": "https://modelscope.cn/models/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/master/Qwen2.5-7B-Instruct-Q4_K_M.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf"},
            {"source": "ModelScope Qwen 官方镜像", "url": "https://modelscope.cn/models/qwen/Qwen2.5-7B-Instruct-GGUF/resolve/master/qwen2.5-7b-instruct-q4_k_m.gguf"},
        ],
        "description": "旗舰级大模型，翻译信达雅，适合独立显卡或强劲多核CPU",
    },
    "opus-mt-en-zh-ct2": {
        "name": "OPUS-MT 英译中 (轻量 CTranslate2)",
        "type": "translation",
        "relative_dir": "models/translation/opus-mt-en-zh-ct2",
        "size_mb": 160,
        "is_multi_file": True,
        "files": [
            {
                "name": "模型权重 (model.bin)",
                "filename": "model.bin",
                "min_size": 40 * 1024 * 1024,
                "urls": [
                    "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin",
                    "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin",
                ],
                "backup_mirrors": [
                    {"source": "Hugging Face 官方源 (gaudi)", "url": "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin"},
                    {"source": "HF-Mirror 国内镜像源", "url": "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin"},
                ],
            },
            {
                "name": "分词词表 (shared_vocabulary.json)",
                "filename": "shared_vocabulary.json",
                "min_size": 50 * 1024,
                "urls": [
                    "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/shared_vocabulary.json",
                    "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/shared_vocabulary.json",
                ],
                "backup_mirrors": [
                    {"source": "Hugging Face 官方源", "url": "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/shared_vocabulary.json"},
                    {"source": "HF-Mirror 国内镜像源", "url": "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/shared_vocabulary.json"},
                ],
            },
            {
                "name": "源语言分词模型 (source.spm)",
                "filename": "source.spm",
                "min_size": 100 * 1024,
                "urls": [
                    "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/source.spm",
                    "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/source.spm",
                ],
                "backup_mirrors": [
                    {"source": "Hugging Face 官方源", "url": "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/source.spm"},
                    {"source": "HF-Mirror 国内镜像源", "url": "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/source.spm"},
                ],
            },
            {
                "name": "目标语言分词模型 (target.spm)",
                "filename": "target.spm",
                "min_size": 100 * 1024,
                "urls": [
                    "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/target.spm",
                    "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/target.spm",
                ],
                "backup_mirrors": [
                    {"source": "Hugging Face 官方源", "url": "https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/target.spm"},
                    {"source": "HF-Mirror 国内镜像源", "url": "https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/target.spm"},
                ],
            },
        ],
        "description": "轻量级高效率 CTranslate2 离线模型，专精英文至简体中文，低内存低延迟",
    },
    "llama-3.2-1b-instruct-q4_k_m": {
        "name": "LLaMA 3.2 1B Instruct Q4_K_M (Meta 轻量)",
        "type": "translation",
        "relative_path": "models/translation/llama-3.2-1b-instruct-q4_k_m.gguf",
        "size_mb": 1300,
        "min_size": 500 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/master/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (国内推荐)", "url": "https://modelscope.cn/models/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/master/Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"},
        ],
        "description": "Meta 最新轻量开源模型，英文语法解析能力强",
    },
    "llama-3.2-3b-instruct-q4_k_m": {
        "name": "LLaMA 3.2 3B Instruct Q4_K_M (Meta 中量)",
        "type": "translation",
        "relative_path": "models/translation/llama-3.2-3b-instruct-q4_k_m.gguf",
        "size_mb": 2000,
        "min_size": 800 * 1024 * 1024,
        "urls": [
            "https://modelscope.cn/models/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/master/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "ModelScope 阿里官方极速源 (国内推荐)", "url": "https://modelscope.cn/models/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/master/Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
            {"source": "HF-Mirror 国内全量加速镜像", "url": "https://hf-mirror.com/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 官方直连源", "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"},
        ],
        "description": "Meta 中量级模型，英文长句逻辑与术语翻译精准",
    },
    # ---------------- 极速 OCR 引擎与模型 ----------------
    "win11_media_ocr": {
        "name": "Windows 11 原生系统 OCR (首选推荐·免下载权重)",
        "type": "ocr",
        "pip_packages": ["winocr"],
        "is_builtin": True,
        "size_mb": 0,
        "backup_mirrors": [
            {"source": "Windows 11 系统级原生组件 (系统内置免下)", "url": "本地 Windows.Media.Ocr API (已安装 winocr 库)"},
        ],
        "description": "直接调用 Windows 11 本地安装的 Windows.Media.Ocr 库，无需任何模型权重文件，30ms 极速",
    },
    "rapidocr_ch": {
        "name": "RapidOCR ONNX 极速引擎 (推荐·自动下载模型·纯CPU高效)",
        "type": "ocr",
        "pip_packages": ["rapidocr-onnxruntime", "onnxruntime"],
        "is_multi_file": True,
        "relative_dir": "models/ocr/rapidocr",
        "size_mb": 17,
        "files": [
            {
                "name": "检测模型 (ch_PP-OCRv4_det)",
                "filename": "ch_PP-OCRv4_det_infer.onnx",
                "min_size": 2 * 1024 * 1024,
                "urls": [
                    "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx",
                    "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx",
                    "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_PP-OCRv4_det_infer.onnx",
                ],
                "backup_mirrors": [
                    {"source": "ModelScope 极速国内镜像 (首选·推荐)", "url": "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx"},
                    {"source": "HF-Mirror 镜像加速源", "url": "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx"},
                    {"source": "GitHub 官方 Release 备用源", "url": "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_PP-OCRv4_det_infer.onnx"},
                ],
            },
            {
                "name": "识别模型 (ch_PP-OCRv4_rec)",
                "filename": "ch_PP-OCRv4_rec_infer.onnx",
                "min_size": 5 * 1024 * 1024,
                "urls": [
                    "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx",
                    "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx",
                    "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_PP-OCRv4_rec_infer.onnx",
                ],
                "backup_mirrors": [
                    {"source": "ModelScope 极速国内镜像 (首选·推荐)", "url": "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx"},
                    {"source": "HF-Mirror 镜像加速源", "url": "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx"},
                    {"source": "GitHub 官方 Release 备用源", "url": "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_PP-OCRv4_rec_infer.onnx"},
                ],
            },
            {
                "name": "方向分类模型 (ch_ppocr_mobile_v2.0_cls)",
                "filename": "ch_ppocr_mobile_v2.0_cls_infer.onnx",
                "min_size": 250 * 1024,
                "urls": [
                    "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
                    "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
                    "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_ppocr_mobile_v2.0_cls_infer.onnx",
                ],
                "backup_mirrors": [
                    {"source": "ModelScope 极速国内镜像 (首选·推荐)", "url": "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx"},
                    {"source": "HF-Mirror 镜像加速源", "url": "https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx"},
                    {"source": "GitHub 官方 Release 备用源", "url": "https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_ppocr_mobile_v2.0_cls_infer.onnx"},
                ],
            },
        ],
        "description": "基于 ONNXRuntime 的高精度中英文 OCR 引擎，自带高速镜像离线模型权重，解耦 Paddle 运行极稳",
    },
    "paddleocr_ch": {
        "name": "PaddleOCR 离线模型 (PP-OCRv4)",
        "type": "ocr",
        "pip_packages": ["paddleocr"],
        "is_archive": True,
        "relative_dir": "models/ocr/paddleocr",
        "size_mb": 17,
        "archives": [
            {
                "name": "检测模型 (ch_PP-OCRv4_det)",
                "sub_dir": "ch_PP-OCRv4_det_infer",
                "min_size": 3 * 1024 * 1024,
                "urls": [
                    "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar",
                    "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar",
                ],
                "backup_mirrors": [
                    {"source": "百度飞桨 BOS 官方高速 CDN (PP-OCRv4 推荐)", "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar"},
                    {"source": "百度飞桨 BOS 备用轻量源 (v2.0 备选)", "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_det_infer.tar"},
                ],
            },
            {
                "name": "识别模型 (ch_PP-OCRv4_rec)",
                "sub_dir": "ch_PP-OCRv4_rec_infer",
                "min_size": 5 * 1024 * 1024,
                "urls": [
                    "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar",
                    "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_rec_infer.tar",
                ],
                "backup_mirrors": [
                    {"source": "百度飞桨 BOS 官方高速 CDN (PP-OCRv4 推荐)", "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar"},
                    {"source": "百度飞桨 BOS 备用轻量源 (v2.0 备选)", "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_rec_infer.tar"},
                ],
            },
            {
                "name": "方向分类模型 (ch_ppocr_mobile_v2.0_cls)",
                "sub_dir": "ch_ppocr_mobile_v2.0_cls_infer",
                "min_size": 800 * 1024,
                "urls": [
                    "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
                ],
                "backup_mirrors": [
                    {"source": "百度飞桨 BOS 官方高速 CDN (推荐)", "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar"},
                ],
            },
        ],
        "description": "百度飞桨 PP-OCRv4 离线模型（支持中英文高精度识别）",
    },
    "easyocr_multi": {
        "name": "EasyOCR 国际化多语言 OCR",
        "type": "ocr",
        "pip_packages": ["easyocr"],
        "size_mb": 15,
        "backup_mirrors": [
            {"source": "清华大学 PyPI 镜像站", "url": "https://pypi.tuna.tsinghua.edu.cn/simple/easyocr/"},
            {"source": "阿里云 PyPI 镜像站", "url": "https://mirrors.aliyun.com/pypi/simple/easyocr/"},
        ],
        "description": "国际权威 OCR 框架，首次运行自动下载高精度多语种离线识别权重",
    },
    "tesseract_ocr": {
        "name": "Tesseract OCR",
        "type": "ocr",
        "pip_packages": ["pytesseract"],
        "size_mb": 15,
        "backup_mirrors": [
            {"source": "UB-Mannheim Tesseract Windows 安装包", "url": "https://github.com/UB-Mannheim/tesseract/wiki"},
            {"source": "清华大学 PyPI 镜像源", "url": "https://pypi.tuna.tsinghua.edu.cn/simple/pytesseract/"},
        ],
        "description": "Google 开源成熟轻量 OCR 引擎",
    },
    "qwen2.5-vl-3b-instruct": {
        "name": "Qwen2.5-VL 3B 视觉大模型 AI OCR",
        "type": "ocr",
        "relative_path": "models/ocr/qwen2.5-vl-3b-instruct.gguf",
        "size_mb": 2200,
        "min_size": 800 * 1024 * 1024,
        "urls": [
            "https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
            "https://hf-mirror.com/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
            "https://huggingface.co/mradermacher/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf",
            "https://hf-mirror.com/mradermacher/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf",
        ],
        "backup_mirrors": [
            {"source": "Hugging Face 官方直连源 (unsloth)", "url": "https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf"},
            {"source": "HF-Mirror 国内镜像加速源 (unsloth)", "url": "https://hf-mirror.com/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf"},
            {"source": "Hugging Face 官方源 (mradermacher)", "url": "https://huggingface.co/mradermacher/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf"},
            {"source": "HF-Mirror 国内镜像源 (mradermacher)", "url": "https://hf-mirror.com/mradermacher/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct.Q4_K_M.gguf"},
        ],
        "description": "阿里开源视觉-语言多模态大模型 (VLM)，直接端到端阅读复杂屏幕与暗黑界面",
    },
    "doclm_ocr": {
        "name": "腾讯 DocLM 屏幕与文档视觉大模型 OCR",
        "type": "ocr",
        "relative_path": "models/ocr/doclm-screen-ocr.gguf",
        "size_mb": 1800,
        "min_size": 700 * 1024 * 1024,
        "urls": [
            "https://huggingface.co/gguf-org/docling-gguf/resolve/main/docling-2.0-q4_k_m.gguf",
            "https://hf-mirror.com/gguf-org/docling-gguf/resolve/main/docling-2.0-q4_k_m.gguf",
        ],
        "backup_mirrors": [
            {"source": "Hugging Face 官方直连源 (docling-gguf)", "url": "https://huggingface.co/gguf-org/docling-gguf/resolve/main/docling-2.0-q4_k_m.gguf"},
            {"source": "HF-Mirror 国内镜像加速源", "url": "https://hf-mirror.com/gguf-org/docling-gguf/resolve/main/docling-2.0-q4_k_m.gguf"},
        ],
        "description": "文档与屏幕排版视觉识别大模型，抗低对比度模糊",
    },
}


def get_project_root() -> str:
    """获取项目根目录绝对路径"""
    return os.path.abspath(os.path.dirname(__file__))


def _get_ssl_context():
    """获取宽松的 SSL 上下文以避免 Windows 环境缺少本地证书链引发握手失败"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None


def _get_python_executable() -> str:
    """获取可用于 subprocess 调用的标准 python.exe 路径 (规避 pythonw.exe 无终端通道崩溃)"""
    py_exe = sys.executable
    if py_exe.lower().endswith("pythonw.exe"):
        cand = py_exe[:-5] + ".exe"
        if os.path.exists(cand):
            return cand
    return py_exe


def is_package_installed(pkg_name: str) -> bool:
    """静态检查 Python 模块是否已安装，严禁使用 __import__ 规避 C 扩展/COM 碰撞导致崩溃"""
    mod_name = pkg_name.replace("-", "_")
    try:
        spec = importlib.util.find_spec(mod_name)
        return spec is not None
    except Exception:
        return False


class SmartRedirectHandler(urllib.request.HTTPRedirectHandler):
    """智能全协议重定向处理器，支持 301, 302, 303, 307, 308"""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_headers = dict(req.headers)
        return urllib.request.Request(newurl, headers=new_headers, origin_req_host=req.origin_req_host, unverifiable=True)

    def http_error_308(self, req, fp, code, msg, headers):
        loc = headers.get("Location")
        if loc:
            new_req = urllib.request.Request(loc, headers=dict(req.headers))
            return self.parent.open(new_req)
        return super().http_error_302(req, fp, code, msg, headers)

    def http_error_307(self, req, fp, code, msg, headers):
        loc = headers.get("Location")
        if loc:
            new_req = urllib.request.Request(loc, headers=dict(req.headers))
            return self.parent.open(new_req)
        return super().http_error_302(req, fp, code, msg, headers)


def download_file_with_progress(
    urls: List[str],
    destination: str,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
    min_expected_bytes: int = 50 * 1024,
) -> bool:
    """
    多镜像尝试下载文件并支持断点续传、实时进度回调与取消感知。
    强化校验：拦截 HTTP 错误代码、拦截 HTML 404/错误文本、校验最小体积，杜绝生成十几个字节损坏坏文件。
    """
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    temp_path = destination + ".download"

    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    ssl_ctx = _get_ssl_context()
    https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)
    opener = urllib.request.build_opener(SmartRedirectHandler(), https_handler)

    for url in urls:
        if is_cancelled and is_cancelled():
            if status_callback:
                status_callback("下载已由用户取消")
            return False

        msg = f"正在连接高速镜像源: {url}..."
        logger.info(msg)
        if status_callback:
            status_callback(msg)

        out_file = None
        try:
            existing_bytes = 0
            if os.path.exists(temp_path):
                existing_bytes = os.path.getsize(temp_path)

            req_headers = dict(base_headers)
            if existing_bytes > 0:
                req_headers["Range"] = f"bytes={existing_bytes}-"

            req = urllib.request.Request(url, headers=req_headers)
            resp = opener.open(req, timeout=35)
            with resp:
                resp_code = getattr(resp, "status", getattr(resp, "code", 200))
                if resp_code not in (200, 206):
                    raise ValueError(f"HTTP 响应异常状态码: {resp_code}")

                content_type = str(resp.headers.get("content-type", "")).lower()
                if "text/html" in content_type:
                    raise ValueError("源服务器返回 HTML 错误页面而非模型二进制数据")

                content_length = int(resp.headers.get("content-length", 0))

                if resp_code == 206:
                    total_size = existing_bytes + content_length
                    downloaded = existing_bytes
                    out_file = open(temp_path, "ab")
                    logger.info(f"触发断点续传: 已保留 {existing_bytes / 1024 / 1024:.1f}MB, 继续下载...")
                else:
                    total_size = content_length
                    downloaded = 0
                    out_file = open(temp_path, "wb")

                start_time = time.time()
                last_time = start_time
                last_log_time = start_time
                last_bytes = downloaded
                speed = 0.0

                chunk_size = 1024 * 256  # 256KB 高速缓冲
                is_first_chunk = True

                while True:
                    if is_cancelled and is_cancelled():
                        logger.info("检测到用户取消信号，终止下载流")
                        if status_callback:
                            status_callback("下载已取消")
                        out_file.close()
                        out_file = None
                        return False

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    # 首块头部严格防伪校验，杜绝 HTML 404 或 API 错误 JSON 伪装成二进制
                    if is_first_chunk and downloaded == 0:
                        is_first_chunk = False
                        head_sample = chunk[:128].lower()
                        if b"<html" in head_sample or b"<!doctype" in head_sample:
                            raise ValueError("接收到 HTML 错误页面而非二进制模型权重")
                        if b'{"code"' in head_sample and b'"message"' in head_sample:
                            raise ValueError("接收到 API 错误 JSON 响应而非模型权重")

                    out_file.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_time >= 0.25:
                        speed = (downloaded - last_bytes) / max(0.001, (now - last_time)) / 1024.0  # KB/s
                        last_time = now
                        last_bytes = downloaded
                        if progress_callback:
                            try:
                                progress_callback(downloaded, total_size, speed)
                            except Exception:
                                pass

                    if now - last_log_time >= 2.0:
                        pct = (downloaded / total_size * 100) if total_size > 0 else 0
                        logger.info(
                            f"[下载进度] {os.path.basename(destination)}: "
                            f"{downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB ({pct:.1f}%) 速度: {speed:.1f} KB/s"
                        )
                        last_log_time = now

                out_file.flush()
                out_file.close()
                out_file = None

            # 最终文件体积防伪完整性校验
            final_size = os.path.getsize(temp_path)
            if final_size < min_expected_bytes:
                os.remove(temp_path)
                raise ValueError(f"下载文件过小 ({final_size} 字节，小于最小阈值 {min_expected_bytes})，判定为下载残缺或网络异常")

            # 下载完成后安全原子替换
            if os.path.exists(destination):
                try:
                    os.remove(destination)
                except Exception:
                    pass
            os.replace(temp_path, destination)
            success_msg = f"[成功] 模型文件下载完成并已就绪: {os.path.basename(destination)} ({final_size / 1024 / 1024:.1f}MB)"
            logger.info(success_msg)
            if status_callback:
                status_callback(success_msg)
            return True

        except Exception as e:
            if out_file:
                try:
                    out_file.close()
                except Exception:
                    pass
            warn_msg = f"当前镜像连接或校验失败 ({e})，正在自动无缝切换至下一备选镜像..."
            logger.warning(warn_msg)
            if status_callback:
                status_callback(warn_msg)

    # 全部镜像源失败后清理残余临时文件
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass
    err_msg = "所有可用镜像源均未能完成下载，请检查网络连接或代理"
    logger.error(err_msg)
    if status_callback:
        status_callback(err_msg)
    return False


def get_model_status(model_id: str) -> Dict[str, Any]:
    """
    获取指定模型的就绪状态与本地真实磁盘大小。
    严格落实要求：
    - 未下载的统一显示【待下载】与所需下载大小；
    - 已下载且体积符合要求的显示【已就绪】及本地实际占用大小；
    - 严苛排查十几个字节的残缺伪文件，杜绝误报就绪。
    """
    meta = MODEL_CATALOG.get(model_id)
    root = get_project_root()

    if not meta:
        # 兼容自定义或动态加入的模型 (如 models/translation/xxx.gguf)
        dest_path = os.path.normpath(os.path.join(root, "models", "translation", f"{model_id}.gguf"))
        if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 10 * 1024 * 1024:
            sz_mb = os.path.getsize(dest_path) / (1024 * 1024)
            return {
                "ready": True,
                "downloaded": True,
                "type": "translation",
                "label": f"已就绪 ({format_size_mb(sz_mb)})",
                "size_mb": int(round(sz_mb)),
                "actual_size_mb": sz_mb,
                "path": dest_path,
                "is_builtin": False,
            }
        return {
            "ready": False,
            "downloaded": False,
            "type": "unknown",
            "label": "未知模型 (待配置)",
            "size_mb": 0,
            "actual_size_mb": 0.0,
            "is_builtin": False,
        }

    expected_mb = meta.get("size_mb", 0)
    expected_str = format_size_mb(expected_mb)

    # 1. Windows 11 原生系统级 OCR 引擎
    if meta.get("is_builtin"):
        has_winocr = is_package_installed("winocr") and sys.platform == "win32"
        return {
            "ready": has_winocr,
            "downloaded": True,  # 系统内置无需下载权重文件
            "type": "ocr",
            "label": "系统内置免下载 (30ms)" if has_winocr else "待安装 winocr (免下载权重)",
            "size_mb": 0,
            "actual_size_mb": 0.0,
            "is_builtin": True,
            "description": meta.get("description", ""),
        }

    # 2. 检查多文件模型 (如 RapidOCR ONNX 权重 / OPUS-MT CTranslate2 权重)
    if meta.get("is_multi_file"):
        pip_ok = not meta.get("pip_packages") or all(is_package_installed(pkg) for pkg in meta["pip_packages"])
        rel_dir = meta.get("relative_dir", "models/ocr/rapidocr")
        target_dir = os.path.normpath(os.path.join(root, rel_dir))
        files_ok = True
        total_valid_bytes = 0

        for f_info in meta.get("files", []):
            f_path = os.path.join(target_dir, f_info.get("filename", ""))
            min_sz = f_info.get("min_size", 50 * 1024)
            if not os.path.isfile(f_path) or os.path.getsize(f_path) < min_sz:
                files_ok = False
                break
            try:
                with open(f_path, "rb") as test_f:
                    head = test_f.read(64)
                    if b"<html" in head.lower() or b"<!doctype" in head.lower() or b'{"code"' in head:
                        files_ok = False
                        break
            except Exception:
                files_ok = False
                break
            total_valid_bytes += os.path.getsize(f_path)

        actual_mb = total_valid_bytes / (1024 * 1024)
        ready = pip_ok and files_ok

        if ready:
            label = f"已就绪 ({format_size_mb(actual_mb)})"
        elif files_ok and not pip_ok:
            label = f"待配置运行环境 (~{expected_str})"
        elif total_valid_bytes > 0:
            label = f"文件残缺待重下 (~{expected_str})"
        else:
            label = f"待下载 (~{expected_str})"

        return {
            "ready": ready,
            "downloaded": files_ok,
            "type": meta.get("type", "ocr"),
            "label": label,
            "size_mb": expected_mb,
            "actual_size_mb": actual_mb,
            "path": target_dir,
            "is_builtin": False,
            "description": meta.get("description", ""),
        }

    # 3. 检查压缩包类型的离线模型 (如 PaddleOCR PP-OCRv4 tar 权重)
    if meta.get("is_archive"):
        pip_ok = not meta.get("pip_packages") or all(is_package_installed(pkg) for pkg in meta["pip_packages"])
        rel_dir = meta.get("relative_dir", "models/ocr/paddleocr")
        target_dir = os.path.normpath(os.path.join(root, rel_dir))
        arch_ok = True
        total_model_bytes = 0

        for arch in meta.get("archives", []):
            sub = os.path.join(target_dir, arch.get("sub_dir", ""))
            min_sz = arch.get("min_size", 1024 * 1024)
            if not os.path.isdir(sub):
                arch_ok = False
                break
            # 必须包含有效的非空模型二进制 (如 inference.pdmodel / inference.pdiparams)
            sub_files = [os.path.join(sub, f) for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f))]
            sub_total = sum(os.path.getsize(fp) for fp in sub_files)
            if sub_total < min_sz:
                arch_ok = False
                break
            total_model_bytes += sub_total

        actual_mb = total_model_bytes / (1024 * 1024)
        ready = pip_ok and arch_ok

        if ready:
            label = f"已就绪 ({format_size_mb(actual_mb)})"
        elif arch_ok and not pip_ok:
            label = f"待配置 paddle 依赖 (~{expected_str})"
        elif total_model_bytes > 0:
            label = f"文件残缺待重下 (~{expected_str})"
        else:
            label = f"待下载 (~{expected_str})"

        return {
            "ready": ready,
            "downloaded": arch_ok,
            "type": meta.get("type", "ocr"),
            "label": label,
            "size_mb": expected_mb,
            "actual_size_mb": actual_mb,
            "path": target_dir,
            "is_builtin": False,
            "description": meta.get("description", ""),
        }

    # 4. 依赖纯 pip 模块的库 (如 easyocr, pytesseract)
    if meta.get("pip_packages") and not meta.get("relative_path"):
        all_ok = all(is_package_installed(pkg) for pkg in meta["pip_packages"])
        label = "已就绪" if all_ok else f"待安装组件 (~{expected_str})"
        return {
            "ready": all_ok,
            "downloaded": all_ok,
            "type": meta.get("type", "ocr"),
            "label": label,
            "size_mb": expected_mb,
            "actual_size_mb": 0.0,
            "is_builtin": False,
            "description": meta.get("description", ""),
        }

    # 5. 单个 GGUF 文件模型 (如 Qwen2.5 翻译模型 / Qwen2.5-VL 视觉模型)
    rel_path = meta.get("relative_path")
    if rel_path:
        dest_path = os.path.normpath(os.path.join(root, rel_path))
        min_sz = meta.get("min_size", 10 * 1024 * 1024)
        is_exist = os.path.isfile(dest_path)
        actual_size = os.path.getsize(dest_path) if is_exist else 0
        actual_mb = actual_size / (1024 * 1024)

        if is_exist and actual_size >= min_sz:
            ready = True
            label = f"已就绪 ({format_size_mb(actual_mb)})"
        elif is_exist:
            ready = False
            label = f"损坏待重新下载 (~{expected_str})"
        else:
            ready = False
            label = f"待下载 (~{expected_str})"

        return {
            "ready": ready,
            "downloaded": ready,
            "type": meta.get("type", "translation"),
            "label": label,
            "size_mb": expected_mb,
            "actual_size_mb": actual_mb,
            "path": dest_path,
            "is_builtin": False,
            "description": meta.get("description", ""),
        }

    return {
        "ready": True,
        "downloaded": True,
        "type": "generic",
        "label": "已就绪",
        "size_mb": 0,
        "actual_size_mb": 0.0,
        "is_builtin": False,
    }


def ensure_model_ready(
    model_id: str,
    auto_download: bool = True,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    is_cancelled: Optional[Callable[[], bool]] = None,
) -> bool:
    """
    检查并确保指定模型完全就绪（包括文件存在、完整性校验与必要 pip 库安装）。
    严格规避 __import__ 与进程阻塞。
    """
    if is_cancelled and is_cancelled():
        return False

    root = get_project_root()
    meta = MODEL_CATALOG.get(model_id)

    if not meta:
        dest_path = os.path.normpath(os.path.join(root, "models", "translation", f"{model_id}.gguf"))
        if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 10 * 1024 * 1024:
            if status_callback:
                status_callback(f"模型文件已就绪: {os.path.basename(dest_path)}")
            return True
        logger.warning(f"未知模型 ID 且未找到对应文件: {model_id}")
        return False

    # 1. 检查 Python 模块依赖 (如 winocr, rapidocr-onnxruntime 等)
    pip_pkgs = meta.get("pip_packages", [])
    if pip_pkgs:
        python_exe = _get_python_executable()
        creation_flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW

        for pkg in pip_pkgs:
            if is_cancelled and is_cancelled():
                return False

            if not is_package_installed(pkg):
                if not auto_download:
                    return False
                msg = f"正在自动安装离线组件 [{pkg}] (清华大学开源镜像站)..."
                logger.info(msg)
                if status_callback:
                    status_callback(msg)
                try:
                    res = subprocess.run(
                        [
                            python_exe,
                            "-m",
                            "pip",
                            "install",
                            pkg,
                            "-i",
                            "https://pypi.tuna.tsinghua.edu.cn/simple",
                            "--trusted-host",
                            "pypi.tuna.tsinghua.edu.cn",
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=180,
                        creationflags=creation_flags,
                    )
                    if res.returncode != 0:
                        # 备选阿里云高速镜像
                        res = subprocess.run(
                            [
                                python_exe,
                                "-m",
                                "pip",
                                "install",
                                pkg,
                                "-i",
                                "https://mirrors.aliyun.com/pypi/simple/",
                                "--trusted-host",
                                "mirrors.aliyun.com",
                            ],
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=180,
                            creationflags=creation_flags,
                        )
                except Exception as e:
                    logger.error(f"安装 [{pkg}] 失败: {e}")
                    if status_callback:
                        status_callback(f"安装 [{pkg}] 失败: {e}")
                    return False

    # 2. 单文件模型 (GGUF)
    rel_path = meta.get("relative_path")
    if rel_path:
        dest_path = os.path.normpath(os.path.join(root, rel_path))
        min_sz = meta.get("min_size", 10 * 1024 * 1024)
        if os.path.isfile(dest_path) and os.path.getsize(dest_path) >= min_sz:
            if status_callback:
                status_callback(f"模型权重已完整就绪: {os.path.basename(dest_path)}")
            return True

        if not auto_download:
            return False

        # 如果已有损坏的残缺文件，先清理
        if os.path.exists(dest_path) and os.path.getsize(dest_path) < min_sz:
            try:
                os.remove(dest_path)
            except Exception:
                pass

        msg = f"检测到模型权重未就绪 [{meta.get('name', model_id)}]，启动高速镜像下载..."
        logger.info(msg)
        if status_callback:
            status_callback(msg)

        urls = meta.get("urls", [])
        return download_file_with_progress(
            urls,
            dest_path,
            progress_callback=progress_callback,
            status_callback=status_callback,
            is_cancelled=is_cancelled,
            min_expected_bytes=min_sz,
        )

    # 3. 多文件离线模型 (如 RapidOCR ONNX, OPUS-MT)
    if meta.get("is_multi_file"):
        rel_dir = meta.get("relative_dir", "")
        target_dir = os.path.normpath(os.path.join(root, rel_dir))
        os.makedirs(target_dir, exist_ok=True)
        files = meta.get("files", [])

        all_ready = True
        for f_info in files:
            f_path = os.path.join(target_dir, f_info.get("filename", ""))
            min_sz = f_info.get("min_size", 50 * 1024)
            if not os.path.isfile(f_path) or os.path.getsize(f_path) < min_sz:
                all_ready = False
                break

        if all_ready:
            if status_callback:
                status_callback(f"离线模型权重均已完整就绪: {meta.get('name', model_id)}")
            return True

        if not auto_download:
            return False

        for f_info in files:
            if is_cancelled and is_cancelled():
                return False
            f_name = f_info.get("name", "组件权重")
            dest_file = os.path.join(target_dir, f_info.get("filename", ""))
            min_sz = f_info.get("min_size", 50 * 1024)

            if os.path.isfile(dest_file) and os.path.getsize(dest_file) >= min_sz:
                continue

            if os.path.exists(dest_file):
                try:
                    os.remove(dest_file)
                except Exception:
                    pass

            urls = f_info.get("urls", [])
            if status_callback:
                status_callback(f"正在下载 {f_name}...")
            ok = download_file_with_progress(
                urls,
                dest_file,
                progress_callback=progress_callback,
                status_callback=status_callback,
                is_cancelled=is_cancelled,
                min_expected_bytes=min_sz,
            )
            if not ok:
                return False

        return True

    # 4. 压缩包类型离线模型 (如 PaddleOCR PP-OCRv4 tar 权重)
    if meta.get("is_archive"):
        rel_dir = meta.get("relative_dir", "models/ocr/paddleocr")
        target_dir = os.path.normpath(os.path.join(root, rel_dir))
        os.makedirs(target_dir, exist_ok=True)
        archives = meta.get("archives", [])

        all_ready = True
        for arch in archives:
            sub = os.path.join(target_dir, arch.get("sub_dir", ""))
            min_sz = arch.get("min_size", 1024 * 1024)
            if not os.path.isdir(sub):
                all_ready = False
                break
            sub_files = [os.path.join(sub, f) for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f))]
            if sum(os.path.getsize(fp) for fp in sub_files) < min_sz:
                all_ready = False
                break

        if all_ready:
            if status_callback:
                status_callback(f"离线模型权重均已完整就绪: {meta.get('name', model_id)}")
            return True

        if not auto_download:
            return False

        msg = f"检测到离线模型权重未就绪 [{meta.get('name', model_id)}]，启动官方/镜像自动下载与校验..."
        logger.info(msg)
        if status_callback:
            status_callback(msg)

        for arch in archives:
            if is_cancelled and is_cancelled():
                return False
            sub = os.path.join(target_dir, arch.get("sub_dir", ""))
            min_sz = arch.get("min_size", 1024 * 1024)

            # 校验是否已完整存在
            if os.path.isdir(sub):
                sub_files = [os.path.join(sub, f) for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f))]
                if sum(os.path.getsize(fp) for fp in sub_files) >= min_sz:
                    continue
                else:
                    # 发现损坏/仅有十几个字节的残缺目录，彻底清除干净再重新下载
                    shutil.rmtree(sub, ignore_errors=True)

            arch_name = arch.get("name", "组件权重")
            temp_tar = os.path.join(target_dir, arch.get("sub_dir", "temp") + ".tar")
            if os.path.exists(temp_tar):
                try:
                    os.remove(temp_tar)
                except Exception:
                    pass

            urls = arch.get("urls", [])
            if status_callback:
                status_callback(f"正在下载 {arch_name}...")
            ok = download_file_with_progress(
                urls,
                temp_tar,
                progress_callback=progress_callback,
                status_callback=status_callback,
                is_cancelled=is_cancelled,
                min_expected_bytes=min_sz,
            )
            if not ok or not os.path.exists(temp_tar) or os.path.getsize(temp_tar) < min_sz:
                logger.error(f"下载 {arch_name} 失败或文件大小不满足要求")
                if os.path.exists(temp_tar):
                    try:
                        os.remove(temp_tar)
                    except Exception:
                        pass
                return False

            try:
                if status_callback:
                    status_callback(f"正在安全解压并校验 {arch_name}...")
                with tarfile.open(temp_tar, "r:*") as tf:
                    tf.extractall(target_dir)
                if os.path.exists(temp_tar):
                    os.remove(temp_tar)

                # 解压后核验
                sub_files = [os.path.join(sub, f) for f in os.listdir(sub) if os.path.isfile(os.path.join(sub, f))]
                if sum(os.path.getsize(fp) for fp in sub_files) < min_sz:
                    logger.error(f"解压后文件体积异常: {arch_name}")
                    return False
            except Exception as e_tar:
                logger.error(f"解压 {arch_name} 失败: {e_tar}")
                if os.path.exists(temp_tar):
                    try:
                        os.remove(temp_tar)
                    except Exception:
                        pass
                return False

        logger.info(f"[成功] 离线模型 [{meta.get('name', model_id)}] 全部组件自动下载解压并校验就绪！")
        return True

    return True


def get_model_backup_urls(model_id: str) -> List[Dict[str, str]]:
    """获取指定模型的所有主用与备用下载链接清单"""
    meta = MODEL_CATALOG.get(model_id)
    if not meta:
        return []
    
    # 若有专门定义 backup_mirrors 直接返回
    if "backup_mirrors" in meta:
        return list(meta["backup_mirrors"])

    # 针对多文件模型汇总其各组件的链接
    mirrors = []
    if "files" in meta:
        for f in meta["files"]:
            f_name = f.get("name", "组件")
            for idx, u in enumerate(f.get("urls", []), 1):
                mirrors.append({"source": f"{f_name} (镜像源 #{idx})", "url": u})
    elif "archives" in meta:
        for a in meta["archives"]:
            a_name = a.get("name", "组件压缩包")
            for idx, u in enumerate(a.get("urls", []), 1):
                mirrors.append({"source": f"{a_name} (镜像源 #{idx})", "url": u})
    elif "urls" in meta:
        for idx, u in enumerate(meta["urls"], 1):
            name = "官方/镜像源" if idx == 1 else f"备用镜像源 #{idx}"
            if "modelscope" in u:
                name = "ModelScope 阿里极速源"
            elif "hf-mirror" in u:
                name = "HF-Mirror 国内全量加速镜像"
            elif "huggingface" in u:
                name = "Hugging Face 官方直连源"
            elif "bcebos" in u:
                name = "百度飞桨 BOS 官方 CDN"
            elif "github" in u:
                name = "GitHub 官方 Release 备用源"
            mirrors.append({"source": name, "url": u})

    return mirrors


def get_all_mirrors_summary() -> Dict[str, Any]:
    """汇总获取系统中所有 OCR 和翻译模型的状态与全部镜像备份链接"""
    result = {"ocr": [], "translation": []}
    for m_id, m_info in MODEL_CATALOG.items():
        st = get_model_status(m_id)
        m_type = m_info.get("type", "generic")
        mirrors = get_model_backup_urls(m_id)
        item = {
            "id": m_id,
            "name": m_info.get("name", m_id),
            "type": m_type,
            "size_mb": m_info.get("size_mb", 0),
            "size_str": format_size_mb(m_info.get("size_mb", 0)),
            "ready": st.get("ready", False),
            "downloaded": st.get("downloaded", False),
            "status_label": st.get("label", "未就绪"),
            "actual_size_mb": st.get("actual_size_mb", 0.0),
            "description": m_info.get("description", ""),
            "backup_mirrors": mirrors,
        }
        if m_type == "ocr":
            result["ocr"].append(item)
        elif m_type == "translation":
            result["translation"].append(item)
    return result


def check_url_connectivity(url: str, timeout: float = 3.5) -> Dict[str, Any]:
    """快速检测指定模型下载 URL 的连通状态与响应时间"""
    if not url.startswith("http"):
        return {"ok": True, "code": 200, "latency_ms": 0, "msg": "本地系统组件无需网络"}
    
    start_t = time.time()
    ssl_ctx = _get_ssl_context()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
                "Range": "bytes=0-10",
            },
        )
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        latency = int((time.time() - start_t) * 1000)
        code = resp.getcode()
        return {"ok": code in (200, 206), "code": code, "latency_ms": latency, "msg": "连通正常"}
    except Exception as e:
        latency = int((time.time() - start_t) * 1000)
        return {"ok": False, "code": 0, "latency_ms": latency, "msg": str(e)[:60]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Win11 离线屏幕翻译助手 - 离线模型与备用镜像高速管理工具")
    parser.add_argument("--list", action="store_true", help="列出所有模型及其状态和备用下载镜像")
    parser.add_argument("--download", type=str, help="指定要下载的模型 ID (如 rapidocr_ch, qwen2.5-0.5b-instruct-q4_k_m)")
    parser.add_argument("--download-all", action="store_true", help="一键全自动下载推荐的离线 OCR 与翻译模型矩阵")
    parser.add_argument("--check-urls", action="store_true", help="全面探测测试所有模型下载源与备份镜像的连通性与时延")
    parser.add_argument("--mirrors", type=str, help="查询指定模型的所有备用镜像下载地址")
    args = parser.parse_args()

    if args.list:
        print("\n" + "=" * 65)
        print("  Win11 离线屏幕翻译助手 - 离线模型状态与备用镜像清单")
        print("=" * 65)
        for m_id, m_info in MODEL_CATALOG.items():
            st = get_model_status(m_id)
            print(f"\n[{m_info['type'].upper()}] {m_id}")
            print(f"  模型名称: {m_info['name']}")
            print(f"  当前状态: {st['label']} (总需: {format_size_mb(m_info.get('size_mb', 0))})")
            mirrors = get_model_backup_urls(m_id)
            print(f"  备用镜像源 ({len(mirrors)} 个):")
            for idx, mir in enumerate(mirrors, 1):
                print(f"    [{idx}] {mir['source']}: {mir['url']}")
        print("\n" + "=" * 65)

    elif args.mirrors:
        m_id = args.mirrors.strip()
        mirrors = get_model_backup_urls(m_id)
        if not mirrors:
            print(f"未找到模型 ID: {m_id}")
        else:
            print(f"\n=== 模型 [{m_id}] 备用下载链接清单 ===")
            for idx, m in enumerate(mirrors, 1):
                print(f"[{idx}] {m['source']}\n    -> {m['url']}")

    elif args.check_urls:
        print("\n=== 正在全面检测模型下载源与备用镜像连通性... ===")
        for m_id, m_info in MODEL_CATALOG.items():
            print(f"\n【{m_info.get('name', m_id)}】")
            mirrors = get_model_backup_urls(m_id)
            for m in mirrors:
                u = m["url"]
                res = check_url_connectivity(u)
                tag = f"✓ 正常 ({res['latency_ms']}ms)" if res["ok"] else f"✗ 异常: {res['msg']}"
                print(f"  • {m['source']}: {tag}")

    elif args.download_all:
        recommended = [
            "rapidocr_ch",
            "qwen2.5-0.5b-instruct-q4_k_m",
            "paddleocr_ch",
        ]
        print(f"\n=== 开始自动下载推荐模型组合: {', '.join(recommended)} ===")
        for m_id in recommended:
            print(f"\n>>> 正在准备/下载模型: {m_id} ...")
            ok = ensure_model_ready(m_id, auto_download=True, status_callback=print)
            print(f"[{'成功' if ok else '失败'}] {m_id}")

    elif args.download:
        ok = ensure_model_ready(args.download, auto_download=True, status_callback=print)
        print("\n>>> 下载与配置完成！" if ok else "\n>>> 下载失败，请检查网络或更换备用镜像！")
    else:
        parser.print_help()
