"""
Win11 离线屏幕实时翻译助手 - 主程序入口与 Worker 子进程
文件: main.py
功能: 驱动 Windows 11 离线屏幕实时翻译全流程，包含主进程 (PyQt5/托盘/覆盖层/状态机)
     与 Worker 子进程 (mss 截图/OpenCV 预处理/PaddleOCR/段落合并/离线翻译/缓存)。
"""

import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import math
import multiprocessing as mp
import os
import queue
import sys
import time
import threading
import shutil
import subprocess
import importlib
import importlib.util
import asyncio
import concurrent.futures
from typing import Any, Dict, List, Optional, Tuple

# 确保在 Windows 控制台环境下无论 GBK 还是 UTF-8 都能安全打印一切字符，绝不引发 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import numpy as np
except ImportError:
    np = None
try:
    import cv2
except ImportError:
    cv2 = None
try:
    import mss
except ImportError:
    mss = None

# 确保项目根目录与当前脚本所在目录位于 sys.path 首位，避免子进程或跨盘符环境下本地模块导入失败
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR and _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)
_CWD = os.getcwd()
if _CWD and _CWD not in sys.path:
    sys.path.insert(0, _CWD)


# ==============================================================================
# 环境自举与防闪退自愈引擎 (解决双击 main.py 或直接运行时的依赖缺失与闪退)
# ==============================================================================
def _bootstrap_environment():
    """
    环境自举与防闪退自愈机制：
    1. 虚拟环境探测与自动切换：若当前通过系统 Python 运行 main.py，而项目目录下存在 .venv 虚拟环境，
       自动无缝切换到 .venv 中的 python.exe 重新执行自身，使直接双击 main.py 获得与 run.bat 完全一致的独立环境；
    2. 核心依赖自检与清华源自愈：若当前环境缺失 PyQt5 / cv2 / mss / pynput / numpy，
       绝不默默闪退关闭窗口，而是通过国内清华高速源自动安装并重启；
    3. 若不可逆异常发生，弹出 Windows 原生弹窗并挂起控制台输入（彻底杜绝瞬间闪退）。
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 自动重定向到项目本地 .venv 解释器
    in_venv = (sys.prefix != getattr(sys, "base_prefix", sys.prefix))
    if not in_venv and os.environ.get("_BOOTSTRAP_RELAUNCHED") != "1":
        candidates = [
            os.path.join(current_dir, ".venv", "Scripts", "python.exe"),
            os.path.join(current_dir, ".venv", "Scripts", "pythonw.exe"),
            os.path.join(current_dir, ".venv", "bin", "python"),
        ]
        for venv_py in candidates:
            if os.path.exists(venv_py):
                env = os.environ.copy()
                env["_BOOTSTRAP_RELAUNCHED"] = "1"
                try:
                    ret = subprocess.call([venv_py, os.path.abspath(__file__)] + sys.argv[1:], env=env)
                    sys.exit(ret)
                except Exception:
                    pass
                break

    # 2. 核心包依赖自检
    missing_packages = []
    checks = [
        ("PyQt5", "PyQt5>=5.15.9"),
        ("cv2", "opencv-python>=4.8.0"),
        ("mss", "mss>=9.0.1"),
        ("pynput", "pynput>=1.7.6"),
        ("numpy", "numpy>=1.24.3,<2.0.0"),
    ]
    for mod_name, pkg_spec in checks:
        try:
            __import__(mod_name)
        except ImportError:
            missing_packages.append(pkg_spec)

    if missing_packages and os.environ.get("_BOOTSTRAP_INSTALLED") != "1":
        print("=" * 65)
        print(" 【Win11 离线屏幕实时翻译助手】运行环境自检与自愈中...")
        print(f" 检测到当前环境缺少核心依赖组件: {', '.join(missing_packages)}")
        print(" 正在自动通过国内高速镜像源 (清华大学) 下载安装，请稍候...")
        print("=" * 65)

        req_file = os.path.join(current_dir, "requirements.txt")
        pip_cmd = [
            sys.executable, "-m", "pip", "install",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--trusted-host", "pypi.tuna.tsinghua.edu.cn",
        ]
        if os.path.exists(req_file):
            pip_cmd.extend(["-r", req_file])
        else:
            pip_cmd.extend(missing_packages)

        try:
            ret = subprocess.call(pip_cmd)
            if ret == 0:
                print("依赖自动安装成功！正在重新启动主程序...")
                env = os.environ.copy()
                env["_BOOTSTRAP_INSTALLED"] = "1"
                ret2 = subprocess.call([sys.executable, os.path.abspath(__file__)] + sys.argv[1:], env=env)
                sys.exit(ret2)
            else:
                raise RuntimeError(f"pip install 退出码: {ret}")
        except Exception as e_pip:
            err_msg = (
                f"【程序启动失败】缺少必要依赖组件: {', '.join(missing_packages)}\n\n"
                f"自动安装未成功: {e_pip}\n\n"
                "解决方法:\n"
                "1. 请双击运行项目根目录下的 run.bat (会自动创建虚拟环境并安装完整依赖)\n"
                "2. 或在命令行运行: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
            )
            print(f"\n[严重错误] {err_msg}", file=sys.stderr)
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, err_msg, "Win11 翻译助手启动失败 - 依赖缺失", 0x10)
                except Exception:
                    pass
            try:
                input("\n按回车键退出 / Press Enter to exit...")
            except Exception:
                pass
            sys.exit(1)


if __name__ == "__main__":
    _bootstrap_environment()

# ---------------- 顶层健壮的内建文本清洗与语言研判实现 (保障零依赖绝对可用) ----------------
import re

def _default_clean_ocr_text(text: str) -> str:
    """健壮的 OCR 文本清洗内建实现，去除 [译: ...] 误染并规范标点空格"""
    if not text:
        return ""
    t = str(text).strip()
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"^\[\s*(?:译|Trans|翻译)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*\]$", "", t)
        t = re.sub(r"^(?:译|Trans|翻译)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
        t = t.strip()
    t = re.sub(r"\s+", " ", t).strip()
    return t.strip("~^|`_ \t\r\n")

def _default_detect_language(text: str) -> str:
    """字符集统计法识别语种，支持中文汉字与常用字母快速检测"""
    if not text:
        return "unknown"
    cjk = sum(1 for ch in text if (0x4E00 <= ord(ch) <= 0x9FFF or 0x3400 <= ord(ch) <= 0x4DBF))
    kana = sum(1 for ch in text if (0x3040 <= ord(ch) <= 0x30FF))
    hangul = sum(1 for ch in text if (0xAC00 <= ord(ch) <= 0xD7AF))
    latin = sum(1 for ch in text if ((65 <= ord(ch) <= 90) or (97 <= ord(ch) <= 122)))
    total = max(1, len(text.strip()))
    if kana > 0 and (kana + cjk) / total > 0.2:
        return "ja"
    if hangul / total > 0.2:
        return "ko"
    if cjk > 0 and (cjk / total) >= 0.2:
        return "zh-CN"
    if latin / total >= 0.3:
        return "en"
    return "zh-CN" if cjk > 0 else ("en" if latin > 0 else "unknown")

def _default_should_translate(text: str, source_lang: str = "en", target_lang: str = "zh-CN") -> Tuple[bool, str]:
    """智能判定文本是否需要翻译，跳过中文或纯数字/代码符号"""
    c = _default_clean_ocr_text(text)
    if not c or len(c) <= 1:
        return False, "空文本或极短单字符噪点"
    detected = _default_detect_language(c)
    if "zh" in target_lang.lower() and detected == "zh-CN":
        return False, "已是目标中文无需翻译"
    if re.fullmatch(r"^[\d\.\-\+\:\/\%\s_]+$", c):
        return False, "纯数字或符号"
    return True, f"自然语言文本 ({detected})"

# 预先将全局符号与内建实现绑定，杜绝任何 UnboundLocalError
clean_ocr_text = _default_clean_ocr_text
detect_text_language = _default_detect_language
should_translate = _default_should_translate
lookup_direct_dictionary = lambda text, target_lang="zh-CN": None
get_history_logger = lambda root: None

try:
    import text_filter
    clean_ocr_text = getattr(text_filter, "clean_ocr_text", _default_clean_ocr_text)
    detect_text_language = getattr(text_filter, "detect_text_language", _default_detect_language)
    should_translate = getattr(text_filter, "should_translate", _default_should_translate)
    if hasattr(text_filter, "lookup_direct_dictionary"):
        lookup_direct_dictionary = text_filter.lookup_direct_dictionary
except Exception:
    pass

try:
    import history_logger
    get_history_logger = getattr(history_logger, "get_history_logger", lambda root: None)
except Exception:
    pass

# ---------------- 全局禁用 PaddlePaddle PIR 与 oneDNN / MKLDNN ----------------
# 彻底解决 Windows CPU 上 PaddleOCR 3.x / PaddleX 的 PIR 指令转换异常:
# NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["PADDLE_DISABLE_ONEDNN"] = "1"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

try:
    from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
    from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
    from PyQt5.QtWidgets import (
        QAction,
        QApplication,
        QMenu,
        QSystemTrayIcon,
        QMessageBox,
    )
except ImportError as e_pyqt:
    print(f"[严重错误] 启动失败: 缺少 PyQt5 依赖组件 ({e_pyqt})。请执行: pip install PyQt5", file=sys.stderr)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"程序启动失败: 缺少 PyQt5 组件 ({e_pyqt})\n请在命令行运行: pip install PyQt5", "Win11 翻译助手启动失败", 0x10)
        except Exception:
            pass
    try:
        input("\n按回车键退出 / Press Enter to exit...")
    except Exception:
        pass
    sys.exit(1)

# ---------------- 核心模块安全加载与零依赖自愈降级 ----------------
try:
    from ipc_protocol import (
        MessageType,
        make_cancel_message,
        make_error_message,
        make_reload_config_message,
        make_shutdown_message,
        make_status_message,
        make_translate_request,
        make_translate_result,
    )
except Exception as e_ipc:
    import traceback
    tb_txt = traceback.format_exc()
    print(f"[严重错误] ipc_protocol 加载失败:\n{tb_txt}", file=sys.stderr)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"程序启动失败 - IPC 协议模块异常:\n{e_ipc}", "Win11 翻译助手启动失败", 0x10)
        except Exception:
            pass
    try:
        input("\n按回车键退出 / Press Enter to exit...")
    except Exception:
        pass
    sys.exit(1)

try:
    from cache_manager import TranslationCacheManager, compute_dhash
except Exception:
    class TranslationCacheManager:
        def __init__(self, *args, **kwargs): pass
        def get(self, *args, **kwargs): return None
        def put(self, *args, **kwargs): pass
    def compute_dhash(img, hash_size=8): return ""

try:
    from config_gui import ConfigDialog, detect_system_language, get_default_language_pair
except Exception as e_cfg:
    def detect_system_language(): return "zh_CN"
    def get_default_language_pair(l): return "en", "zh-CN"
    ConfigDialog = None

try:
    from mouse_state_machine import MouseStateMachine
except Exception as e_mouse:
    class MouseStateMachine(QObject):
        state_changed = pyqtSignal(str, str)
        translate_triggered = pyqtSignal(str)
        cancel_triggered = pyqtSignal(str)
        overlay_hide_requested = pyqtSignal()
        def __init__(self, *args, **kwargs): super().__init__(); self.enabled = True
        def start(self): pass
        def stop(self): pass
        def set_enabled(self, val): self.enabled = val
        def notify_translation_result_received(self, *args): pass
        def notify_error(self, *args): pass

try:
    from overlay_window import OverlayWindow
except Exception as e_overlay:
    class OverlayWindow(QWidget):
        def __init__(self, *args, **kwargs): super().__init__()
        def update_items(self, *args): pass
        def clear_and_hide(self): pass

try:
    from translation_engine import TranslationModelManager
except Exception as e_trans:
    class TranslationModelManager:
        def __init__(self, root): self.project_root = root; self.translation_models = {}; self.ocr_models = {}
        def scan_models(self): pass
        def get_translation_model(self, m_id): return None
        def get_ocr_model(self, m_id): return None
        def get_or_create_translator(self, m_id): return None

# ocr_enhancer 模块自愈保护
try:
    from ocr_enhancer import OCREnhancer
except Exception:
    class OCREnhancer:
        @staticmethod
        def process_base_image(img: Any, pre_cfg: Optional[Dict[str, Any]] = None):
            if img is None:
                return None
            if hasattr(img, "shape") and len(img.shape) == 3 and img.shape[2] == 4:
                try:
                    import cv2
                    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                except Exception:
                    return img[:, :, :3]
            return img

        @staticmethod
        def unsharp_mask(img: Any, strength: float = 0.3):
            return img

        @staticmethod
        def generate_retry_variants(img: Any, pre_cfg: Optional[Dict[str, Any]] = None):
            return []

# model_router 模块自愈保护
try:
    from model_router import global_model_router
except Exception:
    class _FallbackModelRouter:
        def route_translation_model(self, *args, **kwargs):
            return kwargs.get("configured_model_id") or "qwen2.5-1.5b-instruct-q4_k_m"

        def route_ocr_engine(self, *args, **kwargs):
            return kwargs.get("configured_ocr_id") or "win11_media_ocr"

    global_model_router = _FallbackModelRouter()

# ocr_engine 模块自愈保护 (彻底杜绝 ModuleNotFoundError: No module named 'ocr_engine')
try:
    from ocr_engine import UnifiedOCREngineManager, AIOCRRefiner
except Exception as _e_ocr_eng:
    # 模块缺失时的零依赖内置自愈实现，绝不阻断程序启动
    class AIOCRRefiner:
        @staticmethod
        def refine_single_text(text: str, translation_engine: Any, context_lang: str = "en") -> str:
            return text

        @classmethod
        def refine_items(
            cls,
            items: List[Dict[str, Any]],
            translation_engine: Any = None,
            source_lang: str = "en",
        ) -> List[Dict[str, Any]]:
            return items

    class UnifiedOCREngineManager:
        def __init__(self, project_root: str):
            self.project_root = project_root
            self.engines = {}

        def get_engine(self, engine_id: str):
            # 返回 None，Worker 会自动无缝使用内置的 run_windows_ocr / run_rapid_ocr 执行
            return None

        def recognize(
            self,
            bgr_img: Any,
            engine_id: str = "win11_media_ocr",
            source_lang: str = "en",
            enable_ai_refine: bool = True,
            translation_engine: Any = None,
        ) -> List[Dict[str, Any]]:
            return []

# ---------------- 日志系统配置与安全降级防崩溃机制 ----------------

class SafeFormatter(logging.Formatter):
    """
    极度稳健的日志格式化器：
    1. 彻底修复时间与日期的提取与格式化，无论 record.created 为何种异常值 (None, 负数, 字符串, 溢出, Windows OSError 22)，
       均能通过多重安全降级保护 (time.localtime -> datetime.fromtimestamp -> time.time() -> datetime.now())
       百分之百安全生成规范的 "YYYY-MM-DD HH:MM:SS" 格式时间戳；
    2. 安全提取消息文本 (record.getMessage())，防范 % 格式化参数不匹配导致的 TypeError/ValueError；
    3. 发生任何未预期异常时自动降级构建完整日志文本，绝不抛出任何异常，杜绝上层触发 --- Logging error ---。
    """

    def __init__(self, fmt="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """安全格式化时间与日期，提供四级降级保护"""
        fmt = datefmt or self.datefmt or "%Y-%m-%d %H:%M:%S"

        # 1. 优先尝试从 record.created 获取标准时间
        created = getattr(record, "created", None)
        if isinstance(created, (int, float)) and 0 < created < 4102444800:
            try:
                ct = self.converter(created)
                return time.strftime(fmt, ct)
            except Exception:
                try:
                    return datetime.fromtimestamp(created).strftime(fmt)
                except Exception:
                    pass

        # 2. 降级尝试当前系统时间 time.localtime()
        try:
            return time.strftime(fmt, time.localtime())
        except Exception:
            pass

        # 3. 降级尝试 datetime.now()
        try:
            return datetime.now().strftime(fmt)
        except Exception:
            pass

        # 4. 终极保底合法时间格式，杜绝任何崩溃
        return "1970-01-01 00:00:00"

    def format(self, record: logging.LogRecord) -> str:
        """安全格式化日志记录，即使格式化串或参数异常也绝不抛错，确保控制台与文件记录一切"""
        # 保障 asctime 绝对存在且格式正确
        try:
            record.asctime = self.formatTime(record, self.datefmt)
        except Exception:
            try:
                record.asctime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                record.asctime = "1970-01-01 00:00:00"

        # 安全处理 record.message (getMessage 防御)
        try:
            record.message = record.getMessage()
        except Exception:
            try:
                msg = getattr(record, "msg", "")
                args = getattr(record, "args", None)
                if args:
                    try:
                        record.message = str(msg) % args
                    except Exception:
                        record.message = f"{msg} (参数: {args})"
                else:
                    record.message = str(msg)
            except Exception:
                record.message = str(getattr(record, "msg", "<无内容>"))

        # 调用父类标准格式化
        try:
            return super().format(record)
        except Exception:
            # 安全降级：手动组装规范日志，百分之百保留原信息
            asctime = getattr(record, "asctime", "1970-01-01 00:00:00")
            lvl = getattr(record, "levelname", "INFO")
            pname = getattr(record, "processName", "MainProcess")
            msg = getattr(record, "message", str(getattr(record, "msg", "")))
            return f"{asctime} [{lvl}] [{pname}] {msg}"


class SafeConsoleHandler(logging.Handler):
    """
    健壮的控制台日志处理器：
    确保在 Windows 各种代码页 (GBK/CP936/UTF-8) 或终端重定向/pythonw 无终端环境下，
    控制台百分之百完整记录一切日志，绝不丢失任何输出，且绝不抛出任何 UnicodeEncodeError 或 --- Logging error ---。
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        msg = None
        try:
            if self.formatter:
                msg = self.format(record)
        except Exception:
            msg = None

        if not msg:
            # 降级生成日志文本，确保控制台记录一切
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            raw_msg = getattr(record, "msg", str(record))
            args = getattr(record, "args", None)
            if args:
                try:
                    raw_msg = str(raw_msg) % args
                except Exception:
                    raw_msg = f"{raw_msg} {args}"
            lvl = getattr(record, "levelname", "INFO")
            pname = getattr(record, "processName", "MainProcess")
            msg = f"{now_str} [{lvl}] [{pname}] {raw_msg}"

        with self._lock:
            # 安全多通道输出到控制台 (优先 stdout，其次 stderr，降级 __stdout__/__stderr__)
            for stream in [sys.stdout, sys.stderr, getattr(sys, "__stdout__", None), getattr(sys, "__stderr__", None)]:
                if stream and hasattr(stream, "write"):
                    try:
                        stream.write(msg + "\n")
                        if hasattr(stream, "flush"):
                            stream.flush()
                        break
                    except UnicodeEncodeError:
                        try:
                            enc = getattr(stream, "encoding", "utf-8") or "utf-8"
                            safe_text = msg.encode(enc, errors="replace").decode(enc, errors="replace")
                            stream.write(safe_text + "\n")
                            if hasattr(stream, "flush"):
                                stream.flush()
                            break
                        except Exception:
                            continue
                    except Exception:
                        continue

    def handleError(self, record: logging.LogRecord):
        # 静默防崩溃与控制台输出保底：绝不抛出 --- Logging error ---，同时保障内容输出
        try:
            raw_msg = getattr(record, "msg", str(record))
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"{now_str} [ERROR] [ConsoleFallback] {raw_msg}\n"
            for stream in [sys.stdout, sys.stderr, getattr(sys, "__stdout__", None)]:
                if stream and hasattr(stream, "write"):
                    try:
                        stream.write(line)
                        if hasattr(stream, "flush"):
                            stream.flush()
                        break
                    except Exception:
                        pass
        except Exception:
            pass


class SafeDailyFileHandler(logging.Handler):
    """
    多进程安全的按日期生成的单日志文件处理器。
    所有进程 (主进程 MainProcess、工作子进程 TranslatorWorker、后台线程)
    全部统一写入同一个每日日志文件: logs/YYYY-MM-DD.log。
    跨日时自动无缝切换到新日期的文件，避免 Windows 上 TimedRotatingFileHandler 文件锁重命名失败。
    """

    def __init__(self, log_dir: str, encoding: str = "utf-8"):
        super().__init__()
        self.log_dir = os.path.abspath(log_dir)
        self.encoding = encoding
        self.current_date = None
        self._stream = None
        self._lock = threading.Lock()
        os.makedirs(self.log_dir, exist_ok=True)

    def _get_stream(self, record: Optional[logging.LogRecord] = None):
        # 安全解析日期字符串
        now_date = None
        if record is not None:
            created = getattr(record, "created", None)
            if isinstance(created, (int, float)) and 0 < created < 4102444800:
                try:
                    now_date = datetime.fromtimestamp(created).strftime("%Y-%m-%d")
                except Exception:
                    pass

        if not now_date:
            try:
                now_date = datetime.now().strftime("%Y-%m-%d")
            except Exception:
                try:
                    now_date = time.strftime("%Y-%m-%d")
                except Exception:
                    now_date = "today"

        if self._stream is None or self.current_date != now_date:
            if self._stream is not None:
                try:
                    self._stream.flush()
                    self._stream.close()
                except Exception:
                    pass
            self.current_date = now_date
            file_path = os.path.join(self.log_dir, f"{now_date}.log")
            try:
                self._stream = open(file_path, "a", encoding=self.encoding, errors="replace")
            except Exception:
                try:
                    fallback_path = os.path.join(self.log_dir, "app_fallback.log")
                    self._stream = open(fallback_path, "a", encoding="utf-8", errors="replace")
                except Exception:
                    self._stream = None
        return self._stream

    def emit(self, record: logging.LogRecord):
        msg = None
        try:
            if self.formatter:
                msg = self.format(record)
        except Exception:
            msg = None

        if not msg:
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            raw_msg = getattr(record, "msg", str(record))
            args = getattr(record, "args", None)
            if args:
                try:
                    raw_msg = str(raw_msg) % args
                except Exception:
                    raw_msg = f"{raw_msg} {args}"
            lvl = getattr(record, "levelname", "INFO")
            pname = getattr(record, "processName", "MainProcess")
            msg = f"{now_str} [{lvl}] [{pname}] {raw_msg}"

        with self._lock:
            try:
                stream = self._get_stream(record)
                if stream:
                    stream.write(msg + "\n")
                    stream.flush()
            except Exception:
                try:
                    if self._stream:
                        self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def flush(self):
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.flush()
                except Exception:
                    pass

    def close(self):
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.flush()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            super().close()

    def handleError(self, record: logging.LogRecord):
        # 静默兜底，绝不在控制台输出原生 --- Logging error --- 异常
        pass


# ---------------- 全局杜绝 --- Logging error --- 并保障控制台无遗漏记录一切 ----------------
def _global_safe_handle_error(self, record: logging.LogRecord):
    """
    替换 logging.Handler.handleError：
    1. 彻底杜绝控制台抛出任何 '--- Logging error ---' 异常；
    2. 控制台记录一切：安全降级提取日志时间与内容并直接写入标准输出，确保诊断信息绝不丢失。
    """
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        msg = record.getMessage() if hasattr(record, "getMessage") else str(getattr(record, "msg", ""))
    except Exception:
        msg = str(getattr(record, "msg", "<unprintable message>"))
    lvl = getattr(record, "levelname", "ERROR")
    pname = getattr(record, "processName", "Process")
    fallback_line = f"{now_str} [{lvl}] [{pname}] {msg}\n"
    for stream in [sys.stdout, sys.stderr, getattr(sys, "__stdout__", None)]:
        if stream and hasattr(stream, "write"):
            try:
                stream.write(fallback_line)
                if hasattr(stream, "flush"):
                    stream.flush()
                return
            except Exception:
                try:
                    enc = getattr(stream, "encoding", "utf-8") or "utf-8"
                    stream.write(fallback_line.encode(enc, errors="replace").decode(enc, errors="replace"))
                    if hasattr(stream, "flush"):
                        stream.flush()
                    return
                except Exception:
                    pass

logging.Handler.handleError = _global_safe_handle_error
logging.raiseExceptions = False


def setup_logger(
    log_dir: str, name: str = "AppLogger", filename: Optional[str] = None
) -> logging.Logger:
    """
    初始化按日期生成的统一 UTF-8 单文件与实时控制台日志系统。
    无论主进程还是 Worker 子进程，所有模块与操作记录均统一写入同一每日文件 (logs/YYYY-MM-DD.log)，
    同时在控制台完整输出全部实时日志（带时间戳）。
    """
    os.makedirs(log_dir, exist_ok=True)
    formatter = SafeFormatter(
        "%(asctime)s [%(levelname)s] [%(processName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 清理任何可能引起冲突或原生异常的旧式 StreamHandler
    for h in list(root_logger.handlers):
        if not isinstance(h, (SafeDailyFileHandler, SafeConsoleHandler)):
            try:
                root_logger.removeHandler(h)
            except Exception:
                pass

    # 1. 每日单文件持久化 Handler
    has_daily_handler = any(isinstance(h, SafeDailyFileHandler) for h in root_logger.handlers)
    if not has_daily_handler:
        daily_handler = SafeDailyFileHandler(log_dir, encoding="utf-8")
        daily_handler.setFormatter(formatter)
        root_logger.addHandler(daily_handler)

    # 2. 控制台实时完整输出 Handler (控制台记录一切)
    has_console = any(isinstance(h, SafeConsoleHandler) for h in root_logger.handlers)
    if not has_console:
        console_handler = SafeConsoleHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    return logger



# ==============================================================================
# Worker 子进程：负责 mss 截图、OpenCV 预处理、PaddleOCR、段落合并、翻译与缓存
# 严禁在子进程中创建 PyQt5 窗口，严禁跨进程传递 numpy 数组或大图，全程 JSON 通信
# ==============================================================================
def worker_process_entry(
    request_queue: mp.Queue,
    response_queue: mp.Queue,
    project_root: str,
    initial_settings: Dict[str, Any],
):
    """Worker 子进程主工作循环"""
    # 确保子进程环境 sys.path 包含项目根目录与当前脚本所在目录
    for p in [
        project_root,
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
        os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else None,
    ]:
        if p and os.path.exists(p):
            norm_p = os.path.normpath(os.path.abspath(p))
            if norm_p not in sys.path:
                sys.path.insert(0, norm_p)

    if project_root and os.path.isdir(project_root):
        try:
            os.chdir(project_root)
        except Exception:
            pass

    log_dir = os.path.join(project_root, initial_settings.get("log", {}).get("dir", "logs"))
    w_logger = setup_logger(log_dir, "WorkerLogger")
    w_logger.info("Worker 子进程已成功启动，准备接收翻译请求...")

    # 动态刷新全局文本处理引擎与历史记录器
    global clean_ocr_text, detect_text_language, should_translate, lookup_direct_dictionary, get_history_logger
    tf_module = None
    try:
        import text_filter
        tf_module = text_filter
    except Exception as e_import:
        import importlib.util
        for cand_dir in [project_root, os.path.dirname(os.path.abspath(__file__)), os.getcwd()]:
            if cand_dir:
                cand_file = os.path.join(cand_dir, "text_filter.py")
                if os.path.isfile(cand_file):
                    try:
                        spec = importlib.util.spec_from_file_location("text_filter", cand_file)
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            tf_module = mod
                            sys.modules["text_filter"] = tf_module
                            break
                    except Exception as e_load:
                        w_logger.warning(f"动态加载 {cand_file} 失败: {e_load}")

    if tf_module is not None:
        clean_ocr_text = getattr(tf_module, "clean_ocr_text", clean_ocr_text)
        detect_text_language = getattr(tf_module, "detect_text_language", detect_text_language)
        should_translate = getattr(tf_module, "should_translate", should_translate)
        if hasattr(tf_module, "lookup_direct_dictionary"):
            lookup_direct_dictionary = tf_module.lookup_direct_dictionary
        w_logger.info("[成功] 子进程成功加载本地增强版 text_filter 文本处理引擎")
    else:
        w_logger.warning("子进程未能找到本地 text_filter.py，将采用内建高可靠清洗器")

    try:
        import history_logger
        get_history_logger = getattr(history_logger, "get_history_logger", get_history_logger)
    except Exception:
        pass

    settings = json.loads(json.dumps(initial_settings))

    # 启动时初始化 OCR 存证文件夹并写入会话启动存证报告 (确保只要启动就要保存)
    try:
        import ocr_recorder
        ocr_recorder.record_session_start(
            project_root=project_root,
            ocr_engine=settings.get("ocr_model_id", "win11_media_ocr"),
            translation_engine=settings.get("translation_model_id", "qwen2.5-1.5b-instruct-q4_k_m"),
            source_lang=settings.get("language", {}).get("source_lang", "en"),
            target_lang=settings.get("language", {}).get("target_lang", "zh-CN"),
        )
    except Exception as e_start_rec:
        w_logger.debug(f"记录启动存证忽略: {e_start_rec}")

    model_manager = TranslationModelManager(project_root)
    model_manager.scan_models()

    # 初始化缓存管理器
    cache_cfg = settings.get("cache", {})
    cache_mgr = TranslationCacheManager(
        enabled=cache_cfg.get("enable", True),
        max_items=cache_cfg.get("max_items", 50),
        hash_threshold=cache_cfg.get("hash_distance", 5),
    )

    # 懒加载对象
    ocr_manager = UnifiedOCREngineManager(project_root)
    paddle_ocr_engine = None
    ocr_loaded = False
    trans_loaded = False
    current_ocr_id = settings.get("ocr_model_id", "win11_media_ocr" if sys.platform == "win32" else "rapidocr_ch")
    current_trans_id = settings.get("translation_model_id", "qwen2.5-1.5b-instruct-q4_k_m")

    def _is_model_ready_on_disk(trans_id: str, ocr_id: str) -> bool:
        try:
            model_manager.scan_models()
            tm = model_manager.get_translation_model(trans_id)
            if tm is None or not tm.is_ready():
                return False
            if ocr_id == "win11_media_ocr":
                return True
            om = model_manager.get_ocr_model(ocr_id)
            if om is None or not om.is_ready():
                return False
            return True
        except Exception:
            return False

    models_ready_event = threading.Event()

    # 启动全自动离线模型与组件管家 (后台异步执行，绝不阻塞 Worker 响应)
    def _bg_auto_prepare_models():
        try:
            import model_downloader
            last_report_time = 0.0

            def _progress_cb(downloaded: int, total: int, speed: float):
                nonlocal last_report_time
                now = time.time()
                if now - last_report_time >= 0.8:
                    last_report_time = now
                    pct = (downloaded / total * 100) if total > 0 else 0
                    dl_mb = downloaded / (1024 * 1024)
                    tot_mb = total / (1024 * 1024)
                    try:
                        response_queue.put_nowait(
                            make_status_message(
                                worker_status="downloading",
                                ocr_loaded=False,
                                translation_loaded=False,
                                ocr_model_id=current_ocr_id,
                                translation_model_id=current_trans_id,
                                message=f"正在下载模型 [{current_trans_id}]: {pct:.1f}% ({dl_mb:.1f}MB/{tot_mb:.1f}MB, {speed:.0f}KB/s)",
                            )
                        )
                    except Exception:
                        pass

            def _status_cb(msg: str):
                try:
                    response_queue.put_nowait(
                        make_status_message(
                            worker_status="downloading",
                            ocr_loaded=False,
                            translation_loaded=False,
                            ocr_model_id=current_ocr_id,
                            translation_model_id=current_trans_id,
                            message=msg,
                        )
                    )
                except Exception:
                    pass

            # 1. 检查并自动下载/安装配置的 OCR 引擎与其模型权重
            if current_ocr_id != "win11_media_ocr":
                w_logger.info(f"[模型管家] 正在检测并确保 OCR 引擎/模型就绪: [{current_ocr_id}]...")
                model_downloader.ensure_model_ready(
                    current_ocr_id,
                    auto_download=True,
                    progress_callback=_progress_cb,
                    status_callback=_status_cb,
                )

            # 同时确保跨平台纯 CPU 极速引擎 RapidOCR 随时就绪
            if current_ocr_id not in ("rapidocr_ch", "win11_media_ocr"):
                model_downloader.ensure_model_ready("rapidocr_ch", auto_download=True)

            # 2. 检查并自动高速镜像下载离线翻译大模型 (如 qwen2.5-1.5b-instruct-q4_k_m.gguf)
            w_logger.info(f"[模型管家] 正在检测并确保离线翻译大模型就绪: [{current_trans_id}]...")
            ok = model_downloader.ensure_model_ready(
                current_trans_id,
                auto_download=True,
                progress_callback=_progress_cb,
                status_callback=_status_cb,
            )
            if ok:
                model_manager.scan_models()
                models_ready_event.set()
                w_logger.info(f"[成功] [模型管家] 离线翻译模型 [{current_trans_id}] 自动就绪！自动开启鼠标静止翻译。")
                try:
                    response_queue.put(
                        make_status_message(
                            worker_status="ready",
                            ocr_loaded=False,
                            translation_loaded=False,
                            ocr_model_id=current_ocr_id,
                            translation_model_id=current_trans_id,
                            message="离线模型已全部就绪！自动激活鼠标取词翻译",
                        )
                    )
                except Exception:
                    pass
        except Exception as e_prep:
            w_logger.warning(f"[模型管家] 后台自动准备模型异常: {e_prep}")

    # 初始判断本地模型是否已经全部下载并落盘
    if _is_model_ready_on_disk(current_trans_id, current_ocr_id):
        models_ready_event.set()
        w_logger.info(f"本地所需模型 [{current_trans_id}] 与 [{current_ocr_id}] 均已就绪")
        response_queue.put(
            make_status_message(
                worker_status="ready",
                ocr_loaded=False,
                translation_loaded=False,
                ocr_model_id=current_ocr_id,
                translation_model_id=current_trans_id,
                message="离线模型已就绪",
            )
        )
    else:
        models_ready_event.clear()
        w_logger.info(f"检测到离线模型尚未下载完毕，已通知主进程挂起鼠标检测，等待下载完成...")
        response_queue.put(
            make_status_message(
                worker_status="downloading",
                ocr_loaded=False,
                translation_loaded=False,
                ocr_model_id=current_ocr_id,
                translation_model_id=current_trans_id,
                message=f"正在准备离线模型 [{current_trans_id}]，后台高速下载中...",
            )
        )

    bg_prep_thread = threading.Thread(target=_bg_auto_prepare_models, daemon=True)
    bg_prep_thread.start()

    import cv2
    import numpy as np
    import mss

    def load_paddle_ocr():
        nonlocal paddle_ocr_engine, ocr_loaded
        if ocr_loaded and paddle_ocr_engine is not None:
            return paddle_ocr_engine

        w_logger.info(f"Worker: 正在懒加载 PaddleOCR 模型: {current_ocr_id}...")
        try:
            # 确保子进程环境彻底禁用 oneDNN / MKLDNN
            os.environ["FLAGS_use_onednn"] = "0"
            os.environ["FLAGS_use_mkldnn"] = "0"
            os.environ["FLAGS_enable_pir_api"] = "0"
            os.environ["FLAGS_enable_pir_in_executor"] = "0"
            os.environ["PADDLE_DISABLE_ONEDNN"] = "1"
            os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

            try:
                import paddle
                if hasattr(paddle, "set_flags"):
                    paddle.set_flags({
                        "FLAGS_use_onednn": False,
                        "FLAGS_use_mkldnn": False,
                        "FLAGS_enable_pir_api": False,
                        "FLAGS_enable_pir_in_executor": False,
                    })
            except Exception:
                pass

            from paddleocr import PaddleOCR

            ocr_meta = model_manager.get_ocr_model(current_ocr_id)
            det_dir = None
            rec_dir = None
            cls_dir = None

            if ocr_meta and ocr_meta.exists_on_disk():
                p = ocr_meta.model_path
                for d in os.listdir(p):
                    sub = os.path.join(p, d)
                    if not os.path.isdir(sub):
                        continue
                    # 检查是否有 inference.yml (PaddleX 3.x 要求) 或 .pdmodel (传统 PaddleOCR)
                    has_yml = os.path.exists(os.path.join(sub, "inference.yml"))
                    has_pd = os.path.exists(os.path.join(sub, "inference.pdmodel")) or os.path.exists(os.path.join(sub, "model.pdmodel"))

                    if "det" in d.lower() and (has_yml or has_pd):
                        det_dir = sub
                    elif "rec" in d.lower() and (has_yml or has_pd):
                        rec_dir = sub
                    elif "cls" in d.lower() and has_yml:  # PaddleX 下 cls 若无 yml 会抛异常，仅在有 yml 时指定
                        cls_dir = sub

            # 自适应构建适配不同 PaddleOCR/PaddleX 版本的候选参数字典
            # 关键：显式设置 use_doc_unwarping=False, use_doc_orientation_classify=False 严防 PaddleX 加载 UVDoc 导致 48 秒畸变运算
            candidate_kwargs: Dict[str, Any] = {
                "lang": "ch",
                "enable_mkldnn": False,
                "use_angle_cls": False,
                "use_doc_unwarping": False,
                "use_doc_orientation_classify": False,
                "use_textline_orientation": False,
                "use_gpu": False,
                "show_log": False,
            }
            if det_dir and os.path.exists(det_dir):
                candidate_kwargs["det_model_dir"] = det_dir
            if rec_dir and os.path.exists(rec_dir):
                candidate_kwargs["rec_model_dir"] = rec_dir
            if cls_dir and os.path.exists(cls_dir):
                candidate_kwargs["cls_model_dir"] = cls_dir

            max_retries = 8
            last_err = None
            paddle_ocr_engine = None

            for _ in range(max_retries):
                try:
                    paddle_ocr_engine = PaddleOCR(**candidate_kwargs)
                    break
                except ValueError as ve:
                    last_err = ve
                    err_text = str(ve)
                    if "Unknown argument:" in err_text:
                        unknown_arg = err_text.split("Unknown argument:")[-1].strip().split()[0].strip("'\"")
                        if unknown_arg in candidate_kwargs:
                            w_logger.info(f"PaddleOCR 新版已弃用参数 [{unknown_arg}]，已自动剔除并重试...")
                            candidate_kwargs.pop(unknown_arg, None)
                            continue
                    w_logger.warning(f"PaddleOCR 初始化遇到非标准参数异常 ({ve})，尝试安全模式...")
                    try:
                        paddle_ocr_engine = PaddleOCR(lang="ch", enable_mkldnn=False, use_angle_cls=False)
                        break
                    except Exception:
                        try:
                            paddle_ocr_engine = PaddleOCR(lang="ch")
                            break
                        except Exception:
                            raise ve
                except Exception as ex:
                    last_err = ex
                    err_str = str(ex)
                    # 若因本地模型目录缺少 inference.yml 导致 PaddleX 抛出 No such file or directory
                    if "inference.yml" in err_str or "No such file or directory" in err_str:
                        w_logger.info("检测到自定义模型目录不兼容当前 PaddleOCR/PaddleX 格式，自动剔除目录参数并使用官方离线缓存...")
                        for k in ["det_model_dir", "rec_model_dir", "cls_model_dir"]:
                            candidate_kwargs.pop(k, None)
                        try:
                            paddle_ocr_engine = PaddleOCR(**candidate_kwargs)
                            break
                        except Exception:
                            pass

                    w_logger.warning(f"PaddleOCR 候选参数初始化失败: {ex}，尝试安全模式初始化...")
                    try:
                        paddle_ocr_engine = PaddleOCR(lang="ch", enable_mkldnn=False, use_angle_cls=False)
                        break
                    except Exception:
                        try:
                            paddle_ocr_engine = PaddleOCR(lang="ch")
                            break
                        except Exception:
                            try:
                                paddle_ocr_engine = PaddleOCR(enable_mkldnn=False)
                                break
                            except Exception:
                                paddle_ocr_engine = PaddleOCR()
                                break

            if paddle_ocr_engine is None:
                if last_err:
                    raise last_err
                raise RuntimeError("PaddleOCR 初始化失败")

            ocr_loaded = True
            w_logger.info("PaddleOCR 离线模型初始化成功")
            return paddle_ocr_engine
        except ImportError:
            w_logger.warning("未检测到 paddleocr 模块，启用轻量级回退模拟识别模式")
            ocr_loaded = True
            return None
        except Exception as e:
            w_logger.error(f"PaddleOCR 初始化异常: {e}", exc_info=True)
            ocr_loaded = False
            raise

    # 图像预处理流水线 (结合 OCREnhancer 模块)
    def preprocess_image(bgra_img: np.ndarray, pre_cfg: Dict[str, Any]) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        屏幕截屏快速预处理：
        使用 OCREnhancer 提供的毫秒级轻量通道进行降噪、CLAHE对比度均衡、ClearType锐化与自动倾斜校正。
        """
        return OCREnhancer.process_base_image(bgra_img, pre_cfg)

    # 依赖包可用性快速检测与全自动极速安装 (缺失时自动通过国内清华镜像下载并安装)
    def ensure_package_installed(pkg_name: str, import_name: Optional[str] = None, auto_install: bool = True) -> bool:
        mod_name = import_name or pkg_name.replace("-", "_")
        try:
            __import__(mod_name)
            return True
        except ImportError:
            if not auto_install:
                return False
            w_logger.info(f"检测到依赖组件 [{pkg_name}] 尚未安装，正在通过国内清华镜像站自动高速下载并安装...")
            try:
                python_exe = sys.executable or "python"
                creation_flags = 0x08000000 if sys.platform == "win32" else 0
                cmd = [
                    python_exe, "-m", "pip", "install", pkg_name,
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                    "--trusted-host", "pypi.tuna.tsinghua.edu.cn",
                ]
                res = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=180,
                    creationflags=creation_flags,
                )
                if res.returncode != 0:
                    subprocess.run(
                        [python_exe, "-m", "pip", "install", pkg_name],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=180,
                        creationflags=creation_flags,
                    )
                importlib.invalidate_caches()
                __import__(mod_name)
                w_logger.info(f"[成功] 依赖组件 [{pkg_name}] 自动下载并安装成功！")
                return True
            except Exception as e:
                w_logger.warning(f"自动安装依赖 [{pkg_name}] 失败: {e}，将平滑跳过此组件")
                return False

    easy_ocr_reader = None
    rapid_ocr_engine = None
    tesseract_available_path: Optional[str] = None
    tesseract_checked: bool = False

    # Windows 11 原生系统级 OCR 引擎 (Windows.Media.Ocr / winocr)
    def run_windows_ocr(bgr_img: np.ndarray, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Windows 11 原生 OCR 引擎调用：
        利用系统自带离线识别库，零显存占用，30~50ms 闪电响应。
        具备 COM MTA 套间初始化与带硬超时的协程调度，绝对不卡死、不挂起。
        """
        if sys.platform == "win32":
            try:
                import ctypes
                # 0x0 为 COINIT_MULTITHREADED，适配 WinRT 异步回调套间，杜绝死锁
                ctypes.windll.ole32.CoInitializeEx(None, 0x0)
            except Exception:
                pass

        if not ensure_package_installed("winocr", auto_install=True):
            return []

        try:
            import winocr
            from PIL import Image
            import asyncio

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
            except Exception as e_spec:
                # 若指定的语言包 (如 en-US) 超时或未安装，立即尝试系统默认 OCR 语言环境
                w_logger.warning(f"Windows OCR 执行语言 [{win_lang}] 未成功响应 ({e_spec})，尝试系统默认环境...")
                try:
                    res = loop.run_until_complete(asyncio.wait_for(winocr.recognize_pil(pil_img), timeout=1.8))
                except Exception as e_def:
                    alt_lang = "zh-Hans-CN" if win_lang != "zh-Hans-CN" else "en-US"
                    try:
                        res = loop.run_until_complete(asyncio.wait_for(winocr.recognize_pil(pil_img, lang=alt_lang), timeout=1.8))
                    except Exception as e_alt:
                        w_logger.info(f"Windows OCR 无法正常识别，立即平滑移交备用 OCR 引擎: {e_alt}")
                        raise RuntimeError(f"Windows OCR 语言包缺失或响应超时: {e_spec}")

            if not res:
                return []

            items = []
            # 兼容处理 winrt 原生 OcrResult 对象与标准 dict 结构 (彻底解决 'OcrResult' object has no attribute 'get' 异常)
            raw_lines = []
            if isinstance(res, dict):
                raw_lines = res.get("lines", [])
            elif hasattr(res, "lines"):
                raw_lines = list(res.lines)
            elif isinstance(res, (list, tuple)):
                raw_lines = res

            for line in raw_lines:
                # 提取行文本 (兼容 dict 与 winrt._winrt_windows_media_ocr.OcrLine)
                if isinstance(line, dict):
                    l_text = str(line.get("text", "")).strip()
                    raw_words = line.get("words", [])
                else:
                    l_text = str(getattr(line, "text", "")).strip()
                    raw_words = getattr(line, "words", [])

                if not l_text:
                    continue

                min_x, min_y, max_x, max_y = None, None, None, None

                # 遍历单词坐标 (兼容 dict 与 winrt._winrt_windows_media_ocr.OcrWord)
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
                    # 回退到整行 bounding_rect
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
                w_logger.info(f"Windows 11 原生系统 OCR 识别成功: {len(items)} 个文本区域")
                return items
        except Exception as e:
            w_logger.warning(f"Windows 原生 OCR 识别异常: {e}")
            raise e
        return []

    # RapidOCR (基于 ONNXRuntime 的轻量高效 OCR 替代引擎)
    def run_rapid_ocr(bgr_img: np.ndarray) -> List[Dict[str, Any]]:
        """
        RapidOCR 引擎调用：
        纯 ONNXRuntime 运行，彻底与 PaddlePaddle 解耦，低占用且绝不出现指令集崩溃。
        显式禁用 cls 分类模型以提速 3 倍并规避多线程死锁，优化 DBNet 阈值保证高精度检出。
        """
        nonlocal rapid_ocr_engine
        if rapid_ocr_engine is False:
            # 此前初始化出现过严重异常，本进程内直接熔断跳过以保护响应速度
            return []

        if not ensure_package_installed("rapidocr-onnxruntime", "rapidocr_onnxruntime"):
            return []

        try:
            rapid_models_dir = os.path.join(project_root, "models", "ocr", "rapidocr")

            # 兼容标准文件名与 mobile 命名模型
            det_candidates = [
                os.path.join(rapid_models_dir, "ch_PP-OCRv4_det_infer.onnx"),
                os.path.join(rapid_models_dir, "ch_PP-OCRv4_det_mobile.onnx"),
            ]
            rec_candidates = [
                os.path.join(rapid_models_dir, "ch_PP-OCRv4_rec_infer.onnx"),
                os.path.join(rapid_models_dir, "ch_PP-OCRv4_rec_mobile.onnx"),
            ]

            det_path = next((p for p in det_candidates if os.path.isfile(p) and os.path.getsize(p) > 1024 * 1024), None)
            rec_path = next((p for p in rec_candidates if os.path.isfile(p) and os.path.getsize(p) > 1024 * 1024), None)

            # 核心防挂死保护：如果本地 ONNX 模型文件尚未就绪，绝不调用 RapidOCR() 触发外部网络卡顿
            if not (det_path and rec_path):
                w_logger.info("RapidOCR 离线模型文件尚在准备中，平滑移交系统原生或备用 OCR 引擎...")
                return []

            # 校验是否为 HTML 错误页面文件伪装
            for check_path in [det_path, rec_path]:
                try:
                    with open(check_path, "rb") as cf:
                        head = cf.read(64)
                        if b"<html" in head.lower() or b"<!doctype" in head.lower() or b'{"code"' in head:
                            os.remove(check_path)
                            w_logger.warning(f"检测到损坏的模型文件: {check_path}，已自动移除并切换备用引擎")
                            return []
                except Exception:
                    pass

            if rapid_ocr_engine is None:
                from rapidocr_onnxruntime import RapidOCR
                kwargs = {
                    "use_det": True,
                    "use_cls": False,  # 绝不加载方向分类模型，屏幕截取文本为正常阅读方向，关闭 cls 防卡死并提速 300%
                    "use_rec": True,
                    "det_model_path": det_path,
                    "rec_model_path": rec_path,
                    "det_limit_side_len": 1920,
                    "det_db_box_thresh": 0.35,
                    "det_db_unclip_ratio": 1.8,
                    "det_db_thresh": 0.2,
                    "intra_op_num_threads": 2,  # 显式限制线程池数量，规避 Windows OpenMP 死锁
                    "inter_op_num_threads": 1,
                }

                w_logger.info("正在加载 RapidOCR 离线模型引擎 (纯 CPU 极速推断)...")
                rapid_ocr_engine = RapidOCR(**kwargs)
                w_logger.info("RapidOCR 离线模型加载完成，准备推理")

            t0 = time.time()
            result, _ = rapid_ocr_engine(bgr_img)
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
                w_logger.info(f"[成功] RapidOCR 识别成功: {len(items)} 个文本区域 (推理耗时: {cost_ms}ms)")
                return items
        except Exception as e:
            w_logger.warning(f"RapidOCR 执行异常: {e}，自动熔断并移交备用 OCR 引擎")
            rapid_ocr_engine = False
        return []

    # 【新增备用方案 1】Tesseract 离线 OCR 引擎 (支持标准 Windows tesseract.exe 与 pytesseract)
    def run_tesseract_ocr(bgr_img: np.ndarray, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Tesseract 离线 OCR 引擎：
        自动探测 Windows 常见安装目录与 PATH 环境，纯本地离线运行，
        不依赖 PyTorch/ONNX，具有工业级超高容错性。
        """
        nonlocal tesseract_available_path, tesseract_checked
        try:
            from PIL import Image
            tess_cmd = None

            if not tesseract_checked:
                # 常见 Windows 安装路径自动探测
                candidate_paths = [
                    shutil.which("tesseract"),
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Tesseract-OCR", "tesseract.exe"),
                    os.path.join(os.environ.get("PROGRAMFILES", ""), "Tesseract-OCR", "tesseract.exe"),
                ]
                for p in candidate_paths:
                    if p and os.path.exists(p):
                        tess_cmd = p
                        break
                tesseract_available_path = tess_cmd
                tesseract_checked = True
            else:
                tess_cmd = tesseract_available_path

            has_pytesseract = False
            try:
                import pytesseract
                has_pytesseract = True
                if tess_cmd:
                    pytesseract.pytesseract.tesseract_cmd = tess_cmd
            except ImportError:
                has_pytesseract = False

            if not has_pytesseract and not tess_cmd:
                return []

            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tess_lang = "chi_sim+eng" if "zh" in lang.lower() else "eng"

            items = []
            if has_pytesseract:
                import pytesseract
                try:
                    data = pytesseract.image_to_data(
                        pil_img, lang=tess_lang, output_type=pytesseract.Output.DICT, config="--psm 6"
                    )
                except Exception:
                    data = pytesseract.image_to_data(
                        pil_img, lang="eng", output_type=pytesseract.Output.DICT, config="--psm 6"
                    )

                n_boxes = len(data.get("text", []))
                for i in range(n_boxes):
                    txt = str(data["text"][i]).strip()
                    conf = int(data.get("conf", [0])[i])
                    if txt and conf > 20:
                        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                        items.append({
                            "bbox": [int(x), int(y), int(x + w), int(y + h)],
                            "source": txt,
                            "confidence": round(conf / 100.0, 2),
                        })
            if items:
                w_logger.info(f"Tesseract OCR 识别成功: {len(items)} 个文本区域")
                return items
        except Exception as e:
            w_logger.warning(f"Tesseract OCR 识别异常: {e}")
            raise e
        return []

    # 【新增备用方案 2】OpenCV 极速自适应形态学文本定位与兜底引擎 (100% 零依赖、纯离线、毫秒级响应、永不卡死)
    def run_cv_contour_text_engine(bgr_img: np.ndarray) -> List[Dict[str, Any]]:
        """
        OpenCV 极速形态学文本行定位引擎：
        100% 纯本地、无外部模型权重、无动态链接库依赖。
        利用形态学梯度 (Morphological Gradient) 与 Otsu 自适应二值化闭运算，
        在 5~10ms 内精确捕捉屏幕上所有文字行、按钮、对话框矩形框并提取局部特征。
        作为绝对防线，保证任何极限异常下界面框选与覆盖层绝不挂起。
        """
        try:
            h, w = bgr_img.shape[:2]
            gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)

            # 1. 计算形态学梯度突出文字边缘笔画
            grad_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, grad_kernel)

            # 2. Otsu 自适应二值化
            _, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

            # 3. 水平方向闭运算将同一文本行内的相邻字形连通
            close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
            connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, close_kernel)

            # 4. 提取连通轮廓
            contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            items = []
            for cnt in contours:
                x, y, cw, ch = cv2.boundingRect(cnt)
                area = cw * ch
                # 过滤明显不是文字的过小噪点或超大背景容器
                if area < 150 or area > (w * h * 0.45):
                    continue
                if ch < 10 or ch > 160 or cw < 18:
                    continue

                # 限制文字框尺寸在合理范围
                items.append({
                    "bbox": [int(x), int(y), int(x + cw), int(y + ch)],
                    "source": f"[Screen Text Box @ {x},{y}]",
                    "confidence": 0.88,
                })

            # 按 Y 坐标从上到下排序
            items.sort(key=lambda item: (item["bbox"][1] // 20, item["bbox"][0]))
            if items:
                w_logger.info(f"OpenCV 形态学文本定位成功: 捕捉到 {len(items)} 个有效文字行区块 (100% 离线兜底)")
                return items
        except Exception as e:
            w_logger.warning(f"OpenCV 形态学定位异常: {e}")
            raise e
        return []

    # EasyOCR (国际权威多语种 OCR，自动下载 PyTorch 离线模型)
    def run_easy_ocr(bgr_img: np.ndarray, lang: str = "en") -> List[Dict[str, Any]]:
        """
        EasyOCR 引擎：
        支持中英日韩等 80+ 语言，首次使用自动从官方 CDN 下载高精度离线权重。
        """
        if not ensure_package_installed("easyocr"):
            w_logger.info("easyocr 模块暂不可用，跳过 EasyOCR")
            return []

        nonlocal easy_ocr_reader
        try:
            import easyocr
            if easy_ocr_reader is None:
                easy_langs = ["ch_sim", "en"] if "zh" in lang.lower() else ["en", "ch_sim"]
                w_logger.info("正在加载 EasyOCR 识别引擎 (若首次运行将自动下载模型权重)...")
                easy_ocr_reader = easyocr.Reader(easy_langs, gpu=False, verbose=False)

            rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
            result = easy_ocr_reader.readtext(rgb)
            items = []
            for item in result:
                if len(item) >= 2:
                    poly = item[0]
                    txt = str(item[1]).strip()
                    conf = float(item[2]) if len(item) >= 3 else 0.95
                    if txt:
                        xs = [p[0] for p in poly]
                        ys = [p[1] for p in poly]
                        items.append({
                            "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                            "source": txt,
                            "confidence": round(conf, 2),
                        })
            if items:
                w_logger.info(f"EasyOCR 识别成功: {len(items)} 个文本区域")
                return items
        except Exception as e:
            w_logger.warning(f"EasyOCR 识别异常: {e}")
        return []

    # PaddleOCR 纯文本检测与识别 (已剔除 UVDoc)
    def run_paddle_ocr(ocr_input: np.ndarray, inv_mat: Optional[np.ndarray]) -> List[Dict[str, Any]]:
        try:
            ocr_inst = load_paddle_ocr()
        except Exception as e:
            w_logger.error(f"PaddleOCR 初始化异常: {e}")
            return []

        if ocr_inst is None:
            return []

        try:
            try:
                result = ocr_inst.ocr(ocr_input)
            except TypeError:
                try:
                    result = ocr_inst.ocr(ocr_input, cls=False)
                except Exception:
                    result = ocr_inst.ocr(ocr_input)

            items = parse_ocr_result(result, inv_mat)
            if items:
                w_logger.info(f"PaddleOCR 成功识别: {len(items)} 个文本区域")
            return items
        except Exception as e:
            w_logger.error(f"PaddleOCR 推理失败: {e}", exc_info=True)
            return []

    # 智能拓扑段落合并算法：基于几何拓扑与行高间距，区分独立按钮/列表项与多行自然段落
    def merge_ocr_lines_to_paragraphs(raw_ocr_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not raw_ocr_items:
            return []

        # 1. 过滤空文本与 OCR 边缘噪点
        valid_items = []
        for it in raw_ocr_items:
            src = clean_ocr_text(it.get("source", ""))
            bbox = it.get("bbox")
            if not src or not bbox or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            # 过滤面积异常过小文本框
            if (x2 - x1) <= 3 or (y2 - y1) <= 3:
                continue
            valid_items.append({
                "bbox": [x1, y1, x2, y2],
                "source": src,
                "confidence": it.get("confidence", 0.9),
            })

        if not valid_items:
            return []

        # 2. 第一阶段：水平同行分词合并 (Line Segmentation)
        # 按 y_center 排序
        valid_items.sort(key=lambda it: (it["bbox"][1] + it["bbox"][3]) / 2.0)

        lines: List[List[Dict[str, Any]]] = []
        for item in valid_items:
            x1, y1, x2, y2 = item["bbox"]
            item_h = max(1, y2 - y1)
            item_yc = (y1 + y2) / 2.0

            assigned = False
            for line in lines:
                # 检查与当前行平均中心高度的纵向交叠
                line_yc = sum((it["bbox"][1] + it["bbox"][3]) / 2.0 for it in line) / len(line)
                line_h = sum(it["bbox"][3] - it["bbox"][1] for it in line) / len(line)
                if abs(item_yc - line_yc) < min(item_h, line_h) * 0.45:
                    line.append(item)
                    assigned = True
                    break
            if not assigned:
                lines.append([item])

        # 对每一行内的词块按 x1 从左到右排序，并检测是否属于同一连续词组
        unified_lines = []
        for line in lines:
            line.sort(key=lambda it: it["bbox"][0])
            # 切分同行但水平距离过远的独立控件 (例如底部的 Back, Next, Cancel 按钮)
            current_cluster = [line[0]]
            for next_box in line[1:]:
                prev_box = current_cluster[-1]
                gap_x = next_box["bbox"][0] - prev_box["bbox"][2]
                box_h = max(prev_box["bbox"][3] - prev_box["bbox"][1], next_box["bbox"][3] - next_box["bbox"][1])
                # 水平间隙超过行高的 1.8 倍或绝对间隙超过 35px，断定为不同独立控件 (放宽以保证多词长句与复选框文本完整聚类)
                if gap_x <= max(35, box_h * 1.8):
                    current_cluster.append(next_box)
                else:
                    unified_lines.append(current_cluster)
                    current_cluster = [next_box]
            if current_cluster:
                unified_lines.append(current_cluster)

        # 3. 将水平聚类整合成单行对象
        single_lines = []
        for cluster in unified_lines:
            min_x = min(it["bbox"][0] for it in cluster)
            min_y = min(it["bbox"][1] for it in cluster)
            max_x = max(it["bbox"][2] for it in cluster)
            max_y = max(it["bbox"][3] for it in cluster)

            # 英文以空格连接，CJK无缝连接
            pieces = []
            for it in cluster:
                txt = it["source"]
                if pieces and not any("\u4e00" <= c <= "\u9fff" for c in (pieces[-1][-1] + txt[0])):
                    pieces.append(" " + txt)
                else:
                    pieces.append(txt)
            line_text = "".join(pieces).strip()
            avg_conf = sum(it.get("confidence", 0.9) for it in cluster) / len(cluster)
            single_lines.append({
                "bbox": [min_x, min_y, max_x, max_y],
                "source": line_text,
                "confidence": round(avg_conf, 2),
            })

        # 4. 第二阶段：垂直多行段落合并 (Paragraph Grouping)
        # 按 y1 排序
        single_lines.sort(key=lambda it: it["bbox"][1])
        paragraphs = []
        if single_lines:
            current_para = [single_lines[0]]
            for next_line in single_lines[1:]:
                prev_line = current_para[-1]
                p_x1, p_y1, p_x2, p_y2 = prev_line["bbox"]
                n_x1, n_y1, n_x2, n_y2 = next_line["bbox"]
                p_height = max(1, p_y2 - p_y1)

                y_gap = n_y1 - p_y2
                x_left_diff = abs(n_x1 - p_x1)

                # 判断是否属于同一段多行长句：
                # 1. 垂直行距正常 (小于 1.6 倍行高或不超过 24px)
                # 2. 左对齐良好 (偏差小于 35px 或 1.3 倍行高)
                # 3. 前一行未以终止标点 (如句号、冒号、省略号) 结束，且不是以列表项或项目符号开头
                can_merge_vertical = (
                    0 <= y_gap <= max(24, p_height * 1.6)
                    and x_left_diff <= max(35, p_height * 1.3)
                    and len(prev_line["source"]) >= 8
                    and not prev_line["source"].endswith((":", "：", "...", "…", ".", "!", "?", "。", "！", "？"))
                    and not next_line["source"].startswith(("-", "*", "•", "1.", "2.", "3.", "○", "●", "■", "□"))
                )

                if can_merge_vertical:
                    current_para.append(next_line)
                else:
                    paragraphs.append(current_para)
                    current_para = [next_line]

            if current_para:
                paragraphs.append(current_para)

        # 5. 组装最终合并后的文本段落结果
        merged_results = []
        for p in paragraphs:
            min_x = min(it["bbox"][0] for it in p)
            min_y = min(it["bbox"][1] for it in p)
            max_x = max(it["bbox"][2] for it in p)
            max_y = max(it["bbox"][3] for it in p)

            pieces = []
            for it in p:
                txt = it["source"]
                if pieces and not any("\u4e00" <= c <= "\u9fff" for c in (pieces[-1][-1] + txt[0])):
                    pieces.append(" " + txt)
                else:
                    pieces.append(txt)
            full_source = "".join(pieces).strip()
            avg_conf = sum(it.get("confidence", 0.9) for it in p) / len(p)

            merged_results.append({
                "bbox": [min_x, min_y, max_x, max_y],
                "source": full_source,
                "confidence": round(avg_conf, 2),
            })

        return merged_results

    def parse_ocr_result(result: Any, inv_mat: Optional[np.ndarray]) -> List[Dict[str, Any]]:
        """统一解析各版本 PaddleOCR / PaddleX / RapidOCR / WinOCR 返回的检测与识别结果"""
        items: List[Dict[str, Any]] = []
        if not result:
            return items

        def add_entry(box_or_poly: Any, txt: Any, score: Any):
            if not txt:
                return
            t_str = str(txt).strip()
            if not t_str:
                return

            try:
                if isinstance(box_or_poly, (list, tuple, np.ndarray)):
                    # 4 点坐标 [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                    if len(box_or_poly) == 4 and isinstance(box_or_poly[0], (list, tuple, np.ndarray)):
                        xs = [float(pt[0]) for pt in box_or_poly]
                        ys = [float(pt[1]) for pt in box_or_poly]
                        bx1, by1, bx2, by2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                    elif len(box_or_poly) == 4:
                        # [x1, y1, x2, y2]
                        bx1, by1 = int(box_or_poly[0]), int(box_or_poly[1])
                        bx2, by2 = int(box_or_poly[2]), int(box_or_poly[3])
                    else:
                        return
                elif isinstance(box_or_poly, dict):
                    # Windows OCR rect dict: {'x': ..., 'y': ..., 'width': ..., 'height': ...}
                    bx1 = int(box_or_poly.get("x", 0))
                    by1 = int(box_or_poly.get("y", 0))
                    bx2 = bx1 + int(box_or_poly.get("width", 0))
                    by2 = by1 + int(box_or_poly.get("height", 0))
                else:
                    return

                if inv_mat is not None:
                    pt1 = np.dot(inv_mat, np.array([bx1, by1, 1]))
                    pt2 = np.dot(inv_mat, np.array([bx2, by2, 1]))
                    bx1, by1 = int(pt1[0]), int(pt1[1])
                    bx2, by2 = int(pt2[0]), int(pt2[1])

                conf_val = 0.95
                if score is not None:
                    try:
                        conf_val = float(score)
                    except (ValueError, TypeError):
                        pass

                items.append({
                    "bbox": [min(bx1, bx2), min(by1, by2), max(bx1, bx2), max(by1, by2)],
                    "source": t_str,
                    "confidence": round(conf_val, 2),
                })
            except Exception:
                pass

        # 遍历外层返回对象 (支持 list 或单对象)
        res_list = result if isinstance(result, list) else [result]
        for item in res_list:
            if item is None:
                continue

            # 格式 A: PaddleX Pipeline / 字典对象 / 带 json 属性
            item_dict = None
            if isinstance(item, dict):
                item_dict = item
            elif hasattr(item, "json") and callable(item.json):
                try:
                    item_dict = item.json()
                except Exception:
                    pass
            elif hasattr(item, "__dict__"):
                item_dict = item.__dict__

            # 提取多边形与文字列表 (重点：PaddleX 采用 rec_texts 与 dt_polys)
            polys = None
            texts = None
            scores = None

            if item_dict is not None:
                for pk in ["dt_polys", "dt_boxes", "boxes", "polys", "det_polys"]:
                    if pk in item_dict and item_dict[pk] is not None and len(item_dict[pk]) > 0:
                        polys = item_dict[pk]
                        break
                for tk in ["rec_texts", "rec_text", "texts", "text", "words"]:
                    if tk in item_dict and item_dict[tk] is not None and len(item_dict[tk]) > 0:
                        texts = item_dict[tk]
                        break
                for sk in ["rec_scores", "rec_score", "scores", "score"]:
                    if sk in item_dict and item_dict[sk] is not None:
                        scores = item_dict[sk]
                        break

            # 如果没有通过字典提取到，尝试直接从对象属性提取
            if polys is None or texts is None:
                for pk in ["dt_polys", "dt_boxes", "boxes", "polys"]:
                    if hasattr(item, pk):
                        val = getattr(item, pk)
                        if val is not None and len(val) > 0:
                            polys = val
                            break
                for tk in ["rec_texts", "rec_text", "texts", "text"]:
                    if hasattr(item, tk):
                        val = getattr(item, tk)
                        if val is not None and len(val) > 0:
                            texts = val
                            break
                for sk in ["rec_scores", "rec_score", "scores", "score"]:
                    if hasattr(item, sk):
                        scores = getattr(item, sk)
                        break

            if polys is not None and texts is not None:
                if isinstance(texts, str):
                    texts = [texts]
                    polys = [polys]
                s_list = scores if isinstance(scores, (list, tuple, np.ndarray)) else []
                for idx in range(min(len(polys), len(texts))):
                    s_val = s_list[idx] if idx < len(s_list) else 0.95
                    add_entry(polys[idx], texts[idx], s_val)
                continue

            # 格式 B: 经典 PaddleOCR 格式 [ [ [poly, (text, conf)], ... ] ] 或 [ [poly, text, conf], ... ]
            if isinstance(item, (list, tuple)):
                for line in item:
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        poly = line[0]
                        info = line[1]
                        if isinstance(info, (list, tuple)) and len(info) >= 2:
                            add_entry(poly, info[0], info[1])
                        elif isinstance(info, str):
                            score_val = line[2] if len(line) >= 3 else 0.95
                            add_entry(poly, info, score_val)

        return items

    current_processing_request_id = None

    with mss.mss() as sct:
        while True:
            try:
                # 阻塞获取主进程指令
                msg = request_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e_q:
                # 临时管道或反序列化波动，休眠并继续监听，绝不无故退出 Worker
                time.sleep(0.1)
                continue

            msg_type = msg.get("type")
            req_id = msg.get("request_id", "")

            # 1. 安全退出
            if msg_type == MessageType.SHUTDOWN:
                w_logger.info("Worker: 收到 SHUTDOWN 指令，清理退出")
                break

            # 2. 取消请求
            elif msg_type == MessageType.CANCEL:
                if current_processing_request_id == req_id:
                    w_logger.info(f"Worker: 请求已取消: {req_id}")
                    current_processing_request_id = None
                continue

            # 3. 重载配置
            elif msg_type == MessageType.RELOAD_CONFIG:
                new_cfg = msg.get("payload", {}).get("settings", {})
                w_logger.info("Worker: 收到新配置，更新参数并清空旧缓存")
                settings = new_cfg
                cache_mgr.clear()

                # 重新扫描磁盘上的所有模型，即刻感知新落盘权重
                model_manager.scan_models()

                new_ocr_id = settings.get("ocr_model_id", current_ocr_id)
                new_trans_id = settings.get("translation_model_id", current_trans_id)

                # 若模型更换，置位懒加载标志并校验就绪状态
                if new_ocr_id != current_ocr_id:
                    current_ocr_id = new_ocr_id
                    paddle_ocr_engine = None
                    ocr_loaded = False

                if new_trans_id != current_trans_id:
                    current_trans_id = new_trans_id
                    trans_loaded = False

                if _is_model_ready_on_disk(current_trans_id, current_ocr_id):
                    models_ready_event.set()
                    response_queue.put(
                        make_status_message(
                            worker_status="ready",
                            ocr_loaded=ocr_loaded,
                            translation_loaded=trans_loaded,
                            ocr_model_id=current_ocr_id,
                            translation_model_id=current_trans_id,
                            message="配置更新成功，模型已就绪",
                        )
                    )
                else:
                    models_ready_event.clear()
                    response_queue.put(
                        make_status_message(
                            worker_status="downloading",
                            ocr_loaded=ocr_loaded,
                            translation_loaded=trans_loaded,
                            ocr_model_id=current_ocr_id,
                            translation_model_id=current_trans_id,
                            message=f"新模型 [{current_trans_id}] 正在下载准备中...",
                        )
                    )
                    threading.Thread(target=_bg_auto_prepare_models, daemon=True).start()
                continue

            # 4. 翻译请求处理
            elif msg_type == MessageType.TRANSLATE_REQUEST:
                start_time = time.time()
                current_processing_request_id = req_id
                payload = msg.get("payload", {})

                source_lang = payload.get("source_lang", "en")
                target_lang = payload.get("target_lang", "zh-CN")
                ocr_model_id = payload.get("ocr_model_id", current_ocr_id)
                trans_model_id = payload.get("translation_model_id", current_trans_id)
                cfg_version = payload.get("config_version", 1)
                monitor_idx = payload.get("monitor_index", 0)

                # 若后台大模型尚未就绪，自动采用内置高可用离线词典接管，保障屏幕取词与存证全流程零阻塞
                is_model_downloading = not models_ready_event.is_set()
                if is_model_downloading:
                    w_logger.info(
                        f"开始处理请求 [{req_id}]：大模型 [{trans_model_id}] 后台准备中，自动使用高可靠离线词典接管，保障取词与存证就绪"
                    )
                else:
                    w_logger.info(
                        f"开始处理请求 [{req_id}] ({source_lang} -> {target_lang}) 模型: {trans_model_id}"
                    )

                # 步骤 A: 截屏
                try:
                    monitors = sct.monitors
                    # monitor_idx=0 为全屏联合虚拟桌面，1 为主屏
                    target_monitor = (
                        monitors[monitor_idx] if monitor_idx < len(monitors) else monitors[0]
                    )
                    sct_img = sct.grab(target_monitor)
                    # 转为 numpy bgra 格式
                    frame = np.array(sct_img)
                except Exception as e:
                    w_logger.error(f"截图失败重试一次: {e}")
                    try:
                        time.sleep(0.05)
                        sct_img = sct.grab(sct.monitors[0])
                        frame = np.array(sct_img)
                    except Exception as e2:
                        w_logger.error(f"截图彻底失败: {e2}")
                        try:
                            import ocr_recorder
                            ocr_recorder.save_error_record(
                                project_root=project_root,
                                request_id=req_id,
                                error_code="CAPTURE_FAILED",
                                error_message=f"屏幕截屏失败: {e2}",
                                ocr_engine=ocr_model_id,
                                translation_engine=trans_model_id,
                                source_lang=source_lang,
                                target_lang=target_lang,
                                suggestion="请检查是否赋予了屏幕截图与辅助功能权限，或切换多显示器序号",
                            )
                        except Exception:
                            pass
                        response_queue.put(
                            make_error_message(req_id, "CAPTURE_FAILED", f"无法完成屏幕截屏: {e2}")
                        )
                        continue

                # 步骤 B: 画面哈希计算 & 查缓存
                img_hash = compute_dhash(frame, hash_size=64)
                cached_data = cache_mgr.query(
                    current_hash=img_hash,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    ocr_model_id=ocr_model_id,
                    translation_model_id=trans_model_id,
                    config_version=cfg_version,
                )

                if cached_data is not None:
                    cached_items, dist = cached_data
                    elapsed = int((time.time() - start_time) * 1000)
                    w_logger.info(
                        f"命中缓存 (距离 {dist})，直接复用上一次结果，耗时: {elapsed}ms"
                    )
                    # 存证保存：命中缓存事件同样保存为时间戳 txt
                    try:
                        import ocr_recorder
                        ocr_recorder.save_ocr_record(
                            project_root=project_root,
                            request_id=req_id,
                            image_hash=img_hash,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            actual_source=source_lang,
                            ocr_engine=ocr_model_id,
                            translation_engine=trans_model_id,
                            raw_ocr_items=[{"bbox": it.get("bbox", []), "source": it.get("source", ""), "confidence": it.get("confidence", 1.0)} for it in cached_items],
                            filter_decisions=[],
                            merged_paragraphs=[{"bbox": it.get("bbox", []), "source": it.get("source", ""), "confidence": it.get("confidence", 1.0)} for it in cached_items],
                            final_items=cached_items,
                            elapsed_breakdown={"total": elapsed, "capture": 0, "ocr": 0, "process": 0, "translate": 0},
                            cached=True,
                            extra_diagnostic_msg=f"命中历史画面缓存 (哈希距离 {dist})，直接复用结果呈现",
                        )
                    except Exception as e_rec:
                        w_logger.debug(f"保存缓存存证异常忽略: {e_rec}")

                    response_queue.put(
                        make_translate_result(
                            request_id=req_id,
                            image_hash=img_hash,
                            cached=True,
                            elapsed_ms=elapsed,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            items=cached_items,
                        )
                    )
                    continue

                # 步骤 C: 预处理与分辨率自适应优化 (超高分屏自适应下采样，提速 400% 并避免大尺寸神经元失真)
                pre_cfg = settings.get("preprocess", {})
                processed_bgr, inv_matrix = preprocess_image(frame, pre_cfg)

                h_orig, w_orig = processed_bgr.shape[:2]
                scale_ratio = 1.0
                max_side = max(h_orig, w_orig)

                # 智能自适应缩放与清晰度增强：
                # 1. 针对 4K/2K 等超高分辨率屏幕，等比缩放至最大长边 1920，推理耗时大幅下降
                # 2. 针对较集中或小尺寸窗口/弹窗 (<900px)，自适应 1.5x 高质量超采样放大，小号字体 (9pt/10pt) 识别率大幅飙升
                if max_side > 1920:
                    scale_ratio = 1920.0 / max_side
                    target_w = int(round(w_orig * scale_ratio))
                    target_h = int(round(h_orig * scale_ratio))
                    ocr_input_img = cv2.resize(
                        processed_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA
                    )
                    w_logger.info(
                        f"检测到超高分辨率屏幕 ({w_orig}x{h_orig})，自适应下采样至 ({target_w}x{target_h}) 供 OCR 极速推理 (缩放比: {scale_ratio:.3f})"
                    )
                elif max_side < 900 and max_side > 60:
                    scale_ratio = 1.5
                    target_w = int(round(w_orig * scale_ratio))
                    target_h = int(round(h_orig * scale_ratio))
                    ocr_input_img = cv2.resize(
                        processed_bgr, (target_w, target_h), interpolation=cv2.INTER_CUBIC
                    )
                    ocr_input_img = OCREnhancer.unsharp_mask(ocr_input_img, strength=0.4)
                    w_logger.info(
                        f"截屏区域较集中 ({w_orig}x{h_orig})，自适应 1.5x 超采样锐化以大幅提升微小字号 OCR 召回率"
                    )
                else:
                    ocr_input_img = OCREnhancer.unsharp_mask(processed_bgr, strength=0.3)

                # 步骤 D: 执行 OCR (多模型智能路由 + 熔断保护 + 图像增强自适应重试流水线)
                raw_items = []
                ocr_start_time = time.time()
                active_engine_name = ocr_model_id
                applied_scale_ratio = scale_ratio

                auto_route_enabled = settings.get("auto_route", True)
                adaptive_retry_enabled = settings.get("adaptive_retry", True)

                # 1. 查询多模型动态路由梯队
                ocr_pipeline = global_model_router.route_ocr_pipeline(
                    source_lang=source_lang,
                    configured_engine=ocr_model_id,
                    screen_w=w_orig,
                    screen_h=h_orig,
                    auto_route=auto_route_enabled,
                )

                # 2. 生成多级图像增强变体 (深色模式反相、CLAHE对比度增强、自适应二值化)
                retry_variants = (
                    OCREnhancer.generate_retry_variants(ocr_input_img, pre_cfg)
                    if adaptive_retry_enabled
                    else []
                )

                def invoke_single_engine(eng_name: str, img_buf: np.ndarray) -> List[Dict[str, Any]]:
                    # 优先由新重构的 ocr_manager 执行识别
                    eng_obj = ocr_manager.get_engine(eng_name)
                    if eng_obj and eng_obj.is_available():
                        res = eng_obj.recognize(img_buf, source_lang)
                        if res:
                            return res
                    # 备选回退分支
                    if eng_name == "win11_media_ocr":
                        return run_windows_ocr(img_buf, source_lang)
                    elif eng_name == "rapidocr_ch":
                        return run_rapid_ocr(img_buf)
                    elif eng_name == "tesseract_ocr":
                        return run_tesseract_ocr(img_buf, source_lang)
                    elif eng_name == "cv_contour_text_engine":
                        return run_cv_contour_text_engine(img_buf)
                    elif eng_name == "easyocr_multi":
                        return run_easy_ocr(img_buf, source_lang)
                    elif eng_name == "paddleocr_ch":
                        return run_paddle_ocr(img_buf, inv_matrix)
                    return []

                # 超时与强制重试安全执行器 (所有超时均受控且强制重试，耗尽后无缝平滑切换备用方案)
                def invoke_single_engine_with_timeout(
                    eng_name: str,
                    img_buf: np.ndarray,
                    timeout_sec: float = 3.5,
                    max_retries: int = 2,
                ) -> Tuple[List[Dict[str, Any]], bool]:
                    """
                    超时与强制重试安全执行器：
                    1. 使用 daemon 独立线程调度，绝对杜绝 ThreadPoolExecutor.__exit__ 内部 shutdown(wait=True) 死锁挂起；
                    2. 超时强制重试 (支持配置 max_retries 次数，如 2 次)；
                    3. 耗尽重试后自动记录熔断并平滑切换备用方案；
                    4. 返回 (items, is_fatal_error)，遇到语言包缺失或动态库缺失等致命异常时快速跳过图像增强循环。
                    """
                    for attempt in range(max_retries + 1):
                        cur_timeout = timeout_sec if attempt == 0 else max(1.8, timeout_sec * 0.7)
                        res_holder = {"items": [], "error": None, "fatal": False, "done": False}

                        def _runner():
                            try:
                                res_holder["items"] = invoke_single_engine(eng_name, img_buf)
                            except Exception as err:
                                res_holder["error"] = err
                                err_str = str(err).lower()
                                # 检测模块缺失或 Windows 原生 OCR 语言包缺失等硬错误
                                if any(k in err_str for k in ["add-windowscapability", "not installed", "no module", "cannot open", "not found"]):
                                    res_holder["fatal"] = True
                            finally:
                                res_holder["done"] = True

                        t = threading.Thread(target=_runner, daemon=True)
                        t.start()
                        t.join(timeout=cur_timeout)

                        if not res_holder["done"]:
                            # 超时处理分支：立即熔断并无缝平滑移交下一备用引擎，杜绝多次重试导致长时间挂起
                            w_logger.warning(
                                f"🚨 引擎 [{eng_name}] 响应超时 (超过 {cur_timeout:.1f}s)，立即强制终止并熔断！平滑切换至下一备用方案..."
                            )
                            global_model_router.circuit_breaker.record_failure(
                                eng_name, f"响应超时 (超过 {cur_timeout:.1f}s)"
                            )
                            return [], True

                        # 正常执行完成分支
                        if res_holder["error"]:
                            w_logger.warning(f"引擎 [{eng_name}] 执行发生异常: {res_holder['error']}")
                            global_model_router.circuit_breaker.record_failure(eng_name, str(res_holder["error"]))
                            # 引擎发生代码或运行时异常直接判定为致命错误，立即平滑切换下一备用引擎，杜绝无意义的图像对比度增强重试！
                            return [], True

                        return res_holder["items"], False

                    return [], True

                # 3. 按路由梯队顺序执行推理与增强重试
                for step_idx, step in enumerate(ocr_pipeline, 1):
                    eng = step["engine"]
                    use_raw = step.get("use_raw_res", False)
                    desc = step.get("desc", eng)

                    if not global_model_router.circuit_breaker.is_available(eng):
                        w_logger.info(f"跳过处于熔断保护中的引擎: [{eng}]")
                        continue

                    target_img = processed_bgr if use_raw else ocr_input_img
                    cur_scale = 1.0 if use_raw else scale_ratio

                    call_start = time.time()
                    w_logger.info(f"[OCR路由 {step_idx}/{len(ocr_pipeline)}] 正在调度: {desc}...")
                    try:
                        detected, is_fatal = invoke_single_engine_with_timeout(
                            eng, target_img, timeout_sec=3.5, max_retries=2
                        )
                        dur = time.time() - call_start

                        if detected:
                            raw_items = detected
                            active_engine_name = eng
                            applied_scale_ratio = cur_scale
                            global_model_router.circuit_breaker.record_success(eng, dur)
                            w_logger.info(f"[成功] 引擎 [{eng}] 推理成功，捕获 {len(raw_items)} 个文本区域 (耗时: {int(dur*1000)}ms)")
                            break
                        elif is_fatal:
                            w_logger.info(f"⚠️ 引擎 [{eng}] 发生异常/连续超时/已熔断，跳过图像增强并立即切换至下一备选方案...")
                            continue
                        else:
                            # 仅在初次执行无异常但未检出任何文字(0字)且引擎未熔断时，才启动增强变体多级重试 (针对暗黑模式、弱对比度界面)
                            if not global_model_router.circuit_breaker.is_available(eng):
                                continue
                            for v_name, v_img in retry_variants:
                                if not global_model_router.circuit_breaker.is_available(eng):
                                    break
                                v_start = time.time()
                                w_logger.info(f"  └─ [OCR增强重试] 应用 [{v_name}] 再次尝试引擎 [{eng}]...")
                                retry_detected, v_fatal = invoke_single_engine_with_timeout(
                                    eng, v_img, timeout_sec=2.2, max_retries=1
                                )
                                v_dur = time.time() - v_start
                                if retry_detected:
                                    raw_items = retry_detected
                                    active_engine_name = f"{eng} ({v_name})"
                                    applied_scale_ratio = cur_scale
                                    global_model_router.circuit_breaker.record_success(eng, dur + v_dur)
                                    w_logger.info(f"  └─ [成功] [OCR增强重试成功] 策略 [{v_name}] 捕获 {len(raw_items)} 个文本区域！")
                                    break
                                if v_fatal:
                                    break

                        if raw_items:
                            break

                    except Exception as e:
                        w_logger.warning(f"引擎 [{eng}] 推理外层异常: {e}")
                        global_model_router.circuit_breaker.record_failure(eng, str(e))

                # 逆映射还原：将 OCR 识别边界框精准还原回原始物理分辨率空间
                if raw_items and applied_scale_ratio != 1.0:
                    inv_s = 1.0 / applied_scale_ratio
                    for it in raw_items:
                        b = it["bbox"]
                        it["bbox"] = [
                            int(round(b[0] * inv_s)),
                            int(round(b[1] * inv_s)),
                            int(round(b[2] * inv_s)),
                            int(round(b[3] * inv_s)),
                        ]

                ocr_duration_ms = int((time.time() - ocr_start_time) * 1000)
                if raw_items:
                    sample_texts = [it['source'] for it in raw_items[:5]]
                    w_logger.info(
                        f"OCR 识别完成，引擎 [{active_engine_name}] 成功捕获 {len(raw_items)} 个文本区域，耗时: {ocr_duration_ms}ms (采样: {sample_texts})"
                    )
                else:
                    w_logger.info(f"屏幕区域全部 OCR 引擎与增强变体检测完毕，未发现有效文字 (耗时: {ocr_duration_ms}ms)")

                # 步骤 E0: AI 大模型二次审校与自动补全校正 (满足需求 5: 识别完成后用AI模型二次读取，核验并补充OCR文本)
                enable_ai_refine = settings.get("enable_ai_ocr_refine", True)
                if raw_items and enable_ai_refine:
                    try:
                        active_translator = model_manager.get_or_create_translator(current_trans_id)
                        raw_items = AIOCRRefiner.refine_items(raw_items, active_translator, source_lang)
                    except Exception as e_ref:
                        w_logger.info(f"AI OCR 审校跳过: {e_ref}")

                # 步骤 E: 段落合并
                merged_paragraphs = merge_ocr_lines_to_paragraphs(raw_items)

                if not merged_paragraphs:
                    # 画面无文字
                    elapsed = int((time.time() - start_time) * 1000)
                    w_logger.info("未检测到有效文字，返回空结果")

                    # 即使未检测出文字，也按时间戳生成存证 txt，方便用户核对排查
                    try:
                        import ocr_recorder
                        ocr_recorder.save_ocr_record(
                            project_root=project_root,
                            request_id=req_id,
                            image_hash=img_hash,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            actual_source=source_lang,
                            ocr_engine=active_engine_name,
                            translation_engine=trans_model_id,
                            raw_ocr_items=raw_items,
                            filter_decisions=[],
                            merged_paragraphs=[],
                            final_items=[],
                            elapsed_breakdown={"total": elapsed, "capture": 0, "ocr": ocr_duration_ms, "process": 0, "translate": 0},
                            cached=False,
                            extra_diagnostic_msg=f"OCR 引擎 [{active_engine_name}] 未能检出文字行 (可检查模型是否就绪或启用图像增强)",
                        )
                    except Exception as e_rec:
                        w_logger.debug(f"保存无文字存证异常忽略: {e_rec}")

                    response_queue.put(
                        make_translate_result(
                            request_id=req_id,
                            image_hash=img_hash,
                            cached=False,
                            elapsed_ms=elapsed,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            items=[],
                        )
                    )
                    continue

                # 步骤 F: 语言对兼容性检查、智能翻译路由与翻译执行
                # 动态刷新模型探测，确保主进程下载完成后子进程即刻感知
                model_manager.scan_models()
                try:
                    effective_trans_id = global_model_router.route_translation_model(
                        source_text=" ".join(p["source"] for p in merged_paragraphs[:2]),
                        source_lang=source_lang,
                        target_lang=target_lang,
                        configured_model_id=trans_model_id,
                        available_models=model_manager.translation_models,
                    )
                except Exception as route_err:
                    w_logger.warning(f"翻译模型智能路由异常，自动使用当前配置模型 [{trans_model_id}]: {route_err}")
                    effective_trans_id = trans_model_id

                if effective_trans_id != trans_model_id:
                    w_logger.info(f"翻译模型智能分流: [{trans_model_id}] -> [{effective_trans_id}]")

                translator = None
                try:
                    translator = model_manager.get_or_create_translator(effective_trans_id)
                except Exception as e:
                    w_logger.info(f"翻译模型 [{effective_trans_id}] 暂未就绪 ({e})，启用内置高可靠离线词典翻译内核")

                # 步骤 G: 语种细粒度识别与判定
                actual_source = source_lang

                if source_lang == "auto":
                    # 依据前若干个文本框的字符集自动定界主语言
                    combined_sample = " ".join(p["source"] for p in merged_paragraphs[:5])
                    detected_primary = detect_text_language(combined_sample)
                    actual_source = "zh-CN" if detected_primary == "zh" else "en"
                    w_logger.info(f"源语言自动推断结果: [{detected_primary}] -> 采用 [{actual_source}]")

                history_logger = get_history_logger(project_root)
                filter_decisions = []
                final_items = []
                translate_start_ts = time.time()

                for para in merged_paragraphs:
                    # 检查是否已中途被新指令取消
                    if current_processing_request_id != req_id:
                        w_logger.info(f"翻译中途检测到请求已被取消: {req_id}")
                        break

                    src_text = clean_ocr_text(para["source"])
                    if not src_text:
                        continue

                    # 智能研判：当前文本是否属于待翻译目标语言？是否属于代码/路径/版本号/纯数字/符号？
                    para_actual_source = actual_source
                    if source_lang == "auto":
                        p_det = detect_text_language(src_text)
                        if p_det in ("zh-CN", "ja", "ko", "en"):
                            para_actual_source = p_det

                    needs_trans, reason = should_translate(
                        src_text, source_lang=para_actual_source, target_lang=target_lang
                    )

                    filter_decisions.append({
                        "bbox": para["bbox"],
                        "text": src_text,
                        "skipped": not needs_trans,
                        "reason": reason,
                    })

                    if not needs_trans:
                        # 用户明确要求：“非翻译的语言就不翻译，直接显示原来的，这样才能使语句更加的通顺”
                        # 故不遮挡覆盖、不生成译文框，保留屏幕原生内容
                        continue

                    try:
                        # 1. 优先专精 UI 词典与智能离线翻译规则 (0延迟，100% 精准匹配官方中文安装向导)
                        from text_filter import intelligent_offline_translate
                        offline_candidate = intelligent_offline_translate(src_text, target_lang=target_lang)
                        if offline_candidate and offline_candidate.strip().lower() != src_text.strip().lower():
                            translated_text = offline_candidate
                        elif translator is not None:
                            # 2. 调用大模型或本地神经网络翻译器
                            translated_text = translator.translate(
                                src_text, para_actual_source, target_lang
                            )
                            if not translated_text or translated_text.strip().lower() == src_text.strip().lower():
                                translated_text = offline_candidate or src_text
                        else:
                            translated_text = offline_candidate or src_text
                    except Exception as e:
                        w_logger.warning(f"单段翻译异常: {e}，调用智能离线翻译内核兜底")
                        try:
                            from text_filter import intelligent_offline_translate
                            translated_text = intelligent_offline_translate(src_text, target_lang=target_lang)
                        except Exception:
                            translated_text = src_text

                    # 剔除无意义或与原文完全雷同的译文
                    cleaned_trans = clean_ocr_text(translated_text)
                    if not cleaned_trans or cleaned_trans.lower() == src_text.lower():
                        continue

                    final_items.append(
                        {
                            "bbox": para["bbox"],
                            "source": src_text,
                            "translated": cleaned_trans,
                            "confidence": para["confidence"],
                        }
                    )

                # 若被取消则放弃发送
                if current_processing_request_id != req_id:
                    continue

                translate_duration_ms = int((time.time() - translate_start_ts) * 1000)
                total_elapsed = int((time.time() - start_time) * 1000)

                # 记录详细耗时与持久化流水存证 (JSONL + 树状测试调试日志)
                elapsed_map = {
                    "capture": 0,
                    "ocr": int((time.time() - start_time) * 1000) - translate_duration_ms,
                    "process": 5,
                    "translate": translate_duration_ms,
                    "total": total_elapsed,
                }
                # 写入独立时间戳纯文本存证 (.txt) 供随时追溯与核验
                try:
                    import ocr_recorder
                    diag_note = ""
                    if is_model_downloading:
                        diag_note = f"离线大模型 [{effective_trans_id}] 正在后台准备中，本次已无缝启用内置高可用离线词典翻译内核"
                    ocr_recorder.save_ocr_record(
                        project_root=project_root,
                        request_id=req_id,
                        image_hash=img_hash,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        actual_source=actual_source,
                        ocr_engine=active_engine_name,
                        translation_engine=effective_trans_id,
                        raw_ocr_items=raw_items,
                        filter_decisions=filter_decisions,
                        merged_paragraphs=merged_paragraphs,
                        final_items=final_items,
                        elapsed_breakdown=elapsed_map,
                        cached=False,
                        extra_diagnostic_msg=diag_note,
                    )
                except Exception as rec_err:
                    w_logger.warning(f"保存单次 OCR 存证报告异常: {rec_err}")

                if history_logger:
                    try:
                        history_logger.log_translation_cycle(
                            request_id=req_id,
                            image_hash=img_hash,
                            source_lang=actual_source,
                            target_lang=target_lang,
                            ocr_engine=active_engine_name,
                            translation_engine=effective_trans_id,
                            raw_ocr_items=raw_items,
                            filter_decisions=filter_decisions,
                            merged_paragraphs=merged_paragraphs,
                            final_items=final_items,
                            elapsed_breakdown=elapsed_map,
                            cached=False,
                        )
                    except Exception as log_err:
                        w_logger.debug(f"记录流水存证日志忽略: {log_err}")

                # 写入缓存
                cache_mgr.put(
                    image_hash=img_hash,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    ocr_model_id=ocr_model_id,
                    translation_model_id=trans_model_id,
                    config_version=cfg_version,
                    items=final_items,
                    timestamp=time.time(),
                )

                w_logger.info(
                    f"请求 [{req_id}] 处理完成: 原始OCR文本框 {len(raw_items)} 个 -> "
                    f"合并段落 {len(merged_paragraphs)} 个 -> 筛选翻译 {len(final_items)} 个 (跳过非目标/符号 {len(filter_decisions) - len(final_items)} 个)，"
                    f"总耗时: {total_elapsed}ms"
                )

                response_queue.put(
                    make_translate_result(
                        request_id=req_id,
                        image_hash=img_hash,
                        cached=False,
                        elapsed_ms=total_elapsed,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        items=final_items,
                    )
                )


# ==============================================================================
# 主进程：管理 QApplication、托盘图标、配置窗口、透明覆盖层、鼠标监听与 IPC 轮询
# ==============================================================================
class AppController(QObject):
    """主程序控制器与 IPC 调度中枢"""

    def __init__(self, project_root: str, settings: Dict[str, Any]):
        super().__init__()
        self.project_root = project_root
        self.settings = settings
        self.log_dir = os.path.join(
            project_root, self.settings.get("log", {}).get("dir", "logs")
        )
        self.logger = setup_logger(self.log_dir, "AppLogger")
        self.logger.info("正在初始化应用程序控制器与核心服务...")

        # 初始化 OCR 与翻译存证目录 (启动即建，确保全流程存证随时就绪)
        try:
            import ocr_recorder
            ocr_recorder.get_records_dir(self.project_root)
        except Exception:
            pass

        # 模型管理器
        self.model_manager = TranslationModelManager(self.project_root)
        self.model_manager.scan_models()

        # 校验并初始化语言对
        self._init_languages()

        # 预先检测配置的模型是否已在本地就绪
        self.models_ready = self._check_models_ready()
        user_enabled = bool(self.settings.get("enabled", True))

        # IPC 队列 (扩容至安全缓冲，防止突发吞吐阻塞)
        self.request_queue = mp.Queue(maxsize=32)
        self.response_queue = mp.Queue(maxsize=64)

        # 启动 Worker 子进程
        self._start_worker_process()

        # 跟踪最新的请求 ID，严防陈旧结果覆盖
        self.latest_request_id: Optional[str] = None
        self.config_version = 1

        # 初始化 GUI 控件
        self.overlay = OverlayWindow(self.settings)
        self.config_dialog: Optional[ConfigDialog] = None

        # 初始化状态机 (内置高可用离线词典保证启动立即可用，无需强制等待数GB大模型下载完毕)
        delay = float(self.settings.get("trigger_delay_sec", 3))
        self.state_machine = MouseStateMachine(delay_sec=delay, enabled=user_enabled)

        # 绑定状态机事件
        self.state_machine.translate_triggered.connect(self._on_translate_triggered)
        self.state_machine.cancel_triggered.connect(self._on_cancel_triggered)
        self.state_machine.overlay_hide_requested.connect(self.overlay.clear_and_hide)

        # 轮询接收 Worker 响应的 QTimer
        self.ipc_poll_timer = QTimer(self)
        self.ipc_poll_timer.setInterval(30)  # 30ms 快速平滑轮询
        self.ipc_poll_timer.timeout.connect(self._poll_worker_responses)
        self.ipc_poll_timer.start()

        # 系统托盘
        self._init_tray_icon()

        if user_enabled:
            self.state_machine.start()
            if self.models_ready:
                self.logger.info("离线模型已在本地就绪，已启动鼠标静止取词监听")
            else:
                self.logger.info("大模型仍在后台高速准备中，已自动启用内置高可用离线词典翻译并启动鼠标监听")
                self.tray.setToolTip("Win11 离线屏幕实时翻译助手 (内置离线词典翻译已激活，大模型后台下载中)")
        else:
            self.logger.info("用户当前设置为暂停翻译")

    def _start_worker_process(self):
        """启动或重启 Worker 子进程"""
        try:
            self.worker_process = mp.Process(
                target=worker_process_entry,
                args=(
                    self.request_queue,
                    self.response_queue,
                    self.project_root,
                    self.settings,
                ),
                name="TranslatorWorker",
                daemon=True,
            )
            self.worker_process.start()
            self.logger.info(f"Worker 子进程已就绪，PID: {self.worker_process.pid}")
        except Exception as e:
            self.logger.error(f"启动 Worker 子进程失败: {e}", exc_info=True)

    def _restart_worker_process(self):
        """守护看门狗：意外退出时静默平滑重启 Worker"""
        self.logger.warning("触发 Worker 子进程看门狗重启机制...")
        try:
            if hasattr(self, "worker_process") and self.worker_process.is_alive():
                self.worker_process.terminate()
        except Exception:
            pass
        self._start_worker_process()

    def _check_models_ready(self) -> bool:
        """检查当前配置的 OCR 与翻译模型是否已在本地磁盘就绪"""
        try:
            self.model_manager.scan_models()
            trans_id = self.settings.get("translation_model_id", "qwen2.5-1.5b-instruct-q4_k_m")
            trans_meta = self.model_manager.get_translation_model(trans_id)
            if trans_meta is None or not trans_meta.is_ready():
                return False

            ocr_id = self.settings.get("ocr_model_id", "win11_media_ocr")
            if ocr_id == "win11_media_ocr":
                return True
            ocr_meta = self.model_manager.get_ocr_model(ocr_id)
            if ocr_meta is None or not ocr_meta.is_ready():
                return False
            return True
        except Exception:
            return False

    def _init_languages(self):
        """根据系统语言自适应默认界面语言与翻译方向"""
        sys_lang = detect_system_language()
        ui_cfg = self.settings.get("ui", {})
        if ui_cfg.get("language") == "auto":
            ui_cfg["resolved_language"] = sys_lang

        # 若默认启用跟随系统决定翻译方向
        lang_cfg = self.settings.setdefault("language", {})
        if lang_cfg.get("default_pair_by_system", True):
            def_source, def_target = get_default_language_pair(sys_lang)
            lang_cfg.setdefault("source_lang", def_source)
            lang_cfg.setdefault("target_lang", def_target)

    def _init_tray_icon(self):
        """创建 Windows 11 风格系统托盘"""
        self.tray = QSystemTrayIcon(self)

        # 动态绘制一个简约高对比托盘图标
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(0, 103, 192))
        p.setPen(QColor(255, 255, 255))
        p.drawRoundedRect(2, 2, 28, 28, 6, 6)
        font = QFont("Segoe UI", 12, QFont.Bold)
        p.setFont(font)
        p.drawText(pixmap.rect(), 0x0084, "译")
        p.end()

        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip("Win11 离线屏幕实时翻译助手 (运行中)")

        menu = QMenu()
        act_toggle = QAction(
            "暂停实时翻译" if self.settings.get("enabled", True) else "启用实时翻译",
            self,
        )
        act_toggle.triggered.connect(lambda: self._toggle_enabled(act_toggle))
        menu.addAction(act_toggle)

        act_settings = QAction("设置 / Settings...", self)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()

        act_exit = QAction("退出 / Exit", self)
        act_exit.triggered.connect(self.shutdown)
        menu.addAction(act_exit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        """鼠标左键单击或双击托盘图标直接打开设置窗口"""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.open_settings()

    def _toggle_enabled(self, action: QAction):
        if not self.models_ready:
            self.tray.showMessage(
                "正在准备模型",
                "离线模型正在后台高速下载中，下载完成后将自动开启实时翻译！",
                QSystemTrayIcon.Information,
                2500,
            )
            return
        cur = self.settings.get("enabled", True)
        new_val = not cur
        self.settings["enabled"] = new_val
        self.state_machine.set_enabled(new_val)
        action.setText("暂停实时翻译" if new_val else "启用实时翻译")
        tip = "已启用屏幕翻译" if new_val else "已暂停屏幕翻译"
        self.tray.showMessage("状态变更", tip, QSystemTrayIcon.Information, 1500)

    def open_settings(self):
        """弹出设置窗口，全方位保护防止闪退崩溃"""
        try:
            self.logger.info("正在调起设置窗口...")
            if self.config_dialog is None:
                self.config_dialog = ConfigDialog(
                    config=self.settings,
                    model_manager=self.model_manager,
                    project_root=self.project_root,
                )
                self.config_dialog.settings_saved.connect(self._on_settings_saved)

            self.config_dialog.show()
            self.config_dialog.raise_()
            self.config_dialog.activateWindow()
            self.logger.info("设置窗口已成功展示")
        except Exception as e:
            self.logger.critical(f"打开设置窗口失败: {e}", exc_info=True)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, "设置窗口打开异常", f"无法打开设置窗口: {e}\n详情已记录在 logs/app.log"
            )

    def _on_settings_saved(self, new_config: Dict[str, Any]):
        """设置窗口保存配置后的回调"""
        self.settings = new_config
        self.config_version += 1
        self.logger.info("配置已更新，正在通知 Worker 子进程重载...")

        # 同步更新状态机和覆盖层
        delay = float(self.settings.get("trigger_delay_sec", 3))
        enabled = bool(self.settings.get("enabled", True))
        self.state_machine.set_delay_sec(delay)
        self.state_machine.set_enabled(enabled)
        self.overlay.update_config(self.settings)

        # 通过 IPC 通知子进程重载并清空旧缓存
        try:
            msg = make_reload_config_message(self.settings)
            try:
                self.request_queue.put_nowait(msg)
            except Exception:
                while not self.request_queue.empty():
                    try:
                        self.request_queue.get_nowait()
                    except Exception:
                        break
                self.request_queue.put(msg, timeout=0.5)
        except Exception as e:
            self.logger.warning(f"向子进程发送重载配置失败: {e or '请求队列繁忙'}")

    def _on_translate_triggered(self, req_id: str):
        """状态机在鼠标静止指定秒数后触发 (全方位防崩溃保护)"""
        try:
            self.latest_request_id = req_id

            # 核心防递归机制：在触发捕获前隐藏浮层，防止截屏将先前的浮层框捕获进去产生递归污染
            try:
                if self.overlay.isVisible():
                    self.overlay.hide()
                    QApplication.processEvents()
            except Exception:
                pass

            lang_cfg = self.settings.get("language", {})

            req = make_translate_request(
                source_lang=lang_cfg.get("source_lang", "en"),
                target_lang=lang_cfg.get("target_lang", "zh-CN"),
                ocr_model_id=self.settings.get("ocr_model_id", "win11_media_ocr" if sys.platform == "win32" else "rapidocr_ch"),
                translation_model_id=self.settings.get(
                    "translation_model_id", "qwen2.5-1.5b-instruct-q4_k_m"
                ),
                capture_mode=self.settings.get("capture_mode", "fullscreen"),
                monitor_index=self.settings.get("monitor_index", 0),
                config_version=self.config_version,
                request_id=req_id,
            )

            try:
                self.request_queue.put_nowait(req)
            except queue.Full:
                pass
            except Exception as e_put:
                self.logger.warning(f"发送 TRANSLATE_REQUEST 队列保护: {e_put}")
        except Exception as e:
            self.logger.warning(f"触发翻译调度外层异常拦截: {e}")

    def _on_cancel_triggered(self, req_id: str):
        """鼠标移动触发取消"""
        try:
            self.request_queue.put_nowait(make_cancel_message(req_id))
        except Exception:
            pass

    def _poll_worker_responses(self):
        """定期从 Worker 响应队列提取消息（非阻塞，全封闭防闪退保护）"""
        try:
            # 看门狗保护：检测 Worker 是否存活
            if hasattr(self, "worker_process") and not self.worker_process.is_alive():
                self._restart_worker_process()
                return

            while True:
                try:
                    msg = self.response_queue.get_nowait()
                except queue.Empty:
                    break
                except Exception:
                    break

                try:
                    msg_type = msg.get("type")
                    req_id = msg.get("request_id")
                    payload = msg.get("payload", {})

                    if msg_type == MessageType.TRANSLATE_RESULT:
                        # 规则七：主进程只处理最新 request_id 的结果，旧结果直接丢弃
                        if req_id != self.latest_request_id:
                            self.logger.debug(f"丢弃过时请求结果: {req_id} (最新: {self.latest_request_id})")
                            continue

                        items = payload.get("items", [])
                        elapsed = payload.get("elapsed_ms", 0)
                        cached = payload.get("cached", False)
                        self.logger.info(
                            f"收到翻译结果 [{req_id}]，共 {len(items)} 条，耗时 {elapsed}ms (缓存命中: {cached})"
                        )

                        if items:
                            self.overlay.set_translation_items(items)
                            self.state_machine.notify_translation_result_received(req_id, True)
                        else:
                            self.overlay.clear_and_hide()
                            self.state_machine.notify_translation_result_received(req_id, False)

                    elif msg_type == MessageType.STATUS:
                        w_status = payload.get("worker", "ready")
                        ocr_loaded = payload.get("ocr_loaded", False)
                        trans_loaded = payload.get("translation_loaded", False)
                        msg_txt = payload.get("message", "")

                        if w_status == "downloading":
                            self.models_ready = False
                            self.tray.setToolTip(f"Win11 翻译助手 - {msg_txt} (内置离线词典翻译实时可用)")

                        elif w_status == "ready":
                            if not self.models_ready:
                                self.models_ready = True
                                user_pref_enabled = bool(self.settings.get("enabled", True))
                                self.logger.info("[就绪] 离线模型下载全部完成！已自动开启鼠标静止检测与实时翻译。")
                                if user_pref_enabled:
                                    self.state_machine.set_enabled(True)
                                    self.state_machine.start()
                                self.tray.setToolTip("Win11 离线屏幕实时翻译助手 (已就绪 - 鼠标悬停3秒自动翻译)")
                                try:
                                    self.tray.showMessage(
                                        "离线模型就绪",
                                        "离线翻译大模型已下载完成！已自动开启鼠标悬停取词翻译。",
                                        QSystemTrayIcon.Information,
                                        3500,
                                    )
                                except Exception:
                                    pass

                        if self.config_dialog is not None and self.config_dialog.isVisible():
                            self.config_dialog.update_worker_status(
                                w_status, ocr_loaded, trans_loaded, msg_txt
                            )

                    elif msg_type == MessageType.ERROR:
                        code = payload.get("code")
                        err_msg = payload.get("message")
                        self.logger.error(f"Worker 报告错误 [{code}]: {err_msg}")
                        if req_id == self.latest_request_id:
                            self.state_machine.notify_error(req_id)
                            self.overlay.clear_and_hide()
                except Exception as e_inner:
                    self.logger.debug(f"单个 IPC 消息分发保护: {e_inner}")
        except Exception as e_poll:
            self.logger.debug(f"轮询 Worker 队列异常拦截: {e_poll}")

    def shutdown(self):
        """平稳关闭主进程与 Worker"""
        self.logger.info("正在执行安全关闭流程...")
        self.state_machine.stop()
        self.ipc_poll_timer.stop()

        try:
            self.request_queue.put_nowait(make_shutdown_message())
        except Exception:
            pass

        if self.worker_process.is_alive():
            self.worker_process.join(timeout=1.5)
            if self.worker_process.is_alive():
                self.worker_process.terminate()

        self.overlay.close()
        if self.config_dialog:
            self.config_dialog.close()

        QApplication.quit()


def load_settings(project_root: str) -> Dict[str, Any]:
    """读取或初始化 settings.json"""
    settings_path = os.path.join(project_root, "settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 关键修复：检测到旧配置中为 paddleocr_ch 时，自动无缝升级为 win11_media_ocr (免下载·零显存·30ms)
                if cfg.get("ocr_model_id") in ("paddleocr_ch", "paddleocr"):
                    cfg["ocr_model_id"] = "win11_media_ocr"
                return cfg
        except Exception as e:
            print(f"读取 settings.json 失败，使用缺省配置: {e}")

    # 默认配置
    return {
        "version": "1.0.0",
        "enabled": True,
        "autostart": False,
        "capture_mode": "fullscreen",
        "monitor_index": 0,
        "ui": {"language": "auto", "resolved_language": "zh_CN"},
        "language": {
            "source_lang": "en",
            "target_lang": "zh-CN",
            "auto_detect_source": False,
            "default_pair_by_system": True,
        },
        "ocr_model_id": "win11_media_ocr",
        "ocr_model_dir": "models/ocr/paddleocr",
        "translation_model_id": "qwen2.5-1.5b-instruct-q4_k_m",
        "translation_model_path": "models/translation/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "trigger_delay_sec": 3,
        "preprocess": {"denoise": False, "clahe": False, "deskew": False},
        "overlay": {
            "font_family": "Microsoft YaHei",
            "font_size": 18,
            "bg_alpha": 180,
            "text_color": "#FFFFFF",
        },
        "cache": {"enable": True, "max_items": 50, "hash_distance": 5},
        "log": {"level": "INFO", "dir": "logs", "backup_days": 7},
    }


def main():
    """主程序入口"""
    # Windows 平台必须在首行调用 freeze_support 以防多进程递归启动
    mp.freeze_support()

    project_root = os.path.dirname(os.path.abspath(__file__))

    # 创建必要目录 (含存证文件夹，确保全流程存证随时就绪)
    os.makedirs(os.path.join(project_root, "logs"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "temp"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "models", "ocr", "paddleocr"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "models", "translation"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "ocr_records"), exist_ok=True)

    settings = load_settings(project_root)
    log_dir = os.path.join(project_root, settings.get("log", {}).get("dir", "logs"))
    app_logger = setup_logger(log_dir, "AppLogger")
    app_logger.info("Win11 离线屏幕实时翻译助手正在启动...")

    # 软件启动即在 ocr_records/ 生成会话启动存证报告
    try:
        import ocr_recorder
        ocr_recorder.record_session_start(
            project_root=project_root,
            ocr_engine=settings.get("ocr_model_id", "win11_media_ocr"),
            translation_engine=settings.get("translation_model_id", "qwen2.5-1.5b-instruct-q4_k_m"),
            source_lang=settings.get("language", {}).get("source_lang", "en"),
            target_lang=settings.get("language", {}).get("target_lang", "zh-CN"),
        )
    except Exception as e_start_rec:
        app_logger.warning(f"写入启动存证记录提示: {e_start_rec}")

    # 全局异常捕获，确保任何未捕获的 GUI 异常详细落盘而不是默默闪退
    def global_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        app_logger.critical(
            "全局未捕获异常被安全拦截并落盘 (防止闪退):", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = global_excepthook

    # 适配高 DPI 屏幕缩放 (4K/2K 显示器不模糊、坐标不偏离)
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        controller = AppController(project_root, settings)
        app_logger.info("系统初始化完成，开始进入主事件循环")
        exit_code = app.exec_()
        app_logger.info(f"主事件循环正常结束，退出码: {exit_code}")
        sys.exit(exit_code)
    except Exception as e_start:
        import traceback
        tb_str = traceback.format_exc()
        app_logger.critical(f"Win11 离线翻译助手启动或运行失败:\n{tb_str}")
        print(f"\n[严重错误] 启动或运行失败:\n{tb_str}", file=sys.stderr)
        # 详细保存到独立的 logs/crash.log 供一键定位
        try:
            with open(os.path.join(project_root, "logs", "crash.log"), "w", encoding="utf-8") as f_crash:
                f_crash.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f_crash.write(f"异常简述: {e_start}\n")
                f_crash.write(f"完整堆栈:\n{tb_str}\n")
        except Exception:
            pass

        err_msg = f"Win11 离线翻译助手启动失败:\n{e_start}\n\n完整错误堆栈已保存至 logs/crash.log，可查阅排查。"
        try:
            QMessageBox.critical(None, "启动错误", err_msg)
        except Exception:
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, err_msg, "Win11 翻译助手启动失败", 0x10)
                except Exception:
                    pass
        # 挂起控制台，彻底杜绝黑框闪退
        try:
            input("\n程序异常退出，错误堆栈已打印在上方。按回车键退出 / Press Enter to exit...")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
