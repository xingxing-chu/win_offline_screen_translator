"""
Win11 离线屏幕实时翻译助手 - 设置与配置图形界面
文件: config_gui.py
功能: 提供基于 PyQt5 的现代化 Windows 11 风格设置窗口，包含语言配置（系统自适应）、
     模型动态选择与兼容性校验、延时滑块、自启动设置、日志调取与实时状态面板。
"""

import json
import locale
import logging
import os
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QFont, QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from translation_engine import TranslationModelManager
import model_downloader

logger = logging.getLogger(__name__)


# ---------------- 多语言文字资源定义 ----------------
I18N = {
    "zh_CN": {
        "window_title": "Win11 离线屏幕实时翻译助手 - 设置",
        "tab_general": "常规设置",
        "enable_translation": "启用屏幕实时翻译",
        "autostart": "开机自动启动",
        "trigger_delay": "鼠标静止触发延时 (秒):",
        "lang_section": "语言与区域设置",
        "ui_lang": "界面显示语言:",
        "source_lang": "翻译源语言:",
        "target_lang": "翻译目标语言:",
        "auto_system": "跟随系统 (Auto)",
        "lang_zh": "简体中文 (zh-CN)",
        "lang_en": "English (en)",
        "lang_auto_detect": "自动检测 (Auto Detect)",
        "lang_ja": "日本語 (ja)",
        "lang_ko": "한국어 (ko)",
        "lang_fr": "Français (fr)",
        "lang_de": "Deutsch (de)",
        "lang_es": "Español (es)",
        "lang_ru": "Русский (ru)",
        "model_section": "离线模型选择",
        "ocr_model": "OCR 文字识别模型:",
        "trans_model": "离线翻译模型:",
        "model_supported_langs": "支持语言对: ",
        "model_unsupported_warning": "⚠️ 当前模型不支持所选语言对，请更换模型！",
        "model_supported_ok": "✓ 当前模型完全支持所选语言对",
        "status_section": "系统与组件运行状态",
        "app_version": "软件版本: ",
        "worker_status": "Worker 进程: ",
        "ocr_status": "OCR 模块: ",
        "trans_status": "翻译引擎: ",
        "status_unloaded": "未加载 (首次翻译时懒加载)",
        "status_loaded": "已加载至内存/显存",
        "status_ready": "准备就绪",
        "ocr_enhance_section": "OCR 图像增强与智能重试",
        "auto_route": "启用多模型自动路由 (根据语言/分辨率/健康度智能调度)",
        "auto_invert_dark": "启用暗黑模式自动反相 (提升深色主题/VSCode等识别率)",
        "clahe_enhance": "启用局部对比度自适应均衡 (CLAHE)",
        "sharpen_enhance": "启用 ClearType 字体边缘抗锯齿锐化",
        "adaptive_retry": "启用自适应多级重试机制 (未检出时智能应用增强变体)",
        "btn_save": "保存并应用设置",
        "btn_view_logs": "查看运行日志",
        "btn_view_debug_logs": "查看翻译详情存证",
        "btn_close": "关闭",
        "save_success": "配置已成功保存，已清空旧翻译缓存并同步至子进程！",
        "log_not_found": "日志文件尚未生成或不存在。",
    },
    "en_US": {
        "window_title": "Win11 Offline Screen Translator - Settings",
        "tab_general": "General Settings",
        "enable_translation": "Enable Real-time Screen Translation",
        "autostart": "Launch on System Startup",
        "trigger_delay": "Mouse Idle Trigger Delay (sec):",
        "lang_section": "Language & Region",
        "ui_lang": "UI Language:",
        "source_lang": "Source Language:",
        "target_lang": "Target Language:",
        "auto_system": "Follow System (Auto)",
        "lang_zh": "Simplified Chinese (zh-CN)",
        "lang_en": "English (en)",
        "lang_auto_detect": "Auto Detect",
        "lang_ja": "Japanese (ja)",
        "lang_ko": "Korean (ko)",
        "lang_fr": "French (fr)",
        "lang_de": "German (de)",
        "lang_es": "Spanish (es)",
        "lang_ru": "Russian (ru)",
        "model_section": "Offline Models Selection",
        "ocr_model": "OCR Engine & Model:",
        "trans_model": "Translation Model:",
        "model_supported_langs": "Supported: ",
        "model_unsupported_warning": "⚠️ Current model does not support this language pair!",
        "model_supported_ok": "✓ Model supports current language pair",
        "status_section": "Runtime & Component Status",
        "app_version": "Version: ",
        "worker_status": "Worker Process: ",
        "ocr_status": "OCR Module: ",
        "trans_status": "Translation Engine: ",
        "status_unloaded": "Unloaded (Lazy load on first trigger)",
        "status_loaded": "Loaded into memory",
        "status_ready": "Ready",
        "ocr_enhance_section": "OCR Enhancement & Auto Routing",
        "auto_route": "Enable Multi-Model Auto Routing (Language/Resolution/Health aware)",
        "auto_invert_dark": "Auto Invert Dark Mode (Improves dark themes/IDEs)",
        "clahe_enhance": "Enable Adaptive Contrast Enhancement (CLAHE)",
        "sharpen_enhance": "Enable ClearType Font Edge Sharpening",
        "adaptive_retry": "Enable Adaptive Multi-Stage Retry with Enhanced Variants",
        "btn_save": "Save & Apply",
        "btn_view_logs": "View App Logs",
        "btn_view_debug_logs": "View Translation Records",
        "btn_close": "Close",
        "save_success": "Configuration saved successfully. Cache invalidated and synced!",
        "log_not_found": "Log file has not been created yet.",
    },
}


def detect_system_language() -> str:
    """
    根据宿主操作系统语言环境返回规范代码。
    若以 zh 开头返回 'zh_CN'，以 en 开头返回 'en_US'，其他默认 'en_US'。
    """
    try:
        sys_lang = locale.getdefaultlocale()[0] or ""
        if sys_lang.lower().startswith("zh"):
            return "zh_CN"
        elif sys_lang.lower().startswith("en"):
            return "en_US"
        return "en_US"
    except Exception:
        return "zh_CN"


def get_default_language_pair(ui_lang: str) -> (str, str):
    """
    根据系统语言自动决定的翻译默认方向：
    系统语言为中文：默认 en -> zh-CN
    系统语言为英文：默认 zh-CN -> en
    """
    if ui_lang == "zh_CN":
        return "en", "zh-CN"
    else:
        return "zh-CN", "en"


class DownloadWorker(QThread):
    """后台多线程模型与依赖下载器，保证 PyQt5 主事件循环丝滑响应不卡顿且具备强健的异常自愈能力"""
    progress_signal = pyqtSignal(object, object, float)  # downloaded_bytes, total_bytes, speed_kb_s (使用 object 杜绝大模型 32 位整型溢出)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, model_ids: List[str]):
        super().__init__()
        self.model_ids = model_ids
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            for mid in self.model_ids:
                if self._is_cancelled:
                    self.finished_signal.emit(False, "下载已由用户主动取消")
                    return
                self.status_signal.emit(f"正在配置离线组件: {mid}...")
                ok = model_downloader.ensure_model_ready(
                    mid,
                    auto_download=True,
                    progress_callback=self._safe_emit_progress,
                    status_callback=self._safe_emit_status,
                    is_cancelled=lambda: self._is_cancelled,
                )
                if not ok and not self._is_cancelled:
                    self.finished_signal.emit(False, f"模型 [{mid}] 下载配置未完成，请检查网络连接或日志")
                    return
            if not self._is_cancelled:
                self.finished_signal.emit(True, "所选离线模型及依赖已全部就绪！")
        except Exception as e:
            logger.error(f"DownloadWorker 运行异常: {e}", exc_info=True)
            if not self._is_cancelled:
                self.finished_signal.emit(False, f"下载过程遇到异常: {e}")

    def _safe_emit_progress(self, d, t, s):
        if not self._is_cancelled:
            try:
                self.progress_signal.emit(d, t, s)
            except Exception:
                pass

    def _safe_emit_status(self, msg):
        if not self._is_cancelled:
            try:
                self.status_signal.emit(str(msg))
            except Exception:
                pass


class ModelDownloadDialog(QDialog):
    """离线模型全自动下载与 GUI 实时指示器窗口"""

    def __init__(self, model_ids: List[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.model_ids = model_ids
        self.setWindowTitle("离线模型自动下载与配置")
        self.setMinimumWidth(540)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.lbl_title = QLabel("正在从高速镜像站下载并配置离线模型...")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #111827;")
        layout.addWidget(self.lbl_title)

        self.lbl_status = QLabel("正在连接国内开源镜像源 (ModelScope / HF-Mirror / 清华源)...")
        self.lbl_status.setStyleSheet("color: #4B5563; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #E5E7EB; border-radius: 10px; text-align: center; background-color: #F3F4F6; font-size: 11px; font-weight: 600; }"
            "QProgressBar::chunk { background-color: #0067C0; border-radius: 9px; }"
        )
        layout.addWidget(self.progress_bar)

        self.lbl_metrics = QLabel("已下载: 0.0 MB | 实时下载速度: 0.0 KB/s")
        self.lbl_metrics.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(self.lbl_metrics)

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(120)
        self.txt_log.setStyleSheet("background-color: #F9FAFB; border: 1px solid #E5E7EB; font-family: Consolas, 'Courier New', monospace; font-size: 11px; color: #374151;")
        layout.addWidget(self.txt_log)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消下载")
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_finish = QPushButton("完成")
        self.btn_finish.setEnabled(False)
        self.btn_finish.setStyleSheet("QPushButton { background-color: #0067C0; color: white; border: none; padding: 6px 18px; border-radius: 4px; font-weight: 600; }"
                                      "QPushButton:disabled { background-color: #CBD5E1; }")
        self.btn_finish.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_finish)

        layout.addLayout(btn_layout)

        # 启动后台下载线程
        self.worker = DownloadWorker(self.model_ids)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.status_signal.connect(self._on_status)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, downloaded: Any, total: Any, speed: float):
        try:
            d_val = int(downloaded) if downloaded else 0
            t_val = int(total) if total else 0
            if t_val > 0:
                pct = max(0, min(100, int((d_val / t_val) * 100)))
                self.progress_bar.setValue(pct)
                self.lbl_metrics.setText(
                    f"已下载: {d_val / 1024 / 1024:.1f} MB / {t_val / 1024 / 1024:.1f} MB ({pct}%) | 实时速度: {speed:.1f} KB/s"
                )
            else:
                self.lbl_metrics.setText(f"已下载: {d_val / 1024 / 1024:.1f} MB | 实时速度: {speed:.1f} KB/s")
        except Exception:
            pass

    def _on_status(self, msg: str):
        try:
            self.lbl_status.setText(msg)
            self.txt_log.appendPlainText(msg)
        except Exception:
            pass

    def _on_finished(self, success: bool, msg: str):
        try:
            self.btn_cancel.setEnabled(False)
            self.btn_finish.setEnabled(True)
            self.txt_log.appendPlainText(f"\n[任务结果] {msg}")
            if success:
                self.progress_bar.setValue(100)
                self.lbl_title.setText("✓ 离线模型下载与配置成功！")
                self.lbl_status.setText(msg)
            else:
                self.lbl_title.setText("⚠️ 下载流程已停止或遇到异常")
                self.lbl_status.setText(msg)
        except Exception:
            pass

    def _on_cancel_clicked(self):
        try:
            self.lbl_status.setText("正在取消下载，请稍候...")
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.btn_finish.setEnabled(True)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self.worker.progress_signal.disconnect()
            self.worker.status_signal.disconnect()
            self.worker.finished_signal.disconnect()
        except Exception:
            pass
        if self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(800)
        event.accept()


class ModelMirrorsDialog(QDialog):
    """离线模型高速下载与全部备用镜像中心对话框"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("🌐 离线模型高速下载与备用镜像中心 (Offline Models Mirrors)")
        self.resize(800, 600)
        self.setMinimumSize(700, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # 头部说明卡片
        intro_box = QFrame()
        intro_box.setStyleSheet(
            "QFrame { background-color: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 8px; padding: 12px; }"
        )
        intro_layout = QVBoxLayout(intro_box)
        intro_layout.setSpacing(4)
        intro_layout.setContentsMargins(8, 8, 8, 8)

        lbl_head = QLabel("⚡ 离线模型多源容灾高速镜像网络")
        lbl_head.setStyleSheet("font-size: 14px; font-weight: bold; color: #0369A1;")
        intro_layout.addWidget(lbl_head)

        lbl_desc = QLabel(
            "• 系统已预先配置【ModelScope 阿里官方极速源】、【HF-Mirror 国内镜像】、【Hugging Face 官方直连】、【百度飞桨 BOS】等多个备用高速下载节点。\n"
            "• 遇到网络波动时系统会自动无缝重试下一镜像；您也可以点击【复制链接】使用迅雷/IDM直接多线程高速下载。\n"
            "• 下载后的文件直接放置于 models/ 对应文件夹内，软件将秒级自动识别并标记为【已就绪】！"
        )
        lbl_desc.setStyleSheet("font-size: 12px; color: #0C4A6E; line-height: 1.5;")
        lbl_desc.setWordWrap(True)
        intro_layout.addWidget(lbl_desc)

        layout.addWidget(intro_box)

        # 选项卡切换 (OCR 模型 / 翻译模型)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 6px; }"
            "QTabBar::tab { background: #F1F5F9; padding: 8px 20px; font-weight: 600; font-size: 13px; color: #475569; border-top-left-radius: 6px; border-top-right-radius: 6px; }"
            "QTabBar::tab:selected { background: #FFFFFF; color: #0067C0; border-bottom: 2px solid #0067C0; }"
        )

        summary = model_downloader.get_all_mirrors_summary()

        # Tab 1: 翻译模型
        tab_trans = self._create_model_list_widget(summary.get("translation", []))
        self.tabs.addTab(tab_trans, "🤖 离线神经翻译大模型 (GGUF / CTranslate2)")

        # Tab 2: OCR 模型
        tab_ocr = self._create_model_list_widget(summary.get("ocr", []))
        self.tabs.addTab(tab_ocr, "🔍 离线文字识别 OCR 引擎 (ONNX / Tar / Win11)")

        layout.addWidget(self.tabs)

        # 底部操作栏
        bottom_layout = QHBoxLayout()

        btn_open_models_dir = QPushButton("📂 打开本地 models/ 根目录")
        btn_open_models_dir.setStyleSheet("padding: 7px 14px; font-size: 12px;")
        btn_open_models_dir.clicked.connect(self._open_models_dir)
        bottom_layout.addWidget(btn_open_models_dir)

        btn_download_recommended = QPushButton("⚡ 一键自动下载推荐组合 (RapidOCR + Qwen2.5 0.5B)")
        btn_download_recommended.setStyleSheet(
            "QPushButton { background-color: #0067C0; color: white; border: none; padding: 7px 16px; border-radius: 5px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background-color: #00559E; }"
        )
        btn_download_recommended.clicked.connect(self._download_recommended_combo)
        bottom_layout.addWidget(btn_download_recommended)

        bottom_layout.addStretch()

        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet("padding: 7px 20px; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)

        layout.addLayout(bottom_layout)

    def _create_model_list_widget(self, models: List[Dict[str, Any]]) -> QWidget:
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setSpacing(14)
        v_layout.setContentsMargins(12, 12, 12, 12)

        for m in models:
            m_id = m.get("id", "")
            card = QFrame()
            is_ready = m.get("ready", False)
            border_col = "#86EFAC" if is_ready else "#CBD5E1"
            bg_col = "#F0FDF4" if is_ready else "#FFFFFF"
            card.setStyleSheet(
                f"QFrame {{ background-color: {bg_col}; border: 1px solid {border_col}; border-radius: 8px; padding: 12px; }}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)

            # 标题与状态
            h_header = QHBoxLayout()
            lbl_title = QLabel(f"<b>{m.get('name', m_id)}</b>")
            lbl_title.setStyleSheet("font-size: 13px; color: #1E293B;")
            h_header.addWidget(lbl_title)

            h_header.addStretch()

            status_txt = m.get("status_label", "未就绪")
            status_badge = QLabel(f" {status_txt} ")
            if is_ready:
                status_badge.setStyleSheet(
                    "background-color: #22C55E; color: white; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;"
                )
            else:
                status_badge.setStyleSheet(
                    "background-color: #F59E0B; color: white; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 11px;"
                )
            h_header.addWidget(status_badge)

            btn_dl = QPushButton("⚡ 立即下载")
            btn_dl.setStyleSheet(
                "QPushButton { background-color: #0284C7; color: white; border: none; padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 11px; }"
                "QPushButton:hover { background-color: #0369A1; }"
            )
            btn_dl.clicked.connect(lambda checked, mid=m_id: self._trigger_download(mid))
            h_header.addWidget(btn_dl)

            card_layout.addLayout(h_header)

            # 描述
            desc = m.get("description", "")
            if desc:
                lbl_desc = QLabel(f"<i>{desc}</i>")
                lbl_desc.setStyleSheet("color: #64748B; font-size: 11px;")
                lbl_desc.setWordWrap(True)
                card_layout.addWidget(lbl_desc)

            # 镜像列表
            mirrors = m.get("backup_mirrors", [])
            if mirrors:
                mir_group = QFrame()
                mir_group.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px;")
                mir_layout = QVBoxLayout(mir_group)
                mir_layout.setSpacing(6)
                mir_layout.setContentsMargins(6, 6, 6, 6)

                lbl_mir_title = QLabel(f"<b>备用镜像与高速下载链接 ({len(mirrors)} 个):</b>")
                lbl_mir_title.setStyleSheet("font-size: 11px; color: #334155;")
                mir_layout.addWidget(lbl_mir_title)

                for idx, mir in enumerate(mirrors, 1):
                    row = QHBoxLayout()
                    lbl_src = QLabel(f"[{idx}] {mir.get('source', '镜像源')}:")
                    lbl_src.setStyleSheet("font-size: 11px; color: #475569; font-weight: 500;")
                    row.addWidget(lbl_src)

                    txt_url = QLineEdit(mir.get("url", ""))
                    txt_url.setReadOnly(True)
                    txt_url.setStyleSheet("font-size: 11px; background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 3px; padding: 2px 6px; color: #1E293B;")
                    row.addWidget(txt_url, 1)

                    btn_copy = QPushButton("📋 复制")
                    btn_copy.setStyleSheet("font-size: 11px; padding: 3px 8px;")
                    btn_copy.clicked.connect(lambda checked, u=mir.get("url", ""): self._copy_to_clipboard(u))
                    row.addWidget(btn_copy)

                    mir_layout.addLayout(row)

                card_layout.addWidget(mir_group)

            v_layout.addWidget(card)

        v_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(container)
        return scroll

    def _copy_to_clipboard(self, url: str):
        try:
            QApplication.clipboard().setText(url)
            QMessageBox.information(self, "已复制", f"已复制下载链接至剪贴板！\n\n可直接粘贴至浏览器、迅雷或 IDM 下载:\n{url}")
        except Exception as e:
            QMessageBox.warning(self, "复制提示", f"复制失败: {e}\n链接为:\n{url}")

    def _trigger_download(self, model_id: str):
        dlg = ModelDownloadDialog([model_id], parent=self)
        dlg.exec_()

    def _download_recommended_combo(self):
        combo = ["rapidocr_ch", "qwen2.5-0.5b-instruct-q4_k_m"]
        dlg = ModelDownloadDialog(combo, parent=self)
        dlg.exec_()

    def _open_models_dir(self):
        root = model_downloader.get_project_root()
        m_dir = os.path.join(root, "models")
        os.makedirs(m_dir, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(m_dir)
            else:
                import subprocess
                subprocess.call(["xdg-open", m_dir])
        except Exception as e:
            QMessageBox.warning(self, "提示", f"打开文件夹失败: {e}")


class ConfigDialog(QDialog):
    """现代化配置对话框窗口"""

    settings_saved = pyqtSignal(dict)  # 当用户点击保存并校验通过时发出

    def __init__(
        self,
        config: Dict[str, Any],
        model_manager: TranslationModelManager,
        project_root: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config = json.loads(json.dumps(config))  # 深拷贝
        self.model_manager = model_manager
        self.project_root = project_root

        # 解析当前界面语言
        self.current_ui_lang = self._resolve_current_ui_language()

        # 状态记录
        self.worker_online = False
        self.ocr_loaded = False
        self.translation_loaded = False

        self.init_ui()
        self.load_values_to_ui()
        self.apply_theme_style()

    def _resolve_current_ui_language(self) -> str:
        ui_cfg = self.config.get("ui", {}).get("language", "auto")
        if ui_cfg == "auto":
            return detect_system_language()
        elif ui_cfg in ("zh_CN", "zh-CN", "zh"):
            return "zh_CN"
        else:
            return "en_US"

    def t(self, key: str) -> str:
        """获取当前语言文本"""
        bundle = I18N.get(self.current_ui_lang, I18N["zh_CN"])
        return bundle.get(key, key)

    def init_ui(self):
        """构建图形界面控件 - Windows 11 Fluent 现代化选项卡布局，带 QScrollArea 杜绝任何界面挤压"""
        self.setWindowTitle(self.t("window_title"))
        self.resize(780, 620)
        self.setMinimumSize(680, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        self.tabs = QTabWidget()

        # =====================================================================
        # 选项卡 1: 🌐 语言与常规设置 (Language & General)
        # =====================================================================
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        tab1_layout.setSpacing(14)
        tab1_layout.setContentsMargins(12, 12, 12, 12)

        # 1. 语言与区域设置分组
        lang_group = QGroupBox(self.t("lang_section"))
        lang_layout = QGridLayout(lang_group)
        lang_layout.setVerticalSpacing(10)
        lang_layout.setHorizontalSpacing(14)

        # 界面语言
        lang_layout.addWidget(QLabel(self.t("ui_lang")), 0, 0)
        self.combo_ui_lang = QComboBox()
        self.combo_ui_lang.addItem(self.t("auto_system"), "auto")
        self.combo_ui_lang.addItem("简体中文 (zh-CN)", "zh_CN")
        self.combo_ui_lang.addItem("English (en)", "en_US")
        self.combo_ui_lang.currentIndexChanged.connect(self._on_ui_language_changed)
        lang_layout.addWidget(self.combo_ui_lang, 0, 1)

        # 源语言
        lang_layout.addWidget(QLabel(self.t("source_lang")), 1, 0)
        self.combo_source_lang = QComboBox()
        self._populate_language_options(self.combo_source_lang, is_source=True)
        self.combo_source_lang.currentIndexChanged.connect(self._validate_model_compatibility)
        lang_layout.addWidget(self.combo_source_lang, 1, 1)

        # 目标语言
        lang_layout.addWidget(QLabel(self.t("target_lang")), 2, 0)
        self.combo_target_lang = QComboBox()
        self._populate_language_options(self.combo_target_lang, is_source=False)
        self.combo_target_lang.currentIndexChanged.connect(self._validate_model_compatibility)
        lang_layout.addWidget(self.combo_target_lang, 2, 1)

        tab1_layout.addWidget(lang_group)

        # 常规与触发配置分组
        general_group = QGroupBox(self.t("tab_general"))
        gen_layout = QGridLayout(general_group)
        gen_layout.setVerticalSpacing(10)
        gen_layout.setHorizontalSpacing(14)

        self.chk_enabled = QCheckBox(self.t("enable_translation"))
        gen_layout.addWidget(self.chk_enabled, 0, 0, 1, 2)

        self.chk_autostart = QCheckBox(self.t("autostart"))
        gen_layout.addWidget(self.chk_autostart, 1, 0, 1, 2)

        # 鼠标静止延时
        gen_layout.addWidget(QLabel(self.t("trigger_delay")), 2, 0)
        delay_container = QHBoxLayout()
        self.slider_delay = QSlider(Qt.Horizontal)
        self.slider_delay.setRange(1, 10)
        self.slider_delay.setSingleStep(1)
        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(1, 10)
        self.spin_delay.setSuffix(" s")

        self.slider_delay.valueChanged.connect(self.spin_delay.setValue)
        self.spin_delay.valueChanged.connect(self.slider_delay.setValue)

        delay_container.addWidget(self.slider_delay)
        delay_container.addWidget(self.spin_delay)
        gen_layout.addLayout(delay_container, 2, 1)

        tab1_layout.addWidget(general_group)
        tab1_layout.addStretch()

        # 包装到平滑可滚动区域
        scroll_tab1 = QScrollArea()
        scroll_tab1.setWidgetResizable(True)
        scroll_tab1.setFrameShape(QFrame.NoFrame)
        scroll_tab1.setWidget(tab1_widget)
        self.tabs.addTab(scroll_tab1, "🌐 语言与常规")

        # =====================================================================
        # 选项卡 2: 🤖 离线模型管理 (Offline Models & Downloader)
        # =====================================================================
        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout(tab2_widget)
        tab2_layout.setSpacing(14)
        tab2_layout.setContentsMargins(12, 12, 12, 12)

        model_group = QGroupBox(self.t("model_section"))
        model_layout = QGridLayout(model_group)
        model_layout.setVerticalSpacing(10)
        model_layout.setHorizontalSpacing(14)

        # OCR 模型
        model_layout.addWidget(QLabel(self.t("ocr_model")), 0, 0)
        self.combo_ocr_model = QComboBox()
        self._populate_ocr_models()
        self.combo_ocr_model.currentIndexChanged.connect(self._validate_model_compatibility)
        model_layout.addWidget(self.combo_ocr_model, 0, 1)

        # 翻译模型
        model_layout.addWidget(QLabel(self.t("trans_model")), 1, 0)
        self.combo_trans_model = QComboBox()
        self._populate_trans_models()
        self.combo_trans_model.currentIndexChanged.connect(self._validate_model_compatibility)
        model_layout.addWidget(self.combo_trans_model, 1, 1)

        # 模型支持语言状态提示标签
        self.lbl_model_compatibility = QLabel()
        self.lbl_model_compatibility.setWordWrap(True)
        model_layout.addWidget(self.lbl_model_compatibility, 2, 0, 1, 2)

        # 模型就绪状态与本地体积详情卡片
        self.lbl_selected_model_info = QLabel()
        self.lbl_selected_model_info.setStyleSheet(
            "QLabel { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px 14px; font-size: 12px; line-height: 1.5; color: #1E293B; }"
        )
        self.lbl_selected_model_info.setWordWrap(True)
        model_layout.addWidget(self.lbl_selected_model_info, 3, 0, 1, 2)

        # 离线模型一键自动下载与状态检查按钮
        self.btn_download_models = QPushButton("⚡ 一键检查/自动下载所选离线模型")
        self.btn_download_models.setStyleSheet(
            "QPushButton { background-color: #0067C0; color: white; border: none; padding: 8px 16px; border-radius: 5px; font-weight: 600; font-size: 13px; }"
            "QPushButton:hover { background-color: #00559E; }"
        )
        self.btn_download_models.clicked.connect(self._on_download_models_clicked)
        model_layout.addWidget(self.btn_download_models, 4, 0, 1, 2)

        # 离线模型多源备用镜像与下载中心
        self.btn_open_mirrors = QPushButton("🌐 查看所有离线模型备用下载链接与镜像中心 (支持复制多源链接)")
        self.btn_open_mirrors.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #0067C0; border: 1px solid #0067C0; padding: 7px 16px; border-radius: 5px; font-weight: 600; font-size: 12px; }"
            "QPushButton:hover { background-color: #F0F9FF; }"
        )
        self.btn_open_mirrors.clicked.connect(self._on_open_mirrors_clicked)
        model_layout.addWidget(self.btn_open_mirrors, 5, 0, 1, 2)

        tab2_layout.addWidget(model_group)
        tab2_layout.addStretch()

        scroll_tab2 = QScrollArea()
        scroll_tab2.setWidgetResizable(True)
        scroll_tab2.setFrameShape(QFrame.NoFrame)
        scroll_tab2.setWidget(tab2_widget)
        self.tabs.addTab(scroll_tab2, "🤖 离线模型管理")

        # =====================================================================
        # 选项卡 3: 🔍 OCR 增强与识别 (OCR & Enhancement)
        # =====================================================================
        tab3_widget = QWidget()
        tab3_layout = QVBoxLayout(tab3_widget)
        tab3_layout.setSpacing(14)
        tab3_layout.setContentsMargins(12, 12, 12, 12)

        ocr_group = QGroupBox(self.t("ocr_enhance_section"))
        ocr_layout = QGridLayout(ocr_group)
        ocr_layout.setVerticalSpacing(10)
        ocr_layout.setHorizontalSpacing(14)

        self.chk_auto_route = QCheckBox(self.t("auto_route"))
        self.chk_auto_invert_dark = QCheckBox(self.t("auto_invert_dark"))
        self.chk_clahe = QCheckBox(self.t("clahe_enhance"))
        self.chk_sharpen = QCheckBox(self.t("sharpen_enhance"))
        self.chk_adaptive_retry = QCheckBox(self.t("adaptive_retry"))
        self.chk_ai_ocr_refine = QCheckBox("启用 AI 大模型二次审校与自动补全校正 (修正 OCR 笔误与断词)")
        self.chk_ai_ocr_refine.setToolTip("在 OCR 识别完成后，调用 AI 大模型对识别文本进行语法审校，自动修正拼写笔误并补全断词")

        ocr_layout.addWidget(self.chk_auto_route, 0, 0, 1, 2)
        ocr_layout.addWidget(self.chk_auto_invert_dark, 1, 0, 1, 2)
        ocr_layout.addWidget(self.chk_clahe, 2, 0)
        ocr_layout.addWidget(self.chk_sharpen, 2, 1)
        ocr_layout.addWidget(self.chk_adaptive_retry, 3, 0, 1, 2)
        ocr_layout.addWidget(self.chk_ai_ocr_refine, 4, 0, 1, 2)

        tab3_layout.addWidget(ocr_group)
        tab3_layout.addStretch()

        scroll_tab3 = QScrollArea()
        scroll_tab3.setWidgetResizable(True)
        scroll_tab3.setFrameShape(QFrame.NoFrame)
        scroll_tab3.setWidget(tab3_widget)
        self.tabs.addTab(scroll_tab3, "🔍 OCR 增强与识别")

        # =====================================================================
        # 选项卡 4: 📊 运行状态与日志存证 (Status, Evidence & Logs)
        # =====================================================================
        tab4_widget = QWidget()
        tab4_layout = QVBoxLayout(tab4_widget)
        tab4_layout.setSpacing(14)
        tab4_layout.setContentsMargins(12, 12, 12, 12)

        status_group = QGroupBox(self.t("status_section"))
        status_layout = QVBoxLayout(status_group)
        status_layout.setSpacing(8)

        self.lbl_app_info = QLabel(f"{self.t('app_version')} v{self.config.get('version', '1.0.0')}")
        self.lbl_worker_info = QLabel(f"{self.t('worker_status')} {self.t('status_ready')}")
        self.lbl_ocr_info = QLabel(f"{self.t('ocr_status')} {self.t('status_unloaded')}")
        self.lbl_trans_info = QLabel(f"{self.t('trans_status')} {self.t('status_unloaded')}")

        status_layout.addWidget(self.lbl_app_info)
        status_layout.addWidget(self.lbl_worker_info)
        status_layout.addWidget(self.lbl_ocr_info)
        status_layout.addWidget(self.lbl_trans_info)
        tab4_layout.addWidget(status_group)

        # 存证系统快速操作卡片
        records_group = QGroupBox("📁 OCR 与翻译存证系统 (ocr_records/)")
        rec_layout = QVBoxLayout(records_group)
        rec_layout.setSpacing(8)

        lbl_rec_desc = QLabel(
            "系统已激活全流程存证机制：每次屏幕截取、原始 OCR 文字、二次审校与最终翻译呈现，"
            "均会以时间戳纯文本 (.txt) 文件自动保存至 <b>ocr_records</b> 目录，方便随时核对排查。"
        )
        lbl_rec_desc.setWordWrap(True)
        lbl_rec_desc.setStyleSheet("color: #475569; font-size: 12px; line-height: 1.4;")
        rec_layout.addWidget(lbl_rec_desc)

        rec_btn_layout = QHBoxLayout()
        btn_tab_records = QPushButton("📂 打开存证目录 (ocr_records)")
        btn_tab_records.clicked.connect(self._open_records_dir)
        rec_btn_layout.addWidget(btn_tab_records)

        btn_tab_latest = QPushButton("📄 查看最新单次存证")
        btn_tab_latest.clicked.connect(self._open_latest_record)
        rec_btn_layout.addWidget(btn_tab_latest)

        btn_tab_log = QPushButton("📜 查看今日运行日志")
        btn_tab_log.clicked.connect(self._open_log_file)
        rec_btn_layout.addWidget(btn_tab_log)

        rec_layout.addLayout(rec_btn_layout)
        tab4_layout.addWidget(records_group)
        tab4_layout.addStretch()

        scroll_tab4 = QScrollArea()
        scroll_tab4.setWidgetResizable(True)
        scroll_tab4.setFrameShape(QFrame.NoFrame)
        scroll_tab4.setWidget(tab4_widget)
        self.tabs.addTab(scroll_tab4, "📊 运行状态与日志存证")

        main_layout.addWidget(self.tabs)

        # =====================================================================
        # 底部常驻功能按钮栏 (布局清晰舒朗，防止按钮横向堆叠导致界面挤压)
        # =====================================================================
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_open_records = QPushButton("📂 存证目录")
        self.btn_open_records.setToolTip("打开 OCR 与翻译结果存证文件夹 (ocr_records/)")
        self.btn_open_records.clicked.connect(self._open_records_dir)
        btn_layout.addWidget(self.btn_open_records)

        self.btn_view_logs = QPushButton("📜 查看日志")
        self.btn_view_logs.setToolTip("查看今日全流程操作与翻译日志 (logs/YYYY-MM-DD.log)")
        self.btn_view_logs.clicked.connect(self._open_log_file)
        btn_layout.addWidget(self.btn_view_logs)

        btn_layout.addStretch()

        self.btn_close = QPushButton(self.t("btn_close"))
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        self.btn_save = QPushButton(self.t("btn_save"))
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def _populate_language_options(self, combo: QComboBox, is_source: bool):
        """填充支持的语言列表"""
        combo.clear()
        if is_source:
            combo.addItem(self.t("lang_auto_detect"), "auto")
        combo.addItem(self.t("lang_en"), "en")
        combo.addItem(self.t("lang_zh"), "zh-CN")
        combo.addItem(self.t("lang_ja"), "ja")
        combo.addItem(self.t("lang_ko"), "ko")
        combo.addItem(self.t("lang_fr"), "fr")
        combo.addItem(self.t("lang_de"), "de")
        combo.addItem(self.t("lang_es"), "es")
        combo.addItem(self.t("lang_ru"), "ru")

    def _populate_ocr_models(self):
        """从模型管理器动态填充 OCR 模型下拉框，带有直观的状态标识"""
        self.combo_ocr_model.clear()
        for m_id, meta in self.model_manager.ocr_models.items():
            status_info = model_downloader.get_model_status(m_id)
            tag = f"[{status_info['label']}]"
            display = f"{meta.name} {tag}"
            self.combo_ocr_model.addItem(display, m_id)

    def _populate_trans_models(self):
        """从模型管理器动态填充翻译模型下拉框，带有直观的状态标识"""
        self.combo_trans_model.clear()
        for m_id, meta in self.model_manager.translation_models.items():
            status_info = model_downloader.get_model_status(m_id)
            tag = f"[{status_info['label']}]"
            display = f"{meta.name} [{meta.engine}] {tag}"
            self.combo_trans_model.addItem(display, m_id)

    def load_values_to_ui(self):
        """将 settings.json 的配置注入控件"""
        # 启用状态
        self.chk_enabled.setChecked(self.config.get("enabled", True))
        self.chk_autostart.setChecked(self.config.get("autostart", False))

        # 延时
        delay = int(self.config.get("trigger_delay_sec", 3))
        self.slider_delay.setValue(delay)
        self.spin_delay.setValue(delay)

        # 界面语言
        saved_ui_lang = self.config.get("ui", {}).get("language", "auto")
        idx = self.combo_ui_lang.findData(saved_ui_lang)
        if idx >= 0:
            self.combo_ui_lang.setCurrentIndex(idx)

        # 翻译语言
        lang_cfg = self.config.get("language", {})
        s_lang = lang_cfg.get("source_lang", "en")
        t_lang = lang_cfg.get("target_lang", "zh-CN")

        s_idx = self.combo_source_lang.findData(s_lang)
        if s_idx >= 0:
            self.combo_source_lang.setCurrentIndex(s_idx)

        t_idx = self.combo_target_lang.findData(t_lang)
        if t_idx >= 0:
            self.combo_target_lang.setCurrentIndex(t_idx)

        # 模型选择
        saved_ocr = self.config.get("ocr_model_id", "")
        ocr_idx = self.combo_ocr_model.findData(saved_ocr)
        if ocr_idx >= 0:
            self.combo_ocr_model.setCurrentIndex(ocr_idx)

        saved_trans = self.config.get("translation_model_id", "")
        trans_idx = self.combo_trans_model.findData(saved_trans)
        if trans_idx >= 0:
            self.combo_trans_model.setCurrentIndex(trans_idx)

        # OCR 增强预处理与自动路由选项注入
        pre_cfg = self.config.get("preprocess", {})
        self.chk_auto_route.setChecked(self.config.get("auto_route", True))
        self.chk_auto_invert_dark.setChecked(pre_cfg.get("auto_invert_dark", True))
        self.chk_clahe.setChecked(pre_cfg.get("clahe", False))
        self.chk_sharpen.setChecked(pre_cfg.get("sharpen", True))
        self.chk_adaptive_retry.setChecked(self.config.get("adaptive_retry", True))
        self.chk_ai_ocr_refine.setChecked(self.config.get("enable_ai_ocr_refine", True))

        self._validate_model_compatibility()

    def update_worker_status(
        self,
        worker_status: str,
        ocr_loaded: bool,
        trans_loaded: bool,
        msg: str = "",
    ):
        """接收主进程传入的最新状态消息并更新界面展示"""
        self.ocr_loaded = ocr_loaded
        self.translation_loaded = trans_loaded

        status_text = self.t("status_ready") if worker_status == "ready" else worker_status
        self.lbl_worker_info.setText(f"{self.t('worker_status')} {status_text} {msg}")

        ocr_txt = self.t("status_loaded") if ocr_loaded else self.t("status_unloaded")
        self.lbl_ocr_info.setText(f"{self.t('ocr_status')} {ocr_txt}")

        trans_txt = self.t("status_loaded") if trans_loaded else self.t("status_unloaded")
        self.lbl_trans_info.setText(f"{self.t('trans_status')} {trans_txt}")

    def _validate_model_compatibility(self):
        """核心硬性要求：若所选源语言/目标语言不被模型支持，界面显著标红提示；同时动态刷新模型体积与下载状态卡片"""
        s_lang = self.combo_source_lang.currentData()
        t_lang = self.combo_target_lang.currentData()
        model_id = self.combo_trans_model.currentData()
        ocr_id = self.combo_ocr_model.currentData()

        # 1. 刷新语言对兼容性
        if model_id:
            meta = self.model_manager.get_translation_model(model_id)
            if not meta:
                self.lbl_model_compatibility.setText(f"❌ 未找到模型 ID: {model_id}")
                self.lbl_model_compatibility.setStyleSheet("color: #D32F2F; font-weight: bold;")
            else:
                is_supported = meta.supports_pair(s_lang, t_lang)
                supported_str = f"源: {','.join(meta.source_languages)} -> 目标: {','.join(meta.target_languages)}"

                if is_supported:
                    self.lbl_model_compatibility.setText(
                        f"{self.t('model_supported_ok')} ({supported_str})"
                    )
                    self.lbl_model_compatibility.setStyleSheet("color: #2E7D32; font-size: 13px;")
                    self.btn_save.setEnabled(True)
                else:
                    self.lbl_model_compatibility.setText(
                        f"{self.t('model_unsupported_warning')}\n({meta.name} 仅支持 {supported_str})"
                    )
                    self.lbl_model_compatibility.setStyleSheet(
                        "color: #D32F2F; font-weight: bold; font-size: 13px;"
                    )

        # 2. 刷新所选模型的实际磁盘体积与下载就绪状态卡片
        ocr_st = model_downloader.get_model_status(ocr_id) if ocr_id else {}
        trans_st = model_downloader.get_model_status(model_id) if model_id else {}

        ocr_ready = ocr_st.get("ready", False)
        trans_ready = trans_st.get("ready", False)
        ocr_label = ocr_st.get("label", "未就绪")
        trans_label = trans_st.get("label", "未就绪")

        ocr_color = "#2E7D32" if ocr_ready else "#D97706"
        trans_color = "#2E7D32" if trans_ready else "#D97706"

        info_html = (
            f"<b>📊 所选模型就绪与本地文件明细：</b><br>"
            f"• <b>OCR 文字识别:</b> {ocr_id} → "
            f"<span style='color: {ocr_color}; font-weight: bold;'>[{ocr_label}]</span> "
            f"<i>(本地文件: {'✓ 正常' if ocr_ready else '待下载/待配置'})</i><br>"
            f"• <b>离线神经翻译:</b> {model_id} → "
            f"<span style='color: {trans_color}; font-weight: bold;'>[{trans_label}]</span> "
            f"<i>(本地文件: {'✓ 正常' if trans_ready else '待下载/待配置'})</i>"
        )
        self.lbl_selected_model_info.setText(info_html)

        # 3. 动态更新一键下载按钮状态
        if ocr_ready and trans_ready:
            self.btn_download_models.setText("✓ 所选离线模型均已完整就绪 (点击可重新校验/下载)")
            self.btn_download_models.setStyleSheet(
                "QPushButton { background-color: #2E7D32; color: white; border: none; padding: 7px 14px; border-radius: 4px; font-weight: 600; }"
                "QPushButton:hover { background-color: #1E5B24; }"
            )
        else:
            self.btn_download_models.setText("⚡ 一键检查/自动下载未就绪模型 (OCR与翻译)")
            self.btn_download_models.setStyleSheet(
                "QPushButton { background-color: #0067C0; color: white; border: none; padding: 7px 14px; border-radius: 4px; font-weight: 600; }"
                "QPushButton:hover { background-color: #00559E; }"
            )

    def _on_ui_language_changed(self):
        """界面语言变更"""
        new_selection = self.combo_ui_lang.currentData()
        if new_selection == "auto":
            resolved = detect_system_language()
        else:
            resolved = new_selection

        if resolved != self.current_ui_lang:
            self.current_ui_lang = resolved
            QMessageBox.information(
                self,
                "提示 / Notice",
                "界面语言已更新，部分文本在保存重启后将获得完整重构。"
                if resolved == "zh_CN"
                else "UI language updated. Some controls take full effect upon relaunch.",
            )

    def _open_log_file(self):
        """查看当日唯一全流程运行与操作日志 (logs/YYYY-MM-DD.log)"""
        log_dir = os.path.join(self.project_root, self.config.get("log", {}).get("dir", "logs"))
        os.makedirs(log_dir, exist_ok=True)
        today_str = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(log_dir, f"{today_str}.log")

        if not os.path.exists(log_path):
            log_files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")], reverse=True)
            if log_files:
                log_path = os.path.join(log_dir, log_files[0])
            else:
                QMessageBox.information(
                    self, "提示", "今日操作与运行日志尚未生成，请在屏幕上触发一次翻译或执行操作！"
                )
                return

        try:
            if sys.platform == "win32":
                os.startfile(log_path)
            else:
                import subprocess
                subprocess.call(["xdg-open", log_path])
        except Exception as e:
            logger.error(f"打开日志文件失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开日志: {e}")

    def _open_records_dir(self):
        """打开 OCR 与翻译存证文本文件夹 (ocr_records/)"""
        try:
            import ocr_recorder
            ocr_recorder.open_records_directory(self.project_root)
        except Exception as e:
            logger.error(f"打开存证文件夹失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开存证文件夹: {e}")

    def _open_latest_record(self):
        """查看最新单次 OCR 识别与翻译纯文本存证报告"""
        try:
            import ocr_recorder
            latest_file = ocr_recorder.get_latest_record_path(self.project_root)
            if not latest_file or not os.path.exists(latest_file):
                QMessageBox.information(
                    self,
                    "提示",
                    "暂无存证报告！请在屏幕上触发一次识别翻译，系统将自动把原始OCR文字、二次审校与翻译结果保存为时间戳文本文件至 ocr_records 目录。",
                )
                return

            if sys.platform == "win32":
                try:
                    os.startfile(latest_file)
                except Exception:
                    import subprocess
                    subprocess.Popen(["notepad.exe", latest_file])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", latest_file])
        except Exception as e:
            logger.error(f"打开存证报告失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开存证报告: {e}")

    def _on_save_clicked(self):
        """保存配置并将修改记录持久化至今日单日日志中"""
        # 组装新配置
        s_lang = self.combo_source_lang.currentData()
        t_lang = self.combo_target_lang.currentData()
        ocr_model_id = self.combo_ocr_model.currentData()
        trans_model_id = self.combo_trans_model.currentData()

        # 记录用户操作至唯一日志
        logger.info(
            f"[用户操作] 保存配置更新: 源语言={s_lang}, 目标语言={t_lang}, OCR引擎={ocr_model_id}, 翻译模型={trans_model_id}, 自动路由={self.chk_auto_route.isChecked()}"
        )

        # 检查是否支持
        meta = self.model_manager.get_translation_model(trans_model_id)
        if meta and not meta.supports_pair(s_lang, t_lang):
            ret = QMessageBox.question(
                self,
                "语言对不匹配提醒",
                "当前选择的翻译模型可能无法翻译该语言对，是否依然强制保存？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        self.config["enabled"] = self.chk_enabled.isChecked()
        self.config["autostart"] = self.chk_autostart.isChecked()
        self.config["trigger_delay_sec"] = self.spin_delay.value()

        if "ui" not in self.config:
            self.config["ui"] = {}
        self.config["ui"]["language"] = self.combo_ui_lang.currentData()
        self.config["ui"]["resolved_language"] = self.current_ui_lang

        if "language" not in self.config:
            self.config["language"] = {}
        self.config["language"]["source_lang"] = s_lang
        self.config["language"]["target_lang"] = t_lang
        self.config["language"]["auto_detect_source"] = (s_lang == "auto")

        self.config["ocr_model_id"] = ocr_model_id
        self.config["translation_model_id"] = trans_model_id

        # 增强预处理与自动路由配置
        self.config["auto_route"] = self.chk_auto_route.isChecked()
        self.config["adaptive_retry"] = self.chk_adaptive_retry.isChecked()
        self.config["enable_ai_ocr_refine"] = self.chk_ai_ocr_refine.isChecked()
        if "preprocess" not in self.config:
            self.config["preprocess"] = {}
        self.config["preprocess"]["auto_invert_dark"] = self.chk_auto_invert_dark.isChecked()
        self.config["preprocess"]["clahe"] = self.chk_clahe.isChecked()
        self.config["preprocess"]["sharpen"] = self.chk_sharpen.isChecked()

        # 关联模型路径
        ocr_meta = self.model_manager.get_ocr_model(ocr_model_id)
        if ocr_meta:
            self.config["ocr_model_dir"] = ocr_meta.model_path

        trans_meta = self.model_manager.get_translation_model(trans_model_id)
        if trans_meta:
            self.config["translation_model_path"] = trans_meta.model_path

        # 写入 settings.json
        settings_file = os.path.join(self.project_root, "settings.json")
        try:
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info("settings.json 保存成功")

            # 触发向主进程和 Worker 发送更新与清空缓存
            self.settings_saved.emit(self.config)

            QMessageBox.information(self, "成功", self.t("save_success"))
            self.accept()
        except Exception as e:
            logger.error(f"写入 settings.json 失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def _on_download_models_clicked(self):
        """一键检测并启动带 GUI 进度指示器的模型高速下载对话框"""
        ocr_id = self.combo_ocr_model.currentData()
        trans_id = self.combo_trans_model.currentData()

        try:
            # 1. 检查当前 OCR 状态
            ocr_ready = model_downloader.ensure_model_ready(ocr_id, auto_download=False)
            # 2. 检查当前翻译模型状态
            trans_ready = model_downloader.ensure_model_ready(trans_id, auto_download=False)

            if ocr_ready and trans_ready:
                QMessageBox.information(
                    self,
                    "模型状态",
                    f"✓ 所选离线模型已全部就绪！\n\n• OCR: {ocr_id} (已就绪)\n• 翻译: {trans_id} (已就绪)\n无需重复下载。",
                )
                return

            models_to_fetch = []
            if not ocr_ready:
                models_to_fetch.append(ocr_id)
            if not trans_ready:
                models_to_fetch.append(trans_id)

            # 启动专用图形化进度下载指示器
            dlg = ModelDownloadDialog(models_to_fetch, parent=self)
            dlg.exec_()

            # 刷新模型列表与就绪状态标识，并恢复之前的用户选择
            saved_ocr = ocr_id
            saved_trans = trans_id
            self.model_manager.scan_models()
            self._populate_ocr_models()
            self._populate_trans_models()

            if saved_ocr:
                idx_ocr = self.combo_ocr_model.findData(saved_ocr)
                if idx_ocr >= 0:
                    self.combo_ocr_model.setCurrentIndex(idx_ocr)

            if saved_trans:
                idx_trans = self.combo_trans_model.findData(saved_trans)
                if idx_trans >= 0:
                    self.combo_trans_model.setCurrentIndex(idx_trans)

            self._validate_model_compatibility()

        except Exception as e:
            logger.error(f"模型下载调度异常: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"下载管理器调用异常: {e}")

    def _on_open_mirrors_clicked(self):
        """打开全离线模型备用下载链接与镜像中心"""
        try:
            dlg = ModelMirrorsDialog(parent=self)
            dlg.exec_()

            # 重新扫描模型列表并刷新
            ocr_id = self.combo_ocr_model.currentData()
            trans_id = self.combo_trans_model.currentData()
            self.model_manager.scan_models()
            self._populate_ocr_models()
            self._populate_trans_models()

            if ocr_id:
                idx = self.combo_ocr_model.findData(ocr_id)
                if idx >= 0:
                    self.combo_ocr_model.setCurrentIndex(idx)
            if trans_id:
                idx = self.combo_trans_model.findData(trans_id)
                if idx >= 0:
                    self.combo_trans_model.setCurrentIndex(idx)

            self._validate_model_compatibility()
        except Exception as e:
            logger.error(f"打开镜像中心异常: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"打开镜像中心失败: {e}")

    def apply_theme_style(self):
        """注入现代化 Fluent 风格样式表"""
        self.setStyleSheet(
            """
            QDialog {
                background-color: #F9F9FB;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QGroupBox {
                background-color: #FFFFFF;
                border: 1px solid #E0E2E7;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: 600;
                font-size: 14px;
                padding-top: 18px;
                color: #1F2328;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: transparent;
                color: #0067C0;
            }
            QLabel {
                font-size: 13px;
                color: #333333;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 5px 10px;
                min-height: 24px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #0067C0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 13px;
                color: #24292F;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
            QPushButton:default {
                background-color: #0067C0;
                color: #FFFFFF;
                border: none;
                font-weight: 600;
            }
            QPushButton:default:hover {
                background-color: #005A9E;
            }
            QSpinBox {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px 8px;
                background: #FFFFFF;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #E5E7EB;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #0067C0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0067C0;
                width: 16px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 8px;
            }
            QTabWidget::pane {
                border: 1px solid #D1D5DB;
                background: #FFFFFF;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-bottom: none;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                color: #4B5563;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-color: #D1D5DB;
                border-bottom: 1px solid #FFFFFF;
                color: #0067C0;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #E5E7EB;
                color: #111827;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #F3F4F6;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
        )
