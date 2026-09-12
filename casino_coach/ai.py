from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .strategy import Advice


class AIExplainer:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self):
        self.api_key = ""
        self.model = "gpt-5.4-mini"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def configure(self, api_key: str, model: str = "gpt-5.4-mini"):
        self.api_key = api_key
        self.model = model or "gpt-5.4-mini"

    def explain(self, snapshot: dict, chosen_action: str, advice: Advice) -> str:
        if not self.enabled:
            raise RuntimeError("API-ключ не настроен")

        prompt = (
            "Разбери ошибку ученика в блэкджеке. "
            f"Состояние: {snapshot}. Выбранное действие: {chosen_action}. "
            f"Базовая стратегия рекомендует: {advice.action}. Основание: {advice.explanation} "
            "Ответь по-русски простыми словами, максимум 3 короткими предложениями. "
            "Не обещай выигрыш и не давай финансовых советов."
        )
        request = Request(
            self.endpoint,
            data=json.dumps(
                {
                    "model": self.model,
                    "instructions": "Ты спокойный тренер по математической базовой стратегии блэкджека.",
                    "input": prompt,
                    "max_output_tokens": 180,
                    "store": False,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API: HTTP {exc.code}: {details[:180]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Нет соединения с OpenAI API: {exc.reason}") from exc
        parts = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        if not parts:
            raise RuntimeError("API не вернул текстовый разбор")
        return "\n".join(parts).strip()

    def explain_poker(self, situation: dict, chosen_action: str, coaching_note: str) -> str:
        if not self.enabled:
            raise RuntimeError("API-ключ не настроен")
        prompt = (
            "Разбери учебное решение игрока в безлимитном техасском холдеме. "
            f"Ситуация: {situation}. Выбранное действие: {chosen_action}. "
            f"Подсказка автора задачи: {coaching_note}. "
            "Ответь по-русски в дружелюбном стиле, максимум 5 коротких предложений. "
            "Объясни логику диапазонов, позиции и размера ставки. "
            "Не обещай заработок и напомни, что это учебная симуляция без реальных денег."
        )
        return self._request(
            instructions="Ты спокойный покерный тренер. Объясняешь решения ясно, без токсичности и обещаний выигрыша.",
            prompt=prompt,
            max_tokens=320,
        )

    def _request(self, instructions: str, prompt: str, max_tokens: int) -> str:
        request = Request(
            self.endpoint,
            data=json.dumps(
                {
                    "model": self.model,
                    "instructions": instructions,
                    "input": prompt,
                    "max_output_tokens": max_tokens,
                    "store": False,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API: HTTP {exc.code}: {details[:180]}") from exc
        except URLError as exc:
            raise RuntimeError(f"Нет соединения с OpenAI API: {exc.reason}") from exc
        parts = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        if not parts:
            raise RuntimeError("API не вернул текстовый разбор")
        return "\n".join(parts).strip()
