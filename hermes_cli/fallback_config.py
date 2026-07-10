"""Helpers for reading the effective fallback provider chain from config."""

from __future__ import annotations

from typing import Any


def _normalized_base_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().rstrip("/")


def _coerce_entry(entry: Any) -> dict[str, Any] | None:
    """Coerce a single raw fallback entry into a ``{provider, model, ...}`` dict.

    Two on-disk shapes are accepted:

    * ``dict`` — the canonical form written by ``hermes fallback`` and the CLI.
    * ``"provider:model"`` string — the shape produced by the desktop
      *Model → Fallback Models* settings field, which is rendered by the generic
      comma-separated ``list`` editor and whose help text reads
      *"Backup provider:model entries to try if the default model fails."*

    The provider half may itself contain a colon (e.g. ``custom:my-endpoint``),
    so the split is anchored to the **last** colon: everything before it is the
    provider, the remainder is the model.

    Returns ``None`` for shapes that can't be interpreted (e.g. a bare model
    with no provider, or a non-string/non-dict value).
    """
    if isinstance(entry, dict):
        return entry
    if isinstance(entry, str):
        text = entry.strip()
        if ":" not in text:
            return None
        provider, _, model = text.rpartition(":")
        return {"provider": provider.strip(), "model": model.strip()}
    return None


def _iter_fallback_entries(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, (dict, str)):
        candidates: list[Any] = [raw]
    elif isinstance(raw, list):
        candidates = list(raw)
    else:
        return []

    entries: list[dict[str, Any]] = []
    for raw_entry in candidates:
        entry = _coerce_entry(raw_entry)
        if entry is None:
            continue
        provider = str(entry.get("provider") or "").strip()
        model = str(entry.get("model") or "").strip()
        if not provider or not model:
            continue

        normalized = dict(entry)
        normalized["provider"] = provider
        normalized["model"] = model

        base_url = _normalized_base_url(entry.get("base_url"))
        if base_url:
            normalized["base_url"] = base_url

        entries.append(normalized)
    return entries


def _entry_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("provider") or "").strip().lower(),
        str(entry.get("model") or "").strip().lower(),
        _normalized_base_url(entry.get("base_url")).lower(),
    )


def get_fallback_chain(config: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the effective fallback chain merged across old and new config keys.

    ``fallback_providers`` remains the primary source of truth and keeps its
    order. Legacy ``fallback_model`` entries are appended afterwards unless
    they target the same provider/model/base_url route as an earlier entry.
    The returned list always contains fresh dict copies.
    """

    config = config or {}
    chain: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for key in ("fallback_providers", "fallback_model"):
        for entry in _iter_fallback_entries(config.get(key)):
            identity = _entry_identity(entry)
            if identity in seen:
                continue
            seen.add(identity)
            chain.append(entry)

    return chain
