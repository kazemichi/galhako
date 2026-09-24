@echo off
chcp 932 >nul
setlocal enabledelayedexpansion

set "NOA_TOOL=.\tools\noa32c.exe"
set "EXTRACT_OUT=ERI_IN"

:: 检查工具是否存在
if not exist "%NOA_TOOL%" (
    echo ERROR: tools\noa32c.exe not found
    pause
    exit /b 1
)

:: 判断是否有拖拽传入参数
if "%~1"=="" (
	echo ==============================================
    echo Usage:
    echo   1. Drag .noa file onto this bat: extract to ERI_IN
    echo   2. Drag folder onto this bat: package to out.noa
    echo ==============================================
    pause
    exit /b 0
)

set "INPUT=%~1"

:: 判断输入是否存在
if not exist "%INPUT%" (
    echo ERROR: Input not exist: %INPUT%
    pause
    exit /b 1
)

:: 判断是目录还是文件
if exist "%INPUT%\" (
    :: ========== 输入是文件夹：执行打包NOA ==========
    set "OUT_NOA=output.noa"
    echo Output：!OUT_NOA!

    "%NOA_TOOL%" /p "%INPUT%\*" "!OUT_NOA!"
    if errorlevel 1 (
        echo ERROR: Package failed
    ) else (
        echo Package complete: !OUT_NOA!
    )

) else (
    :: ========== 输入是文件：判断后缀是否为.noa，执行解包 ==========
    set "EXT=%~x1"
    if /i not "!EXT!"==".noa" (
        echo ERROR: Not a .noa file: %~nx1
        pause
        exit /b 1
    )

    echo Source NOA：%INPUT%
    echo Output：%EXTRACT_OUT%

    :: 清理旧ERI_IN，重建输出目录
    if exist "%EXTRACT_OUT%" (
        rd /s /q "%EXTRACT_OUT%"
    )
    mkdir "%EXTRACT_OUT%"

    "%NOA_TOOL%" /x "%INPUT%" "%EXTRACT_OUT%"
    if errorlevel 1 (
        echo ERROR: Extract failed
    ) else (
        echo Extract complete: %EXTRACT_OUT%
    )
)

echo.
echo Finished, press any key to close.
pause >nul
