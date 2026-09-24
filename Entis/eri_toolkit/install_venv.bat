@echo off
chcp 65001 >nul
setlocal

:: 获取当前bat所在的目录
set "PROJ_ROOT=%~dp0"
set "VENV_FOLDER=%PROJ_ROOT%venv"
set "VENV_PY=%VENV_FOLDER%\Scripts\python.exe"
set "VENV_PIP=%VENV_FOLDER%\Scripts\pip.exe"
set "REQUIREMENTS=%PROJ_ROOT%requirements.txt"

:: 不存在venv则创建
if not exist "%VENV_FOLDER%\" (
    echo 创建虚拟环境 venv ...
    python -m venv "%VENV_FOLDER%"
    if errorlevel 1 (
        echo ERROR：创建venv失败，请确认系统PATH里有可用python
        pause
        exit /b 1
    )
) else (
    echo venv目录已存在，跳过创建
)

:: 校验venv内python是否生成成功
if not exist "%VENV_PY%" (
    echo ERROR：venv创建完成，但找不到venv内python.exe
    pause
    exit /b 1
)

:: 在虚拟环境内部更新pip
echo.
echo 更新虚拟环境内部pip
"%VENV_PY%" -m pip install --upgrade pip

:: 检查requirements.txt是否存在
if not exist "%REQUIREMENTS%" (
    echo ERROR：找不到 requirements.txt
    pause
    exit /b 1
)

:: 安装依赖
echo.
echo 安装/更新项目依赖
"%VENV_PIP%" install --upgrade -r "%REQUIREMENTS%"

pause
endlocal
