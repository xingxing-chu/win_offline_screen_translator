"""
Win11 离线屏幕实时翻译助手 - 多模型自动路由与健康熔断器
文件: model_router.py
功能: 
1. 监控各 OCR 引擎与翻译模型健康度与耗时，实现熔断保护 (Circuit Breaker)；
2. 语言与分辨率感知自动路由：根据源语言、屏幕分辨率、文字长度智能分流最优模型；
3. 故障平滑降级与无缝切换。
"""

import os
import sys
import time
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("ModelRouter")
logger.setLevel(logging.INFO)
logger.propagate = True


class EngineCircuitBreaker:
    """引擎熔断器：防止劣质或超长卡顿引擎 (如卡住45秒的PaddleX) 重复拖垮系统"""

    def __init__(self, failure_threshold: int = 2, cooldown_sec: float = 45.0, timeout_threshold_sec: float = 3.5):
        self.failure_threshold = failure_threshold
        self.cooldown_sec = cooldown_sec
        self.timeout_threshold_sec = timeout_threshold_sec

        self.failure_counts: Dict[str, int] = {}
        self.tripped_until: Dict[str, float] = {}
        self.latencies: Dict[str, List[float]] = {}

    def is_available(self, engine_id: str) -> bool:
        """检查引擎当前是否可用（未熔断或冷却期已过）"""
        now = time.time()
        trip_time = self.tripped_until.get(engine_id, 0.0)
        if trip_time > now:
            remaining = int(trip_time - now)
            logger.debug(f"引擎 [{engine_id}] 正处于熔断保护中，剩余冷静期: {remaining}s")
            return False
        return True

    def record_success(self, engine_id: str, latency_sec: float):
        """记录引擎成功调用"""
        self.failure_counts[engine_id] = 0
        if engine_id not in self.latencies:
            self.latencies[engine_id] = []
        self.latencies[engine_id].append(latency_sec)
        if len(self.latencies[engine_id]) > 20:
            self.latencies[engine_id].pop(0)

        # 若单次耗时过长超过阈值，也触发警惕
        if latency_sec > self.timeout_threshold_sec:
            logger.warning(f"引擎 [{engine_id}] 单次推理过慢 ({latency_sec:.2f}s > {self.timeout_threshold_sec}s)，记入耗时警告")

    def record_failure(self, engine_id: str, reason: str = ""):
        """记录引擎失败或超时"""
        cnt = self.failure_counts.get(engine_id, 0) + 1
        self.failure_counts[engine_id] = cnt
        logger.warning(f"引擎 [{engine_id}] 发生异常/空检出 (累计连续失败 {cnt} 次): {reason}")

        if cnt >= self.failure_threshold:
            trip_until = time.time() + self.cooldown_sec
            self.tripped_until[engine_id] = trip_until
            logger.error(
                f"🚨 引擎 [{engine_id}] 连续失败已达阈值 ({cnt} 次)，触发自动熔断保护！{self.cooldown_sec} 秒内将自动跳过该引擎"
            )


class ModelRouter:
    """多模型智能路由控制器"""

    def __init__(self):
        self.circuit_breaker = EngineCircuitBreaker()

    def route_ocr_pipeline(
        self,
        source_lang: str,
        configured_engine: str,
        screen_w: int,
        screen_h: int,
        auto_route: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        生成智能调度的 OCR 候选执行梯队流水线。
        返回结构: [{"engine": str, "use_raw_res": bool, "priority": int, "desc": str}]
        """
        pipeline: List[Dict[str, Any]] = []
        is_high_dpi = max(screen_w, screen_h) > 1920

        # 1. 智能首选主控引擎调度
        primary = configured_engine
        if primary in ("paddleocr_ch", "paddleocr"):
            # 特殊保护：若为 paddleocr，自动降低优先级防卡死
            primary = "win11_media_ocr" if sys.platform == "win32" else "rapidocr_ch"

        # 在 Windows 11 平台上，原生系统 OCR (win11_media_ocr) 具备底层系统免加载、0权重依赖与 30ms 极速特性
        # 若用户主动指定了 AI 视觉大模型 (Qwen2.5-VL / DocLM)，则以用户指定的 AI 视觉大模型为主
        if primary in ("qwen2.5-vl-3b-instruct", "doclm_ocr") and self.circuit_breaker.is_available(primary):
            pipeline.append({
                "engine": primary,
                "use_raw_res": False,
                "priority": 1,
                "desc": f"AI 视觉多模态大模型 OCR [{primary}]",
            })
        elif sys.platform == "win32" and auto_route and self.circuit_breaker.is_available("win11_media_ocr"):
            pipeline.append({
                "engine": "win11_media_ocr",
                "use_raw_res": False,
                "priority": 1,
                "desc": "Windows 11 原生极速 OCR (系统级免加载·首选加速)",
            })
            if primary != "win11_media_ocr" and self.circuit_breaker.is_available(primary):
                pipeline.append({
                    "engine": primary,
                    "use_raw_res": False,
                    "priority": 2,
                    "desc": f"配置主控引擎 [{primary}]",
                })
        else:
            if self.circuit_breaker.is_available(primary):
                pipeline.append({
                    "engine": primary,
                    "use_raw_res": False,
                    "priority": 1,
                    "desc": f"首选主控识别 [{primary}]",
                })

        # 2. 第二梯队：高性能轻量级引擎群
        norm_lang = (source_lang or "").lower()

        # Windows 11 原生 OCR 永远是第一备选（系统底层、30ms、零额外开销）
        if "win11_media_ocr" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("win11_media_ocr"):
                pipeline.append({
                    "engine": "win11_media_ocr",
                    "use_raw_res": False,
                    "priority": 2,
                    "desc": "Windows 11 原生极速 OCR (系统底层加速)",
                })

        # RapidOCR 是最稳定轻量的跨平台 ONNX 引擎
        if "rapidocr_ch" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("rapidocr_ch"):
                pipeline.append({
                    "engine": "rapidocr_ch",
                    "use_raw_res": False,
                    "priority": 3,
                    "desc": "RapidOCR ONNX 引擎 (稳定轻量)",
                })

        # 【新增备用方案 1】Tesseract 离线 OCR 引擎 (基于标准 tesseract.exe / pytesseract，高稳定性纯离线)
        if "tesseract_ocr" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("tesseract_ocr"):
                pipeline.append({
                    "engine": "tesseract_ocr",
                    "use_raw_res": False,
                    "priority": 4,
                    "desc": "Tesseract 离线 OCR 引擎 (国际标准/纯离线稳定备用)",
                })

        # 【新增备用方案 2】OpenCV 极速自适应形态学文本定位与兜底引擎 (100% 纯本地、零外部依赖、毫秒级响应、永不卡死)
        if "cv_contour_text_engine" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("cv_contour_text_engine"):
                pipeline.append({
                    "engine": "cv_contour_text_engine",
                    "use_raw_res": False,
                    "priority": 5,
                    "desc": "OpenCV 自适应形态学文本行定位引擎 (内置零依赖保底)",
                })

        # EasyOCR 针对多国语言（特别是西欧或日韩）识别率极佳
        if "easyocr_multi" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("easyocr_multi"):
                pipeline.append({
                    "engine": "easyocr_multi",
                    "use_raw_res": False,
                    "priority": 6,
                    "desc": "EasyOCR 多语言深度识别",
                })

        # 3. 第三梯队：针对高分屏 (4K/3840x2400) 的原始物理分辨率直推尝试
        if is_high_dpi and self.circuit_breaker.is_available("win11_media_ocr"):
            pipeline.append({
                "engine": "win11_media_ocr",
                "use_raw_res": True,
                "priority": 7,
                "desc": "Windows 11 原始 4K 无损分辨率直推 (防止微小字号丢失)",
            })

        # 4. 最终兜底：PaddleOCR (若未熔断)
        if "paddleocr_ch" not in [p["engine"] for p in pipeline]:
            if self.circuit_breaker.is_available("paddleocr_ch"):
                pipeline.append({
                    "engine": "paddleocr_ch",
                    "use_raw_res": False,
                    "priority": 8,
                    "desc": "PaddleOCR 兜底识别",
                })

        return pipeline

    def route_translation_model(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        configured_model_id: str,
        available_models: Dict[str, Any],
    ) -> str:
        """
        翻译模型智能路由：
        1. 检查配置的模型文件是否存在；若不存在自动路由到已安装就绪的备选模型；
        2. 根据字数与语言对自动优选最合适的引擎。
        """
        def check_model_ready(meta: Any) -> bool:
            if meta is None:
                return False
            is_ready_attr = getattr(meta, "is_ready", None)
            if callable(is_ready_attr):
                try:
                    return is_ready_attr()
                except Exception:
                    pass
            elif is_ready_attr is not None:
                return bool(is_ready_attr)

            exists_fn = getattr(meta, "exists_on_disk", None)
            if callable(exists_fn):
                try:
                    return exists_fn()
                except Exception:
                    pass
            return False

        # 1. 检查配置的模型是否准备就绪且未被熔断
        if self.circuit_breaker.is_available(configured_model_id):
            cfg_meta = available_models.get(configured_model_id)
            if cfg_meta and check_model_ready(cfg_meta):
                return configured_model_id
        else:
            logger.warning(f"配置的翻译模型 [{configured_model_id}] 正处于熔断保护或底层冲突中，自动调度其他健康模型...")

        # 2. 遍历其他可用模型寻找就绪且未熔断者
        for m_id, meta in available_models.items():
            if m_id != configured_model_id and self.circuit_breaker.is_available(m_id) and check_model_ready(meta):
                logger.info(f"翻译模型自动降级路由 -> [{m_id}] ({getattr(meta, 'name', m_id)})")
                return m_id

        # 3. 兜底返回原有 ID (系统会平滑调用纯离线智能词典翻译引擎)
        return configured_model_id


# 全局单例
global_model_router = ModelRouter()
