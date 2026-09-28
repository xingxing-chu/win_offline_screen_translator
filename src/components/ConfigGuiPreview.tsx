import React, { useState, useEffect } from 'react';
import {
  Settings,
  Save,
  RefreshCw,
  FileText,
  CheckCircle,
  AlertTriangle,
  Globe,
  Sliders,
  ShieldCheck,
  Download,
  Zap,
  Cpu,
  Layers,
  Sparkles,
  X,
} from 'lucide-react';

export const ConfigGuiPreview: React.FC = () => {
  const [uiLang, setUiLang] = useState<'auto' | 'zh_CN' | 'en_US'>('auto');
  const [sourceLang, setSourceLang] = useState<string>('en');
  const [targetLang, setTargetLang] = useState<string>('zh-CN');
  const [ocrModel, setOcrModel] = useState<string>('win11_media_ocr');
  const [transModel, setTransModel] = useState<string>('qwen2.5-1.5b-instruct-q4_k_m');
  const [delaySec, setDelaySec] = useState<number>(3);
  const [enabled, setEnabled] = useState<boolean>(true);
  const [autostart, setAutostart] = useState<boolean>(false);

  // OCR 增强与路由
  const [autoRoute, setAutoRoute] = useState<boolean>(true);
  const [autoInvertDark, setAutoInvertDark] = useState<boolean>(true);
  const [clahe, setClahe] = useState<boolean>(false);
  const [sharpen, setSharpen] = useState<boolean>(true);
  const [adaptiveRetry, setAdaptiveRetry] = useState<boolean>(true);
  const [enableAiOcrRefine, setEnableAiOcrRefine] = useState<boolean>(true);

  // 当前激活的选项卡 (杜绝界面压缩挤压)
  const [activeSettingTab, setActiveSettingTab] = useState<'general' | 'models' | 'ocr' | 'status'>('general');
  const [showRecordModal, setShowRecordModal] = useState<boolean>(false);
  const [showMirrorsModal, setShowMirrorsModal] = useState<boolean>(false);
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

  // 下载弹窗状态
  const [showDownloadModal, setShowDownloadModal] = useState<boolean>(false);
  const [downloadTargetName, setDownloadTargetName] = useState<string>('');
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [downloadSpeed, setDownloadSpeed] = useState<string>('0 MB/s');
  const [downloadLogs, setDownloadLogs] = useState<string[]>([]);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  const [showSavedNotification, setShowSavedNotification] = useState<boolean>(false);

  // 解析当前界面语言
  const activeUi = uiLang === 'auto' ? 'zh_CN' : uiLang;
  const isZh = activeUi === 'zh_CN';

  // 验证模型与语言对兼容性
  const isOpus = transModel === 'opus-mt-en-zh-ct2';
  const isPairValid = !isOpus || (sourceLang === 'en' && targetLang === 'zh-CN');

  const copyToClipboard = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(null), 2500);
  };

  const handleSave = () => {
    setShowSavedNotification(true);
    setTimeout(() => {
      setShowSavedNotification(false);
    }, 2800);
  };

  const startDownloadSimulation = (targetName?: string) => {
    const name = targetName || `${ocrModel}, ${transModel}`;
    setDownloadTargetName(name);
    setShowDownloadModal(true);
    setIsDownloading(true);
    setDownloadProgress(0);
    setDownloadLogs([
      `[准备] 正在连接国内开源极速镜像站 (ModelScope / 清华源 / HF-Mirror)...`,
      `[解析] 目标下载模型: ${name}`,
      `[线程] 启动非阻塞后台下载工作线程 QThread...`,
    ]);

    let current = 0;
    const interval = setInterval(() => {
      current += Math.floor(Math.random() * 15) + 10;
      if (current >= 100) {
        current = 100;
        clearInterval(interval);
        setIsDownloading(false);
        setDownloadProgress(100);
        setDownloadSpeed('0 MB/s');
        setDownloadLogs((prev) => [
          ...prev,
          `[校验] SHA-256 完整性与体积防伪校验完成: 100% 匹配！`,
          `[就绪] 离线权重已解压并配置完成，挂载至 models/ 目录。`,
          `✓ 下载流程全部成功执行完毕，模型状态已刷新为【已就绪】！`,
        ]);
      } else {
        setDownloadProgress(current);
        const speed = (Math.random() * 8 + 14).toFixed(1);
        setDownloadSpeed(`${speed} MB/s`);
        if (current > 30 && current < 50) {
          setDownloadLogs((prev) =>
            prev.length < 5
              ? [...prev, `[下载中] 分块接收数据 (${current}%): 速度 ${speed} MB/s...`]
              : prev
          );
        }
      }
    }, 400);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-sky-50 text-sky-700 rounded-lg">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                {isZh ? 'PyQt5 设置窗口实时交互仿真 (Windows 11 Fluent)' : 'PyQt5 Settings Dialog Live Preview'}
              </h2>
              <p className="text-xs text-slate-500">
                {isZh
                  ? '对应 config_gui.py 的所有功能控件、多模型自动路由、OCR 增强预处理、自适应重试与下载进度指示器'
                  : 'Full replica of config_gui.py with multi-model routing, OCR enhancements, and download dialog'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 仿真 PyQt5 对话框视窗 */}
      <div className="max-w-3xl mx-auto bg-[#F9F9FB] border border-slate-300 rounded-xl shadow-xl overflow-hidden relative">
        {/* Win11 窗口头部 */}
        <div className="bg-white/80 backdrop-blur-md px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-600 rounded flex items-center justify-center text-[10px] text-white font-bold">
              译
            </div>
            <span className="text-xs font-semibold text-slate-800">
              {isZh ? 'Win11 离线屏幕实时翻译助手 - 设置' : 'Win11 Offline Screen Translator - Settings'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <button className="px-2 py-0.5 hover:bg-slate-100 rounded">_</button>
            <button className="px-2 py-0.5 hover:bg-slate-100 rounded">□</button>
            <button className="px-2 py-0.5 hover:bg-rose-50 hover:text-rose-600 rounded">✕</button>
          </div>
        </div>

        {/* Win11 选项卡导航栏 (消除垂直堆叠压缩，界面宽敞舒朗) */}
        <div className="flex border-b border-slate-200 bg-slate-100/80 px-4 pt-2 gap-1 overflow-x-auto">
          <button
            onClick={() => setActiveSettingTab('general')}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeSettingTab === 'general'
                ? 'bg-white text-[#0067C0] border-t border-x border-slate-200 font-semibold shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>{isZh ? '🌐 语言与常规' : 'Language & General'}</span>
          </button>
          <button
            onClick={() => setActiveSettingTab('models')}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeSettingTab === 'models'
                ? 'bg-white text-[#0067C0] border-t border-x border-slate-200 font-semibold shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>{isZh ? '🤖 离线模型管理' : 'Offline Models'}</span>
          </button>
          <button
            onClick={() => setActiveSettingTab('ocr')}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeSettingTab === 'ocr'
                ? 'bg-white text-[#0067C0] border-t border-x border-slate-200 font-semibold shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{isZh ? '🔍 OCR 增强与识别' : 'OCR & Enhancement'}</span>
          </button>
          <button
            onClick={() => setActiveSettingTab('status')}
            className={`px-3 py-2 text-xs font-medium rounded-t-lg flex items-center gap-1.5 transition-colors cursor-pointer ${
              activeSettingTab === 'status'
                ? 'bg-white text-[#0067C0] border-t border-x border-slate-200 font-semibold shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{isZh ? '📊 运行状态与存证' : 'Status & Evidence'}</span>
          </button>
        </div>

        {/* 窗口主体选项卡内容区 (平滑滚动，杜绝挤压) */}
        <div className="p-6 space-y-5 min-h-[360px] max-h-[520px] overflow-y-auto">
          {/* 保存成功浮动提示 */}
          {showSavedNotification && (
            <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg flex items-center gap-2 text-emerald-800 text-xs animate-fadeIn">
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                {isZh
                  ? '✓ 配置已成功写入 settings.json！旧翻译缓存已清空，Worker 进程已完成多模型路由与增强参数热重载。'
                  : '✓ Configuration saved to settings.json! Model router and enhancer reloaded.'}
              </span>
            </div>
          )}

          {/* 选项卡 1: 🌐 语言与常规设置 */}
          {activeSettingTab === 'general' && (
            <div className="space-y-4">
              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs">
                <h3 className="text-sm font-semibold text-[#0067C0] mb-3 flex items-center gap-1.5">
                  <Globe className="w-4 h-4" />
                  {isZh ? '语言与区域设置' : 'Language & Region Settings'}
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                  <div>
                    <label className="block text-slate-700 font-medium mb-1">
                      {isZh ? '界面显示语言' : 'UI Language'}
                    </label>
                    <select
                      value={uiLang}
                      onChange={(e) => setUiLang(e.target.value as any)}
                      className="w-full bg-white border border-slate-300 rounded-md py-1.5 px-2.5 text-slate-800 focus:outline-none focus:border-blue-600"
                    >
                      <option value="auto">{isZh ? '跟随系统 (Auto - 简体中文)' : 'Follow System (Auto)'}</option>
                      <option value="zh_CN">简体中文 (zh-CN)</option>
                      <option value="en_US">English (en-US)</option>
                    </select>
                    <span className="text-[11px] text-slate-400 mt-1 block">
                      {isZh ? '根据系统语言自动设置默认' : 'Auto detects Windows locale'}
                    </span>
                  </div>

                  <div>
                    <label className="block text-slate-700 font-medium mb-1">
                      {isZh ? '翻译源语言' : 'Source Language'}
                    </label>
                    <select
                      value={sourceLang}
                      onChange={(e) => setSourceLang(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-md py-1.5 px-2.5 text-slate-800 focus:outline-none focus:border-blue-600"
                    >
                      <option value="auto">{isZh ? '自动检测 (Auto Detect)' : 'Auto Detect'}</option>
                      <option value="en">English (en)</option>
                      <option value="zh-CN">简体中文 (zh-CN)</option>
                      <option value="ja">日本語 (ja)</option>
                      <option value="ko">한국어 (ko)</option>
                      <option value="fr">Français (fr)</option>
                      <option value="de">Deutsch (de)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-700 font-medium mb-1">
                      {isZh ? '翻译目标语言' : 'Target Language'}
                    </label>
                    <select
                      value={targetLang}
                      onChange={(e) => setTargetLang(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-md py-1.5 px-2.5 text-slate-800 focus:outline-none focus:border-blue-600"
                    >
                      <option value="zh-CN">简体中文 (zh-CN)</option>
                      <option value="en">English (en)</option>
                      <option value="ja">日本語 (ja)</option>
                      <option value="ko">한국어 (ko)</option>
                      <option value="fr">Français (fr)</option>
                      <option value="de">Deutsch (de)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs">
                <h3 className="text-sm font-semibold text-[#0067C0] mb-3">
                  {isZh ? '常规设置与静止触发' : 'General & Idle Trigger'}
                </h3>

                <div className="space-y-3 text-xs">
                  <label className="flex items-center gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) => setEnabled(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4"
                    />
                    <span>{isZh ? '启用屏幕实时翻译' : 'Enable real-time screen translation'}</span>
                  </label>

                  <label className="flex items-center gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autostart}
                      onChange={(e) => setAutostart(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4"
                    />
                    <span>{isZh ? '开机自动启动' : 'Launch on system startup'}</span>
                  </label>

                  <div className="pt-2">
                    <div className="flex items-center justify-between mb-1 text-slate-700 font-medium">
                      <span>{isZh ? '鼠标静止触发延时' : 'Mouse idle trigger delay'}:</span>
                      <span className="text-[#0067C0] font-bold">{delaySec} 秒 (s)</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="1"
                        max="10"
                        value={delaySec}
                        onChange={(e) => setDelaySec(Number(e.target.value))}
                        className="flex-1 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0067C0]"
                      />
                      <span className="px-2 py-1 bg-slate-100 border border-slate-300 rounded font-mono text-xs">
                        {delaySec} s
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 选项卡 2: 🤖 离线模型管理 */}
          {activeSettingTab === 'models' && (
            <div className="space-y-4">
              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-[#0067C0] flex items-center gap-1.5">
                    <Sliders className="w-4 h-4" />
                    {isZh ? '离线模型配置与状态' : 'Offline Models & Status'}
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowMirrorsModal(true)}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-white text-[#0067C0] border border-[#0067C0] hover:bg-blue-50 rounded-md font-semibold transition-colors cursor-pointer shadow-xs"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{isZh ? '🌐 离线模型备用镜像中心' : 'Mirrors Center'}</span>
                    </button>
                    <button
                      onClick={() => startDownloadSimulation()}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs bg-[#0067C0] text-white hover:bg-[#00559E] rounded-md font-semibold transition-colors cursor-pointer shadow-xs"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{isZh ? '⚡ 一键检查/自动下载未就绪模型' : 'Check/Download Models'}</span>
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs mb-3">
                  <div>
                    <label className="block text-slate-700 font-medium mb-1">
                      {isZh ? '首选 OCR 文字识别模型' : 'OCR Engine'}
                    </label>
                    <select
                      value={ocrModel}
                      onChange={(e) => setOcrModel(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-md py-1.5 px-2.5 text-slate-800 focus:outline-none focus:border-blue-600 font-sans"
                    >
                      <option value="win11_media_ocr">
                        Windows 11 原生系统 OCR [已就绪·免下载·0显存]
                      </option>
                      <option value="rapidocr_ch">
                        RapidOCR ONNX 极速纯CPU引擎 [已就绪·约16MB]
                      </option>
                      <option value="paddleocr_ch">
                        PaddleOCR PP-OCRv4 中英离线模型 [待下载·约17MB]
                      </option>
                      <option value="easyocr_multi">
                        EasyOCR 80语种多语言离线模型 [待下载]
                      </option>
                    </select>
                    <span className="text-[11px] text-emerald-600 mt-1 block">
                      ✓ 首选推荐 Windows 11 原生 OCR，0 显存占用，30ms 极速响应，屏幕截屏无畸变识别
                    </span>
                  </div>

                  <div>
                    <label className="block text-slate-700 font-medium mb-1">
                      {isZh ? '离线翻译模型' : 'Translation Model'}
                    </label>
                    <select
                      value={transModel}
                      onChange={(e) => setTransModel(e.target.value)}
                      className="w-full bg-white border border-slate-300 rounded-md py-1.5 px-2.5 text-slate-800 focus:outline-none focus:border-blue-600"
                    >
                      <option value="qwen2.5-1.5b-instruct-q4_k_m">
                        Qwen2.5 1.5B (GGUF, ~1.1GB, 中英高质量互译) [待下载]
                      </option>
                      <option value="opus-mt-en-zh-ct2">
                        OPUS-MT 英译中 (CTranslate2, ~150MB, 极速专精) [待下载]
                      </option>
                      <option value="qwen2.5-0.5b-instruct-q4_k_m">
                        Qwen2.5 0.5B (GGUF, ~400MB, 超轻量) [待下载]
                      </option>
                    </select>
                    <span className="text-[11px] text-slate-400 mt-1 block">
                      未就绪时自动由内置高可靠离线词典翻译内核无缝接管，确保取词零中断
                    </span>
                  </div>
                </div>

                {/* 模型就绪状态与本地文件详情卡片 */}
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1 mb-3">
                  <div className="font-semibold text-slate-700">📊 所选模型就绪与本地文件明细：</div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-600">• OCR 文字识别: {ocrModel} →</span>
                    <span className="text-emerald-700 font-semibold">[已就绪] (本地文件: ✓ 正常)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-600">• 离线神经翻译: {transModel} →</span>
                    <span className="text-amber-700 font-semibold">[待下载 / 内置离线词典已接管] (本地文件: 待下载)</span>
                  </div>
                </div>

                {/* 语言对兼容性即时校验提示 */}
                <div className="text-xs">
                  {isPairValid ? (
                    <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded text-emerald-800 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>
                        {isZh
                          ? '✓ 当前模型完全支持所选语言对 (支持源: en, zh-CN → 目标: en, zh-CN)'
                          : '✓ Model supports selected language pair'}
                      </span>
                    </div>
                  ) : (
                    <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-rose-800 flex items-center gap-2 font-medium">
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span>
                        {isZh
                          ? '⚠️ 当前模型不支持所选语言对，请更换模型！(OPUS-MT 仅专精英文到中文)'
                          : '⚠️ Current model does not support this language pair!'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 选项卡 3: 🔍 OCR 增强与识别 */}
          {activeSettingTab === 'ocr' && (
            <div className="space-y-4">
              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs">
                <h3 className="text-sm font-semibold text-[#0067C0] mb-3 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" />
                  {isZh ? 'OCR 识别增强预处理与多模型智能路由' : 'OCR Enhancement & Routing'}
                </h3>

                <div className="space-y-3 text-xs">
                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoRoute}
                      onChange={(e) => setAutoRoute(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? '启用多模型自动路由 (智能根据语言、分辨率调度首选/备选引擎，并启用熔断故障隔离)'
                        : 'Enable multi-model auto-routing with circuit breaker fault tolerance'}
                    </span>
                  </label>

                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoInvertDark}
                      onChange={(e) => setAutoInvertDark(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? '暗黑模式文字自适应反相 (检测深色/黑色背景并反转为浅色，大幅改善暗黑窗口文字检出率)'
                        : 'Dark mode text adaptive inversion (converts dark background for better detection)'}
                    </span>
                  </label>

                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={sharpen}
                      onChange={(e) => setSharpen(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? 'ClearType 字体平滑抗锯齿边缘锐化 (消除微小文字模糊，增强字符轮廓边缘梯度)'
                        : 'ClearType sub-pixel font sharpening (unsharp mask filter)'}
                    </span>
                  </label>

                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={clahe}
                      onChange={(e) => setClahe(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? '弱对比度局部 CLAHE 自适应直方图均衡 (提升低对比度文本可视度，耗时仅 ~3ms)'
                        : 'Contrast Limited Adaptive Histogram Equalization (CLAHE)'}
                    </span>
                  </label>

                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={adaptiveRetry}
                      onChange={(e) => setAdaptiveRetry(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? '未检出文字时启用多级变体自适应重试 (自动应用反相/对比度/二值化重试，杜绝空文本返回)'
                        : 'Multi-stage adaptive retry with image variants if text is undetected'}
                    </span>
                  </label>

                  <label className="flex items-start gap-2 text-slate-800 font-medium cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableAiOcrRefine}
                      onChange={(e) => setEnableAiOcrRefine(e.target.checked)}
                      className="rounded text-blue-600 focus:ring-0 w-4 h-4 mt-0.5"
                    />
                    <span>
                      {isZh
                        ? '启用 AI 大模型二次审校与自动补全校正 (修正 OCR 识别笔误与跨行截断断词)'
                        : 'Enable AI secondary proofreading to correct typos and broken words'}
                    </span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* 选项卡 4: 📊 运行状态与存证 */}
          {activeSettingTab === 'status' && (
            <div className="space-y-4">
              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs">
                <h3 className="text-sm font-semibold text-[#0067C0] mb-3">
                  {isZh ? '系统与组件运行状态' : 'System Status'}
                </h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                    <div className="text-slate-500 text-[11px]">软件版本</div>
                    <div className="font-semibold text-slate-800 mt-0.5">v1.0.0 (Fluent Build)</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                    <div className="text-slate-500 text-[11px]">Worker 子进程</div>
                    <div className="font-semibold text-emerald-700 mt-0.5">准备就绪 (PID 活跃)</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                    <div className="text-slate-500 text-[11px]">OCR 识别模块</div>
                    <div className="font-semibold text-emerald-700 mt-0.5">已加载至内存 (Windows.Media.Ocr)</div>
                  </div>
                  <div className="p-2.5 bg-slate-50 border border-slate-200 rounded">
                    <div className="text-slate-500 text-[11px]">翻译引擎</div>
                    <div className="font-semibold text-blue-700 mt-0.5">高可靠离线词典翻译内核 (就绪)</div>
                  </div>
                </div>
              </div>

              <div className="bg-white border border-[#E0E2E7] rounded-lg p-4 shadow-xs space-y-3">
                <h3 className="text-sm font-semibold text-[#0067C0] flex items-center gap-1.5">
                  <FileText className="w-4 h-4" />
                  {isZh ? '📁 OCR 与翻译存证系统 (ocr_records/)' : 'Evidence & Audit System'}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  系统已激活全流程存证机制：每次屏幕截取、原始 OCR 文字、二次审校与最终翻译呈现，
                  均会以时间戳纯文本 (.txt) 文件自动保存至 <b>ocr_records</b> 目录，方便随时核对排查。
                </p>
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <button
                    onClick={() => setShowRecordModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 cursor-pointer shadow-xs"
                  >
                    <span>📂 打开存证目录 (ocr_records)</span>
                  </button>
                  <button
                    onClick={() => setShowRecordModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 cursor-pointer shadow-xs"
                  >
                    <span>📄 查看最新单次存证报告</span>
                  </button>
                  <button
                    onClick={() => alert(isZh ? '今日日志: project/logs/YYYY-MM-DD.log' : 'Logs in project/logs/')}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 cursor-pointer shadow-xs"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>📜 查看今日运行日志</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 底部功能按钮栏 (始终吸底常驻) */}
        <div className="flex items-center justify-between p-4 bg-slate-50 border-t border-slate-200">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowRecordModal(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-100 cursor-pointer shadow-xs"
            >
              <span>📂 存证目录</span>
            </button>
            <button
              onClick={() => setShowRecordModal(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-100 cursor-pointer shadow-xs"
            >
              <span>📄 最新存证</span>
            </button>
            <button
              onClick={() => alert(isZh ? '日志路径: project/logs/YYYY-MM-DD.log' : 'Logs in project/logs/')}
              className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-100 cursor-pointer shadow-xs"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>{isZh ? '查看日志' : 'Logs'}</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-[#0067C0] hover:bg-[#005A9E] rounded-md shadow-xs cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{isZh ? '保存并应用设置' : 'Save & Apply'}</span>
            </button>
          </div>
        </div>

        {/* 单次存证报告查看模态窗口 */}
        {showRecordModal && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-300 w-full max-w-xl max-h-[90%] flex flex-col overflow-hidden animate-fadeIn">
              <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-semibold text-slate-800">
                    存证文本查看器 - project/ocr_records/ (纯文本报告)
                  </span>
                </div>
                <button
                  onClick={() => setShowRecordModal(false)}
                  className="p-1 hover:bg-slate-200 rounded text-slate-500 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="p-4 overflow-y-auto font-mono text-[11px] leading-relaxed text-slate-800 bg-slate-900/5 space-y-3">
                <div className="p-3 bg-white border border-slate-200 rounded-lg shadow-2xs whitespace-pre-wrap">
{`==================================================================================
         Win11 离线屏幕实时翻译助手 - OCR 识别与翻译全流程存证报告
==================================================================================
触发时间     : 2026-09-27 12:00:15.342
请求 ID      : req-8f92a1
画面哈希     : d41d8cd98f00b204...
OCR 识别引擎 : win11_media_ocr
离线翻译模型 : qwen2.5-1.5b-instruct-q4_k_m (内置智能离线词典接管中)
翻译语言配置 : 配置源[en] -> 目标[zh-CN] (实际研判主语言: [en])
缓存复用状态 : × 未命中缓存 (全新完整识别与翻译)
流程耗时统计 : 总耗时: 38ms | 截图: 4ms | OCR识别: 28ms | 文本清洗: 1ms | 翻译: 5ms
数据量概览   : OCR原始文本框: 3 个 | 拓扑合并段落: 2 个 | 需翻译文本: 2 个 | 最终呈现: 2 个
----------------------------------------------------------------------------------

【第一部分：OCR 原始检测识别文字】 (共检测出 3 个原始文本区域)
----------------------------------------------------------------------------------
[001] 坐标: [ 210,  140,  450,  180] | 置信度: 0.98 | 原始识别文本: "Install Now"
[002] 坐标: [ 210,  190,  620,  230] | 置信度: 0.96 | 原始识别文本: "Customize installation"
[003] 坐标: [ 210,  260,  580,  290] | 置信度: 0.94 | 原始识别文本: "Add Python to PATH"

【第二部分：段落合并与二次识别/AI审校/过滤研判】 (合并形成 2 个自然段落)
----------------------------------------------------------------------------------
[001] 合并坐标: [ 210,  140,  450,  180] (均值置信度: 0.98)
      状态研判: ✓ 需翻译 [标准UI交互文本]
      段落文本: "Install Now"
[002] 合并坐标: [ 210,  190,  620,  230] (均值置信度: 0.96)
      状态研判: ✓ 需翻译 [标准UI交互文本]
      段落文本: "Customize installation"

【第三部分：最终翻译呈现结果】 (共生成 2 个屏幕覆盖翻译框)
----------------------------------------------------------------------------------
[001] 屏幕覆盖区域: [ 210,  140,  450,  180]
      源语言原文: "Install Now"
      翻译呈现文: "立即安装"
[002] 屏幕覆盖区域: [ 210,  190,  620,  230]
      源语言原文: "Customize installation"
      翻译呈现文: "自定义安装"

==================================================================================
存证记录完毕。此文件由 Win11 离线屏幕实时翻译助手自动写入，用于追溯核验 OCR 精度与翻译效果。
==================================================================================`}
                </div>
              </div>

              <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs">
                <span className="text-slate-500 text-[11px]">存证路径: project/ocr_records/*.txt</span>
                <button
                  onClick={() => setShowRecordModal(false)}
                  className="px-4 py-1.5 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 cursor-pointer"
                >
                  关闭
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 模型下载 GUI 对话框仿真浮层 (ModelDownloadDialog) */}
        {showDownloadModal && (
          <div className="absolute inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-300 w-full max-w-md overflow-hidden animate-fadeIn">
              <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Download className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-semibold text-slate-800">
                    离线模型高速自动下载管理器 (PyQt5 GUI)
                  </span>
                </div>
                {!isDownloading && (
                  <button
                    onClick={() => setShowDownloadModal(false)}
                    className="p-1 hover:bg-slate-200 rounded text-slate-500"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              <div className="p-5 space-y-4 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-700">
                    {isDownloading ? '正在从国内镜像源下载模型权重...' : '下载已完成！'}
                  </span>
                  <span className="font-mono font-bold text-blue-600">{downloadProgress}%</span>
                </div>

                {/* 进度条 */}
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      downloadProgress === 100 ? 'bg-emerald-500' : 'bg-blue-600'
                    }`}
                    style={{ width: `${downloadProgress}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>源: ModelScope / 清华源</span>
                  <span>速度: {downloadSpeed}</span>
                </div>

                {/* 终端日志滚动窗 */}
                <div className="bg-slate-900 text-slate-200 font-mono text-[11px] p-3 rounded-lg h-32 overflow-y-auto space-y-1">
                  {downloadLogs.map((log, idx) => (
                    <div key={idx}>{log}</div>
                  ))}
                </div>

                <div className="flex justify-end pt-2">
                  {isDownloading ? (
                    <button
                      onClick={() => {
                        setIsDownloading(false);
                        setShowDownloadModal(false);
                      }}
                      className="px-3 py-1.5 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded hover:bg-rose-100"
                    >
                      取消下载
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowDownloadModal(false)}
                      className="px-4 py-1.5 text-xs bg-blue-600 text-white rounded font-medium hover:bg-blue-700"
                    >
                      完成并关闭
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 离线模型多源备用镜像与下载中心 (ModelMirrorsDialog) */}
        {showMirrorsModal && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl border border-slate-300 w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-fadeIn">
              <div className="bg-slate-50 border-b border-slate-200 px-5 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-semibold text-slate-800">
                    🌐 离线模型高速下载与备用镜像中心 (Model Mirrors Center)
                  </span>
                </div>
                <button
                  onClick={() => setShowMirrorsModal(false)}
                  className="p-1 hover:bg-slate-200 rounded text-slate-500 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* 头部提示卡片 */}
              <div className="p-4 bg-sky-50 border-b border-sky-100 text-xs text-sky-900 space-y-1">
                <div className="font-semibold flex items-center gap-1.5 text-sky-800">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>多源容灾高速下载保障：</span>
                </div>
                <p className="text-[11px] leading-relaxed text-sky-800">
                  系统内置【ModelScope 阿里官方源】、【HF-Mirror 国内镜像】、【Hugging Face 官方直连】、【百度飞桨 BOS】等多节点容灾。
                  如遇网络波动，可点击【复制】链接使用迅雷、IDM等多线程工具下载，文件下载后直接放入 <code className="bg-white/70 px-1 py-0.5 rounded font-mono text-sky-900 border border-sky-200">models/</code> 对应文件夹即可秒级自动识别！
                </p>
                {copiedUrl && (
                  <div className="p-1.5 bg-emerald-100 text-emerald-800 text-[11px] rounded font-medium animate-fadeIn">
                    ✓ 下载链接已复制到剪贴板，可粘贴至浏览器/迅雷/IDM高速下载！
                  </div>
                )}
              </div>

              {/* 滚动模型列表 */}
              <div className="p-4 overflow-y-auto space-y-4 flex-1 text-xs">
                {/* 翻译大模型 */}
                <div>
                  <h4 className="font-bold text-slate-800 mb-2 flex items-center gap-1.5 text-xs text-[#0067C0]">
                    <Sliders className="w-3.5 h-3.5" />
                    <span>🤖 离线神经翻译大模型 (GGUF / CTranslate2)</span>
                  </h4>
                  <div className="space-y-3">
                    {/* Qwen 0.5B */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">Qwen2.5 0.5B Instruct Q4_K_M (469MB)</div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 font-bold rounded text-[10px]">已就绪</span>
                          <button
                            onClick={() => startDownloadSimulation('Qwen2.5 0.5B Instruct')}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer"
                          >
                            ⚡ 重新下载
                          </button>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-500">轻量级小钢炮，老旧CPU/低配电脑首选，单次识别翻译仅需几十毫秒</div>
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] text-slate-400 font-medium">可用备用镜像源 (点击一键复制):</div>
                        {[
                          { name: 'ModelScope 阿里官方极速源 (国内免翻墙·推荐)', url: 'https://modelscope.cn/models/qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/qwen2.5-0.5b-instruct-q4_k_m.gguf' },
                          { name: 'HF-Mirror 国内全量加速镜像', url: 'https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf' },
                          { name: 'Hugging Face 官方直连源', url: 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf' },
                          { name: 'ModelScope 社区备份源 (bartowski)', url: 'https://modelscope.cn/models/bartowski/Qwen2.5-0.5B-Instruct-GGUF/resolve/master/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf' },
                        ].map((mir, idx) => (
                          <div key={idx} className="flex items-center justify-between bg-white border border-slate-200 rounded p-1.5 text-[11px]">
                            <span className="text-slate-700 truncate mr-2 font-mono text-[10px]">{mir.name}</span>
                            <button
                              onClick={() => copyToClipboard(mir.url)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[10px] font-medium shrink-0 cursor-pointer"
                            >
                              📋 复制
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Qwen 1.5B */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">Qwen2.5 1.5B Instruct Q4_K_M (~1.1GB)</div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 font-bold rounded text-[10px]">待下载</span>
                          <button
                            onClick={() => startDownloadSimulation('Qwen2.5 1.5B Instruct')}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer"
                          >
                            ⚡ 立即下载
                          </button>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-500">均衡推荐，翻译质量与速度极佳，支持长难句地道口语化表达</div>
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] text-slate-400 font-medium">可用备用镜像源:</div>
                        {[
                          { name: 'ModelScope 阿里官方极速源 (国内免翻墙·推荐)', url: 'https://modelscope.cn/models/qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/master/qwen2.5-1.5b-instruct-q4_k_m.gguf' },
                          { name: 'HF-Mirror 国内全量加速镜像', url: 'https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf' },
                          { name: 'Hugging Face 官方直连源', url: 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf' },
                        ].map((mir, idx) => (
                          <div key={idx} className="flex items-center justify-between bg-white border border-slate-200 rounded p-1.5 text-[11px]">
                            <span className="text-slate-700 truncate mr-2 font-mono text-[10px]">{mir.name}</span>
                            <button
                              onClick={() => copyToClipboard(mir.url)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[10px] font-medium shrink-0 cursor-pointer"
                            >
                              📋 复制
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* OPUS-MT */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">OPUS-MT 英译中 CTranslate2 (~160MB)</div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 font-bold rounded text-[10px]">待下载</span>
                          <button
                            onClick={() => startDownloadSimulation('OPUS-MT 英译中')}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer"
                          >
                            ⚡ 立即下载
                          </button>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-500">极低内存占用，专精英文至简体中文快速互译</div>
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] text-slate-400 font-medium">组件下载链接 (model.bin / shared_vocabulary.json):</div>
                        {[
                          { name: '模型权重 (model.bin) - Hugging Face', url: 'https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin' },
                          { name: '模型权重 (model.bin) - HF-Mirror 国内镜像', url: 'https://hf-mirror.com/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/model.bin' },
                          { name: '分词词表 (shared_vocabulary.json)', url: 'https://huggingface.co/gaudi/opus-mt-en-zh-ctranslate2/resolve/main/shared_vocabulary.json' },
                        ].map((mir, idx) => (
                          <div key={idx} className="flex items-center justify-between bg-white border border-slate-200 rounded p-1.5 text-[11px]">
                            <span className="text-slate-700 truncate mr-2 font-mono text-[10px]">{mir.name}</span>
                            <button
                              onClick={() => copyToClipboard(mir.url)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[10px] font-medium shrink-0 cursor-pointer"
                            >
                              📋 复制
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* OCR 引擎 */}
                <div className="pt-2">
                  <h4 className="font-bold text-slate-800 mb-2 flex items-center gap-1.5 text-xs text-[#0067C0]">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>🔍 离线文字识别 OCR 引擎 (ONNX / Tar / Win11 原生)</span>
                  </h4>
                  <div className="space-y-3">
                    {/* Win11 Native */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">Windows 11 原生系统 OCR (0MB·免下载)</div>
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 font-bold rounded text-[10px]">系统内置已就绪</span>
                      </div>
                      <div className="text-[11px] text-slate-500">首选推荐！调用本地 Windows.Media.Ocr API，30ms 极速响应，0 显存占用</div>
                    </div>

                    {/* RapidOCR */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">RapidOCR ONNX 极速引擎 (16MB)</div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 font-bold rounded text-[10px]">已就绪</span>
                          <button
                            onClick={() => startDownloadSimulation('RapidOCR ONNX')}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer"
                          >
                            ⚡ 重新校验
                          </button>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-500">基于 ONNXRuntime 的高精度中英文 OCR 引擎，自带高速镜像离线模型权重</div>
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] text-slate-400 font-medium">可用备用镜像源:</div>
                        {[
                          { name: '检测模型 (det) - ModelScope 阿里极速源', url: 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx' },
                          { name: '检测模型 (det) - HF-Mirror 国内全量加速镜像', url: 'https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx' },
                          { name: '识别模型 (rec) - ModelScope 阿里极速源', url: 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx' },
                          { name: '识别模型 (rec) - HF-Mirror 国内全量加速镜像', url: 'https://hf-mirror.com/RapidAI/RapidOCR/resolve/main/onnx/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx' },
                          { name: '方向分类模型 (cls) - ModelScope 阿里极速源', url: 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/onnx/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx' },
                          { name: 'GitHub 官方 Release 备用源', url: 'https://github.com/RapidAI/RapidOCR/raw/main/python/rapidocr_onnxruntime/models/ch_PP-OCRv4_rec_infer.onnx' },
                        ].map((mir, idx) => (
                          <div key={idx} className="flex items-center justify-between bg-white border border-slate-200 rounded p-1.5 text-[11px]">
                            <span className="text-slate-700 truncate mr-2 font-mono text-[10px]">{mir.name}</span>
                            <button
                              onClick={() => copyToClipboard(mir.url)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[10px] font-medium shrink-0 cursor-pointer"
                            >
                              📋 复制
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* PaddleOCR */}
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-800">PaddleOCR PP-OCRv4 离线模型 (17MB)</div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 font-bold rounded text-[10px]">已就绪</span>
                          <button
                            onClick={() => startDownloadSimulation('PaddleOCR PP-OCRv4')}
                            className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[10px] cursor-pointer"
                          >
                            ⚡ 重新校验
                          </button>
                        </div>
                      </div>
                      <div className="text-[11px] text-slate-500">百度飞桨 PP-OCRv4 离线模型（已配置防崩溃 PIR 与 oneDNN 安全开关）</div>
                      <div className="space-y-1 pt-1">
                        <div className="text-[10px] text-slate-400 font-medium">可用官方高速 CDN 与备份源:</div>
                        {[
                          { name: '检测模型 (det.tar) - 百度飞桨 BOS 官方 CDN', url: 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar' },
                          { name: '识别模型 (rec.tar) - 百度飞桨 BOS 官方 CDN', url: 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar' },
                          { name: '方向模型 (cls.tar) - 百度飞桨 BOS 官方 CDN', url: 'https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar' },
                        ].map((mir, idx) => (
                          <div key={idx} className="flex items-center justify-between bg-white border border-slate-200 rounded p-1.5 text-[11px]">
                            <span className="text-slate-700 truncate mr-2 font-mono text-[10px]">{mir.name}</span>
                            <button
                              onClick={() => copyToClipboard(mir.url)}
                              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[10px] font-medium shrink-0 cursor-pointer"
                            >
                              📋 复制
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 弹窗底部 */}
              <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
                <span className="text-slate-500 text-[11px]">离线解压路径: models/ocr/ 与 models/translation/</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setShowMirrorsModal(false);
                      startDownloadSimulation('推荐组合 (RapidOCR + Qwen2.5 0.5B)');
                    }}
                    className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium cursor-pointer"
                  >
                    ⚡ 一键下载推荐组合
                  </button>
                  <button
                    onClick={() => setShowMirrorsModal(false)}
                    className="px-4 py-1.5 text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 rounded font-medium cursor-pointer"
                  >
                    关闭
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
