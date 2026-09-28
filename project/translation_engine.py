"""
Win11 离线屏幕实时翻译助手 - 离线翻译引擎管理器
文件: translation_engine.py
功能: 统一封装 GGUF (llama-cpp-python)、CTranslate2 (OPUS-MT / MarianMT) 等离线翻译后端，
     支持模型目录自动扫描、元数据解析、语言对支持判定、模型懒加载及热重载。
"""

import abc
import json
import logging
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

# 安全导入 text_filter 模块，提供零依赖健壮兜底
try:
    from text_filter import clean_ocr_text, lookup_direct_dictionary
except Exception:
    def clean_ocr_text(text: str) -> str:
        if not text:
            return ""
        t = str(text).strip()
        t = re.sub(r"^\[\s*(?:译|Trans|翻译)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*\]$", "", t)
        return t.strip()

    def lookup_direct_dictionary(text: str, target_lang: str = "zh-CN") -> Optional[str]:
        return None

logger = logging.getLogger(__name__)


class ModelMetadata:
    """模型元数据描述对象，解析自 model_info.json"""

    def __init__(self, data: Dict[str, Any], root_dir: str, base_dir: Optional[str] = None):
        self.id = data.get("id", "")
        self.name = data.get("name", self.id)
        self.engine = data.get("engine", "llama_cpp")  # "llama_cpp", "ctranslate2", "paddleocr"
        self.root_dir = root_dir
        self.base_dir = base_dir or root_dir
        self.raw_path = data.get("path", "")
        self.model_path = self._resolve_path(self.raw_path)

        self.source_languages = data.get("source_languages", ["en", "zh-CN"])
        self.target_languages = data.get("target_languages", ["en", "zh-CN"])
        self.default_source = data.get("default_source", "en")
        self.default_target = data.get("default_target", "zh-CN")
        self.description = data.get("description", "")
        self.raw_data = data

    def _resolve_path(self, raw_path: str) -> str:
        if not raw_path:
            return ""
        if os.path.isabs(raw_path):
            return os.path.normpath(raw_path)

        # 智能多候选路径探测列表
        candidates = [
            os.path.normpath(os.path.join(self.base_dir, raw_path)),
            os.path.normpath(os.path.join(self.root_dir, "models", "translation", raw_path)),
            os.path.normpath(os.path.join(self.root_dir, "models", "ocr", raw_path)),
            os.path.normpath(os.path.join(self.root_dir, raw_path)),
            os.path.normpath(os.path.join(self.base_dir, os.path.basename(raw_path))),
            os.path.normpath(os.path.join(self.root_dir, "models", "translation", os.path.basename(raw_path))),
            os.path.normpath(os.path.join(self.root_dir, "models", "ocr", os.path.basename(raw_path))),
        ]

        # 优先选择物理磁盘上确实存在的路径
        for cand in candidates:
            if os.path.exists(cand):
                return cand

        # 若尚未落盘，给出最合理的预期落盘规范位置
        if raw_path.lower().endswith(".gguf") or self.engine == "llama_cpp":
            return os.path.normpath(os.path.join(self.root_dir, "models", "translation", os.path.basename(raw_path)))
        if self.engine in ("paddleocr", "rapidocr", "easyocr", "tesseract"):
            return os.path.normpath(os.path.join(self.root_dir, "models", "ocr", os.path.basename(raw_path)))

        return candidates[0]

    def supports_pair(self, source_lang: str, target_lang: str) -> bool:
        """检查此模型是否支持指定的源语言和目标语言"""
        # 源语言若是 auto，只要目标语言在 target_languages 中即视为潜在支持
        if source_lang == "auto":
            return target_lang in self.target_languages

        s_match = any(self._lang_match(source_lang, s) for s in self.source_languages)
        t_match = any(self._lang_match(target_lang, t) for t in self.target_languages)
        return s_match and t_match

    @staticmethod
    def _lang_match(user_lang: str, model_lang: str) -> bool:
        """归一化语言代码匹配，如 zh-CN 匹配 zh 或 zh-CN，en 匹配 en-US"""
        u = user_lang.lower().replace("_", "-")
        m = model_lang.lower().replace("_", "-")
        if u == m:
            return True
        if u.startswith("zh") and m.startswith("zh"):
            return True
        if u.startswith("en") and m.startswith("en"):
            return True
        return False

    def exists_on_disk(self) -> bool:
        """检查模型文件或目录是否存在于磁盘（支持动态智能探测）"""
        if self.model_path and os.path.exists(self.model_path):
            return True
        # 重新触发一次动态探测（应对主进程在运行时刚完成下载落盘的场景）
        if self.raw_path:
            rechecked = self._resolve_path(self.raw_path)
            if rechecked and os.path.exists(rechecked):
                self.model_path = rechecked
                return True
        return False

    def is_ready(self) -> bool:
        """检查模型是否准备就绪（存在于磁盘上且文件/目录非空，且包含有效模型权重）"""
        if not self.exists_on_disk():
            return False
        try:
            # 针对不同引擎类型严格校验实际核心权重文件
            if self.engine == "ctranslate2":
                if os.path.isdir(self.model_path):
                    # 必须包含 model.bin 或 shared_vocabulary.json 等核心权重，不能仅有 model_info.json
                    has_model_bin = any(
                        f.lower().endswith(".bin") or f.lower() == "model.bin" or f.lower().endswith(".safetensors")
                        for f in os.listdir(self.model_path)
                    )
                    return has_model_bin
                return False
            elif self.engine == "llama_cpp" or (self.model_path and self.model_path.lower().endswith(".gguf")):
                if os.path.isfile(self.model_path):
                    return os.path.getsize(self.model_path) > 10 * 1024 * 1024  # > 10MB
                return False
            elif self.engine == "paddleocr":
                det_d = os.path.join(self.model_path, "ch_PP-OCRv4_det_infer")
                rec_d = os.path.join(self.model_path, "ch_PP-OCRv4_rec_infer")
                if not (os.path.isdir(det_d) and os.path.isdir(rec_d)):
                    return False
                try:
                    det_sz = sum(os.path.getsize(os.path.join(det_d, f)) for f in os.listdir(det_d) if os.path.isfile(os.path.join(det_d, f)))
                    rec_sz = sum(os.path.getsize(os.path.join(rec_d, f)) for f in os.listdir(rec_d) if os.path.isfile(os.path.join(rec_d, f)))
                    return det_sz >= 3 * 1024 * 1024 and rec_sz >= 6 * 1024 * 1024
                except Exception:
                    return False
            elif self.engine == "rapidocr":
                det_f = os.path.join(self.model_path, "ch_PP-OCRv4_det_infer.onnx")
                rec_f = os.path.join(self.model_path, "ch_PP-OCRv4_rec_infer.onnx")
                return (
                    os.path.isfile(det_f) and os.path.getsize(det_f) > 2 * 1024 * 1024 and
                    os.path.isfile(rec_f) and os.path.getsize(rec_f) > 5 * 1024 * 1024
                )
            elif self.engine == "winocr":
                import importlib.util
                return importlib.util.find_spec("winocr") is not None and sys.platform == "win32"
            elif os.path.isdir(self.model_path):
                # 排除仅有元数据文件
                valid_files = [f for f in os.listdir(self.model_path) if f.lower() not in ("model_info.json", "readme.md", ".gitkeep")]
                return len(valid_files) > 0
            elif os.path.isfile(self.model_path):
                return os.path.getsize(self.model_path) > 1024
        except Exception:
            return False
        return True


class BaseTranslator(abc.ABC):
    """离线翻译器抽象基类"""

    def __init__(self, metadata: ModelMetadata):
        self.metadata = metadata
        self.is_loaded = False

    @abc.abstractmethod
    def load(self):
        """懒加载模型权重到内存/显存"""
        pass

    @abc.abstractmethod
    def unload(self):
        """释放模型权重"""
        pass

    @abc.abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """执行单条/多行文本翻译"""
        pass

    def _fallback_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """纯本地高质量离线翻译内核，当神经网络引擎不可用时平滑接管所有文本翻译"""
        cleaned = clean_ocr_text(text)
        try:
            from text_filter import intelligent_offline_translate
            return intelligent_offline_translate(cleaned, target_lang=target_lang)
        except Exception as e:
            logger.error(f"智能离线翻译内核异常: {e}")
            return cleaned


class LlamaCppTranslator(BaseTranslator):
    """
    基于 llama-cpp-python 的 GGUF 翻译器 (如 Qwen2.5-1.5B-Instruct-Q4_K_M)。
    利用精炼的提示词实现高质量的中英双向与多语种互译。
    """

    def __init__(self, metadata: ModelMetadata, n_ctx: int = 2048, n_threads: int = 4):
        super().__init__(metadata)
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.llm = None

    def load(self):
        if self.is_loaded and self.llm is not None:
            return

        # 动态二次探测磁盘，防止下载完成瞬间的路径或状态延迟
        if not self.metadata.exists_on_disk():
            logger.warning(
                f"⚠️ 离线翻译模型文件未就绪: {self.metadata.model_path}\n"
                f"   [提示] 请根据部署指南将 GGUF 权重放入 models/translation 目录。\n"
                f"   系统当前已平滑启用内置离线直译兜底保护，确保屏幕取词与界面交互不中断。"
            )
            self.llm = None
            self.is_loaded = True
            return

        logger.info(f"正在懒加载 GGUF 翻译模型: {self.metadata.name} ({self.metadata.model_path})")
        
        # 安全防御配置：优先通过纯 CPU 沙箱环境加载，杜绝 CUDA 驱动缺失或版本不匹配引发的 0x00000000 内存越界崩溃
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        os.environ["GGML_CUDA_DISABLE"] = "1"
        os.environ["LLAMA_NO_CUBLAS"] = "1"

        try:
            from llama_cpp import Llama

            # 显式指定 n_gpu_layers=0 强制纯 CPU 推理，避免底层驱动空指针异常
            self.llm = Llama(
                model_path=self.metadata.model_path,
                n_gpu_layers=0,
                n_ctx=min(2048, self.n_ctx),
                n_threads=max(1, min(4, self.n_threads)),
                verbose=False,
            )
            self.is_loaded = True
            logger.info("[成功] GGUF 翻译模型加载成功 (CPU 纯净安全模式)")
        except ImportError:
            logger.warning("未安装 llama-cpp-python，自动平滑启用纯离线智能词典与短语翻译引擎")
            self.llm = None
            self.is_loaded = True
        except (Exception, OSError) as e:
            logger.warning(
                f"加载 GGUF 翻译模型底层库异常: {e}\n"
                f"⚠️ 检测到系统安装的 llama-cpp-python 与当前 Python 环境/硬件指令集存在底层兼容性冲突。\n"
                f"系统已自动激活纯离线高可靠智能词典与短语翻译引擎，保障屏幕取词与实时翻译绝对不中断。"
            )
            self.llm = None
            self.is_loaded = True
            # 记录到引擎健康熔断器
            try:
                from model_router import global_model_router
                global_model_router.circuit_breaker.record_failure(self.metadata.id, str(e))
            except Exception:
                pass

    def unload(self):
        if self.llm is not None:
            del self.llm
            self.llm = None
        self.is_loaded = False
        logger.info("GGUF 翻译模型已卸载")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        cleaned = clean_ocr_text(text)
        if not cleaned:
            return ""

        # 优先通过专精 UI 词典直译（0延迟，无语病）
        direct = lookup_direct_dictionary(cleaned, target_lang)
        if direct:
            return direct

        if not self.is_loaded:
            self.load()

        # 映射规范语言名称
        lang_name_map = {
            "zh-CN": "Simplified Chinese",
            "zh": "Simplified Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
        }
        target_name = lang_name_map.get(target_lang, target_lang)

        # 构建专为屏幕 UI 润色翻译的高阶 System Prompt
        system_prompt = (
            f"You are a professional offline screen UI translation engine. "
            f"Translate the provided user interface text into natural, fluent {target_name}. "
            f"Guidelines:\n"
            f"1. Preserve technical proper nouns, commands, paths, and brand names (e.g. Python, pip, IDLE, Tcl/Tk, Windows, GitHub).\n"
            f"2. Automatically repair minor OCR spacing or spelling typos.\n"
            f"3. Translate into authentic, human-like UI terminology.\n"
            f"4. Output ONLY the translated text without quotes, notes, or explanations."
        )

        if self.llm is not None:
            try:
                # 兼容 Chat 模式 (Qwen2.5 模板)
                response = self.llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": cleaned},
                    ],
                    max_tokens=512,
                    temperature=0.1,
                    top_p=0.9,
                    repeat_penalty=1.1,
                )
                output = response["choices"][0]["message"]["content"].strip()
                # 移除可能的多余外层引号与标签
                output = re.sub(r'^["\'「」『』\[\]]+|["\'「」『』\[\]]+$', '', output).strip()
                output = clean_ocr_text(output)
                if output and output.lower() != cleaned.lower():
                    return output
            except Exception as e:
                logger.error(f"LlamaCpp 翻译异常: {e}")

        # 离线保底方案：激活高可靠离线翻译内核 (纯本地智能短语词典)
        return self._fallback_translate(cleaned, source_lang, target_lang)

    def _fallback_translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """纯本地高质量离线翻译内核，当大模型未加载时平滑接管所有文本翻译"""
        cleaned = clean_ocr_text(text)
        try:
            from text_filter import intelligent_offline_translate
            return intelligent_offline_translate(cleaned, target_lang=target_lang)
        except Exception as e:
            logger.error(f"智能离线翻译内核异常: {e}")
            return cleaned


class CTranslate2Translator(BaseTranslator):
    """
    基于 CTranslate2 的翻译器 (如 OPUS-MT / MarianMT)。
    极高 CPU/GPU 推理效率，模型体积小 (约 150MB~300MB)。
    """

    def __init__(self, metadata: ModelMetadata):
        super().__init__(metadata)
        self.translator = None
        self.tokenizer = None

    def load(self):
        if self.is_loaded:
            return

        if not self.metadata.is_ready():
            logger.warning(
                f"⚠️ CTranslate2 模型核心权重文件 (model.bin) 尚未就绪: {self.metadata.model_path}\n"
                f"   系统当前已自动平滑启用内置离线直译智能兜底，确保屏幕取词与交互不中断。"
            )
            self.translator = None
            self.tokenizer = None
            self.is_loaded = True
            return

        logger.info(f"正在懒加载 CTranslate2 翻译模型: {self.metadata.name} ({self.metadata.model_path})")
        try:
            import ctranslate2
            import transformers

            self.translator = ctranslate2.Translator(
                self.metadata.model_path,
                device="cpu",
                intra_threads=4,
            )
            # 尝试加载配套的分词器
            self.tokenizer = transformers.AutoTokenizer.from_pretrained(
                self.metadata.model_path,
                local_files_only=True,
            )
            self.is_loaded = True
            logger.info("CTranslate2 模型与分词器加载成功")
        except ImportError:
            logger.warning("未安装 ctranslate2 或 transformers，启用内置回退策略")
            self.translator = None
            self.tokenizer = None
            self.is_loaded = True
        except (Exception, OSError) as e:
            logger.warning(f"加载 CTranslate2 模型失败: {e}，自动启用高可靠离线智能词典翻译引擎")
            self.translator = None
            self.tokenizer = None
            self.is_loaded = True

    def unload(self):
        if self.translator is not None:
            del self.translator
            self.translator = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self.is_loaded = False
        logger.info("CTranslate2 翻译模型已卸载")

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not text or not text.strip():
            return ""

        if not self.is_loaded:
            self.load()

        if self.translator is not None and self.tokenizer is not None:
            try:
                tokens = self.tokenizer.convert_ids_to_tokens(
                    self.tokenizer.encode(text.strip())
                )
                results = self.translator.translate_batch([tokens])
                output_tokens = results[0].hypotheses[0]
                out_txt = self.tokenizer.decode(self.tokenizer.convert_tokens_to_ids(output_tokens)).strip()
                if out_txt and out_txt.lower() != text.strip().lower():
                    return out_txt
            except Exception as e:
                logger.error(f"CTranslate2 翻译异常: {e}")

        # 离线词典智能兜底
        return self._fallback_translate(text, source_lang, target_lang)


class TranslationModelManager:
    """
    模型管理器：负责扫描 models/ 目录下的所有模型描述文件，
    维护模型元数据清单、支持按模型 ID 查找与动态实例化。
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.ocr_models_dir = os.path.join(project_root, "models", "ocr")
        self.translation_models_dir = os.path.join(project_root, "models", "translation")
        self.ocr_models: Dict[str, ModelMetadata] = {}
        self.translation_models: Dict[str, ModelMetadata] = {}
        self._active_translator: Optional[BaseTranslator] = None
        self._active_model_id: Optional[str] = None

    def scan_models(self):
        """扫描 models/ocr 和 models/translation 目录，解析 model_info.json"""
        self.ocr_models.clear()
        self.translation_models.clear()

        # 1. 扫描 OCR 模型
        if os.path.exists(self.ocr_models_dir):
            for root, dirs, files in os.walk(self.ocr_models_dir):
                if "model_info.json" in files:
                    info_path = os.path.join(root, "model_info.json")
                    meta = self._parse_model_info(info_path, self.project_root)
                    if meta:
                        self.ocr_models[meta.id] = meta
                        logger.info(f"发现 OCR 模型: {meta.name} (ID: {meta.id})")

        # 2. 扫描翻译模型
        if os.path.exists(self.translation_models_dir):
            for root, dirs, files in os.walk(self.translation_models_dir):
                if "model_info.json" in files:
                    info_path = os.path.join(root, "model_info.json")
                    meta = self._parse_model_info(info_path, self.project_root)
                    if meta:
                        self.translation_models[meta.id] = meta
                        logger.info(f"发现翻译模型: {meta.name} (ID: {meta.id})")

            # 动态热插拔扫描：自动将 models/translation/ 下任意 .gguf 文件注册为模型
            for fname in os.listdir(self.translation_models_dir):
                if fname.lower().endswith(".gguf"):
                    m_id = os.path.splitext(fname)[0]
                    if m_id not in self.translation_models:
                        custom_meta = {
                            "id": m_id,
                            "name": f"自定义 GGUF: {fname}",
                            "engine": "llama_cpp",
                            "path": os.path.join("models", "translation", fname),
                            "source_languages": ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"],
                            "target_languages": ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"],
                            "default_source": "en",
                            "default_target": "zh-CN",
                            "description": f"自动扫描发现的本地 GGUF 大模型: {fname}",
                        }
                        self.translation_models[m_id] = ModelMetadata(custom_meta, self.project_root)
                        logger.info(f"自动注册本地 GGUF 翻译模型: {fname} (ID: {m_id})")

        # 注入默认规范配置，以便开箱即用与在界面中方便切换
        self._register_default_ocr_models()
        self._register_default_translation_models()

    def _parse_model_info(self, file_path: str, root_dir: str) -> Optional[ModelMetadata]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            base_dir = os.path.dirname(os.path.abspath(file_path))
            return ModelMetadata(data, root_dir, base_dir=base_dir)
        except Exception as e:
            logger.error(f"解析模型描述文件失败 {file_path}: {e}")
            return None

    def _register_default_ocr_models(self):
        """注册支持的 OCR 引擎清单 (Windows 11 原生 OCR, RapidOCR, EasyOCR, Tesseract, PaddleOCR)"""
        ocr_presets = [
            {
                "id": "win11_media_ocr",
                "name": "Windows 11 原生系统 OCR (首选推荐·免下载·0显存·毫秒级)",
                "engine": "winocr",
                "path": "",
                "languages": ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"],
                "description": "Win11 内置多语种离线 OCR，0 显存占用，30ms 极速响应，屏幕截屏无畸变识别",
            },
            {
                "id": "rapidocr_ch",
                "name": "RapidOCR ONNX 极速引擎 (推荐·自动下载模型·纯CPU高效)",
                "engine": "rapidocr",
                "path": "",
                "languages": ["en", "zh-CN"],
                "description": "基于 ONNXRuntime 的轻量高效 OCR，自带轻量模型，彻底解耦 Paddle",
            },
            {
                "id": "easyocr_multi",
                "name": "EasyOCR 国际化多语种 OCR (支持中/英/日/韩/西/法/德/俄)",
                "engine": "easyocr",
                "path": "",
                "languages": ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"],
                "description": "国际主流 OCR 引擎，首次使用自动下载 PyTorch 离线识别权重",
            },
            {
                "id": "tesseract_ocr",
                "name": "Tesseract OCR (开源标准·轻量级文本识别)",
                "engine": "tesseract",
                "path": "",
                "languages": ["en", "zh-CN"],
                "description": "Google 开源成熟 OCR 引擎",
            },
            {
                "id": "qwen2.5-vl-3b-instruct",
                "name": "Qwen2.5-VL 3B 视觉大模型 AI OCR (阿里通义·端到端屏幕图文识别)",
                "engine": "vlm",
                "path": "models/ocr/qwen2.5-vl-3b-instruct.gguf",
                "languages": ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"],
                "description": "阿里开源多模态视觉大模型 (VLM)，直接端到端理解屏幕截屏、暗黑界面与复杂图表",
            },
            {
                "id": "doclm_ocr",
                "name": "腾讯 DocLM 屏幕与文档视觉大模型 OCR (腾讯·高难排版专精)",
                "engine": "vlm",
                "path": "models/ocr/doclm-screen-ocr.gguf",
                "languages": ["en", "zh-CN", "ja", "ko"],
                "description": "腾讯深度优化的文档与屏幕排版视觉大模型，专精表格/代码/低对比度界面解析",
            },
            {
                "id": "paddleocr_ch",
                "name": "PaddleOCR 离线模型 (传统备选·已关闭 UVDoc)",
                "engine": "paddleocr",
                "path": "models/ocr/paddleocr",
                "languages": ["en", "zh-CN"],
                "description": "百度飞桨 PP-OCR 模型（已做自适应缩放与畸变禁用优化）",
            },
        ]
        for item in ocr_presets:
            if item["id"] not in self.ocr_models:
                self.ocr_models[item["id"]] = ModelMetadata(item, self.project_root)

    def _register_default_translation_models(self):
        """注册丰富的 AI 翻译大模型与专用轻量翻译模型矩阵"""
        all_langs = ["en", "zh-CN", "ja", "ko", "fr", "de", "es", "ru"]
        trans_presets = [
            {
                "id": "qwen2.5-1.5b-instruct-q4_k_m",
                "name": "Qwen2.5 1.5B (GGUF, ~1.1GB, 均衡推荐)",
                "engine": "llama_cpp",
                "path": "models/translation/qwen2.5-1.5b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "阿里通义千问 2.5 1.5B，推理速度与翻译质量俱佳",
            },
            {
                "id": "qwen2.5-0.5b-instruct-q4_k_m",
                "name": "Qwen2.5 0.5B (GGUF, ~350MB, 老旧CPU极速)",
                "engine": "llama_cpp",
                "path": "models/translation/qwen2.5-0.5b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "轻量级小钢炮，内存占用极低，低配置电脑首选",
            },
            {
                "id": "qwen2.5-3b-instruct-q4_k_m",
                "name": "Qwen2.5 3B (GGUF, ~2.0GB, 高精度翻译)",
                "engine": "llama_cpp",
                "path": "models/translation/qwen2.5-3b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "30亿参数高精度模型，复杂句式与地道术语表达极优",
            },
            {
                "id": "qwen2.5-7b-instruct-q4_k_m",
                "name": "Qwen2.5 7B (GGUF, ~4.5GB, 旗舰级文学翻译)",
                "engine": "llama_cpp",
                "path": "models/translation/qwen2.5-7b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "顶级开源大模型，翻译信达雅，适合配备独立显卡或强力CPU",
            },
            {
                "id": "llama-3.2-1b-instruct-q4_k_m",
                "name": "LLaMA 3.2 1B (GGUF, ~1.3GB, Meta轻量模型)",
                "engine": "llama_cpp",
                "path": "models/translation/llama-3.2-1b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "Meta 最新推出的轻量端侧模型",
            },
            {
                "id": "llama-3.2-3b-instruct-q4_k_m",
                "name": "LLaMA 3.2 3B (GGUF, ~2.0GB, Meta中量级模型)",
                "engine": "llama_cpp",
                "path": "models/translation/llama-3.2-3b-instruct-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "Meta 30亿参数模型，英文理解深度卓越",
            },
            {
                "id": "gemma-2-2b-it-q4_k_m",
                "name": "Google Gemma 2 2B (GGUF, ~1.6GB)",
                "engine": "llama_cpp",
                "path": "models/translation/gemma-2-2b-it-q4_k_m.gguf",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "Google 出品的轻量多语言模型",
            },
            {
                "id": "opus-mt-en-zh-ct2",
                "name": "OPUS-MT 英译中 (CTranslate2, ~150MB, 极速专精)",
                "engine": "ctranslate2",
                "path": "models/translation/opus-mt-en-zh-ct2",
                "source_languages": ["en"],
                "target_languages": ["zh-CN"],
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "赫尔辛基大学专业机器翻译模型，CTranslate2 纯CPU极速推理",
            },
            {
                "id": "opus-mt-zh-en-ct2",
                "name": "OPUS-MT 中译英 (CTranslate2, ~150MB, 极速专精)",
                "engine": "ctranslate2",
                "path": "models/translation/opus-mt-zh-en-ct2",
                "source_languages": ["zh-CN"],
                "target_languages": ["en"],
                "default_source": "zh-CN",
                "default_target": "en",
                "description": "轻量级高效率中译英专用模型",
            },
            {
                "id": "nllb-200-distilled-600M-ct2",
                "name": "Meta NLLB-200 (CTranslate2, ~600MB, 200种语言全能)",
                "engine": "ctranslate2",
                "path": "models/translation/nllb-200-distilled-600M-ct2",
                "source_languages": all_langs,
                "target_languages": all_langs,
                "default_source": "en",
                "default_target": "zh-CN",
                "description": "Meta 无语言障碍计划 200 种语言互译精简版",
            },
        ]
        for item in trans_presets:
            if item["id"] not in self.translation_models:
                self.translation_models[item["id"]] = ModelMetadata(item, self.project_root)

    def get_translation_model(self, model_id: str) -> Optional[ModelMetadata]:
        return self.translation_models.get(model_id)

    def get_ocr_model(self, model_id: str) -> Optional[ModelMetadata]:
        return self.ocr_models.get(model_id)

    def get_or_create_translator(self, model_id: str) -> BaseTranslator:
        """获取或创建指定 ID 的翻译器实例（懒加载模式）"""
        if self._active_translator is not None and self._active_model_id == model_id:
            return self._active_translator

        # 更换模型：先卸载旧模型释放资源
        if self._active_translator is not None:
            logger.info(f"卸载旧翻译模型: {self._active_model_id}")
            self._active_translator.unload()
            self._active_translator = None
            self._active_model_id = None

        meta = self.get_translation_model(model_id)
        if not meta:
            raise ValueError(f"未找到指定的翻译模型: {model_id}")

        if meta.engine == "llama_cpp":
            translator = LlamaCppTranslator(meta)
        elif meta.engine == "ctranslate2":
            translator = CTranslate2Translator(meta)
        else:
            raise ValueError(f"不支持的翻译引擎类型: {meta.engine}")

        self._active_translator = translator
        self._active_model_id = model_id
        return translator
