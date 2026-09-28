"""
Win11 离线屏幕实时翻译助手 - 缓存与图像感知哈希管理器
文件: cache_manager.py
功能: 实现基于 dHash (差异哈希) 的屏幕画面比对与结果缓存，避免静止画面重复执行耗时 OCR 与翻译。
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)


def compute_dhash(image: Any, hash_size: int = 8) -> str:
    """
    计算图像的差异哈希 (dHash)。
    输入可以是彩色图像或灰度图像。
    1. 缩放到 (hash_size + 1, hash_size)，例如 9x8 或 65x64。
    2. 转灰度。
    3. 比较相邻像素差异：P[x] > P[x+1]。
    4. 生成二进制串并转换为十六进制字符串。
    """
    try:
        if image is None or cv2 is None or np is None:
            return ""
        if hasattr(image, "size") and image.size == 0:
            return ""

        # 如果是 4 通道或 3 通道转为单通道灰度
        if len(image.shape) == 3:
            if image.shape[2] == 4:
                gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            else:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 缩放到 65x64 (hash_size=64)
        target_w = hash_size + 1
        target_h = hash_size
        resized = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_AREA)

        # 差异比较：左像素是否大于右像素
        diff = resized[:, 1:] > resized[:, :-1]

        # 压平成 1D 数组转为十六进制字符串
        bit_string = "".join(["1" if b else "0" for b in diff.flatten()])
        # 以 4 位转换为十六进制
        hex_len = (len(bit_string) + 3) // 4
        hex_str = f"{int(bit_string, 2):0{hex_len}x}"
        return hex_str
    except Exception as e:
        logger.error(f"计算 dHash 异常: {e}")
        return ""


def hamming_distance(hash1: str, hash2: str) -> int:
    """计算两个十六进制哈希字符串之间的汉明距离"""
    if not hash1 or not hash2:
        return 999999
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        # 计算 1 的位数 (bin(xor_val).count('1'))
        return bin(xor_val).count("1")
    except Exception as e:
        logger.warning(f"汉明距离计算失败: {e}")
        return 999999


class CacheItem:
    """单条缓存数据"""

    def __init__(
        self,
        image_hash: str,
        source_lang: str,
        target_lang: str,
        ocr_model_id: str,
        translation_model_id: str,
        config_version: int,
        items: List[Dict[str, Any]],
        timestamp: float,
    ):
        self.image_hash = image_hash
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.ocr_model_id = ocr_model_id
        self.translation_model_id = translation_model_id
        self.config_version = config_version
        self.items = items
        self.timestamp = timestamp

    def matches_config(
        self,
        source_lang: str,
        target_lang: str,
        ocr_model_id: str,
        translation_model_id: str,
        config_version: int,
    ) -> bool:
        """检查配置元数据是否完全匹配"""
        return (
            self.source_lang == source_lang
            and self.target_lang == target_lang
            and self.ocr_model_id == ocr_model_id
            and self.translation_model_id == translation_model_id
            and self.config_version == config_version
        )


class TranslationCacheManager:
    """翻译结果哈希缓存管理器 (LRU 队列)"""

    def __init__(
        self,
        enabled: bool = True,
        max_items: int = 50,
        hash_threshold: int = 5,
    ):
        self.enabled = enabled
        self.max_items = max_items
        self.hash_threshold = hash_threshold
        # 使用 OrderedDict 维护 LRU
        self._cache: collections.OrderedDict[str, CacheItem] = collections.OrderedDict()

    def set_config(self, enabled: bool, max_items: int, hash_threshold: int):
        self.enabled = enabled
        self.max_items = max_items
        self.hash_threshold = hash_threshold

    def clear(self):
        """清空所有缓存（在更换模型、语言或预处理配置时触发）"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"翻译缓存已清空，丢弃旧记录数: {count}")

    def query(
        self,
        current_hash: str,
        source_lang: str,
        target_lang: str,
        ocr_model_id: str,
        translation_model_id: str,
        config_version: int,
    ) -> Optional[Tuple[List[Dict[str, Any]], int]]:
        """
        查询是否有符合条件的相近画面缓存
        返回: (items, min_distance) 或 None
        """
        if not self.enabled or not current_hash:
            return None

        # 遍历缓存中符合当前语言和模型配置的项
        # 优先查找汉明距离 <= threshold 的最近项
        best_item: Optional[CacheItem] = None
        min_dist = 999999
        matched_key = None

        for key, item in self._cache.items():
            if item.matches_config(
                source_lang,
                target_lang,
                ocr_model_id,
                translation_model_id,
                config_version,
            ):
                dist = hamming_distance(current_hash, item.image_hash)
                if dist <= self.hash_threshold and dist < min_dist:
                    min_dist = dist
                    best_item = item
                    matched_key = key
                    if dist == 0:
                        break

        if best_item is not None and matched_key is not None:
            # 标记为最近使用 (移至有序字典末尾)
            self._cache.move_to_end(matched_key)
            logger.debug(f"缓存命中! 汉明距离: {min_dist}/{self.hash_threshold}")
            return best_item.items, min_dist

        return None

    def put(
        self,
        image_hash: str,
        source_lang: str,
        target_lang: str,
        ocr_model_id: str,
        translation_model_id: str,
        config_version: int,
        items: List[Dict[str, Any]],
        timestamp: float,
    ):
        """保存新的识别与翻译结果"""
        if not self.enabled or not image_hash:
            return

        cache_key = (
            f"{image_hash}_{source_lang}_{target_lang}_{ocr_model_id}_"
            f"{translation_model_id}_v{config_version}"
        )

        item = CacheItem(
            image_hash=image_hash,
            source_lang=source_lang,
            target_lang=target_lang,
            ocr_model_id=ocr_model_id,
            translation_model_id=translation_model_id,
            config_version=config_version,
            items=items,
            timestamp=timestamp,
        )

        # 保持 LRU 上限
        if len(self._cache) >= self.max_items:
            # 移除最久未使用的项 (FIFO)
            self._cache.popitem(last=False)

        self._cache[cache_key] = item
        logger.debug(f"缓存已写入新记录 (当前总数: {len(self._cache)})")
