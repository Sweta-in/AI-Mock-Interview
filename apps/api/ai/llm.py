"""
PrepAI — LiteLLM wrapper with automatic fallback, retry logic, and cost tracking.
"""

import time
import json
import logging
from typing import Optional, List, Dict, Any

import litellm
import redis.asyncio as aioredis

from apps.api.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure LiteLLM
litellm.set_verbose = False
if settings.ANTHROPIC_API_KEY:
    litellm.api_key = settings.ANTHROPIC_API_KEY


class LLMClient:
    """Async LLM client wrapping LiteLLM with fallback, retry, and cost tracking."""

    def __init__(self) -> None:
        self.primary_model = settings.PRIMARY_MODEL
        self.fallback_model = settings.FALLBACK_MODEL
        self.max_retries = settings.LLM_MAX_RETRIES
        self.timeout = settings.LLM_TIMEOUT_SECONDS
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Lazy-init Redis for cost tracking."""
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception as e:
                logger.warning(f"Redis unavailable for cost tracking: {e}")
        return self._redis

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, str]] = None,
        interview_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a completion request with automatic fallback and retry.

        Returns dict with: content, model_used, prompt_tokens, completion_tokens,
        cost_usd, latency_ms.
        """
        target_model = model or self.primary_model
        last_error: Optional[Exception] = None

        # Try primary model with retries
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._call_llm(
                    model=target_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    interview_id=interview_id,
                )
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM call failed (model={target_model}, attempt={attempt+1}): {e}"
                )
                if attempt < self.max_retries:
                    backoff = 0.5 * (2 ** attempt)  # 0.5s, 1.0s
                    import asyncio
                    await asyncio.sleep(backoff)

        # Fallback to secondary model
        if target_model != self.fallback_model and self.fallback_model:
            logger.info(f"Falling back to {self.fallback_model}")
            for attempt in range(self.max_retries + 1):
                try:
                    result = await self._call_llm(
                        model=self.fallback_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=response_format,
                        interview_id=interview_id,
                    )
                    return result
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Fallback LLM call failed (attempt={attempt+1}): {e}"
                    )
                    if attempt < self.max_retries:
                        import asyncio
                        await asyncio.sleep(0.5 * (2 ** attempt))

        raise RuntimeError(
            f"All LLM calls failed after retries and fallback. Last error: {last_error}"
        )

    async def _call_llm(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        response_format: Optional[Dict[str, str]],
        interview_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute a single LLM call and track usage."""
        start_time = time.time()

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": self.timeout,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = await litellm.acompletion(**kwargs)

        latency_ms = (time.time() - start_time) * 1000
        content = response.choices[0].message.content or ""
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        # Calculate cost
        cost_usd = self._estimate_cost(model, prompt_tokens, completion_tokens)

        result = {
            "content": content,
            "model_used": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "latency_ms": round(latency_ms, 2),
        }

        # Log to Redis for cost monitoring
        await self._track_usage(result, interview_id)

        logger.info(
            f"LLM call: model={model} tokens={prompt_tokens}+{completion_tokens} "
            f"cost=${cost_usd:.4f} latency={latency_ms:.0f}ms"
        )

        return result

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on known pricing."""
        pricing = {
            "anthropic/claude-sonnet-4-20250514": {"input": 3.0 / 1_000_000, "output": 15.0 / 1_000_000},
            "openai/gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.6 / 1_000_000},
        }
        rates = pricing.get(model, {"input": 1.0 / 1_000_000, "output": 3.0 / 1_000_000})
        return (prompt_tokens * rates["input"]) + (completion_tokens * rates["output"])

    async def _track_usage(self, result: Dict[str, Any], interview_id: Optional[str]) -> None:
        """Track token usage in Redis for cost monitoring."""
        try:
            redis = await self._get_redis()
            if redis is None:
                return

            # Increment daily counters
            import datetime
            today = datetime.date.today().isoformat()

            pipe = redis.pipeline()
            pipe.incrbyfloat(f"cost:daily:{today}", result["cost_usd"])
            pipe.incrby(f"tokens:daily:{today}:prompt", result["prompt_tokens"])
            pipe.incrby(f"tokens:daily:{today}:completion", result["completion_tokens"])
            pipe.expire(f"cost:daily:{today}", 86400 * 30)  # Keep 30 days
            pipe.expire(f"tokens:daily:{today}:prompt", 86400 * 30)
            pipe.expire(f"tokens:daily:{today}:completion", 86400 * 30)

            if interview_id:
                pipe.incrbyfloat(f"cost:interview:{interview_id}", result["cost_usd"])
                pipe.expire(f"cost:interview:{interview_id}", 86400 * 7)

            await pipe.execute()
        except Exception as e:
            logger.warning(f"Failed to track LLM usage in Redis: {e}")

    async def complete_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        interview_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Complete and parse the response as JSON.

        Strips markdown code fences if present.
        """
        result = await self.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            interview_id=interview_id,
        )

        content = result["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (fences)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nContent: {content[:500]}")
            raise ValueError(f"LLM returned invalid JSON: {e}")

        result["parsed"] = parsed
        return result
