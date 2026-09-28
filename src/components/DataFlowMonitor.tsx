import React, { useState, useEffect } from 'react';
import {
  Activity,
  Layers,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Send,
  RefreshCw,
  Search,
  Filter,
  Copy,
  Check,
  AlertTriangle,
  Cpu,
  Database,
  Terminal,
  ChevronRight,
  Zap,
} from 'lucide-react';

export interface IpcPacket {
  id: string;
  timestamp: string;
  direction: 'main_to_worker' | 'worker_to_main';
  type: 'TRANSLATE_REQUEST' | 'TRANSLATE_RESULT' | 'RELOAD_CONFIG' | 'STATUS' | 'ERROR' | 'CANCEL';
  requestId: string;
  durationMs?: number;
  breakdown?: {
    captureMs: number;
    preprocessMs: number;
    ocrMs: number;
    transMs: number;
    ipcMs: number;
  };
  payload: any;
}

const INITIAL_PACKETS: IpcPacket[] = [
  {
    id: 'pkt-001',
    timestamp: '17:44:21.102',
    direction: 'main_to_worker',
    type: 'RELOAD_CONFIG',
    requestId: 'cfg-init-01',
    payload: {
      type: 'RELOAD_CONFIG',
      request_id: 'cfg-init-01',
      payload: {
        settings: {
          ui_language: 'auto',
          source_lang: 'en',
          target_lang: 'zh-CN',
          ocr_model_id: 'win11_media_ocr',
          translation_model_id: 'qwen2.5-1.5b-instruct-q4_k_m',
          auto_route: true,
          adaptive_retry: true,
          mouse_idle_seconds: 3.0,
        },
      },
    },
  },
  {
    id: 'pkt-002',
    timestamp: '17:44:21.128',
    direction: 'worker_to_main',
    type: 'STATUS',
    requestId: 'cfg-init-01',
    payload: {
      type: 'STATUS',
      request_id: 'cfg-init-01',
      payload: {
        worker_status: 'ready',
        ocr_loaded: true,
        ocr_model_id: 'win11_media_ocr',
        translation_loaded: true,
        translation_model_id: 'qwen2.5-1.5b-instruct-q4_k_m',
        message: 'Worker 进程初始化完成，多模型路由与增强引擎就绪',
      },
    },
  },
  {
    id: 'pkt-003',
    timestamp: '17:44:24.410',
    direction: 'main_to_worker',
    type: 'TRANSLATE_REQUEST',
    requestId: 'req-7a91bf2',
    payload: {
      type: 'TRANSLATE_REQUEST',
      request_id: 'req-7a91bf2',
      payload: {
        source_lang: 'en',
        target_lang: 'zh-CN',
        ocr_model_id: 'win11_media_ocr',
        translation_model_id: 'qwen2.5-1.5b-instruct-q4_k_m',
        monitor_index: 1,
        config_version: 1,
      },
    },
  },
  {
    id: 'pkt-004',
    timestamp: '17:44:24.786',
    direction: 'worker_to_main',
    type: 'TRANSLATE_RESULT',
    requestId: 'req-7a91bf2',
    durationMs: 376,
    breakdown: {
      captureMs: 14,
      preprocessMs: 4,
      ocrMs: 42,
      transMs: 314,
      ipcMs: 2,
    },
    payload: {
      type: 'TRANSLATE_RESULT',
      request_id: 'req-7a91bf2',
      payload: {
        image_hash: '9f8e7d6c5b4a3210',
        cached: false,
        elapsed_ms: 376,
        source_lang: 'en',
        target_lang: 'zh-CN',
        ocr_engine_used: 'win11_media_ocr',
        items: [
          {
            bbox: [48, 62, 380, 94],
            source: 'Visual Studio Code - main.py [Administrator]',
            translated: 'Visual Studio Code - main.py [管理员]',
            confidence: 0.99,
          },
          {
            bbox: [48, 110, 520, 150],
            source: 'Worker process ready to dispatch next translation queue',
            translated: 'Worker 工作子进程准备分发下一组翻译队列',
            confidence: 0.98,
          },
        ],
      },
    },
  },
];

export const DataFlowMonitor: React.FC = () => {
  const [packets, setPackets] = useState<IpcPacket[]>(INITIAL_PACKETS);
  const [selectedPacketId, setSelectedPacketId] = useState<string>(INITIAL_PACKETS[3].id);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterDirection, setFilterDirection] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [isInjecting, setIsInjecting] = useState<boolean>(false);

  // 选中的数据包
  const selectedPacket = packets.find((p) => p.id === selectedPacketId) || packets[0];

  const handleCopyJson = () => {
    if (selectedPacket) {
      navigator.clipboard.writeText(JSON.stringify(selectedPacket.payload, null, 2));
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  // 模拟发送新请求
  const handleSimulateRequest = () => {
    setIsInjecting(true);
    const reqId = 'req-' + Math.random().toString(36).substring(2, 9);
    const now = new Date();
    const timeStr =
      now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');

    const reqPacket: IpcPacket = {
      id: 'pkt-' + Date.now().toString().slice(-4),
      timestamp: timeStr,
      direction: 'main_to_worker',
      type: 'TRANSLATE_REQUEST',
      requestId: reqId,
      payload: {
        type: 'TRANSLATE_REQUEST',
        request_id: reqId,
        payload: {
          source_lang: 'en',
          target_lang: 'zh-CN',
          ocr_model_id: 'win11_media_ocr',
          translation_model_id: 'qwen2.5-1.5b-instruct-q4_k_m',
          monitor_index: 1,
          config_version: 1,
        },
      },
    };

    setPackets((prev) => [reqPacket, ...prev]);
    setSelectedPacketId(reqPacket.id);

    // 模拟子进程异步响应
    setTimeout(() => {
      const respTime = new Date();
      const respTimeStr =
        respTime.toTimeString().split(' ')[0] +
        '.' +
        String(respTime.getMilliseconds()).padStart(3, '0');

      const ocrMs = Math.floor(Math.random() * 20) + 35;
      const transMs = Math.floor(Math.random() * 80) + 210;
      const totalMs = 12 + 3 + ocrMs + transMs + 2;

      const respPacket: IpcPacket = {
        id: 'pkt-' + (Date.now() + 1).toString().slice(-4),
        timestamp: respTimeStr,
        direction: 'worker_to_main',
        type: 'TRANSLATE_RESULT',
        requestId: reqId,
        durationMs: totalMs,
        breakdown: {
          captureMs: 12,
          preprocessMs: 3,
          ocrMs,
          transMs,
          ipcMs: 2,
        },
        payload: {
          type: 'TRANSLATE_RESULT',
          request_id: reqId,
          payload: {
            image_hash: Math.random().toString(16).substring(2, 18),
            cached: false,
            elapsed_ms: totalMs,
            source_lang: 'en',
            target_lang: 'zh-CN',
            ocr_engine_used: 'win11_media_ocr',
            items: [
              {
                bbox: [50, 40, 420, 80],
                source: 'High-performance offline inference completed',
                translated: '高性能离线推理执行完成',
                confidence: 0.99,
              },
            ],
          },
        },
      };

      setPackets((prev) => [respPacket, ...prev]);
      setSelectedPacketId(respPacket.id);
      setIsInjecting(false);
    }, 450);
  };

  // 模拟超时强制重试与自动切换备用引擎 (展示用户关心的防卡死流程)
  const handleSimulateTimeoutAndFallback = () => {
    setIsInjecting(true);
    const reqId = 'req-failover-' + Math.random().toString(36).substring(2, 7);
    const now = new Date();
    const timeStr =
      now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0');

    // 1. 发起请求
    const reqPacket: IpcPacket = {
      id: 'pkt-' + Date.now().toString().slice(-4),
      timestamp: timeStr,
      direction: 'main_to_worker',
      type: 'TRANSLATE_REQUEST',
      requestId: reqId,
      payload: {
        type: 'TRANSLATE_REQUEST',
        request_id: reqId,
        payload: {
          source_lang: 'en',
          target_lang: 'zh-CN',
          ocr_model_id: 'rapidocr_ch',
          translation_model_id: 'qwen2.5-1.5b-instruct-q4_k_m',
          monitor_index: 1,
          config_version: 1,
        },
      },
    };

    setPackets((prev) => [reqPacket, ...prev]);
    setSelectedPacketId(reqPacket.id);

    // 2. 模拟第 1 次超时与重试
    setTimeout(() => {
      const t1 = new Date();
      const t1Str = t1.toTimeString().split(' ')[0] + '.' + String(t1.getMilliseconds()).padStart(3, '0');
      const retry1Packet: IpcPacket = {
        id: 'pkt-' + (Date.now() + 1).toString().slice(-4),
        timestamp: t1Str,
        direction: 'worker_to_main',
        type: 'STATUS',
        requestId: reqId,
        payload: {
          type: 'STATUS',
          request_id: reqId,
          payload: {
            worker_status: 'warning',
            message: '⚠️ 引擎 [rapidocr_ch] 响应超时 (3.5s)，正在发起第 1/2 次强制超时重试...',
            active_engine: 'rapidocr_ch',
            retry_count: 1,
            max_retries: 2,
          },
        },
      };
      setPackets((prev) => [retry1Packet, ...prev]);
      setSelectedPacketId(retry1Packet.id);
    }, 600);

    // 3. 模拟超时熔断与切换备用引擎
    setTimeout(() => {
      const t2 = new Date();
      const t2Str = t2.toTimeString().split(' ')[0] + '.' + String(t2.getMilliseconds()).padStart(3, '0');
      const breakerPacket: IpcPacket = {
        id: 'pkt-' + (Date.now() + 2).toString().slice(-4),
        timestamp: t2Str,
        direction: 'worker_to_main',
        type: 'STATUS',
        requestId: reqId,
        payload: {
          type: 'STATUS',
          request_id: reqId,
          payload: {
            worker_status: 'fallback',
            message: '🚨 引擎 [rapidocr_ch] 连续超时耗尽，自动熔断！平滑切换备用方案 1 [tesseract_ocr]...',
            circuit_breaker: {
              tripped_engine: 'rapidocr_ch',
              switch_to: 'tesseract_ocr',
              state: 'OPEN',
            },
          },
        },
      };
      setPackets((prev) => [breakerPacket, ...prev]);
      setSelectedPacketId(breakerPacket.id);
    }, 1200);

    // 4. 备用引擎推理成功并返回翻译结果
    setTimeout(() => {
      const t3 = new Date();
      const t3Str = t3.toTimeString().split(' ')[0] + '.' + String(t3.getMilliseconds()).padStart(3, '0');
      const successPacket: IpcPacket = {
        id: 'pkt-' + (Date.now() + 3).toString().slice(-4),
        timestamp: t3Str,
        direction: 'worker_to_main',
        type: 'TRANSLATE_RESULT',
        requestId: reqId,
        durationMs: 840,
        breakdown: {
          captureMs: 12,
          preprocessMs: 4,
          ocrMs: 510,
          transMs: 312,
          ipcMs: 2,
        },
        payload: {
          type: 'TRANSLATE_RESULT',
          request_id: reqId,
          payload: {
            image_hash: '3f2e1d0c9b8a7654',
            cached: false,
            elapsed_ms: 840,
            source_lang: 'en',
            target_lang: 'zh-CN',
            ocr_engine_used: 'tesseract_ocr (备用方案1 自动容灾接管)',
            items: [
              {
                bbox: [80, 120, 600, 160],
                source: 'Exception handled: Auto-switched to backup OCR engine without blocking',
                translated: '异常已处理：已自动平滑切换至备用 OCR 引擎，屏幕取词完全未中断',
                confidence: 0.96,
              },
            ],
          },
        },
      };
      setPackets((prev) => [successPacket, ...prev]);
      setSelectedPacketId(successPacket.id);
      setIsInjecting(false);
    }, 1800);
  };

  // 过滤包
  const filteredPackets = packets.filter((p) => {
    if (filterType !== 'ALL' && p.type !== filterType) return false;
    if (filterDirection === 'TO_WORKER' && p.direction !== 'main_to_worker') return false;
    if (filterDirection === 'TO_MAIN' && p.direction !== 'worker_to_main') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchId = p.requestId.toLowerCase().includes(q);
      const matchType = p.type.toLowerCase().includes(q);
      const matchContent = JSON.stringify(p.payload).toLowerCase().includes(q);
      if (!matchId && !matchType && !matchContent) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 顶部概览面板 */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-700 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                双进程 IPC 数据流监控与性能分析面板
              </h2>
              <p className="text-xs text-slate-500">
                实时抓取主进程 (PyQt5) 与 Worker 子进程间通过 multiprocessing.Queue 传递的纯 JSON 数据包
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSimulateRequest}
              disabled={isInjecting}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{isInjecting ? '通信中...' : '模拟常规翻译 (IPC)'}</span>
            </button>

            <button
              onClick={handleSimulateTimeoutAndFallback}
              disabled={isInjecting}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
              title="模拟引擎卡住、强制重试2次以及自动熔断切换至备用引擎的全流程"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{isInjecting ? '容灾切换中...' : '模拟超时重试与备用切换'}</span>
            </button>

            <button
              onClick={() => setPackets(INITIAL_PACKETS)}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-medium"
              title="重置测试数据"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              重置
            </button>
          </div>
        </div>

        {/* 拓扑示意图 */}
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {/* 主进程节点 */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                MainProcess (主进程)
              </span>
              <span className="text-[11px] font-mono text-slate-400">PID: 12044</span>
            </div>
            <p className="text-slate-600 text-[11px]">
              职责: PyQt5 GUI、系统托盘、OverlayWindow 覆盖层、全局鼠标监听与状态机
            </p>
          </div>

          {/* IPC 管道 */}
          <div className="bg-blue-50/60 border border-blue-200 rounded-lg p-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-blue-900 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-blue-600" />
                IPC 通信管道 (Queue)
              </span>
              <span className="text-[11px] font-mono text-blue-600">JSON 协议</span>
            </div>
            <p className="text-blue-800 text-[11px]">
              规范: 严禁传递复杂对象句柄；所有消息均封装为标准可序列化 JSON 结构
            </p>
          </div>

          {/* Worker 节点 */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                TranslatorWorker (子进程)
              </span>
              <span className="text-[11px] font-mono text-slate-400">PID: 25512</span>
            </div>
            <p className="text-slate-600 text-[11px]">
              职责: mss 高速截屏、OpenCV 预处理、多模型 OCR 路由、离线大模型推理、dHash 缓存
            </p>
          </div>
        </div>
      </div>

      {/* 核心监控双栏布局 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 左侧：数据包列表 (7 列) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3">
          {/* 过滤与搜索工具栏 */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 flex-1 min-w-[200px]">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="搜索 Request ID、消息类型或正文..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-md pl-8 pr-2.5 py-1.5 text-slate-800 focus:outline-none focus:border-blue-600 text-xs"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-md py-1.5 px-2 text-slate-800 text-xs"
              >
                <option value="ALL">全部类型</option>
                <option value="TRANSLATE_REQUEST">TRANSLATE_REQUEST</option>
                <option value="TRANSLATE_RESULT">TRANSLATE_RESULT</option>
                <option value="RELOAD_CONFIG">RELOAD_CONFIG</option>
                <option value="STATUS">STATUS</option>
                <option value="ERROR">ERROR</option>
              </select>

              <select
                value={filterDirection}
                onChange={(e) => setFilterDirection(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-md py-1.5 px-2 text-slate-800 text-xs"
              >
                <option value="ALL">全部流向</option>
                <option value="TO_WORKER">Main → Worker</option>
                <option value="TO_MAIN">Worker → Main</option>
              </select>
            </div>
          </div>

          {/* 数据包列表 */}
          <div className="border border-slate-200 rounded-lg overflow-hidden divide-y divide-slate-100 max-h-[460px] overflow-y-auto">
            {filteredPackets.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">没有匹配的数据包</div>
            ) : (
              filteredPackets.map((pkt) => {
                const isSelected = pkt.id === selectedPacketId;
                const isToWorker = pkt.direction === 'main_to_worker';

                return (
                  <div
                    key={pkt.id}
                    onClick={() => setSelectedPacketId(pkt.id)}
                    className={`p-3 cursor-pointer transition-colors text-xs flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-blue-50/80 border-l-4 border-l-blue-600'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      {/* 流向指示 */}
                      <div
                        className={`p-1.5 rounded flex items-center justify-center shrink-0 ${
                          isToWorker
                            ? 'bg-sky-100 text-sky-700'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                        title={isToWorker ? '主进程发往 Worker' : 'Worker 发往主进程'}
                      >
                        {isToWorker ? (
                          <ArrowRight className="w-3.5 h-3.5" />
                        ) : (
                          <ArrowLeft className="w-3.5 h-3.5" />
                        )}
                      </div>

                      <div className="min-w-0 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-800 truncate">{pkt.type}</span>
                          <span className="px-1.5 py-0.2 bg-slate-100 text-slate-600 rounded text-[10px] font-mono">
                            {pkt.requestId}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 truncate">
                          {isToWorker
                            ? `发往子进程队列 | 请求 ID: ${pkt.requestId}`
                            : `子进程响应就绪 | 耗时: ${pkt.durationMs ?? 0}ms`}
                        </p>
                      </div>
                    </div>

                    <div className="text-right shrink-0 space-y-0.5">
                      <span className="text-[11px] font-mono text-slate-400">{pkt.timestamp}</span>
                      {pkt.durationMs !== undefined && (
                        <div className="text-[11px] font-semibold text-emerald-600 flex items-center justify-end gap-1">
                          <Clock className="w-3 h-3" />
                          {pkt.durationMs}ms
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 右侧：单包详细检查器与性能瀑布图 (5 列) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-semibold text-slate-800">IPC 数据包检查器</h3>
            </div>
            <button
              onClick={handleCopyJson}
              className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 bg-slate-50 border border-slate-200 px-2 py-1 rounded"
            >
              {isCopied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="text-emerald-600">已复制</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>复制 JSON</span>
                </>
              )}
            </button>
          </div>

          {selectedPacket ? (
            <div className="space-y-4 flex-1 flex flex-col">
              {/* 性能分解瀑布 (如果是 TRANSLATE_RESULT) */}
              {selectedPacket.breakdown && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 text-xs">
                  <div className="flex items-center justify-between font-semibold text-slate-800 text-xs">
                    <span>端到端耗时瀑布分解 (Total: {selectedPacket.durationMs}ms)</span>
                    <span className="text-emerald-600">100% 离线</span>
                  </div>

                  {/* 进度条堆叠 */}
                  <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden flex">
                    <div
                      style={{
                        width: `${(selectedPacket.breakdown.captureMs / (selectedPacket.durationMs || 1)) * 100}%`,
                      }}
                      className="bg-amber-400"
                      title={`截屏: ${selectedPacket.breakdown.captureMs}ms`}
                    />
                    <div
                      style={{
                        width: `${(selectedPacket.breakdown.preprocessMs / (selectedPacket.durationMs || 1)) * 100}%`,
                      }}
                      className="bg-sky-400"
                      title={`增强预处理: ${selectedPacket.breakdown.preprocessMs}ms`}
                    />
                    <div
                      style={{
                        width: `${(selectedPacket.breakdown.ocrMs / (selectedPacket.durationMs || 1)) * 100}%`,
                      }}
                      className="bg-blue-500"
                      title={`OCR 识别: ${selectedPacket.breakdown.ocrMs}ms`}
                    />
                    <div
                      style={{
                        width: `${(selectedPacket.breakdown.transMs / (selectedPacket.durationMs || 1)) * 100}%`,
                      }}
                      className="bg-indigo-500"
                      title={`翻译推理: ${selectedPacket.breakdown.transMs}ms`}
                    />
                    <div
                      style={{
                        width: `${(selectedPacket.breakdown.ipcMs / (selectedPacket.durationMs || 1)) * 100}%`,
                      }}
                      className="bg-emerald-400"
                      title={`IPC 序列化: ${selectedPacket.breakdown.ipcMs}ms`}
                    />
                  </div>

                  {/* 分解明细 */}
                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded bg-amber-400" />
                        mss 屏幕截取:
                      </span>
                      <span className="font-mono font-medium">{selectedPacket.breakdown.captureMs}ms</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded bg-sky-400" />
                        图像增强预处理:
                      </span>
                      <span className="font-mono font-medium">{selectedPacket.breakdown.preprocessMs}ms</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded bg-blue-500" />
                        OCR 模型识别:
                      </span>
                      <span className="font-mono font-medium text-blue-700 font-semibold">{selectedPacket.breakdown.ocrMs}ms</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded bg-indigo-500" />
                        大模型推理翻译:
                      </span>
                      <span className="font-mono font-medium text-indigo-700 font-semibold">{selectedPacket.breakdown.transMs}ms</span>
                    </div>
                  </div>
                </div>
              )}

              {/* JSON 树状视窗 */}
              <div className="flex-1 bg-slate-950 rounded-lg p-3 overflow-x-auto text-[11px] font-mono text-slate-200 max-h-[300px] leading-relaxed">
                <pre>{JSON.stringify(selectedPacket.payload, null, 2)}</pre>
              </div>

              {/* 性能诊断提示卡片 */}
              <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-lg text-xs space-y-1 text-blue-900">
                <div className="font-semibold flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-blue-600" />
                  IPC 通信优化建议
                </div>
                <p className="text-[11px] leading-relaxed text-blue-800">
                  当前通信采用纯 JSON 序列化。截取的画面通过 <code>dHash</code> 提取 64 位指纹在 Worker 内存缓存比对，无需在 IPC 管道中往返传递原始像素大图，保障跨进程消息往返耗时 &lt; 2ms。
                </p>
              </div>
            </div>
          ) : (
            <div className="text-slate-400 text-xs p-8 text-center">请在左侧选择一个数据包</div>
          )}
        </div>
      </div>
    </div>
  );
};
