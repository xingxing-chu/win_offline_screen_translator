"""
Win11 离线屏幕实时翻译助手 - OCR 与翻译结果存证记录器
文件: ocr_recorder.py
功能:
1. 启动时自动建立 project/ocr_records 存证文件夹并记录启动会话报告；
2. 为每一次屏幕捕获、OCR识别、二次AI审校与翻译全流程，生成独立的按时间戳命名的纯文本存证文件 (.txt)；
3. 详细记录【第一部分：OCR 原始检测文本与坐标框】、【第二部分：段落合并与二次识别/AI审校/过滤研判】、【第三部分：最终翻译呈现结果】；
4. 维护按天聚合的流水清单 (DAILY_SUMMARY_YYYY-MM-DD.txt)，方便一目了然连续核验；
5. 提供一键打开存证文件夹、一键查看最新存证文件的能力。
"""

import os
import sys
import time
import glob
from datetime import datetime
from typing import Any, Dict, List, Optional


def get_records_dir(project_root: str) -> str:
    """获取或初始化存证文件夹目录绝对路径 (支持智能相对/绝对路径解析及权限不足安全降级)"""
    candidate_roots = [
        project_root,
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]
    for r in candidate_roots:
        if not r:
            continue
        try:
            records_dir = os.path.abspath(os.path.join(r, "ocr_records"))
            os.makedirs(records_dir, exist_ok=True)
            # 测试写入权限
            test_file = os.path.join(records_dir, ".test_perm")
            with open(test_file, "w", encoding="utf-8") as tf:
                tf.write("ok")
            if os.path.exists(test_file):
                os.remove(test_file)
            return records_dir
        except Exception:
            continue

    # 终极用户家目录降级保护
    user_fallback = os.path.join(os.path.expanduser("~"), ".win11_translator", "ocr_records")
    try:
        os.makedirs(user_fallback, exist_ok=True)
        return user_fallback
    except Exception:
        temp_fallback = os.path.join(os.environ.get("TEMP", "/tmp"), "win11_ocr_records")
        os.makedirs(temp_fallback, exist_ok=True)
        return temp_fallback


def record_session_start(
    project_root: str,
    ocr_engine: str,
    translation_engine: str,
    source_lang: str,
    target_lang: str,
) -> str:
    """
    软件启动时自动调用，生成当前会话初始化存证记录。
    确保“只要启动就要保存”，并告知用户存证系统已激活。
    """
    records_dir = get_records_dir(project_root)
    now = datetime.now()
    time_prefix = now.strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(records_dir, f"00_STARTUP_{time_prefix}.txt")

    lines = [
        "=" * 82,
        "         Win11 离线屏幕实时翻译助手 - 运行时存证系统已激活",
        "=" * 82,
        f"启动时间     : {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}",
        f"存证保存目录 : {records_dir}",
        f"当前配置OCR  : {ocr_engine}",
        f"当前配置翻译 : {translation_engine}",
        f"语言配置     : [{source_lang}] -> [{target_lang}]",
        "-" * 82,
        "说明:",
        "1. 本文件夹用于自动保存每次屏幕取词、OCR文字识别、二次AI修正和翻译结果；",
        "2. 所有存证均按精确时间戳存储为纯文本 (.txt) 文件，方便随时打开比对；",
        "3. 若发现翻译不准确，可核对该次存证文件中的【第一部分：OCR 原始检测识别文字】",
        "   以判断是否为 OCR 识别错字，或文本被过滤规则跳过。",
        "=" * 82,
        "",
    ]
    try:
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write("\n".join(lines))
    except Exception as e:
        print(f"[警告] 写入启动存证记录失败: {e}", file=sys.stderr)

    # 同步追加到当日聚合摘要文件
    summary_path = os.path.join(records_dir, f"DAILY_SUMMARY_{now.strftime('%Y-%m-%d')}.txt")
    try:
        with open(summary_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"\n[{now.strftime('%H:%M:%S')}] >>> 系统启动 | OCR引擎: {ocr_engine} | 翻译引擎: {translation_engine} | 语言: {source_lang}->{target_lang}\n")
    except Exception:
        pass

    return filepath


def save_ocr_record(
    project_root: str,
    request_id: str,
    image_hash: str,
    source_lang: str,
    target_lang: str,
    actual_source: str,
    ocr_engine: str,
    translation_engine: str,
    raw_ocr_items: List[Dict[str, Any]],
    filter_decisions: List[Dict[str, Any]],
    merged_paragraphs: List[Dict[str, Any]],
    final_items: List[Dict[str, Any]],
    elapsed_breakdown: Dict[str, int],
    cached: bool = False,
    extra_diagnostic_msg: str = "",
) -> str:
    """
    保存单次屏幕识别与翻译存证为时间戳文本文件：
    文件名格式: YYYY-MM-DD_HH-MM-SS_{request_id[:8]}.txt
    返回生成的存证文件绝对路径
    """
    records_dir = get_records_dir(project_root)
    now = datetime.now()
    time_prefix = now.strftime("%Y-%m-%d_%H-%M-%S")
    short_id = request_id[:8] if request_id else "unknown"
    filename = f"{time_prefix}_{short_id}.txt"
    filepath = os.path.join(records_dir, filename)

    raw_ocr_items = raw_ocr_items or []
    filter_decisions = filter_decisions or []
    merged_paragraphs = merged_paragraphs or []
    final_items = final_items or []
    elapsed_breakdown = elapsed_breakdown or {}

    total_elapsed = elapsed_breakdown.get("total", sum(elapsed_breakdown.values()))
    skipped_count = sum(1 for d in filter_decisions if isinstance(d, dict) and d.get("skipped"))
    retained_count = len(filter_decisions) - skipped_count

    lines = []
    lines.append("=" * 82)
    lines.append("         Win11 离线屏幕实时翻译助手 - OCR 识别与翻译全流程存证报告")
    lines.append("=" * 82)
    lines.append(f"触发时间     : {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    lines.append(f"请求 ID      : {request_id}")
    lines.append(f"画面哈希     : {image_hash[:16]}...")
    lines.append(f"OCR 识别引擎 : {ocr_engine}")
    lines.append(f"离线翻译模型 : {translation_engine}")
    lines.append(f"翻译语言配置 : 配置源[{source_lang}] -> 目标[{target_lang}] (实际研判主语言: [{actual_source}])")
    lines.append(f"缓存复用状态 : {'✓ 命中缓存 (直接复用上一次结果)' if cached else '× 未命中缓存 (全新完整识别与翻译)'}")
    lines.append(
        f"流程耗时统计 : 总耗时: {total_elapsed}ms | 截图: {elapsed_breakdown.get('capture', 0)}ms | "
        f"OCR识别: {elapsed_breakdown.get('ocr', 0)}ms | 文本清洗合并: {elapsed_breakdown.get('process', 0)}ms | "
        f"模型翻译: {elapsed_breakdown.get('translate', 0)}ms"
    )
    lines.append(
        f"数据量概览   : OCR原始文本框: {len(raw_ocr_items)} 个 | 拓扑合并段落: {len(merged_paragraphs)} 个 | "
        f"需翻译文本: {retained_count} 个 (跳过: {skipped_count} 个) | 最终翻译呈现: {len(final_items)} 个"
    )
    if extra_diagnostic_msg:
        lines.append(f"诊断附加信息 : {extra_diagnostic_msg}")
    lines.append("-" * 82)

    # ---------------- 第一部分：OCR 原始检测识别文字 ----------------
    lines.append("")
    lines.append(f"【第一部分：OCR 原始检测识别文字】 (共检测出 {len(raw_ocr_items)} 个原始文本区域)")
    lines.append("-" * 82)
    if not raw_ocr_items:
        lines.append("   ⚠️ [OCR 未在此帧画面中检测到任何文本]")
        lines.append("   可能原因与排查建议:")
        lines.append(f"   1. 当前使用的 OCR 引擎 [{ocr_engine}] 本地模型文件是否完整？")
        lines.append("      (若使用 PaddleOCR 或 RapidOCR，请在设置中确认模型状态非十几个字节坏文件并已就绪)")
        lines.append("   2. 若使用的是 Windows 11 原生系统 OCR，请确保已安装 winocr 且系统语言包中包含对应语言识别组件；")
        lines.append("   3. 当前屏幕画面是否属于纯图形、视频或低对比度界面，可尝试开启设置中的【暗黑模式反相】或【CLAHE对比度增强】。")
    else:
        for idx, item in enumerate(raw_ocr_items, 1):
            bbox = item.get("bbox", [])
            conf = item.get("confidence", 1.0)
            txt = item.get("source", "").strip()
            bbox_str = f"[{bbox[0]:4d}, {bbox[1]:4d}, {bbox[2]:4d}, {bbox[3]:4d}]" if len(bbox) == 4 else str(bbox)
            ai_flag = " [AI修正]" if item.get("ai_verified") else ""
            lines.append(f"[{idx:03d}] 坐标: {bbox_str} | 置信度: {conf:.2f}{ai_flag} | 原始识别文本: \"{txt}\"")

    # ---------------- 第二部分：段落合并与二次识别/AI审校/过滤研判 ----------------
    lines.append("")
    lines.append(f"【第二部分：段落合并与二次识别/AI审校/过滤研判】 (合并形成 {len(merged_paragraphs)} 个自然段落)")
    lines.append("-" * 82)
    if not merged_paragraphs:
        lines.append("   (无合并段落)")
    else:
        # 建立段落与过滤决策的关联映射
        decision_map = {}
        for d in filter_decisions:
            decision_map[d.get("text", "")] = d

        for idx, para in enumerate(merged_paragraphs, 1):
            bbox = para.get("bbox", [])
            bbox_str = f"[{bbox[0]:4d}, {bbox[1]:4d}, {bbox[2]:4d}, {bbox[3]:4d}]" if len(bbox) == 4 else str(bbox)
            raw_p_text = para.get("source", "").strip()
            conf = para.get("confidence", 1.0)
            ai_verified = para.get("ai_verified", False)

            dec = decision_map.get(raw_p_text, {})
            skipped = dec.get("skipped", False)
            reason = dec.get("reason", "自然语言" if not skipped else "跳过")

            status_tag = f"× 跳过 [{reason}]" if skipped else f"✓ 需翻译 [{reason}]"
            if ai_verified:
                status_tag += " (已通过 AI 语法与断词二次校正)"

            lines.append(f"[{idx:03d}] 合并坐标: {bbox_str} (均值置信度: {conf:.2f})")
            lines.append(f"      状态研判: {status_tag}")
            lines.append(f"      段落文本: \"{raw_p_text}\"")

    # ---------------- 第三部分：最终翻译呈现结果 ----------------
    lines.append("")
    lines.append(f"【第三部分：最终翻译呈现结果】 (共生成 {len(final_items)} 个屏幕覆盖翻译框)")
    lines.append("-" * 82)
    if not final_items:
        lines.append("   ⚠️ (本轮无需要浮层翻译呈现的内容)")
        lines.append("   详细说明:")
        if not raw_ocr_items:
            lines.append("   - OCR 未检出文字，故无翻译内容呈现。")
        elif all(d.get("skipped", False) for d in filter_decisions):
            lines.append("   - 屏幕上所有文本均被判定为非待翻译内容（例如已经是中文、或纯数字/代码/命令行/版本号/文件路径）。")
            lines.append("   - 规则遵循：“非翻译语言直接保留原样展示，不进行遮挡，保证语句通顺”。")
        else:
            lines.append("   - 翻译引擎未能生成有效译文，或译文与原文雷同。")
    else:
        for idx, item in enumerate(final_items, 1):
            bbox = item.get("bbox", [])
            bbox_str = f"[{bbox[0]:4d}, {bbox[1]:4d}, {bbox[2]:4d}, {bbox[3]:4d}]" if len(bbox) == 4 else str(bbox)
            src = item.get("source", "").strip()
            trans = item.get("translated", "").strip()

            lines.append(f"[{idx:03d}] 屏幕覆盖区域: {bbox_str}")
            lines.append(f"      源语言原文: \"{src}\"")
            lines.append(f"      翻译呈现文: \"{trans}\"")

    lines.append("")
    lines.append("=" * 82)
    lines.append("存证记录完毕。此文件由 Win11 离线屏幕实时翻译助手自动写入，用于追溯核验 OCR 精度与翻译效果。")
    lines.append("=" * 82)
    lines.append("")

    # 写入单次时间戳独立文件
    try:
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write("\n".join(lines))
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception as e:
        print(f"[警告] 写入存证文本失败: {e}", file=sys.stderr)

    # 同步追加到当日聚合摘要文件 (每轮识别一条单行精简摘要，方便连续观察)
    summary_path = os.path.join(records_dir, f"DAILY_SUMMARY_{now.strftime('%Y-%m-%d')}.txt")
    try:
        summary_line = (
            f"[{now.strftime('%H:%M:%S')}] 请求:{short_id} | 耗时:{total_elapsed}ms | "
            f"OCR检出:{len(raw_ocr_items)}框 | 呈现翻译:{len(final_items)}框 | 存证文件:{filename}\n"
        )
        with open(summary_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(summary_line)
            f.flush()
    except Exception:
        pass

    return filepath


def save_error_record(
    project_root: str,
    request_id: str,
    error_code: str,
    error_message: str,
    ocr_engine: str = "unknown",
    translation_engine: str = "unknown",
    source_lang: str = "en",
    target_lang: str = "zh-CN",
    suggestion: str = "",
) -> str:
    """
    当流程发生异常中断时，同样完整生成时间戳存证文本，
    保障存证系统 100% 记录一切请求，方便用户精确比对排查。
    """
    records_dir = get_records_dir(project_root)
    now = datetime.now()
    time_prefix = now.strftime("%Y-%m-%d_%H-%M-%S")
    short_id = request_id[:8] if request_id else "err"
    filename = f"{time_prefix}_{short_id}_ERROR.txt"
    filepath = os.path.join(records_dir, filename)

    lines = [
        "=" * 82,
        "         Win11 离线屏幕实时翻译助手 - 运行时异常中断存证报告",
        "=" * 82,
        f"发生时间     : {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}",
        f"请求 ID      : {request_id}",
        f"错误代码     : {error_code}",
        f"错误原因     : {error_message}",
        f"配置引擎     : OCR: {ocr_engine} | 翻译: {translation_engine}",
        f"语言方向     : [{source_lang}] -> [{target_lang}]",
        "-" * 82,
        "【异常详情与排查建议】:",
        f"1. 异常信息: {error_message}",
    ]
    if suggestion:
        lines.append(f"2. 解决方案建议: {suggestion}")
    else:
        lines.append("2. 建议核查设置中对应 OCR 引擎与离线翻译模型是否已下载并处于就绪状态。")
        lines.append("3. 若为纯图形、游戏或暗黑高对比界面，可在设置中开启【暗黑模式文字反相】或【CLAHE对比度增强】。")
    lines.extend([
        "=" * 82,
        "",
    ])

    try:
        with open(filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write("\n".join(lines))
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
    except Exception as e:
        print(f"[警告] 写入异常存证报告失败: {e}", file=sys.stderr)

    summary_path = os.path.join(records_dir, f"DAILY_SUMMARY_{now.strftime('%Y-%m-%d')}.txt")
    try:
        summary_line = (
            f"[{now.strftime('%H:%M:%S')}] 异常:{short_id} | 错误:[{error_code}] {error_message[:40]} | 存证文件:{filename}\n"
        )
        with open(summary_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(summary_line)
            f.flush()
    except Exception:
        pass

    return filepath


def get_latest_record_path(project_root: str) -> Optional[str]:
    """获取最新生成的一份 OCR 存证文本文件路径"""
    records_dir = get_records_dir(project_root)
    files = glob.glob(os.path.join(records_dir, "*.txt"))
    # 排除聚合摘要文件，寻找单次时间戳存证
    detail_files = [f for f in files if not os.path.basename(f).startswith("DAILY_SUMMARY_")]
    if not detail_files:
        return None
    detail_files.sort(key=os.path.getmtime, reverse=True)
    return detail_files[0]


def open_records_directory(project_root: str):
    """在操作系统资源管理器中直接打开存证文件夹"""
    records_dir = get_records_dir(project_root)
    if sys.platform == "win32":
        try:
            os.startfile(records_dir)
        except Exception:
            import subprocess
            subprocess.Popen(["explorer", records_dir])
    elif sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", records_dir])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", records_dir])
