# 0010 - Anthropic multi-turn prompt caching via explicit cache breakpoints

## Status

Proposed

## Context

When using Anthropic as the LLM provider, conversation history is managed client-side: on every turn the full message list (system context + all prior turns + current user message) is sent to the API. The system context alone (course content extracted by `OpenEdXProcessor`) can be several thousand tokens. Sending it uncached on every turn is expensive and slow.

Anthropic supports prompt caching via `cache_control` markers on individual content blocks. Cached prefixes are reused across requests for a 5-minute window (refreshed on each hit), at 10% of the normal input token price. Cache writes cost 25% more than base input tokens, so the break-even is any prefix read more than once within the TTL — which is guaranteed for every turn after the first in an active conversation.

Two caching strategies exist:

- **Automatic caching**: a single top-level `cache_control` field; Anthropic moves the breakpoint automatically. Simple, but requires the Anthropic API directly — support through LiteLLM's emulation layer is not guaranteed.
- **Explicit breakpoints**: `cache_control` placed on individual content blocks. Fully supported through LiteLLM's `completion()` call, which is the path used for Anthropic in this codebase.

[Official docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

The naive explicit approach (marking every user message) hits Anthropic's limit of 4 breakpoints per request once a conversation exceeds 3 turns.

## Decision

Use **two explicit cache breakpoints** per request, applied as a request-time transformation in `adapt_to_provider`:

1. **Last system message** — the course context and instructions are identical on every turn; an explicit breakpoint here ensures a cache hit from the second turn onward regardless of conversation length.
2. **Last user message** (current turn) — this becomes the cache entry that the *next* turn's lookback window will find. Anthropic's lookback walks backward up to 20 blocks from the new breakpoint; since each turn adds exactly 2 blocks (one assistant + one user), the lookback always finds the previous cache entry within 2 steps.

The transformation is encapsulated in `_apply_multi_turn_cache()` in `processors/llm/providers/__init__.py` and is gated by a `multi_turn_cache` entry in `_PROVIDER_CAPABILITIES["anthropic"]`, consistent with the `provider_supports()` pattern introduced for `server_side_thread_id`.

The transformation converts the `content` field of the targeted messages from a plain string to Anthropic's block format:

```json
{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}
```

This is applied after all other `adapt_to_provider` transforms (user-message injection, streaming key conversion) so it operates on the final message list regardless of which key (`input` or `messages`) is in use.

The transformation is **never persisted**. `get_full_message_history()` in the submission processor filters out any message whose `content` is not a plain string, so history always round-trips as plain strings and the block format is reconstructed fresh on each request.

## Consequences

- System context and growing conversation history are cached at Anthropic from the second turn onward, reducing input token costs and latency for active conversations.
- The 2-breakpoint strategy stays within Anthropic's 4-breakpoint limit for conversations of any length.
- Adding a new provider that supports prompt caching requires only adding `multi_turn_cache` to its `_PROVIDER_CAPABILITIES` entry; no other code changes are needed.
- The minimum cacheable prompt length for `claude-sonnet-4-6` is 1,024 tokens. Requests below this threshold are silently processed without caching; no error is returned.
- Cache hits and misses are visible in the Anthropic API response under `usage.cache_read_input_tokens` and `usage.cache_creation_input_tokens`.
