@echo off
setlocal EnableDelayedExpansion
REM PubMed 文献检索 — Windows 批处理（行为对齐 run.sh）
REM 依赖：项目根目录下 .venv 已创建并已 pip install -r requirements.txt

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "VENV_PY=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "ENV_FILE=%SCRIPT_DIR%.env"
set "EXAMPLE=%SCRIPT_DIR%.env.example"

if not exist "%VENV_PY%" (
  echo 错误：未找到 "%VENV_PY%"
  echo 请先执行: python -m venv .venv
  echo 然后: .venv\Scripts\pip install -r requirements.txt
  exit /b 1
)

if not exist "%ENV_FILE%" if exist "%EXAMPLE%" (
  echo [提示] 未找到 .env，从 .env.example 复制...
  copy /y "%EXAMPLE%" "%ENV_FILE%" >nul
)

call :section "环境与 API 配置"
echo [日志] 检查 NCBI 联系信息与 LLM 配置...

set "ENTREZ_EMAIL="
set "OPENAI_API_KEY="
set "NCBI_API_KEY="
set "OPENAI_BASE_URL="
set "OPENAI_MODEL="
for /f "delims=" %%E in ('"%VENV_PY%" "%SCRIPT_DIR%scripts\read_env.py" ENTREZ_EMAIL') do set "ENTREZ_EMAIL=%%E"
for /f "delims=" %%E in ('"%VENV_PY%" "%SCRIPT_DIR%scripts\read_env.py" OPENAI_API_KEY') do set "OPENAI_API_KEY=%%E"
for /f "delims=" %%E in ('"%VENV_PY%" "%SCRIPT_DIR%scripts\read_env.py" NCBI_API_KEY') do set "NCBI_API_KEY=%%E"
for /f "delims=" %%E in ('"%VENV_PY%" "%SCRIPT_DIR%scripts\read_env.py" OPENAI_BASE_URL') do set "OPENAI_BASE_URL=%%E"
for /f "delims=" %%E in ('"%VENV_PY%" "%SCRIPT_DIR%scripts\read_env.py" OPENAI_MODEL') do set "OPENAI_MODEL=%%E"

if "!ENTREZ_EMAIL!"=="" (
  set /p "ENTREZ_EMAIL=请输入 NCBI E-utilities 联系邮箱 ENTREZ_EMAIL（政策要求，非 API Key）: "
  if "!ENTREZ_EMAIL!"=="" (
    echo 错误：ENTREZ_EMAIL 不能为空。 >&2
    exit /b 1
  )
  "%VENV_PY%" "%SCRIPT_DIR%scripts\env_write.py" ENTREZ_EMAIL "!ENTREZ_EMAIL!"
)

if "!NCBI_API_KEY!"=="" (
  echo.
  echo 说明：NCBI_API_KEY 可选；回车跳过。
  set /p "NCBI_API_KEY=输入 NCBI API Key（可选）: "
  if not "!NCBI_API_KEY!"=="" "%VENV_PY%" "%SCRIPT_DIR%scripts\env_write.py" NCBI_API_KEY "!NCBI_API_KEY!"
)

if "!OPENAI_API_KEY!"=="" (
  set /p "OPENAI_API_KEY=请输入 OPENAI_API_KEY（兼容服务密钥，输入会显示在屏幕上）: "
  if "!OPENAI_API_KEY!"=="" (
    echo 错误：OPENAI_API_KEY 不能为空。 >&2
    exit /b 1
  )
  "%VENV_PY%" "%SCRIPT_DIR%scripts\env_write.py" OPENAI_API_KEY "!OPENAI_API_KEY!"
)

if "!OPENAI_BASE_URL!"=="" (
  echo.
  echo 说明：OPENAI_BASE_URL 一般为 https://.../v1 ；回车使用默认。
  set /p "OPENAI_BASE_URL=OPENAI_BASE_URL [回车默认 https://api.openai.com/v1]: "
  if "!OPENAI_BASE_URL!"=="" set "OPENAI_BASE_URL=https://api.openai.com/v1"
  "%VENV_PY%" "%SCRIPT_DIR%scripts\env_write.py" OPENAI_BASE_URL "!OPENAI_BASE_URL!"
)

if "!OPENAI_MODEL!"=="" (
  set /p "OPENAI_MODEL=模型名称 [回车默认 gpt-4o-mini]: "
  if "!OPENAI_MODEL!"=="" set "OPENAI_MODEL=gpt-4o-mini"
  "%VENV_PY%" "%SCRIPT_DIR%scripts\env_write.py" OPENAI_MODEL "!OPENAI_MODEL!"
)

echo [日志] 配置就绪。

call :section "选择运行模式"
echo   1) 综述模式 (review^)
echo   2) 研究趋势 (trend^)
echo   3) 作者分析 (author^)
echo.
set /p "MODE_CHOICE=请输入序号 [1-3]: "
if "%MODE_CHOICE%"=="1" set "CMD_MODE=review"
if "%MODE_CHOICE%"=="2" set "CMD_MODE=trend"
if "%MODE_CHOICE%"=="3" set "CMD_MODE=author"
if not defined CMD_MODE (
  echo 错误：无效选择。 >&2
  exit /b 1
)

call :section "检索参数"
set "RETMAX_DEFAULT=80"
set /p "RETMAX=单次检索最大文献条数 retmax [默认 !RETMAX_DEFAULT!]: "
if "!RETMAX!"=="" set "RETMAX=!RETMAX_DEFAULT!"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "OUT_DEFAULT=report_!TS!.txt"
set /p "OUTPUT_REPORT=输出文本报告路径 [默认 !OUT_DEFAULT!]: "
if "!OUTPUT_REPORT!"=="" set "OUTPUT_REPORT=!OUT_DEFAULT!"

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"
set "LOG_FILE=%SCRIPT_DIR%logs\run_!TS!.log"

if "!CMD_MODE!"=="review" goto :mode_review
if "!CMD_MODE!"=="trend" goto :mode_trend
if "!CMD_MODE!"=="author" goto :mode_author
exit /b 1

:mode_review
echo.
echo 综述模式：自然语言描述检索意图；可选手工 PubMed 检索式（等价 -q）。
set /p "KEYWORD=检索意图自然语言（必填）: "
if "!KEYWORD!"=="" (
  echo 错误：检索意图不能为空。 >&2
  exit /b 1
)
set /p "PUB_QUERY=手工 PubMed 检索式（可选，回车则由 LLM 生成）: "
set /p "AUTH=是否限定权威生物医学期刊? [y/N]: "
set "PIPELINE_HINT=A) LLM 检索式  B) 最终表达式  C) NCBI  D) LLM 报告  E) 文本"
call :section "即将执行的流水线"
echo !PIPELINE_HINT!
call :section "启动 Python"
echo [日志] 日志文件: !LOG_FILE!
echo ----------
if not "!PUB_QUERY!"=="" (
  if /i "!AUTH!"=="y" (
    "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" review "!KEYWORD!" -q "!PUB_QUERY!" -a
  ) else (
    "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" review "!KEYWORD!" -q "!PUB_QUERY!"
  )
) else (
  if /i "!AUTH!"=="y" (
    "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" review "!KEYWORD!" -a
  ) else (
    "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" review "!KEYWORD!"
  )
)
set EXIT_CODE=!ERRORLEVEL!
goto :after_run

:mode_trend
echo.
echo 研究趋势：自然语言或选手工检索式（-q）。
set /p "KEYWORD=检索意图自然语言（必填）: "
if "!KEYWORD!"=="" (
  echo 错误：检索意图不能为空。 >&2
  exit /b 1
)
set /p "RAW_Q=手工 PubMed 检索式（可选）: "
set /p "YEARS=回溯年数 [默认 5]: "
if "!YEARS!"=="" set "YEARS=5"
set "PIPELINE_HINT=A) LLM 检索式  B) 最终表达式  C) NCBI+日期  D) LLM 报告  E) 文本"
call :section "即将执行的流水线"
echo !PIPELINE_HINT!
call :section "启动 Python"
echo [日志] 日志文件: !LOG_FILE!
echo ----------
if "!RAW_Q!"=="" (
  "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" trend "!KEYWORD!" -y !YEARS!
) else (
  "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" trend "!KEYWORD!" -y !YEARS! -q "!RAW_Q!"
)
set EXIT_CODE=!ERRORLEVEL!
goto :after_run

:mode_author
echo.
echo 作者分析：自然语言或选手工检索式（-q）。
set /p "AUTH_NAME=作者或检索意图自然语言（必填）: "
if "!AUTH_NAME!"=="" (
  echo 错误：输入不能为空。 >&2
  exit /b 1
)
set /p "RAW_Q=手工 PubMed 检索式（可选）: "
set "PIPELINE_HINT=A) LLM 检索式  B) 最终表达式  C) NCBI  D) LLM 报告  E) 文本"
call :section "即将执行的流水线"
echo !PIPELINE_HINT!
call :section "启动 Python"
echo [日志] 日志文件: !LOG_FILE!
echo ----------
if "!RAW_Q!"=="" (
  "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" author "!AUTH_NAME!"
) else (
  "%VENV_PY%" -u "%SCRIPT_DIR%scripts\tee_run.py" "!LOG_FILE!" -n !RETMAX! -o "!OUTPUT_REPORT!" author "!AUTH_NAME!" -q "!RAW_Q!"
)
set EXIT_CODE=!ERRORLEVEL!
goto :after_run

:after_run
echo ----------
call :section "运行结束"
if !EXIT_CODE! EQU 0 (
  echo [日志] 任务成功结束 (exit 0^)。
) else (
  echo [日志] 任务失败，退出码: !EXIT_CODE! （详见日志：!LOG_FILE!^）
)
exit /b !EXIT_CODE!

:section
echo.
echo ========== %date% %time% %~1 ==========
goto :eof
