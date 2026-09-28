"""
Win11 离线屏幕实时翻译助手 - 识别与翻译结果持久化存证与详细操作日志模块
文件: history_logger.py
功能:
1. 保证按日期仅生成一个统一日志文件 (logs/YYYY-MM-DD.log)
2. 杜绝生成多个日志文件 (不再产生 recognition_history.jsonl 或 translation_debug.log)
3. 完整保存系统的所有操作：系统启动、参数修改、快捷键触发、截图捕获、OCR原始识别、智能清洗、段落拓扑合并、大模型翻译对比与异常恢复
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


class HistoryLogger:
    """持久化记录 OCR 识别、翻译及系统全流程操作的统一单日记录器"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.log_dir = os.path.join(project_root, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.max_file_size = 30 * 1024 * 1024  # 30MB 轮转上限

    def _safe_now_date(self) -> str:
        try:
            return datetime.now().strftime("%Y-%m-%d")
        except Exception:
            try:
                return time.strftime("%Y-%m-%d")
            except Exception:
                return "today"

    def _safe_now_timestamp(self) -> str:
        try:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except Exception:
            try:
                return time.strftime("%Y-%m-%d %H:%M:%S") + ".000"
            except Exception:
                return "1970-01-01 00:00:00.000"

    def get_daily_log_path(self) -> str:
        """返回按日期命名的唯一日志文件路径 (logs/YYYY-MM-DD.log)"""
        now_date = self._safe_now_date()
        return os.path.join(self.log_dir, f"{now_date}.log")

    def _rotate_if_needed(self, filepath: str):
        """检查单日文件体积，超过限制时重命名备份"""
        try:
            if os.path.exists(filepath) and os.path.getsize(filepath) > self.max_file_size:
                backup_path = filepath + f".{int(time.time())}.bak"
                os.rename(filepath, backup_path)
        except Exception:
            pass

    def log_system_event(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        持久化记录系统关键操作 (如启动、设置变更、热键触发、托盘操作等)
        确保所有操作均完整落盘至当日唯一日志文件
        """
        timestamp_str = self._safe_now_timestamp()
        daily_log = self.get_daily_log_path()
        line = f"{timestamp_str} [INFO] [SystemOperation] [{event_type}] {message}"
        if details:
            try:
                line += f" | 详细参数: {json.dumps(details, ensure_ascii=False)}"
            except Exception:
                line += f" | 详细参数: {details}"

        try:
            self._rotate_if_needed(daily_log)
            with open(daily_log, "a", encoding="utf-8", errors="replace") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def log_translation_cycle(
        self,
        request_id: str,
        image_hash: str,
        source_lang: str,
        target_lang: str,
        ocr_engine: str,
        translation_engine: str,
        raw_ocr_items: List[Dict[str, Any]],
        filter_decisions: List[Dict[str, Any]],
        merged_paragraphs: List[Dict[str, Any]],
        final_items: List[Dict[str, Any]],
        elapsed_breakdown: Dict[str, int],
        cached: bool = False,
    ):
        """
        完整持久化一次识别与翻译操作的全生命周期数据
        直接写入当日唯一日志文件 logs/YYYY-MM-DD.log，绝不产生多余附属文件
        """
        timestamp_str = self._safe_now_timestamp()
        daily_log_path = self.get_daily_log_path()

        skipped_count = sum(1 for d in filter_decisions if d.get("skipped"))
        retained_count = len(filter_decisions) - skipped_count
        total_elapsed = elapsed_breakdown.get("total", sum(elapsed_breakdown.values()))

        lines = []
        lines.append("=" * 80)
        lines.append(f"[{timestamp_str}] [翻译全流程存证] - 请求 ID: {request_id}")
        lines.append(
            f"语向: {source_lang} -> {target_lang} | 缓存命中: {'是' if cached else '否'} | "
            f"画面哈希: {image_hash[:12]}... | OCR引擎: {ocr_engine} | 翻译模型: {translation_engine}"
        )
        lines.append(
            f"耗时明细: 截图捕获: {elapsed_breakdown.get('capture', 0)}ms | "
            f"OCR识别: {elapsed_breakdown.get('ocr', 0)}ms | "
            f"智能清洗与段落重构: {elapsed_breakdown.get('process', 0)}ms | "
            f"模型推理翻译: {elapsed_breakdown.get('translate', 0)}ms | "
            f"全流程总耗时: {total_elapsed}ms"
        )
        lines.append("-" * 80)
        lines.append(
            f"文本量统计: 原始检出文本框: {len(raw_ocr_items)} 个 | "
            f"智能过滤跳过(代码/专名/噪点): {skipped_count} 个 | "
            f"保留自然语言文本: {retained_count} 个 | "
            f"拓扑重构合并段落: {len(merged_paragraphs)} 个 | "
            f"最终浮层呈现译文: {len(final_items)} 个"
        )

        # 智能过滤决策记录 (代码、数字、专有名词原样保留不遮挡)
        skipped_items = [d for d in filter_decisions if d.get("skipped")]
        if skipped_items:
            lines.append("├─ [智能过滤决策清单 (非目标语言/UI按键/代码/专有名词，原样保留)]:")
            for s in skipped_items[:20]:
                lines.append(f"│  • 跳过: \"{s.get('text', '')}\" (原因: {s.get('reason', '')})")
            if len(skipped_items) > 20:
                lines.append(f"│  • ... 其余 {len(skipped_items) - 20} 项已省略")

        # 最终呈现对比清单
        lines.append("└─ [段落重构与翻译呈现清单]:")
        if not final_items:
            lines.append("   (本轮未检测到需要翻译的自然语言文本或均在过滤白名单中)")
        else:
            for idx, item in enumerate(final_items, 1):
                src = item.get("source", "").strip()
                trans = item.get("translated", "").strip()
                bbox = item.get("bbox", [])
                conf = item.get("confidence", 1.0)
                lines.append(f"   [{idx}] 坐标: {bbox} (置信度: {conf:.2f})")
                lines.append(f"       原文: {src}")
                lines.append(f"       译文: {trans}")

        lines.append("=" * 80 + "\n")

        try:
            self._rotate_if_needed(daily_log_path)
            with open(daily_log_path, "a", encoding="utf-8", errors="replace") as f:
                f.write("\n".join(lines))
        except Exception:
            pass


# 全局单例
_global_history_logger: Optional[HistoryLogger] = None


def get_history_logger(project_root: Optional[str] = None) -> HistoryLogger:
    global _global_history_logger
    if _global_history_logger is None:
        root = project_root or os.path.abspath(os.path.dirname(__file__))
        _global_history_logger = HistoryLogger(root)
    return _global_history_logger
