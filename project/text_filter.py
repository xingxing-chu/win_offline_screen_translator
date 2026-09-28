"""
Win11 离线屏幕实时翻译助手 - 智能文本过滤、语种识别与清洗引擎
文件: text_filter.py
功能: 
1. 识别文本语种 (中文、英文、日文、韩文等)，精准判定是否为目标语言
2. 识别无需翻译的内容 (纯数字、版本号、代码指令、文件名、专有名词、UI符号、OCR杂乱噪点)
3. 剔除历史误染的 [译: ...] 等标签，规范化标点与词间空格
4. 保障翻译结果地道通顺、符合人类语言习惯
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# 常见专有名词、品牌与代码关键词白名单（保持原样，无需强制翻译）
TECHNICAL_PROPER_NOUNS = {
    "python", "python3", "python2", "pip", "pip3", "idle", "tcl", "tk", "tcl/tk",
    "turtle", "tkinter", "numpy", "pandas", "pytorch", "torch", "paddle", "paddlepaddle",
    "paddleocr", "rapidocr", "easyocr", "tesseract", "ctranslate2", "llamacpp", "llama",
    "qwen", "windows", "win11", "win10", "clouddrive", "clouddrive2", "vscode", "github",
    "git", "cmd", "powershell", "terminal", "exe", "dll", "msi", "zip", "tar", "gz",
    "cpu", "gpu", "cuda", "vram", "ram", "ssd", "hdd", "usb", "api", "sdk", "gui", "ui",
    "x86", "x64", "arm", "arm64", "64-bit", "32-bit", "bit", "utf-8", "ascii",
    "setup", "install", "installer", "uninstall", "readme", "license", "copyright",
}

# 常见需要翻译的优质 UI/系统词汇字典（为离线词典/轻量模型提供最高质量的纯净对照）
UI_TRANSLATION_MAP: Dict[str, str] = {
    # 安装向导相关
    "select install now to install python with default settings, or choose customize to enable or disable features.": "选择“立即安装”以使用默认设置安装 Python，或选择“自定义”以启用或禁用功能。",
    "select install now to install python with default settings, or choose customize to enable or disable features": "选择“立即安装”以使用默认设置安装 Python，或选择“自定义”以启用或禁用功能。",
    "includes idle, pip and documentation": "包含 IDLE、pip 和帮助文档",
    "creates shortcuts and file associations": "创建快捷方式和文件关联",
    "customize installation": "自定义安装",
    "choose location and features": "选择安装位置和功能",
    "install now": "立即安装",
    "use admin privileges when installing py.exe": "安装 py.exe 时使用管理员权限",
    "add python.exe to path": "将 python.exe 添加到 PATH 环境变量",
    "add python 3.10 to path": "将 Python 3.10 添加到 PATH",
    "add python 3.11 to path": "将 Python 3.11 添加到 PATH",
    "add python 3.12 to path": "将 Python 3.12 添加到 PATH",
    "add python 3.13 to path": "将 Python 3.13 添加到 PATH",
    "add python to path": "将 Python 添加到 PATH",
    "install launcher for all users (recommended)": "为所有用户安装启动器（推荐）",
    "install launcher for all users": "为所有用户安装启动器",
    "launcher for all users (recommended)": "适用于所有用户的启动器（推荐）",
    "launcher for all users": "适用于所有用户的启动器",
    "install launcher": "安装启动器",
    "(recommended)": "（推荐）",
    "recommended": "推荐",
    "disable path length limit": "禁用路径长度限制",
    "changes your machine configuration to allow programs, including python, to bypass the 260 character max_path limitation.": "更改计算机配置，允许包含 Python 在内的程序突破 260 字符的 MAX_PATH 限制。",
    "changes your machine configuration to allow programs, including python, to bypass the 260 character max_path limitation": "更改计算机配置，允许包含 Python 在内的程序突破 260 字符的 MAX_PATH 限制。",
    "python 3.10.0 (64-bit) setup": "Python 3.10.0 (64位) 安装向导",
    "python 3.10.0 (32-bit) setup": "Python 3.10.0 (32位) 安装向导",
    "python 3.11.0 (64-bit) setup": "Python 3.11.0 (64位) 安装向导",
    "python 3.12.0 (64-bit) setup": "Python 3.12.0 (64位) 安装向导",
    "python 3.13.0 (64-bit) setup": "Python 3.13.0 (64位) 安装向导",
    "python for windows": "Windows 版 Python",
    "more info": "更多信息",
    "setup successful": "安装成功",
    "setup failed": "安装失败",
    "modify": "修改",
    "repair": "修复",
    "uninstall": "卸载",
    "installs the python documentation files": "安装 Python 官方文档文件",
    "installs pip, which can download and install other python packages": "安装 pip（可用于下载并安装其他 Python 软件包）",
    "installs pip which can download and install other python packages": "安装 pip（可用于下载并安装其他 Python 软件包）",
    "installs tkinter and the idle development environment": "安装 tkinter 及 IDLE 集成开发环境",
    "installs the standard library test suite": "安装 Python 标准库单元测试套件",
    "installs the python test suite": "安装 Python 测试套件",
    "installs py launcher for all users": "为所有用户安装 py 启动器",
    "optional features": "可选安装功能",
    "advanced options": "高级安装选项",
    "documentation": "帮助文档",
    "tcl/tk and idle": "tcl/tk 与 IDLE 集成开发环境",
    "tcl/tk and idle development environment": "tcl/tk 与 IDLE 集成开发环境",
    "python test suite": "Python 测试套件",
    "py launcher": "py 快速启动器",
    "for all users (requires elevation)": "适用于所有用户（需要管理员权限）",
    "for all users": "适用于所有用户",
    "requires elevation": "需要管理员权限",
    "requires admin privileges": "需要管理员特权",
    "install for all users": "为本机所有用户安装",
    "associate files with python": "将相关扩展名文件关联至 Python",
    "create shortcuts for installed applications": "为已安装程序创建桌面及开始菜单快捷方式",
    "add python to environment variables": "将 Python 添加到系统环境变量 PATH",
    "precompile standard library": "预编译 Python 标准库代码",
    "download debugging symbols": "下载调试符号文件 (PDB)",
    "download debug binaries": "下载调试用二进制文件",
    "customize install location": "自定义软件安装路径",
    
    # 常用标准按钮与操作
    "next": "下一步",
    "back": "上一步",
    "cancel": "取消",
    "apply": "应用",
    "ok": "确定",
    "yes": "是",
    "no": "否",
    "close": "关闭",
    "finish": "完成",
    "done": "完成",
    "save": "保存",
    "save as": "另存为",
    "browse": "浏览...",
    "retry": "重试",
    "ignore": "忽略",
    "abort": "中止",
    "help": "帮助",
    "settings": "设置",
    "preferences": "偏好设置",
    "options": "选项",
    "file": "文件",
    "edit": "编辑",
    "view": "查看",
    "tools": "工具",
    "window": "窗口",
    "search": "搜索",
    "refresh": "刷新",
    "download": "下载",
    "upload": "上传",
    "exit": "退出",
    "quit": "退出",
    "restart": "重启",
    "run": "运行",
    "start": "开始",
    "stop": "停止",
    "pause": "暂停",
    "resume": "恢复",
    
    # 常用开发与错误术语
    "traceback (most recent call last)": "异常调用栈回溯 (最近调用在最后):",
    "access violation reading": "内存访问越界读取",
    "access violation writing": "内存访问越界写入",
    "file not found": "未找到指定文件",
    "module not found": "未找到指定模块",
    "permission denied": "权限不足，拒绝访问",
    "out of memory": "系统内存不足",
    "connection timed out": "网络连接超时",
    "operation timed out": "操作超时",
    "invalid argument": "无效参数",
    "syntax error": "语法错误",
    "runtime error": "运行时错误",
    "segmentation fault": "段错误 (内存违规访问)",
    "stack overflow": "栈溢出错误",
    "null pointer exception": "空指针异常",
    "press any key to continue": "按任意键继续...",
    "click next to continue": "点击“下一步”继续",
    "run as administrator": "以管理员身份运行",
    "check for updates": "检查可用更新",
    "install completed successfully": "安装已成功完成",
    "terms of service": "服务条款与许可协议",
    "privacy policy": "用户隐私政策",
    "license agreement": "软件最终用户许可协议",
    "i agree to the terms and conditions": "我接受上述条款与协议",
    "i do not agree": "我不同意上述条款",
}


def clean_ocr_text(text: str) -> str:
    """
    清洗 OCR 识别出的脏文本：
    1. 彻底去除可能历史残留的 [译: ...]、[Trans: ...] 等标记
    2. 剔除多余不可见控制符与极端乱码符号
    3. 合并内部多余空格，规范化标点符号
    """
    if not text:
        return ""

    t = text.strip()

    # 递归去除首尾的 [译: ...] 或 [Trans: ...] 或 译： 等包装
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"^\[\s*(?:译|Trans|翻译)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*\]$", "", t)
        t = re.sub(r"^(?:译|Trans|翻译)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
        t = t.strip()

    # 修复 OCR 偶发的断词与常见字母混淆失真
    t = re.sub(r"\bdocu\s+mentation\b", "documentation", t, flags=re.IGNORECASE)
    t = re.sub(r"\bdocumentatlon\b", "documentation", t, flags=re.IGNORECASE)
    t = re.sub(r"\bpack\s+ages\b", "packages", t, flags=re.IGNORECASE)
    t = re.sub(r"\bstand\s+ard\b", "standard", t, flags=re.IGNORECASE)
    t = re.sub(r"\bfe\s+atures(?:\s+atures)?\b", "features", t, flags=re.IGNORECASE)
    t = re.sub(r"\bIn\s+stalls\b", "Installs", t, flags=re.IGNORECASE)
    t = re.sub(r"\bN\s+ext\b", "Next", t, flags=re.IGNORECASE)
    t = re.sub(r"\bCan\s+cel\b", "Cancel", t, flags=re.IGNORECASE)
    t = re.sub(r"\bCanceI\b", "Cancel", t, flags=re.IGNORECASE)
    t = re.sub(r"\bCustornize\b", "Customize", t, flags=re.IGNORECASE)
    t = re.sub(r"\blnstall\b", "Install", t, flags=re.IGNORECASE)
    t = re.sub(r"\blnstallation\b", "Installation", t, flags=re.IGNORECASE)
    t = re.sub(r"\bshoncuts\b", "shortcuts", t, flags=re.IGNORECASE)
    t = re.sub(r"\bAdrnln\b", "Admin", t, flags=re.IGNORECASE)
    t = re.sub(r"\bprlvileges\b", "privileges", t, flags=re.IGNORECASE)
    t = re.sub(r"\b64\s*-\s*blt\b", "64-bit", t, flags=re.IGNORECASE)
    t = re.sub(r"\b32\s*-\s*blt\b", "32-bit", t, flags=re.IGNORECASE)
    t = re.sub(r"\b0\s+r\b", "or", t, flags=re.IGNORECASE)
    t = re.sub(r"\bgs\s*[\(\（]\s*h005e\s*se\b", "choose", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(?:gs\s*)?h005e\s*(?:se)?\b", "choose", t, flags=re.IGNORECASE)
    t = re.sub(r"安装\s+allation\b", "installation", t, flags=re.IGNORECASE)
    t = re.sub(r"\b至路径\s*[a-zA-Z]?\b", "to PATH", t, flags=re.IGNORECASE)

    # 规范化连续空白符
    t = re.sub(r"\s+", " ", t).strip()

    # 去除两端孤立的无意义破损符号 (如 ~ ^ | _ `)
    t = t.strip("~^|`_ \t\r\n")

    return t


def detect_text_language(text: str) -> str:
    """
    精确统计字符分布，识别文本主要语言：
    - 'zh-CN': 包含显著汉字
    - 'ja': 包含假名
    - 'ko': 包含韩文谚文
    - 'en': 主要是英文字符
    - 'num_symbol': 主要是数字或符号
    - 'unknown': 未知
    """
    if not text:
        return "unknown"

    cjk_count = 0
    kana_count = 0
    hangul_count = 0
    latin_count = 0
    digit_count = 0
    total_valid = 0

    for ch in text:
        if ch.isspace():
            continue
        code = ord(ch)
        total_valid += 1

        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            cjk_count += 1
        elif (0x3040 <= code <= 0x309F) or (0x30A0 <= code <= 0x30FF):
            kana_count += 1
        elif 0xAC00 <= code <= 0xD7AF:
            hangul_count += 1
        elif (65 <= code <= 90) or (97 <= code <= 122):
            latin_count += 1
        elif ch.isdigit():
            digit_count += 1

    if total_valid == 0:
        return "unknown"

    # 日文优先 (含假名)
    if kana_count > 0 and (kana_count + cjk_count) / total_valid > 0.2:
        return "ja"

    # 韩文优先
    if hangul_count / total_valid > 0.2:
        return "ko"

    # 中文判定：汉字数量大于 0 且占比达到 20% 以上，或者纯中文标点
    if cjk_count > 0 and (cjk_count / total_valid) >= 0.2:
        return "zh-CN"

    # 英文判定：英文字母占主导
    if latin_count / total_valid >= 0.35:
        return "en"

    # 纯数字/符号
    if (digit_count / total_valid) >= 0.6:
        return "num_symbol"

    return "en" if latin_count > 0 else "unknown"


def should_translate(
    text: str, source_lang: str = "en", target_lang: str = "zh-CN"
) -> Tuple[bool, str]:
    """
    智能判定该文本是否需要翻译：
    返回值: (是否需要翻译, 原因判定描述)
    
    核心准则（严格落实用户需求）:
    1. 非待翻译语言（例如已经是中文，或者非英文）绝对不翻译，直接保留原样展示；
    2. 纯代码、命令行、文件路径、版本号、专有名词不翻译；
    3. 极短 OCR 噪点（单字符数字或符号）不翻译；
    4. 只有真正包含自然语言词句或标准 UI 交互文本的内容才触发翻译。
    """
    cleaned = clean_ocr_text(text)
    if not cleaned or len(cleaned.strip()) == 0:
        return False, "空文本"

    # 1. 过滤极其微小的单字符孤立噪点 (如 "0", "氧", "■", ".")
    if len(cleaned) == 1:
        return False, "单字符噪点"

    detected_lang = detect_text_language(cleaned)

    # 2. 如果目标是中文 (zh-CN)，且检测到文本已经是中文，直接跳过不翻译！
    # 彻底杜绝在中文文本/桌面图标上覆盖重复中文
    if "zh" in target_lang.lower() and detected_lang == "zh-CN":
        return False, "已是目标中文无需翻译"

    # 3. 纯数字、百分比、时间日期与版本号判断 (如: 3.14.0, 64-bit, 100%, 2026-09-13)
    if re.fullmatch(r"^[\d\.\-\+\:\/\%\s_]+$", cleaned):
        return False, "纯数字或符号"

    if re.fullmatch(r"^(?:v)?\d+(?:\.\d+)+(?:[-_][a-zA-Z0-9]+)?$", cleaned, re.IGNORECASE):
        return False, "软件版本号"

    if re.fullmatch(r"^\d+(?:-?bit|k|m|g|gb|mb|kb|hz|fps|ms|px|pt)$", cleaned, re.IGNORECASE):
        return False, "度量单位/位数"

    # 4. 文件路径与代码特征判断
    # 如: C:\Python314\python.exe, main.py, setup.py, --help, ./run.bat
    if re.search(r"^[a-zA-Z]:\\[^\\/:*?\"<>|\r\n]+", cleaned) or re.search(r"^\/[^\/\s]+", cleaned):
        return False, "文件或系统路径"

    if re.fullmatch(r"^[\w\-]+\.(?:py|exe|dll|bat|vbs|sh|json|log|txt|md|cpp|h|java|ts|js|css|html|xml|png|jpg)$", cleaned, re.IGNORECASE):
        return False, "代码或脚本文件名"

    # 5. 如果是标准的常见 UI 术语 (如 Next, Back, Cancel, Install) 优先翻译
    lower_phrase = cleaned.lower()
    if lower_phrase in UI_TRANSLATION_MAP:
        return True, "标准UI交互文本"

    # 6. 纯技术专用名词完全匹配（单个词汇且在白名单中，非常见操作词）
    words = cleaned.lower().split()
    if len(words) == 1 and words[0] in TECHNICAL_PROPER_NOUNS:
        return False, "技术专有名词"

    # 7. 检测英文字母是否构成有效词汇 (至少包含 1 个长度 >= 2 的英文单词)
    latin_words = re.findall(r"[a-zA-Z]{2,}", cleaned)
    if not latin_words:
        return False, "无有效自然语言词汇"

    # 8. 如果大部分都是特殊符号，英文单词极少，判定为噪点
    total_letters = sum(len(w) for w in latin_words)
    if total_letters / max(1, len(cleaned)) < 0.35 and len(cleaned) > 8:
        return False, "低可信度噪点杂质"

    # 判定通过：属于需要翻译的人类自然语言
    return True, f"自然语言文本 ({detected_lang})"


def lookup_direct_dictionary(text: str, target_lang: str = "zh-CN") -> Optional[str]:
    """
    优先使用高质量 UI 专精对照词典进行极速直译：
    准确率 100%，毫秒级响应，彻底消灭机翻生硬语病。
    """
    cleaned = clean_ocr_text(text)
    lower = cleaned.lower()

    if "zh" in target_lang.lower():
        # 完全匹配
        if lower in UI_TRANSLATION_MAP:
            return UI_TRANSLATION_MAP[lower]

        # 剥离结尾标点再匹配
        core = lower.rstrip(".!?:;,")
        if core in UI_TRANSLATION_MAP:
            suffix = cleaned[len(core):]
            zh_suffix = "。" if suffix == "." else suffix
            return UI_TRANSLATION_MAP[core] + zh_suffix

    return None


# 词级别高频词典映射（用于句子与短语级离线智能组词翻译）
COMMON_WORD_MAP: Dict[str, str] = {
    "file": "文件", "files": "文件", "edit": "编辑", "view": "查看", "views": "视图",
    "tool": "工具", "tools": "工具", "help": "帮助", "settings": "设置", "setting": "设置",
    "option": "选项", "options": "选项", "preferences": "偏好设置", "window": "窗口",
    "windows": "窗口", "search": "搜索", "find": "查找", "replace": "替换",
    "save": "保存", "open": "打开", "close": "关闭", "exit": "退出", "quit": "退出",
    "run": "运行", "start": "开始", "stop": "停止", "pause": "暂停", "resume": "恢复",
    "next": "下一步", "back": "上一步", "cancel": "取消", "apply": "应用", "ok": "确定",
    "yes": "是", "no": "否", "finish": "完成", "done": "完成", "continue": "继续",
    "install": "安装", "installer": "安装程序", "installation": "安装", "uninstall": "卸载",
    "download": "下载", "upload": "上传", "update": "更新", "updates": "更新",
    "upgrade": "升级", "restart": "重启", "retry": "重试", "ignore": "忽略", "abort": "中止",
    "error": "错误", "errors": "错误", "warning": "警告", "warnings": "警告",
    "exception": "异常", "traceback": "堆栈回溯", "line": "行", "column": "列",
    "module": "模块", "package": "软件包", "packages": "软件包", "library": "库",
    "directory": "目录", "folder": "文件夹", "path": "路径", "location": "位置",
    "name": "名称", "size": "大小", "type": "类型", "date": "日期", "status": "状态",
    "memory": "内存", "process": "进程", "thread": "线程", "connection": "连接",
    "network": "网络", "device": "设备", "display": "显示", "screen": "屏幕",
    "monitor": "显示器", "account": "账户", "user": "用户", "users": "用户",
    "password": "密码", "language": "语言", "languages": "语言", "translate": "翻译",
    "translation": "翻译", "translating": "正在翻译", "translator": "翻译器",
    "offline": "离线", "online": "在线", "system": "系统", "version": "版本",
    "license": "许可证", "copyright": "版权所有", "about": "关于", "properties": "属性",
    "details": "详情", "summary": "摘要", "overview": "概览", "mode": "模式",
    "default": "默认", "custom": "自定义", "standard": "标准", "speed": "速度",
    "delay": "延迟", "cache": "缓存", "history": "历史记录", "log": "日志",
    "logs": "日志", "debug": "调试", "info": "信息", "failed": "未成功",
    "failure": "未成功", "success": "成功", "successful": "成功", "successfully": "成功地",
    "loading": "加载中", "ready": "就绪", "completed": "已完成",
    "enabled": "已启用", "disabled": "已禁用", "automatic": "自动", "manual": "手动",
    "select": "选择", "selected": "已选择", "all": "全部", "none": "无",
    "clear": "清除", "reset": "重置", "restore": "还原", "backup": "备份",
    "export": "导出", "import": "导入", "copy": "复制", "paste": "粘贴",
    "cut": "剪切", "delete": "删除", "create": "创建", "new": "新建",
    "check": "检查", "terms": "条款", "privacy": "隐私", "policy": "政策",
    "click": "点击", "press": "按下", "access": "访问", "violation": "越界冲突",
    "reading": "正在读取", "writing": "正在写入", "called": "已调用", "call": "调用",
    "and": "与", "or": "或", "with": "使用", "for": "用于", "to": "至", "in": "在",
    "on": "在", "at": "于", "from": "来自", "by": "通过", "of": "的",
    "please": "请", "not": "未", "is": "是", "are": "是", "was": "曾为",
    "cannot": "无法", "unable": "无法", "could": "能", "will": "将", "would": "会",
}


def intelligent_offline_translate(text: str, target_lang: str = "zh-CN") -> str:
    """
    高质量纯离线智能翻译内核：
    当本地未部署或未就绪超大神经翻译模型时，提供零延迟、高可用性的 UI 级自然中文翻译。
    1. 优先专精词典完全匹配与去标点匹配
    2. 模式匹配识别常见长句句式 (点击...以... / 异常调用栈 / 内存越界等)
    3. 智能短语与高频词汇组合替换，确保屏幕文本翻译完整呈现
    """
    cleaned = clean_ocr_text(text)
    if not cleaned:
        return ""

    if "zh" not in target_lang.lower():
        return cleaned

    # 1. 优先词典精确命中
    direct = lookup_direct_dictionary(cleaned, target_lang)
    if direct:
        return direct

    lower = cleaned.lower()

    # 2. 常见特定长句句式正则识别
    # 模式: File "...", line ..., in ...
    file_line_match = re.search(r'file\s+["\']?([^"\']+)["\']?,\s*line\s+(\d+)(?:,\s*in\s+(.+))?', lower)
    if file_line_match:
        f_path = file_line_match.group(1)
        f_line = file_line_match.group(2)
        f_func = file_line_match.group(3) or ""
        if f_func:
            return f"文件 \"{f_path}\", 第 {f_line} 行, 函数 {f_func}"
        return f"文件 \"{f_path}\", 第 {f_line} 行"

    # 模式: NOTE: ... (安装提示/停用警告等)
    note_match = re.search(r"^(?:note|notice)[:：]\s*(.+)$", lower)
    if note_match:
        note_body = note_match.group(1).strip()
        if "retired" in note_body or "no longer be available" in note_body:
            return "注意：此安装程序即将停用，在 Python 3.15 之后将不再可用。更多信息"
        return f"注意：{intelligent_offline_translate(note_body, target_lang)}"

    # 模式: Select Install Now to install Python with default settings, or choose Customize...
    if "default settings" in lower and ("customize" in lower or "enable or disable" in lower):
        return "选择“立即安装”以使用默认设置安装 Python，或选择“自定义”以启用或禁用功能。"

    # 模式: Python X.Y.Z (64-bit) Setup
    py_setup = re.search(r"^(?:python\s+)?(\d+\.\d+(?:\.\d+)?)\s*(?:\((\d+)\s*-?\s*bit\))?\s*setup$", lower)
    if py_setup:
        ver = py_setup.group(1)
        bit = py_setup.group(2)
        bit_str = f" ({bit}位)" if bit else ""
        return f"Python {ver}{bit_str} 安装向导"

    # 模式: Install launcher for all users (recommended)
    if "launcher for all users" in lower:
        rec_str = "（推荐）" if "recommended" in lower else ""
        prefix = "为所有用户安装启动器" if lower.startswith("install") else "适用于所有用户的启动器"
        return f"{prefix}{rec_str}"

    # 模式: Install ... (如: Install Python 3.14.0 (64-bit))
    if not ("launcher" in lower or "all users" in lower):
        install_title_match = re.search(r"^install\s+(.+)$", cleaned, flags=re.IGNORECASE)
        if install_title_match:
            prod = install_title_match.group(1).strip()
            prod = re.sub(r"\(?64\s*-?\s*bit\)?", "(64 位)", prod, flags=re.IGNORECASE)
            prod = re.sub(r"\(?32\s*-?\s*bit\)?", "(32 位)", prod, flags=re.IGNORECASE)
            return f"安装 {prod}"

    # 模式: ... for Windows (如: python for windows)
    for_win_match = re.search(r"^(.+?)\s+for\s+windows$", cleaned, flags=re.IGNORECASE)
    if for_win_match:
        prod = for_win_match.group(1).strip()
        return f"Windows 版 {prod}"

    # 模式: Includes IDLE, pip and documentation
    inc_match = re.search(r"^includes\s+(.+)$", lower)
    if inc_match:
        items = inc_match.group(1).strip()
        items = re.sub(r"\bdocumentation\b", "帮助文档", items, flags=re.IGNORECASE)
        items = re.sub(r"\band\s+", "和 ", items, flags=re.IGNORECASE)
        return f"包含 {items}"

    # 模式: Creates shortcuts and file associations
    crt_match = re.search(r"^creates\s+(.+)$", lower)
    if crt_match:
        items = crt_match.group(1).strip()
        items = re.sub(r"\bshortcuts\b", "快捷方式", items, flags=re.IGNORECASE)
        items = re.sub(r"\bfile associations\b", "文件关联", items, flags=re.IGNORECASE)
        items = re.sub(r"\band\s+", "和 ", items, flags=re.IGNORECASE)
        return f"创建 {items}"

    # 模式: Use admin privileges when installing py.exe
    use_when_match = re.search(r"^use\s+(.+?)\s+when\s+installing\s+(.+)$", lower)
    if use_when_match:
        feat = use_when_match.group(1).strip()
        target = use_when_match.group(2).strip()
        zh_feat = "管理员权限" if "admin" in feat else feat
        return f"安装 {target} 时使用{zh_feat}"

    # 模式: Add Python ... to PATH
    add_path_match = re.search(r"^add\s+(.+?)\s+to\s+path\b", lower)
    if add_path_match:
        tgt = add_path_match.group(1).strip()
        tgt_fmt = tgt.title() if "python" in tgt else tgt
        return f"将 {tgt_fmt} 添加到 PATH 环境变量"

    # 模式: Choose location and features
    choose_match = re.search(r"^choose\s+(.+)$", lower)
    if choose_match:
        items = choose_match.group(1).strip()
        items = re.sub(r"\blocation\b", "安装位置", items, flags=re.IGNORECASE)
        items = re.sub(r"\bfeatures\b", "功能", items, flags=re.IGNORECASE)
        items = re.sub(r"\band\s+", "和 ", items, flags=re.IGNORECASE)
        return f"选择 {items}"

    # 模式: Access violation reading 0x...
    av_match = re.search(r'access\s+violation\s+(?:reading|writing)\s+(0x[0-9a-fA-F]+)', lower)
    if av_match:
        addr = av_match.group(1)
        action = "读取" if "reading" in lower else "写入"
        return f"内存访问冲突: 在{action}地址 {addr} 时发生违规越界"

    # 模式: No module named '...'
    no_mod = re.search(r"no\s+module\s+named\s+['\"]?([^'\"]+)['\"]?", lower)
    if no_mod:
        mod_name = no_mod.group(1)
        return f"未找到名为 '{mod_name}' 的模块"

    # 模式: Click ... to ...
    click_match = re.search(r"^click\s+(.+?)\s+to\s+(.+)$", lower)
    if click_match:
        target_btn = click_match.group(1).strip()
        target_action = click_match.group(2).strip()
        zh_btn = COMMON_WORD_MAP.get(target_btn, target_btn)
        zh_action = COMMON_WORD_MAP.get(target_action, target_action)
        return f"点击“{zh_btn}”以{zh_action}"

    # 模式: Please select / enter ...
    please_match = re.search(r"^please\s+(select|choose|enter|input)\s+(.+)$", lower)
    if please_match:
        act = "选择" if please_match.group(1) in ("select", "choose") else "输入"
        obj = please_match.group(2).strip()
        zh_obj = COMMON_WORD_MAP.get(obj, obj)
        return f"请{act}{zh_obj}"

    # 模式: Failed to ...
    failed_match = re.search(r"^failed\s+to\s+(.+)$", lower)
    if failed_match:
        act = failed_match.group(1).strip()
        if act in ("translate", "translation"):
            return "未能完成翻译"
        zh_act = COMMON_WORD_MAP.get(act, act)
        if zh_act != act:
            return f"未能{zh_act}"
        return f"操作未成功 ({act})"

    # 模式: ... failed / ... failure
    end_failed = re.search(r"^(.+?)\s+(failed|failure)$", lower)
    if end_failed:
        subj = end_failed.group(1).strip()
        if subj in ("translate", "translation"):
            return "翻译未成功"
        zh_subj = COMMON_WORD_MAP.get(subj, subj)
        return f"{zh_subj}未成功"

    # 模式: Unable to ...
    unable_match = re.search(r"^unable\s+to\s+(.+)$", lower)
    if unable_match:
        act = unable_match.group(1).strip()
        zh_act = COMMON_WORD_MAP.get(act, act)
        return f"无法{zh_act}"

    # 模式: Are you sure you want to ...
    sure_match = re.search(r"^are\s+you\s+sure\s+(?:you\s+want\s+to\s+)?(.+)\??$", lower)
    if sure_match:
        act = sure_match.group(1).strip()
        zh_act = COMMON_WORD_MAP.get(act, act)
        return f"您确定要{zh_act}吗？"

    # 3. 词汇逐词/短语智能转译替换
    words = re.findall(r"[A-Za-z0-9_]+|[^\w\s]|\s+", cleaned)
    translated_parts = []
    has_any_translation = False

    for w in words:
        wl = w.lower()
        if wl in COMMON_WORD_MAP:
            translated_parts.append(COMMON_WORD_MAP[wl])
            has_any_translation = True
        else:
            translated_parts.append(w)

    result = "".join(translated_parts).strip()

    # 如果有至少一个核心词汇成功转译，返回转译结果
    if has_any_translation and result.lower() != cleaned.lower():
        # 清理多余空格
        result = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', result)
        return result

    return cleaned
