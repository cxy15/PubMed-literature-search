"""从环境变量加载配置。

NCBI E-utilities（Biopython Entrez）：
  - ENTREZ_EMAIL：政策要求的联系邮箱，用于标识调用方，不是「登录密码」。
  - NCBI_API_KEY（可选）：在 NCBI 申请的 key，请求中会带上 api_key=…，用于提高速率限制等。
    见 https://www.ncbi.nlm.nih.gov/books/NBK25497/

OpenAI 兼容 HTTP 接口（本项目的 LLM 调用）：
  - OPENAI_BASE_URL：兼容服务的「根地址」，须带版本路径时一般为 …/v1（与官方 OpenAI SDK 一致）。
    客户端会在其下请求 /chat/completions 等路径，不要求使用 ChatGPT 或 OpenAI 官方账号。
  - OPENAI_API_KEY：该兼容服务要求的密钥（Bearer），名称沿用环境变量，可对应 DeepSeek、本地 vLLM 等任意兼容实现。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    entrez_email: str
    ncbi_api_key: str | None
    openai_api_key: str
    openai_base_url: str | None
    openai_model: str


def load_settings() -> Settings:
    email = os.getenv("ENTREZ_EMAIL", "").strip()
    ncbi_key = (
        os.getenv("NCBI_API_KEY", "").strip()
        or os.getenv("ENTREZ_API_KEY", "").strip()
        or None
    )
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    base = os.getenv("OPENAI_BASE_URL", "").strip() or None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    return Settings(
        entrez_email=email,
        ncbi_api_key=ncbi_key,
        openai_api_key=api_key,
        openai_base_url=base,
        openai_model=model,
    )
