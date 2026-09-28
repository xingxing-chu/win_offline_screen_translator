@echo off
chcp 65001 >nul
title Win11 离线屏幕翻译助手 - 离线模型高速下载与备用镜像中心
cd /d "%~dp0"

echo ======================================================================
echo       Win11 离线屏幕翻译助手 - 离线模型高速下载与备用镜像管理器
echo ======================================================================
echo.
echo 支持多高速源自动容灾切换: ModelScope 阿里极速源 / HF-Mirror / HuggingFace / 百度 BOS
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

:MENU
echo [1] 自动下载推荐组合 (RapidOCR ONNX + Qwen2.5 0.5B 翻译模型，~486MB)
echo [2] 下载 Qwen2.5 0.5B 离线翻译大模型 (~469MB，低配/老旧CPU秒级响应)
echo [3] 下载 Qwen2.5 1.5B 离线翻译大模型 (~1.1GB，翻译质量与速度均衡)
echo [4] 下载 Qwen2.5 3B 离线翻译大模型 (~2.0GB，高精度专业级翻译)
echo [5] 下载 RapidOCR PP-OCRv4 离线模型 (~17MB，ONNX 纯 CPU 极速 OCR)
echo [6] 下载 PaddleOCR PP-OCRv4 离线模型 (~17MB，百度飞桨离线权重)
echo [7] 下载 OPUS-MT 英译中 CTranslate2 模型 (~160MB，极低内存占用)
echo [8] 查看所有离线模型状态与全部备用下载镜像清单 (可复制链接至迅雷/IDM)
echo [9] 检测测试所有模型下载源与备用镜像的连通性与时延
echo [0] 退出
echo.
set /p choice=请输入选项编号 [0-9]: 

if "%choice%"=="1" (
    python model_downloader.py --download-all
    goto END
)
if "%choice%"=="2" (
    python model_downloader.py --download qwen2.5-0.5b-instruct-q4_k_m
    goto END
)
if "%choice%"=="3" (
    python model_downloader.py --download qwen2.5-1.5b-instruct-q4_k_m
    goto END
)
if "%choice%"=="4" (
    python model_downloader.py --download qwen2.5-3b-instruct-q4_k_m
    goto END
)
if "%choice%"=="5" (
    python model_downloader.py --download rapidocr_ch
    goto END
)
if "%choice%"=="6" (
    python model_downloader.py --download paddleocr_ch
    goto END
)
if "%choice%"=="7" (
    python model_downloader.py --download opus-mt-en-zh-ct2
    goto END
)
if "%choice%"=="8" (
    python model_downloader.py --list
    goto MENU
)
if "%choice%"=="9" (
    python model_downloader.py --check-urls
    goto MENU
)
if "%choice%"=="0" (
    exit /b 0
)

echo.
echo 无效的选项，请重新输入！
echo.
goto MENU

:END
echo.
echo ======================================================================
echo 操作执行完成！模型文件已校验保存至 models/ 对应文件夹内。
echo 打开程序时系统将自动识别并标记为【已就绪】。
echo ======================================================================
echo.
pause
goto MENU
