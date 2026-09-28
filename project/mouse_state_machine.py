"""
Win11 离线屏幕实时翻译助手 - 鼠标监听与事件驱动状态机
文件: mouse_state_machine.py
功能: 使用 pynput 全局低开销监听鼠标移动，驱动 PyQt5 QTimer 进行防抖倒计时，
     严格管理 IDLE、WAIT_STABLE、TRANSLATING、SHOWING、PAUSED、ERROR 六大核心状态。
"""

import logging
import time
from enum import Enum
from typing import Callable, Optional

try:
    from pynput import mouse
except Exception:
    mouse = None

try:
    from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
except ImportError:
    class QObject: pass
    class QTimer: pass
    def pyqtSignal(*args, **kwargs): return lambda: None
    class Qt:
        QueuedConnection = None

logger = logging.getLogger(__name__)


class AppState(Enum):
    IDLE = "IDLE"
    WAIT_STABLE = "WAIT_STABLE"
    TRANSLATING = "TRANSLATING"
    SHOWING = "SHOWING"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class MouseListenerSignal(QObject):
    """用于将 pynput 独立监听线程的事件无缝转发到 Qt 主事件循环的信号发射器"""

    mouse_moved = pyqtSignal(int, int)


class MouseStateMachine(QObject):
    """
    鼠标静止识别状态机。
    - 鼠标一旦移动，立即隐藏覆盖层并重启静止计时器。
    - 达到设定静止延迟 (1~10 秒) 后，触发 translate_triggered 信号。
    - 强化防崩溃机制：
      1. 跨线程信号绑定强制使用 Qt.QueuedConnection，杜绝非 GUI 线程直接调用 QWidget 导致的崩溃闪退；
      2. 所有槽函数全量增加顶级 try-except 容错保护，杜绝未捕获异常导致 PyQt5 触发 abort()；
      3. 增加微小抖动阈值过滤 (<= 2 像素)，过滤高回报率鼠标传感器微抖动；
      4. pynput 监听回调全层异常屏蔽。
    """

    state_changed = pyqtSignal(str, str)  # (old_state, new_state)
    translate_triggered = pyqtSignal(str)  # request_id
    cancel_triggered = pyqtSignal(str)  # request_id
    overlay_hide_requested = pyqtSignal()

    def __init__(self, delay_sec: float = 3.0, enabled: bool = True):
        super().__init__()
        self.state = AppState.IDLE
        self.delay_sec = max(1.0, min(10.0, float(delay_sec)))
        self.enabled = enabled
        self.current_request_id: Optional[str] = None
        self.last_move_timestamp: float = time.time()
        self.last_move_log_time: float = 0.0
        self.last_pos = (-9999, -9999)

        # Qt 定时器 (单次触发模式)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._on_idle_timeout)

        # pynput 信号桥梁：强制指定 Qt.QueuedConnection，确保无论来自哪个子线程，
        # 回调必须安全排队进入 Qt 主 GUI 线程事件循环执行，彻底杜绝多线程闪退！
        self._signal_bridge = MouseListenerSignal()
        try:
            queued_conn = getattr(Qt, "QueuedConnection", None)
            if queued_conn is not None:
                self._signal_bridge.mouse_moved.connect(self._on_mouse_moved_main_thread, queued_conn)
            else:
                self._signal_bridge.mouse_moved.connect(self._on_mouse_moved_main_thread)
        except Exception:
            self._signal_bridge.mouse_moved.connect(self._on_mouse_moved_main_thread)

        self._pynput_listener: Optional[mouse.Listener] = None

    def start(self):
        """启动鼠标移动监听与状态机"""
        try:
            if not self.enabled:
                self._set_state(AppState.PAUSED)
                return

            self._set_state(AppState.IDLE)
            self._start_pynput_listener()
            # 初始进入等待稳定计时
            self._restart_timer()
        except Exception as e:
            logger.warning(f"启动鼠标状态机保护异常: {e}")

    def stop(self):
        """停止监听与计时"""
        try:
            self.idle_timer.stop()
            if self._pynput_listener is not None:
                try:
                    self._pynput_listener.stop()
                except Exception as e:
                    logger.warning(f"停止 pynput 监听异常: {e}")
                self._pynput_listener = None
            self._set_state(AppState.IDLE)
        except Exception as e:
            logger.warning(f"停止鼠标状态机保护异常: {e}")

    def set_enabled(self, enabled: bool):
        """用户开关切换"""
        try:
            if self.enabled == enabled:
                return
            self.enabled = enabled
            if not self.enabled:
                self.idle_timer.stop()
                try:
                    self.overlay_hide_requested.emit()
                except Exception:
                    pass
                self._set_state(AppState.PAUSED)
            else:
                self._set_state(AppState.IDLE)
                self._restart_timer()
        except Exception as e:
            logger.warning(f"设置鼠标监听状态异常: {e}")

    def set_delay_sec(self, delay_sec: float):
        """设置鼠标静止触发秒数 (1-10 秒)"""
        try:
            self.delay_sec = max(1.0, min(10.0, float(delay_sec)))
            if self.idle_timer.isActive():
                self._restart_timer()
        except Exception:
            pass

    def notify_translation_result_received(self, request_id: str, has_items: bool):
        """当主进程收到 Worker 的翻译结果时调用"""
        try:
            # 只有匹配当前最新的 request_id 才切换为 SHOWING
            if self.state == AppState.TRANSLATING and self.current_request_id == request_id:
                if has_items:
                    self._set_state(AppState.SHOWING)
                else:
                    self._set_state(AppState.IDLE)
        except Exception as e:
            logger.warning(f"通知翻译结果状态异常: {e}")

    def notify_error(self, request_id: str):
        """发生错误时通知"""
        try:
            if self.current_request_id == request_id:
                self._set_state(AppState.ERROR)
        except Exception:
            pass

    # ---------------- 内部处理逻辑 ----------------

    def _start_pynput_listener(self):
        """启动低开销全局鼠标监听线程"""
        if self._pynput_listener is not None:
            return

        global mouse
        if mouse is None:
            try:
                from pynput import mouse as _p_mouse
                mouse = _p_mouse
            except Exception as e_pynput:
                logger.warning(f"未能初始化 pynput 鼠标监听 (缺少依赖或权限不足): {e_pynput}")
                return

        def on_move(x, y):
            try:
                # 严格遵守规定：禁止在 pynput 回调中 sleep，只更新时间并安全抛出 Qt 信号
                self.last_move_timestamp = time.time()
                self._signal_bridge.mouse_moved.emit(int(x), int(y))
            except Exception:
                pass

        try:
            self._pynput_listener = mouse.Listener(on_move=on_move)
            self._pynput_listener.daemon = True
            self._pynput_listener.start()
            logger.info("pynput 鼠标全局监听已启动")
        except Exception as e:
            logger.error(f"启动 pynput 鼠标监听失败: {e}", exc_info=True)
            self._set_state(AppState.ERROR)

    def _on_mouse_moved_main_thread(self, x: int, y: int):
        """在 PyQt 主线程中响应鼠标移动 (严格捕获一切未预期异常，杜绝主事件循环崩溃闪退)"""
        try:
            if not self.enabled:
                return

            # 抖动微滤：若坐标与上次位移小于 2px，视为传感器底噪微颤，不打断静止倒计时
            dx = abs(x - self.last_pos[0])
            dy = abs(y - self.last_pos[1])
            if dx <= 2 and dy <= 2:
                return
            self.last_pos = (x, y)

            # 任何状态下只要鼠标发生移动：
            # 1. 安全通知隐藏覆盖层
            try:
                self.overlay_hide_requested.emit()
            except Exception as e_hide:
                logger.debug(f"隐藏覆盖层忽略: {e_hide}")

            # 节流打日志，避免鼠标划动产生海量日志刷屏 (每隔 1.5 秒打印一次移动信息)
            now = time.time()
            if now - self.last_move_log_time >= 1.5:
                self.last_move_log_time = now
                logger.info(f"[鼠标检测] 检测到鼠标移动至坐标 ({x}, {y})，重置静止计时器 (倒计时: {self.delay_sec:.1f} 秒)")

            # 2. 如果当前正在翻译，发送取消并废弃旧请求
            if self.state == AppState.TRANSLATING and self.current_request_id:
                old_req = self.current_request_id
                self.current_request_id = None
                logger.info(f"[鼠标检测] 正在翻译中途检测到鼠标移动，取消旧请求: {old_req}")
                try:
                    self.cancel_triggered.emit(old_req)
                except Exception:
                    pass

            # 3. 重启 QTimer
            self._restart_timer()

            # 4. 状态切换至 WAIT_STABLE
            if self.state != AppState.WAIT_STABLE:
                self._set_state(AppState.WAIT_STABLE)
        except Exception as e_main_move:
            logger.warning(f"鼠标主线程响应逻辑保护拦截: {e_main_move}")

    def _restart_timer(self):
        """重启防抖静止计时器"""
        try:
            if not self.enabled:
                return
            msec = int(self.delay_sec * 1000)
            self.idle_timer.start(msec)
        except Exception as e:
            logger.warning(f"重启计时器异常: {e}")

    def _on_idle_timeout(self):
        """QTimer 超时：说明鼠标已完全静止达到预设秒数 (顶级防崩溃保护)"""
        try:
            if not self.enabled:
                return

            # 生成新的 request_id
            import uuid
            self.current_request_id = str(uuid.uuid4())
            self._set_state(AppState.TRANSLATING)

            logger.info(f"[鼠标检测] 鼠标已保持静止超过 {self.delay_sec:.1f} 秒！开始捕获屏幕并执行 OCR 与翻译 (Request ID: {self.current_request_id})")
            self.translate_triggered.emit(self.current_request_id)
        except Exception as e_timeout:
            logger.warning(f"鼠标静止超时触发异常防崩溃拦截: {e_timeout}")

    def _set_state(self, new_state: AppState):
        """统一状态跃迁管理并打日志"""
        try:
            if self.state != new_state:
                old_str = self.state.value
                new_str = new_state.value
                self.state = new_state
                logger.info(f"[状态机] 跃迁: [{old_str}] -> [{new_str}]")
                try:
                    self.state_changed.emit(old_str, new_str)
                except Exception:
                    pass
        except Exception:
            pass
