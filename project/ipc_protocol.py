"""
Win11 离线屏幕实时翻译助手 - 跨进程通信 (IPC) 协议与消息定义
文件: ipc_protocol.py
功能: 定义主进程与 Worker 子进程之间的标准 JSON 可序列化消息结构、构造与验证方法。
"""

import time
import uuid
from typing import Any, Dict, List, Optional


class MessageType:
    # 主进程 -> Worker
    TRANSLATE_REQUEST = "TRANSLATE_REQUEST"
    CANCEL = "CANCEL"
    RELOAD_CONFIG = "RELOAD_CONFIG"
    SHUTDOWN = "SHUTDOWN"

    # Worker -> 主进程
    TRANSLATE_RESULT = "TRANSLATE_RESULT"
    STATUS = "STATUS"
    ERROR = "ERROR"


def create_request_id() -> str:
    """生成唯一的请求 ID"""
    return str(uuid.uuid4())


def make_translate_request(
    source_lang: str,
    target_lang: str,
    ocr_model_id: str,
    translation_model_id: str,
    capture_mode: str = "fullscreen",
    monitor_index: int = 0,
    config_version: int = 1,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """主进程发送给 Worker 的翻译请求消息"""
    return {
        "type": MessageType.TRANSLATE_REQUEST,
        "request_id": request_id or create_request_id(),
        "timestamp": int(time.time()),
        "payload": {
            "capture_mode": capture_mode,
            "monitor_index": monitor_index,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "ocr_model_id": ocr_model_id,
            "translation_model_id": translation_model_id,
            "config_version": config_version,
        },
    }


def make_cancel_message(request_id: Optional[str] = None) -> Dict[str, Any]:
    """主进程向 Worker 发送的取消当前翻译请求消息"""
    return {
        "type": MessageType.CANCEL,
        "request_id": request_id or "",
        "timestamp": int(time.time()),
        "payload": {},
    }


def make_reload_config_message(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    """主进程向 Worker 发送的重载配置与清空缓存消息"""
    return {
        "type": MessageType.RELOAD_CONFIG,
        "request_id": create_request_id(),
        "timestamp": int(time.time()),
        "payload": {
            "settings": new_settings,
        },
    }


def make_shutdown_message() -> Dict[str, Any]:
    """主进程通知 Worker 安全退出"""
    return {
        "type": MessageType.SHUTDOWN,
        "request_id": create_request_id(),
        "timestamp": int(time.time()),
        "payload": {},
    }


def make_translate_result(
    request_id: str,
    image_hash: str,
    cached: bool,
    elapsed_ms: int,
    source_lang: str,
    target_lang: str,
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Worker 返回给主进程的翻译结果
    items 示例:
    [
        {
            "bbox": [100, 200, 500, 240], # [x1, y1, x2, y2]
            "source": "Hello world",
            "translated": "你好，世界",
            "confidence": 0.98
        }
    ]
    """
    return {
        "type": MessageType.TRANSLATE_RESULT,
        "request_id": request_id,
        "payload": {
            "image_hash": image_hash,
            "cached": cached,
            "elapsed_ms": elapsed_ms,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "items": items,
        },
    }


def make_status_message(
    worker_status: str,
    ocr_loaded: bool,
    translation_loaded: bool,
    ocr_model_id: str,
    translation_model_id: str,
    message: str = "",
) -> Dict[str, Any]:
    """Worker 向主进程汇报当前状态"""
    return {
        "type": MessageType.STATUS,
        "payload": {
            "worker": worker_status,  # "ready", "busy", "loading", "error"
            "ocr_loaded": ocr_loaded,
            "translation_loaded": translation_loaded,
            "ocr_model_id": ocr_model_id,
            "translation_model_id": translation_model_id,
            "message": message,
        },
    }


def make_error_message(
    request_id: str,
    code: str,
    message: str,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    """Worker 向主进程报告错误消息"""
    return {
        "type": MessageType.ERROR,
        "request_id": request_id,
        "payload": {
            "code": code,  # CAPTURE_FAILED, OCR_FAILED, TRANSLATION_FAILED, MODEL_NOT_FOUND, UNSUPPORTED_PAIR
            "message": message,
            "detail": detail or "",
        },
    }
