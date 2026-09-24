@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 本bat所在目录
set "PY_EXE=venv\Scripts\python.exe"

:: 检查虚拟环境python是否存在
if not exist "%PY_EXE%" (
    echo ERROR: 未找到 venv\Scripts\python.exe
    echo 请确认venv文件夹在本bat同一目录下。
    pause
    exit /b 1
)

:: 判断是否有传入的参数
if "%~1"=="" (
    echo ==============================================
    echo 用法：把 .py 文件拖拽到此bat图标上运行
    echo 使用项目venv虚拟环境的python解释器
    echo ==============================================
    pause
    exit /b 0
)

:: 获取传入脚本的完整路径
set "SCRIPT=%~1"

:: 校验传入文件是否是py
if /i not "%~x1"==".py" (
    echo ERROR: 输入不是 .py 文件：%~nx1
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo ERROR: 文件不存在：%SCRIPT%
    pause
    exit /b 1
)

:: 收集参数
set "ARGS="
shift
:loop_collect_arg
if not "%~1"=="" (
    set "ARGS=!ARGS! "%~1""
    shift
    goto loop_collect_arg
)

echo [使用venv运行] %SCRIPT%
:: 执行脚本，把全部后续参数原样传给py脚本
"%PY_EXE%" "%SCRIPT%" !ARGS!

echo 脚本执行完成，按任意键关闭窗口
pause >nul
endlocal
