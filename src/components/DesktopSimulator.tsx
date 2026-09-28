import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, Monitor, Cpu, Eye, EyeOff, Layers, RefreshCw, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react';

interface BBoxItem {
  bbox: [number, number, number, number]; // x1, y1, x2, y2
  source: string;
  translated: string;
  confidence: number;
}

const SAMPLE_SCREENS: {
  id: string;
  title: string;
  category: string;
  itemsEnToZh: BBoxItem[];
  itemsZhToEn: BBoxItem[];
}[] = [
  {
    id: 'vscode',
    title: 'VS Code 代码与开发文档',
    category: 'IDE / Editor',
    itemsEnToZh: [
      {
        bbox: [32, 28, 480, 56],
        source: 'Windows 11 Offline Screen Real-Time Translation Assistant',
        translated: 'Windows 11 离线屏幕实时翻译助手',
        confidence: 0.99,
      },
      {
        bbox: [32, 70, 520, 104],
        source: 'Autonomous background screen capture, OCR, and local GGUF model inference.',
        translated: '自动后台屏幕截屏、OCR 识别与本地 GGUF 模型推理。',
        confidence: 0.98,
      },
      {
        bbox: [32, 120, 380, 148],
        source: 'High-DPI multi-monitor coordinate alignment and seamless overlay.',
        translated: '高 DPI 多显示器坐标精准对齐与无缝半透明覆盖层。',
        confidence: 0.97,
      },
      {
        bbox: [32, 168, 300, 196],
        source: 'Press Ctrl+Shift+P to open commands',
        translated: '按 Ctrl+Shift+P 打开命令面板',
        confidence: 0.99,
      },
    ],
    itemsZhToEn: [
      {
        bbox: [32, 28, 420, 56],
        source: 'Windows 11 离线屏幕实时翻译助手',
        translated: 'Windows 11 Offline Screen Real-Time Translation Assistant',
        confidence: 0.99,
      },
      {
        bbox: [32, 70, 500, 104],
        source: '无需联网，通过本地离线大模型在鼠标停顿时进行浮层翻译覆盖。',
        translated: 'Completely offline; overlays translations using local LLMs when the mouse rests.',
        confidence: 0.98,
      },
      {
        bbox: [32, 120, 360, 148],
        source: '支持 PaddleOCR 与 Qwen GGUF 智能段落合并。',
        translated: 'Supports PaddleOCR and Qwen GGUF with intelligent paragraph merging.',
        confidence: 0.98,
      },
    ],
  },
  {
    id: 'settings',
    title: 'Windows 11 系统设置界面',
    category: 'System Dialog',
    itemsEnToZh: [
      {
        bbox: [40, 30, 260, 60],
        source: 'Display & Graphics Settings',
        translated: '显示与图形设置',
        confidence: 0.99,
      },
      {
        bbox: [40, 78, 460, 106],
        source: 'Scale and layout: Change the size of text, apps, and other items.',
        translated: '缩放与布局：更改文本、应用和其他项目的大小。',
        confidence: 0.98,
      },
      {
        bbox: [40, 126, 320, 154],
        source: 'Recommended scaling: 150% (High DPI)',
        translated: '推荐缩放：150% (高清晰度显示)',
        confidence: 0.97,
      },
      {
        bbox: [40, 172, 390, 200],
        source: 'Multiple displays: Extend desktop to this display',
        translated: '多显示器：将桌面扩展到此显示器',
        confidence: 0.99,
      },
    ],
    itemsZhToEn: [
      {
        bbox: [40, 30, 220, 60],
        source: '显示与图形设置',
        translated: 'Display & Graphics Settings',
        confidence: 0.99,
      },
      {
        bbox: [40, 78, 440, 106],
        source: '更改文本、应用和其他项目的大小。',
        translated: 'Change the size of text, apps, and other items.',
        confidence: 0.98,
      },
      {
        bbox: [40, 126, 280, 154],
        source: '推荐缩放：150% (高分辨率)',
        translated: 'Recommended scaling: 150% (High DPI)',
        confidence: 0.97,
      },
    ],
  },
  {
    id: 'paper',
    title: '技术论文与技术文档',
    category: 'Documentation',
    itemsEnToZh: [
      {
        bbox: [36, 26, 490, 54],
        source: 'Accelerating Deep Neural Networks via Quantized Inference',
        translated: '通过量化推理加速深度神经网络计算',
        confidence: 0.99,
      },
      {
        bbox: [36, 68, 540, 100],
        source: 'In this paper, we explore 4-bit integer quantization (Q4_K_M) for large language models.',
        translated: '在本文中，我们探索了大语言模型的 4 位整数低比特量化 (Q4_K_M) 机制。',
        confidence: 0.98,
      },
      {
        bbox: [36, 114, 510, 144],
        source: 'Experimental results demonstrate 3.8x speedup on consumer-grade CPU and GPU.',
        translated: '实验结果表明在消费级 CPU 与 GPU 上推理速度提升达 3.8 倍。',
        confidence: 0.97,
      },
    ],
    itemsZhToEn: [
      {
        bbox: [36, 26, 420, 54],
        source: '基于 PaddleOCR 与本地大模型的实时翻译',
        translated: 'Real-time Translation based on PaddleOCR and Local LLMs',
        confidence: 0.99,
      },
      {
        bbox: [36, 68, 520, 100],
        source: '采用感知差异哈希比对静止画面，杜绝无谓的重复推理。',
        translated: 'Employs perceptual dHash comparison for still screens to prevent redundant inferences.',
        confidence: 0.98,
      },
    ],
  },
];

export const DesktopSimulator: React.FC = () => {
  const [activeScreenId, setActiveScreenId] = useState('vscode');
  const [delaySec, setDelaySec] = useState<number>(3);
  const [isEnabled, setIsEnabled] = useState<boolean>(true);
  const [direction, setDirection] = useState<'en-to-zh' | 'zh-to-en'>('en-to-zh');
  const [modelId, setModelId] = useState<'qwen2.5' | 'opus-mt'>('qwen2.5');
  const [ocrEngine, setOcrEngine] = useState<string>('auto_route');
  const [enableEnhance, setEnableEnhance] = useState<boolean>(true);
  const [enableRetry, setEnableRetry] = useState<boolean>(true);
  const [activeRoutedEngine, setActiveRoutedEngine] = useState<string>('win11_media_ocr');
  const [enhancementApplied, setEnhancementApplied] = useState<string>('无');

  // 状态机状态: IDLE, WAIT_STABLE, TRANSLATING, SHOWING, PAUSED, ERROR
  const [state, setState] = useState<'IDLE' | 'WAIT_STABLE' | 'TRANSLATING' | 'SHOWING' | 'PAUSED'>('IDLE');
  const [countdown, setCountdown] = useState<number>(delaySec);
  const [lastRequestId, setLastRequestId] = useState<string>('');
  const [cacheHit, setCacheHit] = useState<boolean>(false);
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 300, y: 150 });
  const [showOriginalBBoxes, setShowOriginalBBoxes] = useState<boolean>(true);
  const [showIpcInspector, setShowIpcInspector] = useState<boolean>(true);
  const [ipcLogs, setIpcLogs] = useState<{ time: string; type: string; summary: string }[]>([]);

  // 缓存记录模拟
  const cacheRef = useRef<Record<string, BBoxItem[]>>({});
  const timerRef = useRef<any>(null);
  const countdownIntervalRef = useRef<any>(null);

  const currentScreen = SAMPLE_SCREENS.find((s) => s.id === activeScreenId) || SAMPLE_SCREENS[0];
  const items = direction === 'en-to-zh' ? currentScreen.itemsEnToZh : currentScreen.itemsZhToEn;

  // 检查当前模型是否支持所选语言对
  const isModelSupported = !(modelId === 'opus-mt' && direction === 'zh-to-en');

  const addIpcLog = (type: string, summary: string) => {
    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');
    setIpcLogs((prev) => [{ time: timeStr, type, summary }, ...prev.slice(0, 14)]);
  };

  // 重置/触发防抖定时器
  const resetIdleTimer = () => {
    if (!isEnabled) {
      setState('PAUSED');
      return;
    }

    // 鼠标移动：立即隐藏覆盖层，状态切为 WAIT_STABLE
    setState('WAIT_STABLE');
    setCountdown(delaySec);

    if (timerRef.current) clearTimeout(timerRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);

    const startTime = Date.now();
    countdownIntervalRef.current = setInterval(() => {
      const passed = (Date.now() - startTime) / 1000;
      const remaining = Math.max(0, delaySec - passed);
      setCountdown(Number(remaining.toFixed(1)));
    }, 100);

    timerRef.current = setTimeout(() => {
      clearInterval(countdownIntervalRef.current);
      triggerTranslation();
    }, delaySec * 1000);
  };

  // 触发翻译
  const triggerTranslation = () => {
    const reqId = 'req-' + Math.random().toString(36).substring(2, 9);
    setLastRequestId(reqId);
    setState('TRANSLATING');

    const srcLang = direction === 'en-to-zh' ? 'en' : 'zh-CN';
    const tgtLang = direction === 'en-to-zh' ? 'zh-CN' : 'en';

    // 智能多模型路由决策
    const selectedEng =
      ocrEngine === 'auto_route'
        ? activeScreenId === 'vscode'
          ? 'win11_media_ocr'
          : 'rapidocr_ch'
        : ocrEngine;
    setActiveRoutedEngine(selectedEng);

    // 图像增强决策
    const isDarkTheme = activeScreenId === 'vscode';
    let appliedEnhance = '基础轻量通道';
    if (enableEnhance && isDarkTheme) {
      appliedEnhance = '暗黑背景反相 + ClearType 边缘锐化';
    } else if (enableEnhance) {
      appliedEnhance = 'ClearType 字体锐化 + CLAHE 局部对比度';
    }
    setEnhancementApplied(appliedEnhance);

    addIpcLog(
      'TRANSLATE_REQUEST',
      `[${reqId}] ${srcLang} -> ${tgtLang} | 引擎: ${selectedEng} (路由) | 增强: ${appliedEnhance} | 翻译: ${modelId === 'qwen2.5' ? 'Qwen2.5 1.5B (GGUF)' : 'OPUS-MT (CT2)'}`
    );

    if (enableEnhance && isDarkTheme) {
      addIpcLog('OCR_ENHANCE', `[${reqId}] 检出暗黑背景 (均值 26.2 < 85)，触发自适应色彩反相与抗锯齿锐化`);
    }

    if (!isModelSupported) {
      setTimeout(() => {
        addIpcLog('ERROR', `[${reqId}] UNSUPPORTED_PAIR: 当前模型不支持 ${srcLang} -> ${tgtLang}`);
        setState('IDLE');
      }, 400);
      return;
    }

    const cacheKey = `${activeScreenId}_${direction}_${modelId}_${selectedEng}`;
    const isCached = !!cacheRef.current[cacheKey];

    const inferenceDelay = isCached ? 15 : modelId === 'qwen2.5' ? 380 : 160;

    setTimeout(() => {
      setCacheHit(isCached);
      setElapsedMs(inferenceDelay);
      cacheRef.current[cacheKey] = items;

      addIpcLog(
        'TRANSLATE_RESULT',
        `[${reqId}] 成功检出 ${items.length} 段 | 耗时: ${inferenceDelay}ms | 引擎: ${selectedEng} | 缓存: ${isCached ? 'YES' : 'NO'}`
      );

      setState('SHOWING');
    }, inferenceDelay);
  };

  // 鼠标移动交互
  const handleMouseMoveOnCanvas = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    setMousePos({ x, y });
    resetIdleTimer();
  };

  // 切换配置时清空缓存
  const handleModelOrLangChange = () => {
    cacheRef.current = {};
    addIpcLog('RELOAD_CONFIG', '模型或语言变更，已自动清空 Worker 画面感知哈希缓存');
    resetIdleTimer();
  };

  useEffect(() => {
    if (!isEnabled) {
      setState('PAUSED');
      if (timerRef.current) clearTimeout(timerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    } else {
      resetIdleTimer();
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [isEnabled, delaySec, activeScreenId, direction, modelId]);

  return (
    <div className="space-y-6">
      {/* 顶部控制面板 */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-lg">
              <Monitor className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">Win11 离线翻译运行时交互仿真</h2>
              <p className="text-xs text-slate-500">模拟鼠标全局监听 (pynput)、状态机流转、PaddleOCR 段落合并与半透明黑色覆盖层</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEnabled(!isEnabled)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                isEnabled ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {isEnabled ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
              {isEnabled ? '实时翻译: 运行中' : '实时翻译: 已暂停'}
            </button>

            <button
              onClick={() => {
                cacheRef.current = {};
                addIpcLog('RELOAD_CONFIG', '手动清空哈希缓存');
                resetIdleTimer();
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-medium"
              title="清空缓存"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              清空缓存
            </button>
          </div>
        </div>

        {/* 调节栏 */}
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          {/* 场景选择 */}
          <div>
            <label className="block font-medium text-slate-700 mb-1">测试屏幕场景</label>
            <select
              value={activeScreenId}
              onChange={(e) => setActiveScreenId(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-md py-1.5 px-2.5 text-slate-800"
            >
              {SAMPLE_SCREENS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          {/* 翻译方向 */}
          <div>
            <label className="block font-medium text-slate-700 mb-1">翻译语言方向</label>
            <div className="flex items-center gap-1">
              <button
                onClick={() => {
                  setDirection('en-to-zh');
                  handleModelOrLangChange();
                }}
                className={`flex-1 py-1.5 px-2 rounded text-center font-medium border ${
                  direction === 'en-to-zh'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-slate-50 text-slate-700 border-slate-200'
                }`}
              >
                英语 → 中文
              </button>
              <button
                onClick={() => {
                  setDirection('zh-to-en');
                  handleModelOrLangChange();
                }}
                className={`flex-1 py-1.5 px-2 rounded text-center font-medium border ${
                  direction === 'zh-to-en'
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-slate-50 text-slate-700 border-slate-200'
                }`}
              >
                中文 → 英语
              </button>
            </div>
          </div>

          {/* 模型选择 */}
          <div>
            <label className="block font-medium text-slate-700 mb-1">翻译引擎与模型</label>
            <select
              value={modelId}
              onChange={(e) => {
                setModelId(e.target.value as any);
                handleModelOrLangChange();
              }}
              className="w-full bg-slate-50 border border-slate-200 rounded-md py-1.5 px-2.5 text-slate-800"
            >
              <option value="qwen2.5">Qwen2.5 1.5B (GGUF llama-cpp)</option>
              <option value="opus-mt">OPUS-MT 英译中 (CTranslate2)</option>
            </select>
          </div>

          {/* 延时滑块 */}
          <div>
            <div className="flex justify-between font-medium text-slate-700 mb-1">
              <span>鼠标静止触发延时</span>
              <span className="text-blue-600 font-bold">{delaySec} 秒</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={delaySec}
              onChange={(e) => setDelaySec(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>

        {/* OCR 路由与增强预处理控制栏 */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-700">OCR 路由策略:</span>
            <select
              value={ocrEngine}
              onChange={(e) => {
                setOcrEngine(e.target.value);
                handleModelOrLangChange();
              }}
              className="bg-slate-50 border border-slate-200 rounded py-1 px-2 text-slate-800"
            >
              <option value="auto_route">⚡ 多模型智能自动路由 (Win11原生/Rapid/Paddle 动态级联)</option>
              <option value="win11_media_ocr">Windows 11 原生系统 OCR (零资源/4K无损)</option>
              <option value="rapidocr_ch">RapidOCR 极速轻量 ONNX 引擎</option>
              <option value="easyocr_multi">EasyOCR 国际化引擎</option>
              <option value="paddleocr_ch">PaddleOCR 离线引擎</option>
            </select>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={enableEnhance}
                onChange={(e) => {
                  setEnableEnhance(e.target.checked);
                  handleModelOrLangChange();
                }}
                className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
              />
              <span className="font-medium text-slate-700">暗黑自适应反相 + 字体锐化</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={enableRetry}
                onChange={(e) => {
                  setEnableRetry(e.target.checked);
                  handleModelOrLangChange();
                }}
                className="rounded text-blue-600 focus:ring-0 w-3.5 h-3.5"
              />
              <span className="font-medium text-slate-700">自适应变体多级重试</span>
            </label>
          </div>
        </div>

        {/* 模型兼容性提示 */}
        {!isModelSupported && (
          <div className="mt-3 p-2.5 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-rose-700 text-xs font-medium">
            <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>⚠️ 规则七校验触发：当前选择的模型 OPUS-MT 仅支持「英语 → 中文」，不支持中文逆向翻译！请更换模型为 Qwen2.5 互译模型。</span>
          </div>
        )}
      </div>

      {/* 虚拟桌面舞台与状态栏 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：虚拟屏幕画布 (2 列) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500 px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-700">Windows 11 虚拟主屏幕</span>
              <span className="px-1.5 py-0.5 bg-slate-100 rounded text-[11px]">DPI: 150% (1.5x)</span>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOriginalBBoxes}
                  onChange={(e) => setShowOriginalBBoxes(e.target.checked)}
                  className="rounded text-blue-600 focus:ring-0"
                />
                <span>显示 OCR 识别框</span>
              </label>
              <span className="text-slate-400">|</span>
              <span>光标位置: ({mousePos.x}, {mousePos.y})</span>
            </div>
          </div>

          {/* 模拟屏幕容器 */}
          <div
            onMouseMove={handleMouseMoveOnCanvas}
            className="relative w-full h-[360px] bg-slate-900 rounded-xl overflow-hidden shadow-md border border-slate-300 select-none cursor-crosshair group"
            style={{
              backgroundImage:
                activeScreenId === 'vscode'
                  ? 'radial-gradient(circle at 10% 20%, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 1))'
                  : activeScreenId === 'settings'
                  ? 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)'
                  : 'linear-gradient(135deg, #1e293b 0%, #111827 100%)',
            }}
          >
            {/* 模拟 Win11 窗口标题栏 */}
            <div className="h-8 bg-slate-800/80 backdrop-blur-xs border-b border-slate-700/60 px-3 flex items-center justify-between text-xs text-slate-300">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-600 inline-block" />
                <span className="font-medium text-slate-200">{currentScreen.title}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <span>_</span>
                <span>□</span>
                <span>✕</span>
              </div>
            </div>

            {/* 屏幕内原生文本内容层 */}
            <div className="relative p-6 h-[calc(100%-32px)]">
              {items.map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    position: 'absolute',
                    left: `${item.bbox[0]}px`,
                    top: `${item.bbox[1]}px`,
                    width: `${item.bbox[2] - item.bbox[0]}px`,
                    height: `${item.bbox[3] - item.bbox[1]}px`,
                  }}
                  className={`flex items-center text-sm transition-all ${
                    showOriginalBBoxes ? 'border border-dashed border-sky-400/40 bg-sky-500/5' : ''
                  }`}
                >
                  <span className="text-slate-100 font-mono tracking-tight leading-snug">
                    {item.source}
                  </span>
                  {showOriginalBBoxes && (
                    <span className="absolute -top-3.5 right-0 text-[10px] text-sky-300 font-mono bg-sky-950/80 px-1 rounded">
                      {(item.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              ))}

              {/* 覆盖层 (OverlayWindow): 状态为 SHOWING 时以半透明黑底 + 翻译后文本覆盖原位置 */}
              {state === 'SHOWING' && isModelSupported && (
                <div className="absolute inset-0 pointer-events-none transition-opacity duration-150 animate-fadeIn">
                  {items.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        position: 'absolute',
                        left: `${item.bbox[0] - 4}px`,
                        top: `${item.bbox[1] - 2}px`,
                        width: `${item.bbox[2] - item.bbox[0] + 8}px`,
                        minHeight: `${item.bbox[3] - item.bbox[1] + 4}px`,
                      }}
                      className="bg-black/85 backdrop-blur-xs border border-white/20 rounded px-2 py-0.5 shadow-lg flex items-center"
                    >
                      <span className="text-white text-[13px] font-sans font-medium tracking-normal leading-snug break-words">
                        {item.translated}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* 鼠标光标示意 */}
              <div
                className="absolute pointer-events-none -translate-x-1/2 -translate-y-1/2 transition-transform duration-75 z-20"
                style={{ left: `${mousePos.x}px`, top: `${mousePos.y}px` }}
              >
                <div className="w-3.5 h-3.5 border-2 border-white rounded-full bg-blue-500/80 shadow-md animate-pulse" />
              </div>

              {/* 提示遮罩：鼠标移动提示 */}
              <div className="absolute bottom-2 right-3 text-[11px] text-slate-400 bg-slate-800/80 px-2 py-1 rounded border border-slate-700 pointer-events-none">
                在上方区域内移动鼠标触发防抖；停止移动 {delaySec} 秒后将自动翻译
              </div>
            </div>
          </div>

          {/* 实时状态流转指示条 */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
            <div className="flex items-center justify-between mb-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-700">状态机当前流转状态:</span>
                <span
                  className={`px-2 py-0.5 rounded font-mono font-bold text-xs ${
                    state === 'IDLE'
                      ? 'bg-slate-100 text-slate-700'
                      : state === 'WAIT_STABLE'
                      ? 'bg-amber-100 text-amber-800 animate-pulse'
                      : state === 'TRANSLATING'
                      ? 'bg-blue-100 text-blue-800'
                      : state === 'SHOWING'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-rose-100 text-rose-800'
                  }`}
                >
                  {state}
                </span>
              </div>

              {state === 'WAIT_STABLE' && (
                <span className="text-amber-700 font-mono text-xs">
                  静止等待倒计时: <b>{countdown}s</b> / {delaySec}s
                </span>
              )}

              {state === 'SHOWING' && (
                <span className="text-emerald-700 text-xs flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  覆盖层展示中 (鼠标移动将立即隐藏)
                </span>
              )}
            </div>

            {/* 进度条 */}
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-100 ${
                  state === 'WAIT_STABLE'
                    ? 'bg-amber-500'
                    : state === 'TRANSLATING'
                    ? 'bg-blue-600 animate-pulse'
                    : state === 'SHOWING'
                    ? 'bg-emerald-500'
                    : 'bg-slate-300'
                }`}
                style={{
                  width:
                    state === 'WAIT_STABLE'
                      ? `${((delaySec - countdown) / delaySec) * 100}%`
                      : state === 'SHOWING' || state === 'TRANSLATING'
                      ? '100%'
                      : '0%',
                }}
              />
            </div>

            {/* 性能与缓存指标 */}
            <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              <div className="bg-slate-50 p-2 rounded-lg">
                <span className="text-slate-500 block text-[11px]">响应耗时</span>
                <span className="font-mono font-semibold text-slate-800">{elapsedMs} ms</span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg">
                <span className="text-slate-500 block text-[11px]">dHash 画面缓存</span>
                <span className={`font-semibold ${cacheHit ? 'text-emerald-600' : 'text-slate-600'}`}>
                  {cacheHit ? '✓ 命中 (距离 0)' : '未命中 (新画面)'}
                </span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg">
                <span className="text-slate-500 block text-[11px]">OCR 路由调度</span>
                <span className="font-mono font-semibold text-blue-700">{activeRoutedEngine}</span>
              </div>
              <div className="bg-slate-50 p-2 rounded-lg">
                <span className="text-slate-500 block text-[11px]">熔断器状态</span>
                <span className="font-semibold text-emerald-600">✓ 全部健康可用</span>
              </div>
            </div>

            {/* 预处理与增强状态条 */}
            <div className="mt-2 px-3 py-1.5 bg-blue-50/60 border border-blue-100 rounded-md text-[11px] text-blue-900 flex items-center justify-between">
              <span><b>当前图像增强预处理:</b> {enhancementApplied}</span>
              <span><b>识别段落:</b> {items.length} 段</span>
            </div>
          </div>
        </div>

        {/* 右侧：IPC 跨进程通信监视器 */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col h-full">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-800">IPC 跨进程通信监视</h3>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Queue Buffer</span>
          </div>

          <p className="text-xs text-slate-500 mb-3 leading-relaxed">
            主进程通过 <code className="text-blue-600 font-mono">multiprocessing.Queue</code> 与 Worker 子进程通信，仅传递 JSON 可序列化数据。
          </p>

          <div className="flex-1 bg-slate-950 rounded-lg p-3 overflow-y-auto font-mono text-[11px] space-y-2 max-h-[380px]">
            {ipcLogs.length === 0 ? (
              <div className="text-slate-500 italic py-6 text-center">暂无 IPC 消息，在左侧移动鼠标测试...</div>
            ) : (
              ipcLogs.map((log, i) => (
                <div key={i} className="border-b border-slate-800/80 pb-1.5 last:border-0">
                  <div className="flex items-center justify-between text-slate-400 text-[10px]">
                    <span>{log.time}</span>
                    <span
                      className={`font-semibold px-1 rounded ${
                        log.type.includes('RESULT')
                          ? 'text-emerald-400 bg-emerald-950/60'
                          : log.type.includes('REQUEST')
                          ? 'text-sky-400 bg-sky-950/60'
                          : log.type.includes('ERROR')
                          ? 'text-rose-400 bg-rose-950/60'
                          : 'text-amber-400 bg-amber-950/60'
                      }`}
                    >
                      {log.type}
                    </span>
                  </div>
                  <p className="text-slate-300 mt-1 break-all leading-tight">{log.summary}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
