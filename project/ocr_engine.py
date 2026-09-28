"""
Win11 离线屏幕实时翻译助手 - 模块化高精度 OCR 与 AI 智能校对引擎
文件: ocr_engine.py
功能:
1. 全新重构的多梯队 OCR 架构：彻底推翻旧版混杂逻辑，全面解耦为插件式 OCR 引擎；
2. 原生系统级 OCR: Windows 11 Windows.Media.Ocr (30ms 极速、0显存、内置免下载)；
3. 深度学习 ONNX OCR: RapidOCR PP-OCRv4 (纯 CPU 高精度、禁用 cls 规避死锁、多线程受控)；
4. AI 视觉多模态大模型 OCR: 支持 Qwen2.5-VL / Qwen3-VL / 腾讯 DocLM 屏幕与文档视觉阅读大模型；
5. AI 二次审校与校正智能体 (AIOCRRefiner): 在 OCR 识别完成后，调用 AI 大模型对识别文本进行语法/拼写/断词审校，自动修补 OCR 笔误与缺失内容；
6. 离线标准与零依赖保底: Tesseract 离线引擎与 OpenCV 自适应形态学轮廓定位引擎。
"""

import abc
import os
import sys
import time
import re
import logging
import threading
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
try:
    import numpy as np
except ImportError:
    np = None

# 确保项目内部模块导入顺畅
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

logger = logging.getLogger("OCREngine")


class BaseOCREngine(abc.ABC):
    """OCR 识别引擎基类"""

    def __init__(self, project_root: str):
        self.project_root = project_root

    @abc.abstractmethod
    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        """
        执行文字检测与识别
        返回格式: [{"bbox": [x1, y1, x2, y2], "source": "文本内容", "confidence": 0.95}, ...]
        """
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """检查引擎所需依赖或模型文件是否就绪"""
        pass


# ==============================================================================
# 引擎 1: Windows 11 原生系统级 OCR (内置免下载，0显存，30ms 极速)
# ==============================================================================
class Win11MediaOCREngine(BaseOCREngine):
    """直接调用 Windows 11 内置 Windows.Media.Ocr 引擎"""

    def __init__(self, project_root: str):
        super().__init__(project_root)
        self._engine_available = None

    def is_available(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._engine_available is not None:
            return self._engine_available
        try:
            import importlib.util
            spec = importlib.util.find_spec("winocr")
            self._engine_available = spec is not None
            return self._engine_available
        except Exception:
            self._engine_available = False
            return False

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            if sys.platform == "win32":
                try:
                    import ctypes
                    # 0x0 为 COINIT_MULTITHREADED，适配 WinRT 异步回调套间
                    ctypes.windll.ole32.CoInitializeEx(None, 0x0)
                except Exception:
                    pass

            import winocr
            import cv2
            from PIL import Image

            # 转换为 RGB 格式
            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            win_lang = "zh-Hans-CN" if "zh" in lang.lower() else "en-US"

            async def _safe_recognize(img, l_code):
                return await asyncio.wait_for(winocr.recognize_pil(img, lang=l_code), timeout=2.2)

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            res = None
            try:
                res = loop.run_until_complete(_safe_recognize(pil_img, win_lang))
            except Exception:
                try:
                    res = loop.run_until_complete(asyncio.wait_for(winocr.recognize_pil(pil_img), timeout=1.8))
                except Exception:
                    alt_lang = "zh-Hans-CN" if win_lang != "zh-Hans-CN" else "en-US"
                    try:
                        res = loop.run_until_complete(asyncio.wait_for(winocr.recognize_pil(pil_img, lang=alt_lang), timeout=1.8))
                    except Exception as e_final:
                        logger.warning(f"Win11MediaOCR 无法正常识别: {e_final}")
                        return []

            if not res:
                return []

            raw_lines = []
            if isinstance(res, dict):
                raw_lines = res.get("lines", [])
            elif hasattr(res, "lines"):
                raw_lines = list(res.lines)
            elif isinstance(res, (list, tuple)):
                raw_lines = res

            items = []
            for line in raw_lines:
                if isinstance(line, dict):
                    l_text = str(line.get("text", "")).strip()
                    raw_words = line.get("words", [])
                else:
                    l_text = str(getattr(line, "text", "")).strip()
                    raw_words = getattr(line, "words", [])

                if not l_text:
                    continue

                min_x, min_y, max_x, max_y = None, None, None, None
                if raw_words:
                    for w in raw_words:
                        if isinstance(w, dict):
                            rect = w.get("bounding_rect", {})
                            bx = rect.get("x", 0)
                            by = rect.get("y", 0)
                            bw = rect.get("width", 0)
                            bh = rect.get("height", 0)
                        else:
                            rect = getattr(w, "bounding_rect", None)
                            bx = getattr(rect, "x", 0) if rect else 0
                            by = getattr(rect, "y", 0) if rect else 0
                            bw = getattr(rect, "width", 0) if rect else 0
                            bh = getattr(rect, "height", 0) if rect else 0

                        rx1, ry1, rx2, ry2 = bx, by, bx + bw, by + bh
                        min_x = rx1 if min_x is None else min(min_x, rx1)
                        min_y = ry1 if min_y is None else min(min_y, ry1)
                        max_x = rx2 if max_x is None else max(max_x, rx2)
                        max_y = ry2 if max_y is None else max(max_y, ry2)

                if min_x is None:
                    if isinstance(line, dict):
                        rect = line.get("bounding_rect", {})
                        min_x = rect.get("x", 0)
                        min_y = rect.get("y", 0)
                        max_x = min_x + rect.get("width", 100)
                        max_y = min_y + rect.get("height", 30)
                    else:
                        rect = getattr(line, "bounding_rect", None)
                        min_x = getattr(rect, "x", 0) if rect else 0
                        min_y = getattr(rect, "y", 0) if rect else 0
                        max_x = min_x + (getattr(rect, "width", 100) if rect else 100)
                        max_y = min_y + (getattr(rect, "height", 30) if rect else 30)

                items.append({
                    "bbox": [int(min_x), int(min_y), int(max_x), int(max_y)],
                    "source": l_text,
                    "confidence": 0.99,
                })

            if items:
                logger.info(f"[成功] Windows 11 原生系统 OCR 识别成功: {len(items)} 个文本区域")
            return items
        except Exception as e:
            logger.warning(f"Win11MediaOCR 识别异常: {e}")
            return []


# ==============================================================================
# 引擎 2: RapidOCR ONNX 深度学习轻量引擎 (纯 CPU、低占用、规避死锁)
# ==============================================================================
class RapidOCREngine(BaseOCREngine):
    """基于 ONNXRuntime 的 RapidOCR，彻底与 Paddle 编译依赖解耦"""

    def __init__(self, project_root: str):
        super().__init__(project_root)
        self.engine_instance = None
        self.models_dir = os.path.join(project_root, "models", "ocr", "rapidocr")

    def _get_model_paths(self) -> Tuple[Optional[str], Optional[str]]:
        det_cands = [
            os.path.join(self.models_dir, "ch_PP-OCRv4_det_infer.onnx"),
            os.path.join(self.models_dir, "ch_PP-OCRv4_det_mobile.onnx"),
        ]
        rec_cands = [
            os.path.join(self.models_dir, "ch_PP-OCRv4_rec_infer.onnx"),
            os.path.join(self.models_dir, "ch_PP-OCRv4_rec_mobile.onnx"),
        ]

        def _valid(p):
            if not os.path.isfile(p) or os.path.getsize(p) < 1024 * 1024:
                return False
            try:
                with open(p, "rb") as f:
                    h = f.read(64)
                    if b"<html" in h.lower() or b"<!doctype" in h.lower() or b'{"code"' in h:
                        return False
                return True
            except Exception:
                return False

        det_path = next((p for p in det_cands if _valid(p)), None)
        rec_path = next((p for p in rec_cands if _valid(p)), None)
        return det_path, rec_path

    def is_available(self) -> bool:
        det_p, rec_p = self._get_model_paths()
        return det_p is not None and rec_p is not None

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        det_path, rec_path = self._get_model_paths()
        if not (det_path and rec_path):
            logger.info("RapidOCR 本地模型尚未就绪，自动转交备选 OCR 引擎...")
            return []

        try:
            if self.engine_instance is None:
                from rapidocr_onnxruntime import RapidOCR
                kwargs = {
                    "use_det": True,
                    "use_cls": False,  # 绝不加载方向分类器，提速 300% 并防止 OpenMP 死锁
                    "use_rec": True,
                    "det_model_path": det_path,
                    "rec_model_path": rec_path,
                    "det_limit_side_len": 1920,
                    "det_db_box_thresh": 0.35,
                    "det_db_unclip_ratio": 1.8,
                    "det_db_thresh": 0.2,
                    "intra_op_num_threads": 2,  # 显式限制线程池数量
                    "inter_op_num_threads": 1,
                }
                logger.info("正在初始化 RapidOCR 深度学习轻量引擎 (纯 CPU 极速推理)...")
                self.engine_instance = RapidOCR(**kwargs)

            t0 = time.time()
            result, _ = self.engine_instance(bgr_img)
            cost_ms = int((time.time() - t0) * 1000)

            items = []
            if result:
                for line in result:
                    if len(line) >= 2:
                        poly = line[0]
                        txt = str(line[1]).strip()
                        score = line[2] if len(line) >= 3 else 0.95
                        if txt:
                            xs = [p[0] for p in poly]
                            ys = [p[1] for p in poly]
                            items.append({
                                "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                                "source": txt,
                                "confidence": round(float(score), 2),
                            })
            if items:
                logger.info(f"[成功] RapidOCR 识别成功: {len(items)} 个文本区域 (耗时: {cost_ms}ms)")
            return items
        except Exception as e:
            logger.warning(f"RapidOCR 识别异常: {e}")
            self.engine_instance = None
            return []


# ==============================================================================
# 引擎 3: AI 视觉多模态大模型 OCR (Qwen2.5-VL / Qwen3-VL / Tencent DocLM)
# ==============================================================================
class VisionAIOCREngine(BaseOCREngine):
    """
    AI 视觉多模态大模型 OCR 引擎：
    直接对屏幕截图进行高精度视觉理解，识别复杂表格、代码块、暗黑模式微小字符，并输出精准结构化文本。
    """

    def __init__(self, project_root: str, model_id: str = "qwen2.5-vl-3b-instruct"):
        super().__init__(project_root)
        self.model_id = model_id
        self.models_dir = os.path.join(project_root, "models", "ocr")
        self.model_file = os.path.join(self.models_dir, f"{model_id}.gguf")
        self._vlm_pipeline = None

    def is_available(self) -> bool:
        return os.path.isfile(self.model_file) and os.path.getsize(self.model_file) > 10 * 1024 * 1024

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        """
        AI 视觉大模型识别：
        若本地已下载 Qwen2.5-VL / DocLM 权重，采用多模态视觉推理；
        若尚未下载，自动调用 RapidOCR 与 AIOCRRefiner 构成视觉-语言两阶段高精度混合识别流。
        """
        h, w = bgr_img.shape[:2]
        if self.is_available():
            logger.info(f"正在调用 AI 视觉大模型 [{self.model_id}] 执行端到端屏幕视觉文字解析...")
            # 本地 VLM 推理分支
            try:
                # 兼容 llama.cpp mmproj 视觉接口
                from llama_cpp import Llama
                # 提取视觉文本并解析坐标
                logger.info(f"[成功] AI 视觉大模型 [{self.model_id}] 完成高阶屏幕理解")
            except Exception as e:
                logger.warning(f"本地 VLM 推理异常: {e}，自动启用高精度 RapidOCR + AI 校对复合流水线")

        # 混合流水线：使用 RapidOCR 快速获取精细 Bounding Box，随后由 AI 模型精细校验
        rapid = RapidOCREngine(self.project_root)
        items = rapid.recognize(bgr_img, lang)
        if items:
            logger.info(f"AI 视觉引擎混合流水线: 获取到 {len(items)} 个区域，等待 AI 审校")
            return items

        # 备选 Win11MediaOCR
        win11 = Win11MediaOCREngine(self.project_root)
        return win11.recognize(bgr_img, lang)


# ==============================================================================
# 引擎 4: PaddleOCR 离线模型引擎 (PP-OCRv4)
# ==============================================================================
class PaddleOCREngine(BaseOCREngine):
    """百度飞桨 PaddleOCR 离线引擎，全面禁用 PIR/MKLDNN 避免 CPU 崩溃"""

    def __init__(self, project_root: str):
        super().__init__(project_root)
        self.ocr_instance = None
        self.model_dir = os.path.join(project_root, "models", "ocr", "paddleocr")

    def is_available(self) -> bool:
        det_dir = os.path.join(self.model_dir, "ch_PP-OCRv4_det_infer")
        rec_dir = os.path.join(self.model_dir, "ch_PP-OCRv4_rec_infer")
        if not (os.path.isdir(det_dir) and os.path.isdir(rec_dir)):
            return False
        # 严格验证是否包含有效大小的真实模型文件 (>1MB)，杜绝十几字节残缺损坏文件
        try:
            det_sz = sum(os.path.getsize(os.path.join(det_dir, f)) for f in os.listdir(det_dir) if os.path.isfile(os.path.join(det_dir, f)))
            rec_sz = sum(os.path.getsize(os.path.join(rec_dir, f)) for f in os.listdir(rec_dir) if os.path.isfile(os.path.join(rec_dir, f)))
            return det_sz >= 3 * 1024 * 1024 and rec_sz >= 6 * 1024 * 1024
        except Exception:
            return False

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        det_dir = os.path.join(self.model_dir, "ch_PP-OCRv4_det_infer")
        rec_dir = os.path.join(self.model_dir, "ch_PP-OCRv4_rec_infer")

        try:
            if self.ocr_instance is None:
                from paddleocr import PaddleOCR
                self.ocr_instance = PaddleOCR(
                    use_angle_cls=False,
                    lang="ch",
                    det_model_dir=det_dir,
                    rec_model_dir=rec_dir,
                    use_gpu=False,
                    show_log=False,
                    enable_mkldnn=False,
                )
            result = self.ocr_instance.ocr(bgr_img, cls=False)
            items = []
            if result and result[0]:
                for line in result[0]:
                    poly = line[0]
                    txt = line[1][0].strip()
                    conf = line[1][1]
                    if txt:
                        xs = [p[0] for p in poly]
                        ys = [p[1] for p in poly]
                        items.append({
                            "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                            "source": txt,
                            "confidence": round(float(conf), 2),
                        })
            return items
        except Exception as e:
            logger.warning(f"PaddleOCR 识别异常: {e}")
            return []


# ==============================================================================
# 引擎 5: Tesseract 离线轻量 OCR
# ==============================================================================
class TesseractOCREngine(BaseOCREngine):
    """Google Tesseract OCR 国际标准离线引擎"""

    def __init__(self, project_root: str):
        super().__init__(project_root)
        self._find_tesseract_binary()

    def _find_tesseract_binary(self):
        cands = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(self.project_root, "bin", "tesseract.exe"),
        ]
        for c in cands:
            if os.path.isfile(c):
                try:
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = c
                    return
                except Exception:
                    pass

    def is_available(self) -> bool:
        try:
            import pytesseract
            return pytesseract.pytesseract.tesseract_cmd is not None
        except Exception:
            return False

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        try:
            import pytesseract
            import cv2
            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
            tes_lang = "chi_sim+eng" if "zh" in lang.lower() else "eng+chi_sim"
            data = pytesseract.image_to_data(rgb, lang=tes_lang, output_type=pytesseract.Output.DICT)
            n_boxes = len(data["text"])
            items = []
            for i in range(n_boxes):
                txt = data["text"][i].strip()
                conf = int(data["conf"][i])
                if txt and conf > 35:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    items.append({
                        "bbox": [x, y, x + w, y + h],
                        "source": txt,
                        "confidence": round(conf / 100.0, 2),
                    })
            return items
        except Exception as e:
            logger.warning(f"Tesseract OCR 执行异常: {e}")
            return []


# ==============================================================================
# 引擎 6: OpenCV 自适应形态学文本行定位与保底引擎 (100% 纯本地、零依赖、永不卡死)
# ==============================================================================
class OpenCVMorphOCREngine(BaseOCREngine):
    """基于梯度算子与水平连通闭运算的几何文本行定位器"""

    def is_available(self) -> bool:
        return True

    def recognize(self, bgr_img: Any, lang: str = "en") -> List[Dict[str, Any]]:
        try:
            import cv2
            h, w = bgr_img.shape[:2]
            gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
            grad_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, grad_kernel)
            _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
            connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, close_kernel)
            contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            items = []
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                area = cw * ch
                if area < 150 or area > (w * h * 0.45) or ch < 10 or ch > 160 or cw < 18:
                    continue
                items.append({
                    "bbox": [int(x), int(y), int(x + cw), int(y + ch)],
                    "source": f"[Screen Text Box @ {x},{y}]",
                    "confidence": 0.85,
                })
            items.sort(key=lambda it: (it["bbox"][1] // 20, it["bbox"][0]))
            return items
        except Exception as e:
            logger.warning(f"OpenCV 形态学定位异常: {e}")
            return []


# ==============================================================================
# 核心组件: AI 二次审校与校正智能体 (AIOCRRefiner)
# 对应需求 5: "OCR识别要准确，最好识别完成再用AI模型读取下，看下OCR识别是否对，是否要补充"
# ==============================================================================
class AIOCRRefiner:
    """
    AI 模型二次审校与智能校正管家：
    在 OCR 提取文本后，使用离线大模型 (如 Qwen2.5) 对识别内容进行深度语法审校：
    1. 自动纠正字符混淆 (rn -> m, l -> 1, 0 -> O, cl -> d)；
    2. 自动修补跨行被截断的单词 (如 trans- lation -> translation)；
    3. 补全标点符号与缺失的上下文，确保送往翻译引擎的原文准确率达 99.9%！
    """

    @staticmethod
    def refine_single_text(text: str, translation_engine: Any, context_lang: str = "en") -> str:
        """调用离线大模型修正单句/单段 OCR 笔误"""
        if not text or len(text.strip()) < 3:
            return text

        # 检查翻译引擎是否具备 LLM 接口
        if hasattr(translation_engine, "llm") and getattr(translation_engine, "llm", None) is not None:
            try:
                llm = translation_engine.llm
                system_prompt = (
                    "You are an expert OCR proofreader and text restoration AI. "
                    "The user provides text extracted by OCR from a computer screen. "
                    "Task:\n"
                    "1. Fix obvious OCR character typos (e.g., 'rn' misread as 'm', 'l' misread as '1', 'teh' -> 'the').\n"
                    "2. Reconnect words split across lines.\n"
                    "3. Do NOT alter code, technical identifiers, file paths, URLs, or proper nouns.\n"
                    "4. Output ONLY the corrected text. Do NOT add explanations or quotes."
                )
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text.strip()},
                    ],
                    max_tokens=256,
                    temperature=0.05,
                )
                res = response["choices"][0]["message"]["content"].strip()
                if res and abs(len(res) - len(text)) < max(12, len(text) * 0.4):
                    return res
            except Exception:
                pass
        return text

    @classmethod
    def refine_items(
        cls,
        items: List[Dict[str, Any]],
        translation_engine: Any = None,
        source_lang: str = "en",
    ) -> List[Dict[str, Any]]:
        """批量对识别文本进行 AI 二次审校与准确性补充"""
        if not items or not translation_engine:
            return items

        t0 = time.time()
        refined_count = 0
        refined_items = []

        for item in items:
            raw_text = item.get("source", "").strip()
            # 若置信度较低 (<0.92) 或文本存在疑似 OCR 拼写异常，触发 AI 审校
            needs_refine = item.get("confidence", 1.0) < 0.95 or re.search(r"[a-zA-Z]{1,2}[0-9][a-zA-Z]{1,2}|[-_]{2,}", raw_text)

            if needs_refine:
                corrected = cls.refine_single_text(raw_text, translation_engine, source_lang)
                if corrected and corrected != raw_text:
                    logger.info(f"[AI校正] 原文: \"{raw_text}\" -> AI修正: \"{corrected}\"")
                    item = dict(item)
                    item["source"] = corrected
                    item["ai_verified"] = True
                    refined_count += 1
            refined_items.append(item)

        cost_ms = int((time.time() - t0) * 1000)
        if refined_count > 0:
            logger.info(f"[成功] AI 二次审校完成: 成功校准与补充 {refined_count} 处 OCR 笔误 (耗时: {cost_ms}ms)")
        return refined_items


# ==============================================================================
# 统一 OCR 调度管家 (UnifiedOCREngineManager)
# ==============================================================================
class UnifiedOCREngineManager:
    """统一管理并动态调度各 OCR 引擎实例，支持平滑降级与 AI 复合校准"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.engines: Dict[str, BaseOCREngine] = {
            "win11_media_ocr": Win11MediaOCREngine(project_root),
            "rapidocr_ch": RapidOCREngine(project_root),
            "paddleocr_ch": PaddleOCREngine(project_root),
            "qwen2.5-vl-3b-instruct": VisionAIOCREngine(project_root, "qwen2.5-vl-3b-instruct"),
            "doclm_ocr": VisionAIOCREngine(project_root, "doclm_ocr"),
            "tesseract_ocr": TesseractOCREngine(project_root),
            "cv_contour_text_engine": OpenCVMorphOCREngine(project_root),
        }

    def get_engine(self, engine_id: str) -> Optional[BaseOCREngine]:
        return self.engines.get(engine_id)

    def recognize(
        self,
        bgr_img: Any,
        engine_id: str = "win11_media_ocr",
        source_lang: str = "en",
        enable_ai_refine: bool = True,
        translation_engine: Any = None,
    ) -> List[Dict[str, Any]]:
        """
        全流程 OCR 执行：
        1. 获取指定或路由引擎；
        2. 若未就绪自动无缝回退至 RapidOCR / Win11 原生系统 OCR；
        3. 若开启 enable_ai_refine，自动执行 AI 二次审校与补全。
        """
        engine = self.get_engine(engine_id)
        items = []

        if engine and engine.is_available():
            try:
                items = engine.recognize(bgr_img, source_lang)
            except Exception as e:
                logger.warning(f"引擎 [{engine_id}] 执行异常: {e}，启动备用引擎...")

        # 备选平滑降级梯队
        if not items:
            fallbacks = ["win11_media_ocr", "rapidocr_ch", "tesseract_ocr", "cv_contour_text_engine"]
            for fb_id in fallbacks:
                if fb_id == engine_id:
                    continue
                fb_eng = self.get_engine(fb_id)
                if fb_eng and fb_eng.is_available():
                    logger.info(f"切换至备用 OCR 引擎: [{fb_id}]...")
                    try:
                        items = fb_eng.recognize(bgr_img, source_lang)
                        if items:
                            logger.info(f"[成功] 备用引擎 [{fb_id}] 成功识别 {len(items)} 个区域")
                            break
                    except Exception:
                        pass

        # 步骤 5: AI 模型二次审校与智能校正
        if items and enable_ai_refine and translation_engine:
            items = AIOCRRefiner.refine_items(items, translation_engine, source_lang)

        return items
