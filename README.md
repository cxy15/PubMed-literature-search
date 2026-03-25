# PubMed 文献检索与 LLM 中文报告

基于 **Biopython `Bio.Entrez`**（NCBI E-utilities）检索 PubMed，再通过 **OpenAI 兼容 HTTP 接口** 调用任意大模型整理文献，并导出 **中文 PDF**（支持 LLM 输出的 **Markdown** 排版）。

## 功能概览

| 模式 | 说明 |
|------|------|
| **综述 (review)** | 围绕关键词或自定义 PubMed 检索式生成简报；可选限定权威生物医学期刊 |
| **趋势 (trend)** | 按近年时间窗检索，分析研究热点变化 |
| **作者 (author)** | 按作者字段检索并归纳研究方向 |

检索字段包括标题、作者、摘要、发表日期、期刊等（不下载全文）。

## 环境要求

- Python 3.10+（推荐 3.11+）
- 网络访问（NCBI、LLM 服务）

## 快速开始

### 1. 获取代码并创建虚拟环境

```bash
cd 文献检索
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. 安装依赖

使用 pip：

```bash
pip install -U pip
pip install -r requirements.txt
```

或使用 uv（若已安装）：

```bash
uv pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例并编辑：

```bash
cp .env.example .env
```

**必填**

| 变量 | 说明 |
|------|------|
| `ENTREZ_EMAIL` | NCBI E-utilities 政策要求的**联系邮箱**（用于标识调用方，不是登录密码） |
| `OPENAI_API_KEY` | 所选 **OpenAI 兼容服务** 的密钥（Bearer），变量名沿用 SDK 惯例 |

**常用选填**

| 变量 | 说明 |
|------|------|
| `NCBI_API_KEY` | NCBI 账户申请的 key，请求会带 `api_key=…`，提高速率限制 |
| `OPENAI_BASE_URL` | 兼容服务根地址，一般为 `https://…/v1`（如自建网关、DeepSeek、官方 OpenAI 等） |
| `OPENAI_MODEL` | 模型名，由服务商定义 |
| `CHINESE_FONT_PATH` | 中文字体 `.ttf` / `.ttc` 路径；不填则尝试常见系统路径 |

说明：`OPENAI_BASE_URL` + `OPENAI_API_KEY` 对接的是 **HTTP API 形态与 OpenAI 一致** 的服务，**不强制使用 ChatGPT**。

### 4. 运行

**命令行**

```bash
python -m pubmed_reporter --help

# 综述（80 篇上限，输出 PDF）
python -m pubmed_reporter -n 80 -o report.pdf review "CRISPR therapy" -a

# 近 5 年趋势
python -m pubmed_reporter -n 100 -o trend.pdf trend "mRNA vaccine" -y 5

# 作者
python -m pubmed_reporter -n 60 -o author.pdf author "Smith JA"
```

**交互脚本**（检查配置、选模式、记日志）

```bash
chmod +x run.sh
./run.sh
```

日志默认写入 `logs/run_*.log`。

## 项目结构（概要）

```
文献检索/
├── main.py                 # 入口转发
├── run.sh                  # 交互启动脚本
├── requirements.txt
├── .env.example
├── pubmed_reporter/
│   ├── cli.py              # 命令行
│   ├── config.py           # 环境变量
│   ├── entrez_client.py    # PubMed 检索
│   ├── llm_client.py       # OpenAI 兼容客户端
│   ├── markdown_render.py  # Markdown → HTML（PDF 用）
│   ├── pdf_report.py       # PDF 生成
│   ├── modes.py            # 三种业务模式
│   └── ...
└── logs/                   # 运行日志（可选）
```

## PDF 与 Markdown

LLM 报告正文建议使用 Markdown（标题、列表、表格、粗体等）。程序用 **Python-Markdown** 转为 HTML，再通过 **fpdf2** 的 `write_html` 写入 PDF；若中文字体不可用，会退化为简易纯文本排版。

## 合规与限制

- 请遵守 [NCBI E-utilities 使用政策](https://www.ncbi.nlm.nih.gov/books/NBK25497/)，合理设置 `retmax` 与请求频率。