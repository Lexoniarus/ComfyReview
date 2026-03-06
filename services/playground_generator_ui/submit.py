from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.comfy_client import ComfyClient


def submit_preview_drafts(
    drafts: List[Dict[str, Any]],
    *,
    client: Optional[ComfyClient] = None,
) -> Tuple[str, Optional[str]]:
    """Enqueue all drafts to ComfyUI.

    Returns
    enqueue_info, error
    """

    if not drafts:
        return "queued: 0/0", None

    c = client or ComfyClient()

    responses: List[Any] = []
    errors: List[str] = []

    for d in drafts:
        did = str(d.get("draft_id") or "").strip() or "draft"
        try:
            resp = c.enqueue_from_playground(
                character_name=str(d.get("character_name") or ""),
                positive_prompt=str(d.get("prompt_positive") or ""),
                negative_prompt=str(d.get("prompt_negative") or ""),
                checkpoint=d.get("checkpoint"),
                seed=d.get("seed"),
                steps=d.get("steps"),
                cfg=d.get("cfg"),
                denoise=d.get("denoise"),
                sampler=d.get("sampler"),
                scheduler=d.get("scheduler"),
                subdir=str(d.get("subdir") or "playground"),
            )
            responses.append(resp)

            if not getattr(resp, "ok", False):
                msg = getattr(resp, "error", "") or str(getattr(resp, "response_json", {}) or {})
                errors.append(f"{did}: {getattr(resp, 'status_code', 0)} {msg}")

        except Exception as e:
            responses.append({"ok": False, "status_code": 0, "error": str(e)})
            errors.append(f"{did}: {str(e)}")

    total = len(drafts)
    ok_count = sum(
        1
        for r in responses
        if (r.get("ok", False) if isinstance(r, dict) else getattr(r, "ok", False))
    )
    fail_count = total - ok_count

    enqueue_info = f"queued: {ok_count}/{total}"
    if fail_count > 0:
        enqueue_info += f" | failed: {fail_count}"

    error = None
    if errors:
        head = errors[:5]
        tail = " ..." if len(errors) > 5 else ""
        error = " | ".join(head) + tail

    return enqueue_info, error
