from __future__ import annotations
import httpx
from openai import OpenAI

class OpenAIClientFactory:
    @staticmethod
    def build(api_key: str) -> OpenAI:
        key = (api_key or "").strip()
        if not key:
            raise ValueError("API key não informada.")

        # httpx sem herdar variáveis do ambiente (trust_env=False) => ignora HTTP(S)_PROXY
        http_client = httpx.Client(trust_env=False, timeout=30.0, verify=True)
        return OpenAI(api_key=key, http_client=http_client)