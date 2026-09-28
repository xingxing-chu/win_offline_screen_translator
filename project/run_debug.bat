@echo off
chcp 65001 >nul
title Win11 离线屏幕实时翻译助手 (控制台调试模式)
cd /d "%~dp0"

:: 彻底禁用 PaddlePaddle oneDNN/MKLDNN 规避 Windows CPU PIR 指令冲突
set FLAGS_use_onednn=0
set FLAGS_use_mkldnn=0
set FLAGS_enable_pir_api=0
set FLAGS_enable_pir_in_executor=0
set PADDLE_DISABLE_ONEDNN=1
set PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0

echo ========================================================
echo        Win11 离线屏幕实时翻译助手 (控制台调试模式)
echo    提示: 此模式会保持 CMD 窗口开启以实时输出终端日志
echo ========================================================

if not exist ".venv" (
    echo [提示] 正在创建 Python 虚拟环境...
    python -m venv .venv
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:: 自动检查并安装核心依赖与高性能 OCR 替代引擎 (若尚未安装)
python -c "import PyQt5, mss, cv2, pynput" 2>nul || pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -c "import winocr" 2>nul || pip install winocr -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
python -c "import rapidocr_onnxruntime" 2>nul || pip install rapidocr-onnxruntime -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

echo.
echo [提示] 正在启动主程序 (控制台实时输出模式)...
echo ========================================================

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" main.py
) else (
    python main.py
)

echo.
echo ========================================================
echo [提示] 应用程序已退出。
pause
