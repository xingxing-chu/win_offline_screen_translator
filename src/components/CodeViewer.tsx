import React, { useState } from 'react';
import { PROJECT_FILES, ProjectFileItem } from '../projectFiles';
import { FileCode, Download, Copy, Check, Search, Folder, Terminal, Settings } from 'lucide-react';
import JSZip from 'jszip';

export const CodeViewer: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string>(PROJECT_FILES[0].path);
  const [copied, setCopied] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isDownloadingZip, setIsDownloadingZip] = useState<boolean>(false);

  const selectedFile =
    PROJECT_FILES.find((f) => f.path === selectedPath) || PROJECT_FILES[0];

  const filteredFiles = PROJECT_FILES.filter(
    (f) =>
      f.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadZip = async () => {
    try {
      setIsDownloadingZip(true);
      const zip = new JSZip();
      const folder = zip.folder('win11_offline_screen_translator');

      for (const item of PROJECT_FILES) {
        folder?.file(item.path, item.content);
      }

      // 额外加入空目录结构说明
      folder?.folder('logs')?.file('.gitkeep', '# 日志目录');
      folder?.folder('temp')?.file('.gitkeep', '# 临时文件目录');
      folder?.folder('models/ocr/paddleocr/ch_PP-OCRv4_det_infer')?.file('.gitkeep', '# 放置检测模型');
      folder?.folder('models/ocr/paddleocr/ch_PP-OCRv4_rec_infer')?.file('.gitkeep', '# 放置识别模型');
      folder?.folder('models/ocr/paddleocr/ch_ppocr_mobile_v2.0_cls_infer')?.file('.gitkeep', '# 放置方向分类模型');
      folder?.folder('models/translation/opus-mt-en-zh-ct2')?.file('.gitkeep', '# 放置 ctranslate2 模型权重');

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
      alert('打包 ZIP 失败，请检查控制台');
    } finally {
      setIsDownloadingZip(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 顶部工具栏 */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <FileCode className="w-5 h-5 text-blue-600" />
            完整项目代码与配置文件浏览器
          </h2>
          <p className="text-xs text-slate-500">
            全部基于 Python 3.10/3.11 + PyQt5 + PaddleOCR + llama-cpp/CTranslate2 规范编写，可一键打包为 Windows 运行包
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? '已复制此文件' : '复制当前文件代码'}
          </button>

          <button
            onClick={handleDownloadZip}
            disabled={isDownloadingZip}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            {isDownloadingZip ? '正在打包中...' : '下载完整项目源码 (.ZIP)'}
          </button>
        </div>
      </div>

      {/* 文件目录与代码编辑器布局 */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* 左侧文件树 (4 列) */}
        <div className="md:col-span-4 bg-white border border-slate-200 rounded-xl p-3 shadow-xs flex flex-col h-[650px]">
          {/* 搜索框 */}
          <div className="relative mb-3">
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="搜索项目文件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600"
            />
          </div>

          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 mb-1.5 flex items-center gap-1">
            <Folder className="w-3.5 h-3.5" />
            工程文件列表 ({PROJECT_FILES.length})
          </div>

          {/* 列表 */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {filteredFiles.map((file) => {
              const isSelected = file.path === selectedPath;
              return (
                <button
                  key={file.path}
                  onClick={() => setSelectedPath(file.path)}
                  className={`w-full text-left p-2 rounded-lg text-xs transition-colors flex flex-col gap-0.5 ${
                    isSelected
                      ? 'bg-blue-50 text-blue-900 border border-blue-200'
                      : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-mono font-medium">
                    {file.category === 'python' ? (
                      <Terminal className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    ) : file.category === 'json' ? (
                      <Settings className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    ) : (
                      <FileCode className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                    )}
                    <span className="truncate">{file.name}</span>
                  </div>
                  <span className="text-[11px] text-slate-500 truncate">{file.description}</span>
                </button>
              );
            })}
          </div>

          <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 text-center">
            点击文件在右侧查看完整实现
          </div>
        </div>

        {/* 右侧代码展示区域 (8 列) */}
        <div className="md:col-span-8 bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-md flex flex-col h-[650px]">
          {/* 文件信息栏 */}
          <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <span className="font-mono text-amber-400 font-medium">{selectedFile.path}</span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-400 text-[11px]">{selectedFile.description}</span>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">
              {selectedFile.content.split('\n').length} 行
            </span>
          </div>

          {/* 代码内容视窗 */}
          <div className="flex-1 overflow-auto p-4 font-mono text-xs text-slate-200 leading-relaxed select-text">
            <pre className="whitespace-pre">
              <code>{selectedFile.content}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
