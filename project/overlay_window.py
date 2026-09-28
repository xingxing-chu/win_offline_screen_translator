"""
Win11 离线屏幕实时翻译助手 - 屏幕透明覆盖层
文件: overlay_window.py
功能: 使用 PyQt5 创建完全穿透鼠标事件、透明背景且高 DPI / 多显示器自适应的置顶覆盖窗口，
     在原文字区域精确绘制半透明黑色圆角背景与翻译后文本。
"""

import logging
from typing import Any, Dict, List, Optional
from PyQt5.QtCore import Qt, QRectF, QRect
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt5.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


class OverlayWindow(QWidget):
    """
    全屏透明覆盖窗口。
    - 鼠标完全穿透 (Qt.WindowTransparentForInput)
    - 始终置顶 (Qt.WindowStaysOnTopHint)
    - 无边框工具窗 (Qt.FramelessWindowHint | Qt.Tool)
    - 背景全透 (Qt.WA_TranslucentBackground)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        self.items: List[Dict[str, Any]] = []

        # 从配置中提取覆盖层外观参数
        overlay_cfg = self.config.get("overlay", {})
        self.font_family = overlay_cfg.get("font_family", "Microsoft YaHei")
        self.font_size = overlay_cfg.get("font_size", 16)
        self.bg_alpha = overlay_cfg.get("bg_alpha", 180)  # 0~255
        self.text_color_hex = overlay_cfg.get("text_color", "#FFFFFF")

        self.init_window_flags()
        self._apply_capture_exclusion()

    def _apply_capture_exclusion(self):
        """让当前覆盖层在 Windows 10/11 截屏与录屏中彻底隐形，从根源杜绝截图捕获自己造成的递归套娃"""
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                # WDA_EXCLUDEFROMCAPTURE = 0x00000011 (Windows 10 2004+ 及 Windows 11)
                WDA_EXCLUDEFROMCAPTURE = 0x00000011
                res = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
                if res != 0:
                    logger.debug("已成功为覆盖窗口启用 Windows 11 截屏排除保护 (WDA_EXCLUDEFROMCAPTURE)")
            except Exception as e:
                logger.debug(f"设置截屏豁免异常: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_capture_exclusion()

    def init_window_flags(self):
        """设置窗口标志与透明穿透特性"""
        try:
            flags = (
                Qt.FramelessWindowHint
                | Qt.WindowStaysOnTopHint
                | Qt.Tool
                | Qt.WindowTransparentForInput
                | Qt.WindowDoesNotAcceptFocus
            )
            if hasattr(self, "setWindowFlags"):
                self.setWindowFlags(flags)
            if hasattr(self, "setAttribute"):
                self.setAttribute(Qt.WA_TranslucentBackground, True)
                self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        except Exception as e:
            logger.debug(f"设置窗口标志容错: {e}")

        # 覆盖所有可用屏幕几何区域 (多显示器适配)
        self.update_geometry_for_screens()

    def update_geometry_for_screens(self):
        """计算包含所有显示器的虚拟桌面总边界"""
        try:
            desktop = QApplication.desktop() if hasattr(QApplication, "desktop") else None
            if desktop and hasattr(desktop, "geometry"):
                virtual_rect = desktop.geometry()
                self.setGeometry(virtual_rect)
            else:
                self.setGeometry(0, 0, 1920, 1080)
        except Exception:
            try:
                self.setGeometry(0, 0, 1920, 1080)
            except Exception:
                pass

    def update_config(self, new_config: Dict[str, Any]):
        """动态更新配置项并重绘"""
        self.config = new_config
        overlay_cfg = self.config.get("overlay", {})
        self.font_family = overlay_cfg.get("font_family", self.font_family)
        self.font_size = overlay_cfg.get("font_size", self.font_size)
        self.bg_alpha = overlay_cfg.get("bg_alpha", self.bg_alpha)
        self.text_color_hex = overlay_cfg.get("text_color", self.text_color_hex)
        self.update()

    def set_translation_items(self, items: List[Dict[str, Any]]):
        """更新待展示的翻译条目并触发重绘"""
        try:
            self.items = items or []
            if self.items:
                self.update_geometry_for_screens()
                self.show()
                self.update()
            else:
                self.hide()
        except Exception as e:
            logger.debug(f"更新覆盖层条目容错: {e}")

    def clear_and_hide(self):
        """清空条目并隐藏覆盖层"""
        try:
            self.items = []
            self.hide()
            self.update()
        except Exception as e:
            logger.debug(f"隐藏覆盖层容错: {e}")

    def paintEvent(self, event):
        """在透明图层上绘制翻译框和文字"""
        if not self.items:
            return

        try:
            painter = QPainter(self)
        except Exception:
            return

        try:
            if hasattr(painter, "setRenderHint") and hasattr(QPainter, "Antialiasing"):
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.TextAntialiasing, True)

            # 处理高 DPI 缩放比
            dpr = 1.0
            if hasattr(self, "devicePixelRatioF"):
                try:
                    dpr = float(self.devicePixelRatioF())
                except Exception:
                    dpr = 1.0
            elif hasattr(self, "devicePixelRatio"):
                try:
                    dpr = float(self.devicePixelRatio())
                except Exception:
                    dpr = 1.0
            if dpr <= 0:
                dpr = 1.0

            bg_color = QColor(0, 0, 0, self.bg_alpha)
            border_color = QColor(255, 255, 255, 60)
            text_color = QColor(self.text_color_hex)

            base_font = QFont(self.font_family, self.font_size)
            if hasattr(base_font, "setStyleStrategy") and hasattr(QFont, "PreferAntialias"):
                base_font.setStyleStrategy(QFont.PreferAntialias)

            for item in list(self.items):
                try:
                    if item.get("skip_render", False) or item.get("skipped", False):
                        continue
                    bbox = item.get("bbox")  # [x1, y1, x2, y2]
                    translated_text = str(item.get("translated", "")).strip()
                    source_text = str(item.get("source", "")).strip()
                    if not bbox or len(bbox) != 4 or not translated_text:
                        continue
                    # 若原文本与译文完全一致，跳过绘制以保留系统原生文字清晰呈现
                    if translated_text.lower() == source_text.lower() and not item.get("force_render", False):
                        continue

                    x1, y1, x2, y2 = bbox
                    # 将物理像素坐标转为 Qt 逻辑坐标
                    lx = x1 / dpr
                    ly = y1 / dpr
                    lw = max(10.0, (x2 - x1) / dpr)
                    lh = max(10.0, (y2 - y1) / dpr)

                    # 边距容差膨胀，保证文字完全覆盖原文字
                    pad_x = 4.0
                    pad_y = 2.0
                    box_rect = QRectF(lx - pad_x, ly - pad_y, lw + pad_x * 2, lh + pad_y * 2)

                    # 1. 绘制半透明黑色圆角背景框
                    path = QPainterPath()
                    corner_radius = 4.0
                    path.addRoundedRect(box_rect, corner_radius, corner_radius)

                    painter.fillPath(path, bg_color)
                    painter.setPen(QPen(border_color, 1.0))
                    painter.drawPath(path)

                    # 2. 计算最佳文字字号与自动换行/自适应收缩
                    fitted_font, actual_rect = self._fit_text_in_rect(
                        painter, base_font, translated_text, box_rect
                    )

                    # 3. 绘制文字
                    painter.setFont(fitted_font)
                    painter.setPen(QPen(text_color))
                    # 居中偏左对齐绘制
                    align_flag = (Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap) if hasattr(Qt, "AlignVCenter") else 0
                    painter.drawText(box_rect, align_flag, translated_text)
                except Exception:
                    continue
        except Exception as e_paint:
            logger.debug(f"覆盖层绘制捕获异常: {e_paint}")
        finally:
            try:
                if painter.isActive():
                    painter.end()
            except Exception:
                pass

    def _fit_text_in_rect(
        self,
        painter: QPainter,
        base_font: QFont,
        text: str,
        target_rect: QRectF,
    ) -> (QFont, QRectF):
        """
        自动计算文字字号，若默认字号超出矩形区域，则阶梯式微调缩小，
        确保翻译文字尽量完整显示在覆盖区域内。
        """
        font = QFont(base_font)
        min_point_size = 9
        current_size = font.pointSize()

        while current_size >= min_point_size:
            font.setPointSize(current_size)
            metrics = QFontMetricsF(font)
            # 计算换行后所需的外接矩形高度
            needed_rect = metrics.boundingRect(
                target_rect,
                Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap,
                text,
            )
            if (
                needed_rect.height() <= target_rect.height() * 1.2
                and needed_rect.width() <= target_rect.width() * 1.1
            ):
                return font, needed_rect
            current_size -= 1

        font.setPointSize(min_point_size)
        return font, target_rect
