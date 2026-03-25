#!/usr/bin/env bash
# 文献检索项目快速启动：检查 API 配置 → 选择模式 → 输入检索式 → 跟踪执行过程
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

log "检查 API 与联系信息配置..."

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

if [[ -z "${CHINESE_FONT_PATH:-}" ]]; then
  read -r -p "中文字体路径 CHINESE_FONT_PATH（可选，回车跳过）: " _font
  if [[ -n "${_font// /}" ]]; then
    CHINESE_FONT_PATH="$_font"
    write_env_kv CHINESE_FONT_PATH "$CHINESE_FONT_PATH"
    export CHINESE_FONT_PATH
  fi
fi

log "配置就绪。"

# --- 模式选择 ---
echo ""
echo "请选择运行模式："
echo "  1) 综述模式 (review) — 围绕主题/检索式生成简报"
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
RETMAX_DEFAULT="80"
read -r -p "单次检索最大文献条数 retmax [默认 ${RETMAX_DEFAULT}]: " _retmax
RETMAX="${_retmax:-$RETMAX_DEFAULT}"

OUT_DEFAULT="report_$(date '+%Y%m%d_%H%M%S').pdf"
read -r -p "输出 PDF 路径 [默认 ${OUT_DEFAULT}]: " _out
OUTPUT_PDF="${_out:-$OUT_DEFAULT}"

ARGS=("-n" "$RETMAX" "-o" "$OUTPUT_PDF")

case "$CMD_MODE" in
  review)
    echo ""
    echo "综述模式："
    echo "  - 「关键词」用于报告标题与 LLM 主题说明；"
    echo "  - 「PubMed 检索式」可选：若填写则作为实际检索式（等价于 -q）；不填则用语义关键词自动组式。"
    read -r -p "关键词（必填）: " KEYWORD
    if [[ -z "${KEYWORD// /}" ]]; then
      echo "错误：关键词不能为空。" >&2
      exit 1
    fi
    read -r -p "PubMed 检索式（可选，回车跳过）: " PUB_QUERY
    read -r -p "是否限定权威生物医学期刊? [y/N]: " AUTH
    ARGS+=(review "$KEYWORD")
    if [[ -n "${PUB_QUERY// /}" ]]; then
      ARGS+=("-q" "$PUB_QUERY")
    fi
    if [[ "$AUTH" =~ ^[yY]$ ]]; then
      ARGS+=("-a")
    fi
    ;;
  trend)
    echo ""
    echo "研究趋势：将按发表日期检索近年文献并分析。"
    read -r -p "关键词/检索主题（必填）: " KEYWORD
    if [[ -z "${KEYWORD// /}" ]]; then
      echo "错误：关键词不能为空。" >&2
      exit 1
    fi
    read -r -p "回溯年数 [默认 5]: " _y
    YEARS="${_y:-5}"
    ARGS+=(trend "$KEYWORD" "-y" "$YEARS")
    ;;
  author)
    echo ""
    echo "作者分析：将使用 PubMed 作者字段检索。"
    read -r -p "作者姓名（如 Zhang Y 或 Smith JA，必填）: " AUTH_NAME
    if [[ -z "${AUTH_NAME// /}" ]]; then
      echo "错误：作者姓名不能为空。" >&2
      exit 1
    fi
    ARGS+=(author "$AUTH_NAME")
    ;;
esac

mkdir -p "${SCRIPT_DIR}/logs"
LOG_FILE="${SCRIPT_DIR}/logs/run_$(date '+%Y%m%d_%H%M%S').log"

log "命令: $VENV_PY -u -m pubmed_reporter ${ARGS[*]}"
log "日志文件: $LOG_FILE"
log "开始执行（标准输出与错误均会显示并写入日志）..."
echo "----------"

set +e
"$VENV_PY" -u -m pubmed_reporter "${ARGS[@]}" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "----------"
if [[ "$EXIT_CODE" -eq 0 ]]; then
  log "任务成功结束 (exit 0)。"
else
  log "任务失败，退出码: $EXIT_CODE（详见日志）。"
fi

exit "$EXIT_CODE"
