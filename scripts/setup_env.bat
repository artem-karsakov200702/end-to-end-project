@echo off
setlocal enabledelayedexpansion

set "ENV_NAME=week1_env"
set "PY_VER=3.11"
set "REQ_FILE=%~dp0..\requirements.txt"
set "SMOKE_FILE=%~dp0..\broken_env.py"
set "CONDA_BAT="

echo ========================================
echo     Setup Environment for Week1 Project
echo ========================================
echo.

for %%P in (
    "%USERPROFILE%\miniconda3\condabin\conda.bat"
    "%USERPROFILE%\anaconda3\condabin\conda.bat"
    "C:\ProgramData\Anaconda3\condabin\conda.bat"
    "C:\miniconda3\condabin\conda.bat"
    "C:\anaconda3\condabin\conda.bat"
) do (
    if exist %%~P (
        set "CONDA_BAT=%%~P"
        goto :conda_found
    )
)

where conda.bat >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%I in ('where conda.bat') do (
        set "CONDA_BAT=%%I"
        goto :conda_found
    )
)

:conda_found
if not defined CONDA_BAT (
    echo [ERROR] conda.bat not found.
    echo Check Anaconda/Miniconda installation.
    pause
    exit /b 1
)

echo [OK] conda found: %CONDA_BAT%

if not exist "%REQ_FILE%" (
    echo [ERROR] requirements.txt not found:
    echo %REQ_FILE%
    pause
    exit /b 1
)
echo [OK] requirements.txt found.

if not exist "%SMOKE_FILE%" (
    echo [ERROR] broken_env.py not found:
    echo %SMOKE_FILE%
    pause
    exit /b 1
)
echo [OK] broken_env.py found.

call "%CONDA_BAT%" env list | findstr /i "%ENV_NAME%" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Creating environment %ENV_NAME%...
    call "%CONDA_BAT%" create -y -n %ENV_NAME% python=%PY_VER%
    if errorlevel 1 (
        echo [ERROR] failed to create env.
        pause
        exit /b 1
    )
    echo [OK] environment created.
) else (
    echo [OK] environment %ENV_NAME% already exists.
)

echo [INFO] Installing dependencies...
call "%CONDA_BAT%" run -n %ENV_NAME% python -m pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] failed to upgrade pip.
    pause
    exit /b 1
)

call "%CONDA_BAT%" run -n %ENV_NAME% python -m pip install -r "%REQ_FILE%"
if errorlevel 1 (
    echo [ERROR] failed to install requirements.
    pause
    exit /b 1
)

echo [INFO] Running smoke test...
call "%CONDA_BAT%" run -n %ENV_NAME% python "%SMOKE_FILE%"
if errorlevel 1 (
    echo [ERROR] smoke test failed.
    pause
    exit /b 1
)

echo.
echo [OK] Environment is ready.
pause
exit /b 0