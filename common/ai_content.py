import http.client
import json
import logging
import socket
import re
import time
from urllib import error, request
from urllib.parse import urlparse

from decouple import config


logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_CONNECT_TIMEOUT = 15
OPENROUTER_READ_TIMEOUT = 30
OPENROUTER_MAX_RETRIES = 2
OPENROUTER_RESPONSE_LOG_LIMIT = 1000
AI_RUNTIME_STATUS = {
    "calls": 0,
    "success": 0,
    "fallback": 0,
    "provider": "fallback",
    "enabled": False,
}


def get_ai_configuration():
    api_key = config("OPENROUTER_API_KEY", default="").strip()
    model = config("OPENROUTER_MODEL", default="openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"
    return {
        "api_key": api_key,
        "model": model,
        "enabled": bool(api_key),
    }


def is_ai_enabled():
    return get_ai_configuration()["enabled"]


def get_ai_runtime_status():
    config_data = get_ai_configuration()
    return {
        **AI_RUNTIME_STATUS,
        "provider": "openrouter" if config_data["enabled"] else "fallback",
        "enabled": config_data["enabled"],
        "model": config_data["model"],
    }


def _validate_payload(data, fallback):
    if not isinstance(data, dict):
        raise ValueError("Resposta da IA precisa ser um objeto JSON.")
    missing_keys = [key for key in fallback.keys() if key not in data]
    if missing_keys:
        raise ValueError(f"Resposta da IA sem chaves obrigatorias: {', '.join(missing_keys)}")
    return data


def _build_request_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Referer": "https://educas.local",
        "X-Title": "Educas",
        "User-Agent": "Educas/1.0",
    }


def _render_response_preview(raw_text):
    preview = raw_text.strip()
    if len(preview) > OPENROUTER_RESPONSE_LOG_LIMIT:
        preview = preview[:OPENROUTER_RESPONSE_LOG_LIMIT] + "..."
    return preview


def _perform_openrouter_request(payload, headers):
    parsed = urlparse(OPENROUTER_URL)
    scheme = parsed.scheme
    if scheme != "https":
        raise ValueError("Apenas HTTPS é suportado para OpenRouter.")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=OPENROUTER_CONNECT_TIMEOUT)
    try:
        connection.request("POST", path, body=json.dumps(payload).encode("utf-8"), headers=headers)
        response = connection.getresponse()
        if connection.sock is not None:
            connection.sock.settimeout(OPENROUTER_READ_TIMEOUT)
        raw_body = response.read()
        return response.status, raw_body
    finally:
        connection.close()


def generate_json(prompt, fallback):
    config_data = get_ai_configuration()
    logger.debug("Iniciando geração de JSON | Prompt: %s", prompt[:50])
    AI_RUNTIME_STATUS["calls"] += 1
    AI_RUNTIME_STATUS["enabled"] = config_data["enabled"]
    AI_RUNTIME_STATUS["provider"] = "openrouter" if config_data["enabled"] else "fallback"

    if not config_data["enabled"]:
        AI_RUNTIME_STATUS["fallback"] += 1
        logger.warning("IA desativada: OPENROUTER_API_KEY ausente. Usando fallback local.")
        logger.info("Status da IA | ativa=False | provider=fallback | chamadas=%s", AI_RUNTIME_STATUS["calls"])
        return fallback, {"provider": "fallback", "used_api": False, "error": "missing_api_key"}

    payload = {
        "model": config_data["model"],
        "messages": [
            {
                "role": "system",
                "content": "Voce gera dados institucionais brasileiros realistas em JSON puro.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.8,
    }
    headers = _build_request_headers(config_data["api_key"])
    logger.info(
        "OpenRouter request | url=%s | model=%s | timeout_connect=%ss | timeout_read=%ss | attempt_count=%s",
        OPENROUTER_URL,
        config_data["model"],
        OPENROUTER_CONNECT_TIMEOUT,
        OPENROUTER_READ_TIMEOUT,
        OPENROUTER_MAX_RETRIES + 1,
    )
    logger.debug("OpenRouter payload | length=%s | sample=%s", len(json.dumps(payload)), json.dumps(payload)[0:200])

    last_exception = None
    for attempt in range(1, OPENROUTER_MAX_RETRIES + 2):
        start_time = time.perf_counter()
        try:
            status, raw_body = _perform_openrouter_request(payload, headers)
            elapsed = time.perf_counter() - start_time
            raw_text = raw_body.decode("utf-8", errors="replace")
            preview = _render_response_preview(raw_text)
            logger.info(
                "OpenRouter response | status=%s | elapsed=%.2fs | size=%s bytes | preview=%s",
                status,
                elapsed,
                len(raw_body),
                preview,
            )

            if status != 200:
                error_message = f"HTTP {status}"
                logger.error("ERRO OPENROUTER: %s | Detalhes: %s", status, preview)
                if status in {401, 403, 429, 500, 502}:
                    logger.warning("OpenRouter respondeu com status de erro %s: %s", status, preview)
                else:
                    logger.warning("OpenRouter retornou status inesperado %s: %s", status, preview)

                if status in {429, 500, 502} and attempt <= OPENROUTER_MAX_RETRIES:
                    logger.warning("Tentativa %s de %s para status %s", attempt, OPENROUTER_MAX_RETRIES + 1, status)
                    time.sleep(attempt)
                    continue

                return fallback, {"provider": "fallback", "used_api": False, "error": error_message}

            if not raw_text.strip():
                raise ValueError("Resposta da IA vazia.")

            try:
                response_payload = json.loads(raw_text)
            except json.JSONDecodeError:
                # Tenta extrair JSON (objeto ou array) se houver texto extra ao redor
                match = re.search(r'(\{.*\}|\[.*\])', raw_text, re.DOTALL)
                if not match: raise ValueError("Nenhum JSON encontrado na resposta.")
                response_payload = json.loads(match.group())

            choices = response_payload.get("choices", [])
            if not choices or not isinstance(choices, list):
                raise ValueError("Resposta da IA sem lista de choices valida.")

            content = choices[0].get("message", {}).get("content", "")
            if not content or not isinstance(content, str):
                raise ValueError("Resposta da IA vazia ou invalida.")

            # Limpeza agressiva de markdown blocks
            cleaned = content.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```[a-z]*\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)
            
            if not cleaned:
                raise ValueError("Resposta da IA retornou conteudo JSON vazio.")

            parsed = _validate_payload(json.loads(cleaned), fallback)
            AI_RUNTIME_STATUS["success"] += 1
            logger.info(
                "IA externa utilizada com sucesso | provider=openrouter | modelo=%s | chamadas=%s | sucesso=%s",
                config_data["model"],
                AI_RUNTIME_STATUS["calls"],
                AI_RUNTIME_STATUS["success"],
            )
            return parsed, {"provider": "openrouter", "used_api": True, "error": None}
        except (error.URLError, http.client.HTTPException, socket.timeout, OSError, json.JSONDecodeError, ValueError) as exc:
            elapsed = time.perf_counter() - start_time
            last_exception = exc
            logger.warning(
                "Falha na tentativa %s de OpenRouter | erro=%s | elapsed=%.2fs",
                attempt,
                exc,
                elapsed,
            )
            if attempt <= OPENROUTER_MAX_RETRIES:
                logger.warning("Retrying OpenRouter request (attempt %s/%s)", attempt + 1, OPENROUTER_MAX_RETRIES + 1)
                time.sleep(attempt)
                continue
            AI_RUNTIME_STATUS["fallback"] += 1
            AI_RUNTIME_STATUS["provider"] = "fallback"
            logger.warning("Falha ao usar IA externa; fallback local ativado. Motivo: %s", exc)
            logger.info(
                "Status da IA | ativa=True | provider=openrouter/fallback | chamadas=%s | fallback=%s",
                AI_RUNTIME_STATUS["calls"],
                AI_RUNTIME_STATUS["fallback"],
            )
            return fallback, {"provider": "fallback", "used_api": False, "error": str(last_exception)}
