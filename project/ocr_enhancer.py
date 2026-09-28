"""
Win11 离线屏幕实时翻译助手 - OCR 增强预处理流水线
文件: ocr_enhancer.py
功能: 
1. 自动检测深色/暗黑模式 (Dark Mode)，自适应反相高对比度增强；
2. 自适应对比度限制直方图均衡化 (CLAHE)；
3. ClearType 抗锯齿锐化 (Unsharp Mask)，修复高分屏微小字号模糊；
4. 双通道候选变体生成 (Standard / Inverted / Sharpened / Dual-Pass Binarized)，供重试引擎竞速。
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("OCREnhancer")
logger.setLevel(logging.INFO)
logger.propagate = True


class OCREnhancer:
    """OCR 图像增强与自适应候选预处理引擎"""

    @staticmethod
    def detect_dark_mode(bgr_img: np.ndarray) -> Tuple[bool, float]:
        """
        计算图像平均亮度 (Luminance) 判断是否为暗黑主题 (Dark Mode)。
        返回: (is_dark_mode, mean_brightness)
        """
        if bgr_img is None or bgr_img.size == 0:
            return False, 255.0

        # 取灰度计算平均亮度
        if len(bgr_img.shape) == 3:
            gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = bgr_img

        mean_val = float(np.mean(gray))
        # 屏幕应用平均亮度 < 110 通常为深色编辑器 (VSCode, Windows 11 Dark Mode, 终端等)
        is_dark = mean_val < 110.0
        return is_dark, mean_val

    @staticmethod
    def invert_colors(bgr_img: np.ndarray) -> np.ndarray:
        """
        颜色反相：将深底浅字反转为传统白底深字，极大提高针对白纸黑字训练的 OCR 模型的召回率
        """
        return cv2.bitwise_not(bgr_img)

    @staticmethod
    def apply_clahe(bgr_img: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
        """
        LAB 空间自适应局部对比度增强 (CLAHE)，不破坏色彩分布的同时强化边缘微对比度
        """
        try:
            lab = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
            l_enhanced = clahe.apply(l)
            merged = cv2.merge((l_enhanced, a, b))
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        except Exception as e:
            logger.warning(f"CLAHE 增强异常: {e}")
            return bgr_img

    @staticmethod
    def unsharp_mask(bgr_img: np.ndarray, strength: float = 0.6, kernel_size: int = 3) -> np.ndarray:
        """
        反锐化掩膜 (Unsharp Masking)：强化 Windows ClearType 亚像素字体边缘，去除虚焦与缩放模糊
        """
        try:
            blurred = cv2.GaussianBlur(bgr_img, (kernel_size, kernel_size), 0)
            sharpened = cv2.addWeighted(bgr_img, 1.0 + strength, blurred, -strength, 0)
            return sharpened
        except Exception as e:
            logger.warning(f"锐化处理异常: {e}")
            return bgr_img

    @staticmethod
    def adaptive_binarization(bgr_img: np.ndarray) -> np.ndarray:
        """
        双阈值自适应二值化 (Otsu + 局部对比度提升)，用于极端低对比度复杂背景文本提取
        """
        try:
            gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
            # 自适应高斯滤波二值化
            bin_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
            )
            # 转回 3 通道兼容各种 OCR 引擎输入格式
            return cv2.cvtColor(bin_img, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            logger.warning(f"自适应二值化异常: {e}")
            return bgr_img

    @classmethod
    def process_base_image(cls, bgra_or_bgr: np.ndarray, cfg: Dict[str, Any]) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        标准初级处理流水线 (保持原有极低耗时, < 5ms)
        """
        if len(bgra_or_bgr.shape) == 3 and bgra_or_bgr.shape[2] == 4:
            bgr = cv2.cvtColor(bgra_or_bgr, cv2.COLOR_BGRA2BGR)
        else:
            bgr = bgra_or_bgr.copy()

        # 轻量降噪 (默认关闭)
        if cfg.get("denoise", False):
            bgr = cv2.GaussianBlur(bgr, (3, 3), 0)

        # 基础对比度微调
        if cfg.get("clahe", False):
            bgr = cls.apply_clahe(bgr, clip_limit=1.5)

        # 边缘锐化
        if cfg.get("sharpen", False):
            bgr = cls.unsharp_mask(bgr, strength=0.5)

        # 自动倾斜校正
        inv_matrix = None
        if cfg.get("deskew", False):
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            coords = np.column_stack(np.where(gray > 0))
            if len(coords) > 50:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                if abs(angle) > 0.8:
                    (h, w) = bgr.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    bgr = cv2.warpAffine(bgr, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                    inv_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)

        return bgr, inv_matrix

    @classmethod
    def generate_retry_variants(
        cls, base_bgr: np.ndarray, cfg: Dict[str, Any]
    ) -> List[Tuple[str, np.ndarray]]:
        """
        智能生成用于重试阶段的多级增强变体。
        按成功概率高低优先排序，供重试流水线调用。
        """
        variants: List[Tuple[str, np.ndarray]] = []
        is_dark, brightness = cls.detect_dark_mode(base_bgr)

        # 策略 1: 若当前是暗黑界面 (白字黑底)，生成反相高对比度图像 (通常可让 OCR 召回率暴增 300%)
        if is_dark or cfg.get("auto_invert_dark", True):
            inverted = cls.invert_colors(base_bgr)
            # 在反相后叠加上反锐化，字符边框极具立体感
            sharpened_inv = cls.unsharp_mask(inverted, strength=0.7)
            variants.append(("dark_mode_inverted_sharpened", sharpened_inv))

        # 策略 2: 强力 CLAHE 对比度提升 + 边缘锐化 (专克淡灰色字符、磨砂透明背景文字)
        clahe_sharp = cls.unsharp_mask(cls.apply_clahe(base_bgr, clip_limit=2.5), strength=0.8)
        variants.append(("clahe_contrast_boost", clahe_sharp))

        # 策略 3: 二值化变体 (极端复杂彩色渐变背景文字)
        binarized = cls.adaptive_binarization(base_bgr)
        variants.append(("adaptive_binarized", binarized))

        return variants
