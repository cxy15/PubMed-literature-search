"""OpenAI 兼容 Chat Completions 客户端。

使用官方 `openai` SDK 的兼容模式：任意提供 OpenAI API 形态的服务均可接入，无需使用 ChatGPT。

URL 约定：
  - `base_url`（环境变量 OPENAI_BASE_URL）应为服务根地址，通常以 `/v1` 结尾，例如：
      https://api.openai.com/v1
      https://api.deepseek.com/v1
      http://127.0.0.1:8000/v1
  - SDK 会在其下拼接路径，如 `POST {base_url}/chat/completions`。
  - 鉴权使用 `OPENAI_API_KEY`（Bearer），由具体服务商颁发；名称沿用 OpenAI 生态惯例。
"""

from __future__ import annotations

from openai import OpenAI

from pubmed_reporter.config import Settings


def get_client(settings: Settings) -> OpenAI:
    kwargs: dict = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def chat_completion(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.4,
    *,
    flow_stage: str | None = None,
) -> str:
    if flow_stage:
        from pubmed_reporter.flow_log import flow_info

        flow_info(f"开始 | {flow_stage}")

    client = get_client(settings)
    try:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
    except Exception:
        if flow_stage:
            from pubmed_reporter.flow_log import flow_info

            flow_info(f"失败 | {flow_stage}")
        raise

    choice = resp.choices[0]
    content = choice.message.content
    if not content:
        out = ""
    else:
        out = content.strip()

    if flow_stage:
        from pubmed_reporter.flow_log import flow_info

        flow_info(f"完成 | {flow_stage}")
    return out
