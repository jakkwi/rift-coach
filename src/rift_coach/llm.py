"""Two ways to get a structured answer from Claude.

- ApiBackend (default): Claude API with ANTHROPIC_API_KEY (prepaid Console credits).
- SubscriptionBackend: Claude Agent SDK signed in with your own Claude plan, for
  personal local use only. Anthropic does not allow third-party apps to offer
  claude.ai login, so anything shared or deployed must use the API backend.
  One-time setup: `rift-coach login`.

Both take a JSON schema and return the parsed object, so the rest of the app doesn't care.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLMError(RuntimeError):
    pass


class Backend(Protocol):
    async def structured(self, system: str, prompt: str, name: str, schema: dict) -> dict: ...


class ApiBackend:
    def __init__(self, api_key: str, model: str, max_tokens: int):
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    async def structured(self, system: str, prompt: str, name: str, schema: dict) -> dict:
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            tools=[{"name": name, "description": f"Submit {name}.", "input_schema": schema}],
            tool_choice={"type": "tool", "name": name},
            messages=[{"role": "user", "content": prompt}],
        )
        for block in msg.content:
            if block.type == "tool_use":
                return block.input
        raise LLMError("Model did not return a tool call.")


class SubscriptionBackend:
    def __init__(self, model: str):
        self.model = model

    async def structured(self, system: str, prompt: str, name: str, schema: dict) -> dict:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        # Without this, an ANTHROPIC_API_KEY from .env would silently switch to API billing.
        env = {"ANTHROPIC_API_KEY": ""} if os.getenv("ANTHROPIC_API_KEY") else {}
        options = ClaudeAgentOptions(
            system_prompt=system,
            model=self.model,
            tools=[],              # no file/shell tools: pure reasoning
            setting_sources=[],    # ignore any local CLAUDE.md / settings
            max_turns=3,
            output_format={"type": "json_schema", "schema": schema},
            env=env,
        )
        result: ResultMessage | None = None
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result = message
        return parse_result(result)


def parse_result(result) -> dict:
    if result is None:
        raise LLMError("No result from Claude. Run `rift-coach login` and try again.")
    if result.is_error:
        detail = "; ".join(result.errors or []) or result.result or result.subtype
        raise LLMError(f"Claude returned an error: {detail}")
    if not isinstance(result.structured_output, dict):
        raise LLMError("Claude did not return structured output.")
    return result.structured_output


def make_backend(cfg) -> Backend:
    if cfg.claude.backend == "api":
        return ApiBackend(cfg.anthropic_api_key, cfg.claude.model, cfg.claude.max_tokens)
    return SubscriptionBackend(cfg.claude.model)
