"""Google-only model access. Project agents call this at runtime."""

from __future__ import annotations

import json
from typing import Any, Mapping

from google import genai
from google.genai import types


class GeminiJsonGenerator:
    def __init__(self, *, project: str, location: str, model: str) -> None:
        self.model = model
        self.client = genai.Client(vertexai=True, project=project, location=location)

    def generate(
        self,
        *,
        prompt: str,
        response_schema: Mapping[str, Any],
        system_instruction: str,
    ) -> dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_json_schema=dict(response_schema),
                temperature=0,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned no structured text")
        value = json.loads(response.text)
        if not isinstance(value, dict):
            raise TypeError("Gemini response must be a JSON object")
        return value

