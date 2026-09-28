/**
 * 集中管理生成的完整 Python 项目源码与配置，供代码查看器、一键复制以及 JSZip 打包下载使用。
 * 直接引用 project/ 目录下的真实文件，确保代码与生产架构 100% 同步且无偏差。
 */

import ipcProtocolPy from '../project/ipc_protocol.py?raw';
import cacheManagerPy from '../project/cache_manager.py?raw';
import translationEnginePy from '../project/translation_engine.py?raw';
import modelDownloaderPy from '../project/model_downloader.py?raw';
import ocrEnhancerPy from '../project/ocr_enhancer.py?raw';
import modelRouterPy from '../project/model_router.py?raw';
import overlayWindowPy from '../project/overlay_window.py?raw';
import mouseStateMachinePy from '../project/mouse_state_machine.py?raw';
import configGuiPy from '../project/config_gui.py?raw';
import ocrRecorderPy from '../project/ocr_recorder.py?raw';
import ocrEnginePy from '../project/ocr_engine.py?raw';
import textFilterPy from '../project/text_filter.py?raw';
import historyLoggerPy from '../project/history_logger.py?raw';
import mainPy from '../project/main.py?raw';
import settingsJson from '../project/settings.json?raw';
import requirementsTxt from '../project/requirements.txt?raw';
import runBat from '../project/run.bat?raw';
import runDebugBat from '../project/run_debug.bat?raw';
import downloadModelsBat from '../project/download_models.bat?raw';
import startSilentVbs from '../project/start_silent.vbs?raw';

import opusModelInfo from '../project/models/translation/opus-mt-en-zh-ct2/model_info.json?raw';
import qwenModelInfo from '../project/models/translation/model_info.json?raw';
import ocrModelInfo from '../project/models/ocr/paddleocr/model_info.json?raw';

export interface ProjectFileItem {
  path: string;
  name: string;
  category: 'python' | 'json' | 'doc' | 'script';
  description: string;
  content: string;
}

export const PROJECT_FILES: ProjectFileItem[] = [
  {
    path: 'main.py',
    name: 'main.py',
    category: 'python',
    description: '主入口、双进程架构协调、Win11 原生/Rapid/Paddle 多引擎级联与自适应缩放调度',
    content: mainPy,
  },
  {
    path: 'ocr_enhancer.py',
    name: 'ocr_enhancer.py',
    category: 'python',
    description: 'OCR 图像增强预处理流水线 (深色模式检测反相、CLAHE局部对比度、ClearType字体锐化、自适应二值化)',
    content: ocrEnhancerPy,
  },
  {
    path: 'model_router.py',
    name: 'model_router.py',
    category: 'python',
    description: '多模型智能路由调度器与引擎熔断器 (根据语种/分辨率自适应决策，故障自动降级与恢复)',
    content: modelRouterPy,
  },
  {
    path: 'model_downloader.py',
    name: 'model_downloader.py',
    category: 'python',
    description: '模型全自动高速下载管理器 (国内 ModelScope/清华镜像、断点续传、SHA256 校验与状态查询)',
    content: modelDownloaderPy,
  },
  {
    path: 'config_gui.py',
    name: 'config_gui.py',
    category: 'python',
    description: 'PyQt5 高级可视化设置面板与模型下载图形化进度指示器 (Windows 11 Fluent 风格)',
    content: configGuiPy,
  },
  {
    path: 'ocr_recorder.py',
    name: 'ocr_recorder.py',
    category: 'python',
    description: 'OCR 与翻译结果时间戳纯文本存证记录器 (生成 project/ocr_records 存证及按天聚合日志)',
    content: ocrRecorderPy,
  },
  {
    path: 'ocr_engine.py',
    name: 'ocr_engine.py',
    category: 'python',
    description: '多引擎 OCR 统一管理器 (Win11原生Media OCR / RapidOCR / PaddleOCR / EasyOCR / Tesseract / AI二次审校)',
    content: ocrEnginePy,
  },
  {
    path: 'text_filter.py',
    name: 'text_filter.py',
    category: 'python',
    description: '智能文本清洗、语种检测、代码路径白名单过滤与高可靠零延迟离线词典翻译内核',
    content: textFilterPy,
  },
  {
    path: 'history_logger.py',
    name: 'history_logger.py',
    category: 'python',
    description: '全流程结构化运行历史与流水测试诊断日志记录器 (JSONL格式)',
    content: historyLoggerPy,
  },
  {
    path: 'ipc_protocol.py',
    name: 'ipc_protocol.py',
    category: 'python',
    description: '跨进程通信 (IPC) 协议与纯 JSON 可序列化消息定义',
    content: ipcProtocolPy,
  },
  {
    path: 'cache_manager.py',
    name: 'cache_manager.py',
    category: 'python',
    description: '局部与全屏截屏差分哈希 (dHash) 汉明距离两级 LRU 翻译缓存',
    content: cacheManagerPy,
  },
  {
    path: 'translation_engine.py',
    name: 'translation_engine.py',
    category: 'python',
    description: '离线翻译引擎抽象工厂与多模型元数据管理器 (llama-cpp-python / CTranslate2)',
    content: translationEnginePy,
  },
  {
    path: 'overlay_window.py',
    name: 'overlay_window.py',
    category: 'python',
    description: 'PyQt5 原生无边框置顶透明覆盖层与高 DPI 多屏缩放坐标变换',
    content: overlayWindowPy,
  },
  {
    path: 'mouse_state_machine.py',
    name: 'mouse_state_machine.py',
    category: 'python',
    description: '鼠标活动有限状态机 (FSM) 与动态防抖触发器',
    content: mouseStateMachinePy,
  },
  {
    path: 'settings.json',
    name: 'settings.json',
    category: 'json',
    description: '用户持久化运行时配置文件 (含自动路由、增强预处理及多模型配置)',
    content: settingsJson,
  },
  {
    path: 'models/translation/qwen2.5-1.5b-instruct-q4_k_m/model_info.json',
    name: 'model_info.json (Qwen)',
    category: 'json',
    description: 'Qwen2.5 1.5B GGUF 离线翻译模型元数据描述',
    content: qwenModelInfo,
  },
  {
    path: 'models/translation/opus-mt-en-zh-ct2/model_info.json',
    name: 'model_info.json (OPUS-MT)',
    category: 'json',
    description: 'OPUS-MT CTranslate2 极速翻译模型元数据描述',
    content: opusModelInfo,
  },
  {
    path: 'models/ocr/paddleocr/model_info.json',
    name: 'model_info.json (PaddleOCR)',
    category: 'json',
    description: 'PaddleOCR PP-OCRv4 中英文离线模型元数据描述',
    content: ocrModelInfo,
  },
  {
    path: 'requirements.txt',
    name: 'requirements.txt',
    category: 'doc',
    description: '项目核心与可选扩展依赖包清单 (清华/阿里云国内镜像源加速)',
    content: requirementsTxt,
  },
  {
    path: 'run.bat',
    name: 'run.bat',
    category: 'script',
    description: '标准前台启动脚本 (带实时日志终端与优雅退出)',
    content: runBat,
  },
  {
    path: 'download_models.bat',
    name: 'download_models.bat',
    category: 'script',
    description: '离线模型多源极速下载与备用镜像管理器脚本 (支持一键下载、连通性测速与镜像查询)',
    content: downloadModelsBat,
  },
  {
    path: 'run_debug.bat',
    name: 'run_debug.bat',
    category: 'script',
    description: '详细诊断模式启动脚本 (开启详细 OCR 与推理日志)',
    content: runDebugBat,
  },
  {
    path: 'start_silent.vbs',
    name: 'start_silent.vbs',
    category: 'script',
    description: 'Windows 开机后台无黑框静默启动 VBScript 脚本',
    content: startSilentVbs,
  },
];
