import React, { useState } from 'react';
import {
  Monitor,
  Settings,
  Code2,
  BookOpen,
  Download,
  ShieldCheck,
  Cpu,
  Layers,
  Sparkles,
  Activity,
} from 'lucide-react';
import { DesktopSimulator } from './components/DesktopSimulator';
import { ConfigGuiPreview } from './components/ConfigGuiPreview';
import { CodeViewer } from './components/CodeViewer';
import { DeploymentGuide } from './components/DeploymentGuide';
import { DataFlowMonitor } from './components/DataFlowMonitor';
import { PROJECT_FILES } from './projectFiles';
import JSZip from 'jszip';

type ActiveTab = 'simulator' | 'config' | 'dataflow' | 'code' | 'guide';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('simulator');
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  const handleDownloadZip = async () => {
    try {
      setIsDownloading(true);
      const zip = new JSZip();
      const folder = zip.folder('win11_offline_screen_translator');

      for (const item of PROJECT_FILES) {
        folder?.file(item.path, item.content);
      }

      folder?.folder('logs')?.file('.gitkeep', '# 日志目录');
      folder?.folder('ocr_records')?.file('.gitkeep', '# OCR与翻译结果存证记录目录');
      folder?.folder('temp')?.file('.gitkeep', '# 临时文件目录');
      folder?.folder('models/ocr/paddleocr/ch_PP-OCRv4_det_infer')?.file('.gitkeep', '# 检测模型');
      folder?.folder('models/ocr/paddleocr/ch_PP-OCRv4_rec_infer')?.file('.gitkeep', '# 识别模型');
      folder?.folder('models/ocr/paddleocr/ch_ppocr_mobile_v2.0_cls_infer')?.file('.gitkeep', '# 分类模型');
      folder?.folder('models/translation/opus-mt-en-zh-ct2')?.file('.gitkeep', '# CTranslate2 权重');

      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'win11_offline_screen_translator.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('打包 ZIP 失败:', e);
      alert('打包 ZIP 失败');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      {/* 顶部 Windows 11 风格应用导航条 */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-base shadow-sm">
              译
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-semibold text-slate-900 text-sm sm:text-base tracking-tight">
                  Win11 离线屏幕实时翻译助手
                </h1>
                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-medium rounded-full border border-emerald-200">
                  <ShieldCheck className="w-3 h-3" />
                  100% 离线隐私保护
                </span>
              </div>
              <p className="text-[11px] text-slate-500 hidden md:block">
                Python 3.10/3.11 + PyQt5 + PaddleOCR + llama-cpp (Qwen2.5 GGUF) + CTranslate2
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleDownloadZip}
              disabled={isDownloading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isDownloading ? '正在打包...' : '下载完整项目 (.ZIP)'}</span>
            </button>
          </div>
        </div>

        {/* 标签栏导航 */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-1 overflow-x-auto border-t border-slate-100">
          <button
            onClick={() => setActiveTab('simulator')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'simulator'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Monitor className="w-4 h-4" />
            屏幕翻译与状态机仿真
          </button>

          <button
            onClick={() => setActiveTab('config')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'config'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Settings className="w-4 h-4" />
            设置窗口与语言校验 (PyQt5)
          </button>

          <button
            onClick={() => setActiveTab('dataflow')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'dataflow'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Activity className="w-4 h-4" />
            IPC 数据流实时监控与性能分析
          </button>

          <button
            onClick={() => setActiveTab('code')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'code'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <Code2 className="w-4 h-4" />
            完整工程源码查看器 ({PROJECT_FILES.length})
          </button>

          <button
            onClick={() => setActiveTab('guide')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'guide'
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
            }`}
          >
            <BookOpen className="w-4 h-4" />
            模型存放与部署运行指南
          </button>
        </div>
      </header>

      {/* 核心特性摘要指示条 */}
      <section className="bg-white border-b border-slate-200 py-2.5 px-4">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs text-slate-600">
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              双进程架构: 主进程 GUI / 托盘 + Worker 进程 OCR / 翻译
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              IPC 协议: 纯 JSON 可序列化标准消息
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              画面感知缓存: 64x64 dHash + 汉明距离 (≤5)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              覆盖层: 鼠标穿透置顶 + 半透明黑底自适应排版
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-mono">
            settings.json 同步就绪 | 懒加载支持
          </div>
        </div>
      </section>

      {/* 主体视窗 */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'simulator' && <DesktopSimulator />}
        {activeTab === 'config' && <ConfigGuiPreview />}
        {activeTab === 'dataflow' && <DataFlowMonitor />}
        {activeTab === 'code' && <CodeViewer />}
        {activeTab === 'guide' && <DeploymentGuide />}
      </main>

      {/* 页脚 */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Win11 离线屏幕实时翻译助手 · 完整项目源码工程与架构规范</span>
          <span className="font-mono text-[11px]">
            PyQt5 · mss · OpenCV · PaddleOCR · llama-cpp-python · CTranslate2 · pynput
          </span>
        </div>
      </footer>
    </div>
  );
}
