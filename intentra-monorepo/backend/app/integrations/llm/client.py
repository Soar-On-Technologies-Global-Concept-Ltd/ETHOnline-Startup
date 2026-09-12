"""AgentService model access. Anthropic (claude-opus-5) by default; a deterministic fake for tests and keyless local demos."""
import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import log
from app.integrations.llm import fake, prompts

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("ai")

FALLBACK_BETA = "server-side-fallback-2026-07-01"   # pairs with fallbacks="default"
MIN_RETRY_SECONDS = 8.0                             # retry once only if this much of the budget remains


class AIUnavailable(Exception):
    """Timeout, provider error, or output that failed validation. Callers fall back; they never guess."""


class AIRefused(AIUnavailable):
    """The model (and its server-side fallback) declined."""


@dataclass(frozen=True)
class AIResult(Generic[T]):
    output: T
    model: str
    prompt_version: str
    input_hash: str


def input_hash(system: str, user: str) -> str:
    return "0x" + hashlib.sha256(f"{system}\n\n{user}".encode()).hexdigest()


class AnthropicLLM:
    def __init__(self) -> None:
        import anthropic

        s = get_settings()
        self.model = s.llm_model
        self.client = anthropic.AsyncAnthropic(api_key=s.llm_api_key.get_secret_value() if s.llm_api_key else None, max_retries=0)

    async def _once(self, system: str, user: str, schema: type[T], max_tokens: int, timeout: float) -> tuple[T, str]:
        resp = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": "low"},
            fallbacks="default",
            betas=[FALLBACK_BETA],
            timeout=timeout,
        )
        if resp.stop_reason == "refusal":
            raise AIRefused("the model declined the request")
        if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
            raise AIUnavailable("the model output was incomplete")
        served = next((getattr(it, "model", None) for it in (getattr(resp.usage, "iterations", None) or [])
                       if getattr(it, "type", None) == "fallback_message"), None)
        return resp.parsed_output, served or resp.model

    async def run(self, task: str, data: dict, schema: type[T], max_tokens: int = 4096) -> AIResult[T]:
        system, user = prompts.render(task, data)
        budget = get_settings().ai_timeout_seconds
        start = time.monotonic()
        last: Exception | None = None
        for attempt in range(2):
            remaining = budget - (time.monotonic() - start)
            if attempt and remaining < MIN_RETRY_SECONDS:
                break
            try:
                output, model = await asyncio.wait_for(self._once(system, user, schema, max_tokens, remaining), timeout=remaining)
                return AIResult(output, model, prompts.PROMPT_VERSION, input_hash(system, user))
            except AIRefused:
                log(logger, "ai refused", task=task)
                raise
            except Exception as err:  # timeout, API error, validation error: fall back after at most one retry
                last = err
                log(logger, "ai attempt failed", task=task, attempt=attempt + 1, error=type(err).__name__)
        raise AIUnavailable(f"{task}: {type(last).__name__ if last else 'timeout'}")


class FakeLLM:
    model = "fake-llm"

    def __init__(self) -> None:
        self.overrides: dict[str, Callable[[dict], dict]] = {}

    async def run(self, task: str, data: dict, schema: type[T], max_tokens: int = 4096) -> AIResult[T]:
        system, user = prompts.render(task, data)
        raw = (self.overrides.get(task) or fake.HANDLERS[task])(data)
        if isinstance(raw, Exception):
            raise AIUnavailable(str(raw))
        try:
            output = schema.model_validate(raw)
        except ValidationError as err:
            raise AIUnavailable(f"{task}: invalid output ({err.error_count()} errors)") from err
        return AIResult(output, self.model, prompts.PROMPT_VERSION, input_hash(system, user))


class OpenAILLM:
    def __init__(self) -> None:
        import openai

        s = get_settings()
        self.model = s.llm_model
        self.client = openai.AsyncOpenAI(
            api_key=s.llm_api_key.get_secret_value() if s.llm_api_key else None,
            base_url=s.llm_base_url,
            max_retries=0,
        )

    async def _once(self, system: str, user: str, schema: type[T], max_tokens: int, timeout: float) -> tuple[T, str]:
        import json
        
        # Append schema instructions for models that don't support native structured outputs
        schema_json = json.dumps(schema.model_json_schema())
        system_with_format = f"{system}\n\nCRITICAL: You must output strictly valid JSON matching this schema. Do not output markdown code blocks or any other text. Schema:\n{schema_json}"

        resp = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_with_format},
                {"role": "user", "content": user}
            ],
            timeout=timeout,
        )
        if not resp.choices:
            raise AIUnavailable("the model returned no choices")
        choice = resp.choices[0]
        if choice.finish_reason == "length":
            raise AIUnavailable("the model output was incomplete")
        
        content = choice.message.content
        if not content:
            raise AIUnavailable("the model returned empty content")
            
        # Clean up common markdown formatting if the model ignored instructions
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            parsed = schema.model_validate_json(content.strip())
            return parsed, resp.model
        except Exception as e:
            raise AIUnavailable(f"the model output was invalid JSON: {e}")

    async def run(self, task: str, data: dict, schema: type[T], max_tokens: int = 4096) -> AIResult[T]:
        system, user = prompts.render(task, data)
        budget = get_settings().ai_timeout_seconds
        start = time.monotonic()
        last: Exception | None = None
        for attempt in range(2):
            remaining = budget - (time.monotonic() - start)
            if attempt and remaining < MIN_RETRY_SECONDS:
                break
            try:
                output, model = await asyncio.wait_for(self._once(system, user, schema, max_tokens, remaining), timeout=remaining)
                return AIResult(output, model, prompts.PROMPT_VERSION, input_hash(system, user))
            except AIRefused:
                log(logger, "ai refused", task=task)
                raise
            except Exception as err:  # timeout, API error, validation error: fall back after at most one retry
                last = err
                log(logger, "ai attempt failed", task=task, attempt=attempt + 1, error=type(err).__name__)
        raise AIUnavailable(f"{task}: {type(last).__name__ if last else 'timeout'}")


_llm: AnthropicLLM | FakeLLM | OpenAILLM | None = None


def llm() -> AnthropicLLM | FakeLLM | OpenAILLM:
    global _llm
    if _llm is None:
        provider = get_settings().llm_provider
        if provider == "fake":
            _llm = FakeLLM()
        elif provider == "openai":
            _llm = OpenAILLM()
        else:
            _llm = AnthropicLLM()
    return _llm


def set_llm(instance: AnthropicLLM | FakeLLM | OpenAILLM | None) -> None:
    global _llm
    _llm = instance
