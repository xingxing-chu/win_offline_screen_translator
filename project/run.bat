@echo off
chcp 65001 >nul
title Win11 离线屏幕实时翻译助手
cd /d "%~dp0"

:: 彻底禁用 PaddlePaddle oneDNN/MKLDNN 规避 Windows CPU PIR 指令冲突
set FLAGS_use_onednn=0
set FLAGS_use_mkldnn=0
set FLAGS_enable_pir_api=0
set FLAGS_enable_pir_in_executor=0
set PADDLE_DISABLE_ONEDNN=1
set PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0

echo ========================================================
echo        Win11 离线屏幕实时翻译助手 (后台托盘启动器)
echo ========================================================

if not exist ".venv" (
    echo [提示] 正在检查/创建 Python 虚拟环境...
    python -m venv .venv || (
        echo [错误] 创建虚拟环境失败，请确认系统已正确安装 Python 3.10 或 3.11 并勾选添加到 PATH。
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    echo [提示] 正在安装核心依赖包 (使用清华镜像源)...
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || (
        echo [错误] 依赖安装失败，请检查网络连接后重试。
        pause
        exit /b 1
    )
) else (
    call .venv\Scripts\activate.bat
    python -c "import PyQt5, mss, cv2, pynput" 2>nul || pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    python -c "import winocr" 2>nul || pip install winocr -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
    python -c "import rapidocr_onnxruntime" 2>nul || pip install rapidocr-onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
)

echo.
echo [状态] 正在启动后台托盘进程 (pythonw.exe)...
echo [说明] 程序已常驻 Windows 任务栏右下角系统托盘（图标: 译）。
echo [说明] 此控制台窗口将在 2 秒后自动关闭，程序将继续在后台正常运行！
echo ========================================================

:: 优先使用虚拟环境中的 pythonw.exe 独立后台启动
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" main.py
) else (
    start "" pythonw main.py
)

timeout /t 2 >nul
exit
