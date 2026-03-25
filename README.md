# PubMed 文献检索与 AI 总结

基于 **Biopython `Bio.Entrez`**（NCBI E-utilities）检索 PubMed，再通过 **OpenAI 兼容 HTTP 接口** 调用任意大模型整理文献，并导出 **中文 PDF 总结报告**（支持 LLM 输出的 **Markdown** 排版）。

支持用**自然语言**（中/英）描述检索意图，由 LLM 生成 **PubMed 检索式**；也可用 **`-q` / `--raw-query`** 直接提供手工检索式。

程序会在 **`logs/`** 下保存本次拉取的文献快照（`.txt`），便于核对 PMID 与顺序，保证分析准确性。

## 功能概览

| 模式 | 说明 |
|------|------|
| **综述 (review)** | 自然语言 → PubMed 检索式 → 简报；可选 **`-a`** 限定权威生物医学期刊；可用 **`-q`** 跳过检索式生成 |
| **趋势 (trend)** | 近年时间窗内检索，分析热点变化；日期由程序通过 E-utilities 限定，不必写进检索式 |
| **作者 (author)** | 自然语言描述作者或「作者+主题」→ PubMed 检索式 → 归纳研究方向 |

检索字段包括标题、作者、摘要、发表日期、期刊等（不下载全文）。

## 环境要求

- Python 3.10+（推荐 3.11+）

## 快速开始

### 1. 克隆仓库并创建虚拟环境

```bash
cd PubMed-literature-search
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install uv
uv pip install -r requirements.txt
```

### 3. 配置环境变量

任选其一：

- **方法 1**：复制 `.env.example` 为 `.env` 并按表填写后保存。

```bash
cp .env.example .env
# 编辑 .env
```

- **方法 2**：运行 `./run.sh`（见下节），脚本会引导填写并写回 `.env`。

| 变量 | 必填 | 说明 |
|------|------|------|
| `ENTREZ_EMAIL` | 是 | NCBI E-utilities 政策要求的**联系邮箱**（标识调用方，不是登录密码） |
| `NCBI_API_KEY` | 否 | NCBI 账户申请的 key，请求带 `api_key=…`，提高速率限制 |
| `OPENAI_BASE_URL` | 否 | 兼容服务根地址，一般为 `https://…/v1`；不填则依赖 SDK 默认 |
| `OPENAI_API_KEY` | 是 | 所选 **OpenAI 兼容服务** 的密钥 |
| `OPENAI_MODEL` | 否 | 模型名（如 `gpt-4o-mini`），由服务商定义 |
| `CHINESE_FONT_PATH` | 否 | 中文字体 `.ttf` / `.ttc`；不填则尝试常见系统路径 |

后续若需要更改，直接编辑 `.env` 即可。

### 4. 启动方式

#### 方式 A：交互脚本（推荐）

在项目根目录执行（会分段提示配置、模式、参数，并把**标准输出与标准错误**一并写入 `logs/run_*.log`）：

```bash
chmod +x run.sh
./run.sh
```

也可使用：`bash run.sh`。

#### 方式 B：命令行（`python -m pubmed_reporter`）

在**项目根目录**（或已安装包的环境）下：

```bash
python -m pubmed_reporter --help
python -m pubmed_reporter review --help
```

**通用选项**：`-n` / `--retmax` 单次拉取详情条数上限；`-o` / `--output` 输出 PDF 路径。

**自然语言（默认）**：位置参数为检索意图描述，程序会先调用 LLM 生成 PubMed 检索式，再检索与写报告。

**手工检索式**：加 **`-q '检索式'`**，跳过「自然语言 → 检索式」的 LLM；此时综述模式**不会**自动追加权威期刊过滤（需自行写在检索式里）。

示例：

```bash
# 综述：自然语言，可选权威期刊子集
python -m pubmed_reporter -n 80 -o report.pdf review "CRISPR 基因治疗相关临床试验" -a

# 综述：直接给 PubMed 检索式（跳过检索式 LLM）
python -m pubmed_reporter -n 80 -o report.pdf review "主题说明" -q '(CRISPR[Title/Abstract]) AND "Nature"[Journal]'

# 近 5 年趋势
python -m pubmed_reporter -n 100 -o trend.pdf trend "mRNA vaccine" -y 5

# 作者 / 作者+主题（自然语言）
python -m pubmed_reporter -n 60 -o author.pdf author "Zhang Y 肺癌免疫治疗"

# 作者：手工检索式
python -m pubmed_reporter -n 60 -o author.pdf author "展示用标签" -q '"Zhang Y"[Author] AND lung cancer[Title/Abstract]'
```

也可用 **`python main.py …`**，等价于 `python -m pubmed_reporter …`。

## 项目结构

```
PubMed-literature-search/
├── main.py                    # 入口：转发到 pubmed_reporter.cli
├── run.sh                     # 交互启动：环境检查、模式选择、tee 日志
├── requirements.txt
├── .env.example
├── pubmed_reporter/
│   ├── __main__.py            # python -m pubmed_reporter
│   ├── cli.py                 # 命令行解析与调度
│   ├── config.py              # 环境变量与 Settings
│   ├── entrez_client.py       # PubMed esearch/efetch、Medline 解析；权威期刊常量
│   ├── models.py              # PubMedArticle / SearchResult
│   ├── modes.py               # review / trend / author 流水线
│   ├── query_builder.py       # 自然语言 → PubMed 检索式（LLM）
│   ├── llm_client.py          # OpenAI 兼容 Chat Completions
│   ├── flow_log.py            # 流程日志（stderr 前缀）
│   ├── retrieval_log.py       # 检索结果落盘 logs/*.txt
│   ├── pdf_report.py          # fpdf2 生成 PDF
│   ├── markdown_render.py     # Markdown → HTML（PDF 用）
│   ├── font_utils.py          # 中文字体解析
│   └── prompts/               # 提示词（系统/用户/检索式翻译等）
│       ├── __init__.py
│       ├── common.py          # 综述用 SYSTEM_ZH、articles_bundle
│       ├── query_translate.py # 自然语言 → PubMed 检索式提示
│       ├── review.py
│       ├── trend.py
│       └── author.py
└── logs/                      # 运行产生（见下节；已加入 .gitignore）
```

## 自定义 LLM 提示词

LLM 相关提示词位于 `pubmed_reporter/prompts/`，可按需修改（系统提示、各模式用户提示、自然语言→PubMed 检索式等）。

## `logs/` 目录与文件说明

在项目**当前工作目录**下会创建 `logs/`（请在项目根目录运行命令，以便与 `run.sh` 一致）。

| 文件模式 | 来源 | 说明 |
|----------|------|------|
| `run_YYYYMMDD_HHMMSS.log` | **`run.sh`** | 交互脚本执行时，`tee` 将终端上的**标准输出 + 标准错误**追加写入；含 `[pubmed_reporter]` 流程行、CLI 输出等 |
| `retrieved_{review\|trend\|author}_YYYYMMDD_HHMMSS.txt` | **`pubmed_reporter/retrieval_log.py`** | 每次 **NCBI 检索完成之后、调用「报告生成 LLM」之前** 写入；UTF-8，含检索式、命中数、**esearch PMID 顺序**、以及每篇的 **序号、PMID、DOI、标题、期刊、日期、作者、摘要**，便于与 PDF 报告核对 |

**说明**：直接使用 `python -m pubmed_reporter` 时也会生成 `retrieved_*.txt`（若当前目录下存在或可创建 `logs/`）；若需 `run_*.log` 的完整终端回放，请使用 `./run.sh`。

## 自定义「权威生物医学期刊」

综述模式下 **`review -a` / `--authoritative`** 会在「自然语言 → PubMed 检索式」**之后**，把程序生成的检索式与**期刊过滤**用 `AND` 连接。期刊列表来自源码中的常量：

**文件**：`pubmed_reporter/entrez_client.py`  
**常量名**：`AUTHORITATIVE_JOURNALS_QUERY`

为 **PubMed 检索语法** 的一段布尔表达式，每条期刊使用 `"期刊名称"[Journal]`，并用 `OR` 连接，整体用括号包一层，例如：

```text
("Nature"[Journal] OR "Science"[Journal] OR "Cell"[Journal] OR ...)
```

**修改步骤**：

1. 在 [PubMed](https://pubmed.ncbi.nlm.nih.gov/) 中确认期刊的**规范名称**（与数据库中 `Journal` 字段一致），必要时先单独用 `某刊名[Journal]` 试检索。
2. 编辑 `AUTHORITATIVE_JOURNALS_QUERY`：增删 `OR "刊名"[Journal]`，保持括号与引号匹配。
3. 保存后重新运行本程序，无需改命令行参数。

**注意**：

- 使用 **`review -q`** 手工检索式时，程序**不会**自动追加权威期刊过滤；若需限刊，请把期刊条件写进自己的 `-q` 检索式。
- 自然语言综述 + `-a` 时，最终检索式为：`(LLM 生成的主题检索式) AND (AUTHORITATIVE_JOURNALS_QUERY)`。

## PDF 与 Markdown

LLM 报告正文建议使用 Markdown（标题、列表、表格、粗体等）。程序用 **Python-Markdown** 转为 HTML，再通过 **fpdf2** 的 `write_html` 写入 PDF；若中文字体不可用，会退化为简易纯文本排版。

## 合规与限制

- 请遵守 [NCBI E-utilities 使用政策](https://www.ncbi.nlm.nih.gov/books/NBK25497/)，合理设置 `retmax` 与请求频率。
