#!/usr/bin/env bash
# PubMed 文献检索：配置 API → 选择模式 → 执行流水线（全程日志可追溯）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PY="${SCRIPT_DIR}/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "错误：未找到 ${SCRIPT_DIR}/.venv/bin/python，请先创建虚拟环境并安装依赖。" >&2
  exit 1
fi

ENV_FILE="${SCRIPT_DIR}/.env"
EXAMPLE="${SCRIPT_DIR}/.env.example"

# --- 工具函数 ---
ts() { date '+%Y-%m-%d %H:%M:%S'; }

log() { echo "[$(ts)] $*"; }

# 分段标题（便于在终端与日志中扫读）
section() {
  echo ""
  echo "========== [$(ts)] $* =========="
}

# 安全写入 .env 中一行 KEY（若已存在则先删除旧行）
write_env_kv() {
  local key="$1"
  local val="$2"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    grep -v "^[[:space:]]*${key}=" "$ENV_FILE" >"$tmp" || true
    mv "$tmp" "$ENV_FILE"
  else
    : >"$ENV_FILE"
  fi
  printf '%s=%q\n' "$key" "$val" >>"$ENV_FILE"
  chmod 600 "$ENV_FILE" 2>/dev/null || true
}

# 从 .env 加载（忽略注释与空行）
load_dotenv() {
  if [[ ! -f "$ENV_FILE" ]]; then
    return 0
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

prompt_if_empty() {
  local var_name="$1"
  local prompt_text="$2"
  local secret="${3:-0}"
  local current="${!var_name-}"
  if [[ -n "${current// /}" ]]; then
    return 0
  fi
  if [[ "$secret" == "1" ]]; then
    read -r -s -p "${prompt_text}" input
    echo
  else
    read -r -p "${prompt_text}" input
  fi
  if [[ -z "${input// /}" ]]; then
    echo "错误：${var_name} 不能为空。" >&2
    exit 1
  fi
  printf -v "$var_name" '%s' "$input"
  write_env_kv "$var_name" "${!var_name}"
  export "$var_name"
}

# --- 初始化 .env ---
if [[ ! -f "$ENV_FILE" ]] && [[ -f "$EXAMPLE" ]]; then
  log "未找到 .env，从 .env.example 复制..."
  cp "$EXAMPLE" "$ENV_FILE"
  chmod 600 "$ENV_FILE" 2>/dev/null || true
fi

load_dotenv

# 若仍为示例占位符，视为未配置
if [[ "${ENTREZ_EMAIL:-}" == *"your_email"* ]] || [[ "${ENTREZ_EMAIL:-}" == "your_email@example.com" ]]; then
  ENTREZ_EMAIL=""
fi
if [[ "${OPENAI_API_KEY:-}" == "sk-..." ]]; then
  OPENAI_API_KEY=""
fi

section "环境与 API 配置"
log "检查 NCBI 联系信息与 LLM 配置..."

# 必填：NCBI 政策要求的联系邮箱（不是 eutils 的 api_key）
prompt_if_empty ENTREZ_EMAIL "请输入 NCBI E-utilities 联系邮箱 ENTREZ_EMAIL（政策要求，非 API Key）: " 0

# 选填：NCBI 账号申请的 Key，对应 URL 参数 api_key=…，与邮箱不同
if [[ -z "${NCBI_API_KEY:-}" ]]; then
  echo ""
  echo "说明：NCBI_API_KEY 可选，在 NCBI 账户设置中创建；请求会附带 api_key=…，用于提高速率等。"
  echo "      ENTREZ_EMAIL 仅为联系信息；二者均可在 https://www.ncbi.nlm.nih.gov/account/ 管理。"
  read -r -p "输入 NCBI API Key（可选，回车跳过）: " _nk
  if [[ -n "${_nk// /}" ]]; then
    NCBI_API_KEY="$_nk"
    write_env_kv NCBI_API_KEY "$NCBI_API_KEY"
    export NCBI_API_KEY
  fi
fi

# LLM：任意 OpenAI 兼容服务（不必使用 ChatGPT）
prompt_if_empty OPENAI_API_KEY "请输入兼容服务的密钥 OPENAI_API_KEY（Bearer，输入不回显）: " 1

# 选填：若仍为空则询问是否填写
if [[ -z "${OPENAI_BASE_URL:-}" ]]; then
  echo ""
  echo "说明：OPENAI_BASE_URL 为兼容服务的根地址，通常以 /v1 结尾；SDK 会请求 {base}/chat/completions 等。"
  read -r -p "OPENAI_BASE_URL [回车默认 https://api.openai.com/v1]: " _base
  if [[ -n "${_base// /}" ]]; then
    OPENAI_BASE_URL="$_base"
    write_env_kv OPENAI_BASE_URL "$OPENAI_BASE_URL"
    export OPENAI_BASE_URL
  else
    export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
    log "使用默认 OPENAI_BASE_URL=${OPENAI_BASE_URL}"
  fi
fi

if [[ -z "${OPENAI_MODEL:-}" ]]; then
  read -r -p "模型名称 [回车默认 gpt-4o-mini]: " _model
  if [[ -n "${_model// /}" ]]; then
    OPENAI_MODEL="$_model"
    write_env_kv OPENAI_MODEL "$OPENAI_MODEL"
    export OPENAI_MODEL
  else
    export OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o-mini}"
    log "使用默认 OPENAI_MODEL=${OPENAI_MODEL}"
  fi
fi

log "配置就绪。"

# --- 模式选择 ---
section "选择运行模式"
echo "  1) 综述模式 (review) — 围绕主题生成简报"
echo "  2) 研究趋势 (trend) — 近年文献按时序分析热点"
echo "  3) 作者分析 (author) — 按作者归纳研究方向"
echo ""
read -r -p "请输入序号 [1-3]: " MODE_CHOICE

case "$MODE_CHOICE" in
  1) CMD_MODE="review" ;;
  2) CMD_MODE="trend" ;;
  3) CMD_MODE="author" ;;
  *)
    echo "错误：无效选择。" >&2
    exit 1
    ;;
esac

# --- 检索表达式与参数 ---
section "检索参数"
RETMAX_DEFAULT="80"
read -r -p "单次检索最大文献条数 retmax [默认 ${RETMAX_DEFAULT}]: " _retmax
RETMAX="${_retmax:-$RETMAX_DEFAULT}"

OUT_DEFAULT="report_$(date '+%Y%m%d_%H%M%S').txt"
read -r -p "输出文本报告路径 [默认 ${OUT_DEFAULT}]: " _out
OUTPUT_REPORT="${_out:-$OUT_DEFAULT}"

ARGS=("-n" "$RETMAX" "-o" "$OUTPUT_REPORT")

case "$CMD_MODE" in
  review)
    echo ""
    echo "综述模式："
    echo "  - 支持使用自然语言检索，或者输入标准PubMed检索表达式。"
    echo "  - 若在此栏填写「手工检索式」，则跳过翻译，直接使用（等价命令行 -q）。"
    read -r -p "检索意图（必填）: " KEYWORD
    if [[ -z "${KEYWORD// /}" ]]; then
      echo "错误：检索意图不能为空。" >&2
      exit 1
    fi
    read -r -p "手工 PubMed 检索式（可选，直接回车则由 LLM 根据上一行生成: " PUB_QUERY
    read -r -p "是否限定权威生物医学期刊? [y/N]: " AUTH
    ARGS+=(review "$KEYWORD")
    if [[ -n "${PUB_QUERY// /}" ]]; then
      ARGS+=("-q" "$PUB_QUERY")
    fi
    if [[ "$AUTH" =~ ^[yY]$ ]]; then
      ARGS+=("-a")
    fi
    PIPELINE_HINT=$'  A) （若未选手工检索式）LLM：自然语言 → PubMed 检索式\n  B) 打印「实际用于检索的 PubMed 表达式（完整）」\n  C) NCBI：esearch + efetch\n  D) LLM：生成中文文献报告（综述）\n  E) 写入 UTF-8 文本报告'
    ;;
  trend)
    echo ""
    echo "研究趋势："
    echo "  - 支持使用自然语言检索，或者输入标准PubMed检索表达式。"
    echo "  - 若在此栏填写「手工检索式」，则跳过翻译，直接使用（等价命令行 -q）。"
    read -r -p "检索意图（必填）: " KEYWORD
    if [[ -z "${KEYWORD// /}" ]]; then
      echo "错误：检索意图不能为空。" >&2
      exit 1
    fi
    read -r -p "手工 PubMed 检索式（可选，直接回车则由 LLM 根据上一行生成: " RAW_Q
    read -r -p "回溯年数 [默认 5]: " _y
    YEARS="${_y:-5}"
    ARGS+=(trend "$KEYWORD" "-y" "$YEARS")
    if [[ -n "${RAW_Q// /}" ]]; then
      ARGS+=("-q" "$RAW_Q")
    fi
    PIPELINE_HINT=$'  A) （若未选手工检索式）LLM：自然语言 → PubMed 检索式\n  B) 打印「实际用于检索的 PubMed 表达式（完整）」\n  C) NCBI：esearch + efetch（含日期范围）\n  D) LLM：生成中文文献报告（研究趋势）\n  E) 写入 UTF-8 文本报告'
    ;;
  author)
    echo ""
    echo "作者分析："
    echo "  - 支持使用自然语言检索，或者输入标准PubMed检索表达式。"
    echo "  - 若在此栏填写「手工检索式」，则跳过翻译，直接使用（等价命令行 -q）。"
    read -r -p "检索意图（必填）: " AUTH_NAME
    if [[ -z "${AUTH_NAME// /}" ]]; then
      echo "错误：输入不能为空。" >&2
      exit 1
    fi
    read -r -p "手工 PubMed 检索式（可选，直接回车则由 LLM 根据上一行生成）: " RAW_Q
    ARGS+=(author "$AUTH_NAME")
    if [[ -n "${RAW_Q// /}" ]]; then
      ARGS+=("-q" "$RAW_Q")
    fi
    PIPELINE_HINT=$'  A) （若未选手工检索式）LLM：自然语言 → PubMed 检索式\n  B) 打印「实际用于检索的 PubMed 表达式（完整）」\n  C) NCBI：esearch + efetch\n  D) LLM：生成中文文献报告（作者画像）\n  E) 写入 UTF-8 文本报告'
    ;;
esac

mkdir -p "${SCRIPT_DIR}/logs"
LOG_FILE="${SCRIPT_DIR}/logs/run_$(date '+%Y%m%d_%H%M%S').log"

section "即将执行的流水线）"
echo "$PIPELINE_HINT"

section "启动 Python"
log "命令: $VENV_PY -u -m pubmed_reporter ${ARGS[*]}"
log "日志文件: $LOG_FILE"
echo "----------"

set +e
"$VENV_PY" -u -m pubmed_reporter "${ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "----------"
section "运行结束"
if [[ "$EXIT_CODE" -eq 0 ]]; then
  log "任务成功结束 (exit 0)。"
else
  log "任务失败，退出码: $EXIT_CODE（详见日志：$LOG_FILE）。"
fi

exit "$EXIT_CODE"
