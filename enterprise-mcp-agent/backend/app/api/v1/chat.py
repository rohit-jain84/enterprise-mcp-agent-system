"""Chat endpoints -- REST and WebSocket."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.api.websocket import manager
from app.dependencies import CurrentUser, DBSession, SettingsDep
from app.models.schemas import ChatRequest, ChatResponse, WSMessage
from app.services.chat_service import ChatService
from app.services.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def post_chat(
    body: ChatRequest,
    user: CurrentUser,
    db: DBSession,
    settings: SettingsDep,
):
    """Synchronous chat endpoint -- sends a message and returns the full response."""
    # --- Budget enforcement ---
    tracker = CostTracker()
    allowed, reason = await tracker.check_budget(user_id=user.id, session_id=body.session_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    svc = ChatService(db=db, settings=settings, user=user)
    result = await svc.invoke(session_id=body.session_id, user_message=body.message)
    return result


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: uuid.UUID):
    """Full-duplex WebSocket for streaming chat.

    Client sends:
        {"type": "user_message", "payload": {"message": "..."}}
        {"type": "approval_response", "payload": {"approval_id": "...", "action": "approved"}}

    Server sends:
        {"type": "stream_start", "payload": {}}
        {"type": "stream_chunk", "payload": {"content": "..."}}
        {"type": "stream_end", "payload": {"message_id": "...", "token_count": N, "cost": F}}
        {"type": "tool_call", "payload": {"tool_name": "...", "tool_args": {...}}}
        {"type": "tool_result", "payload": {"tool_name": "...", "result": "..."}}
        {"type": "approval_request", "payload": {"approval_id": "...", "tool_name": "...", "tool_args": {...}}}
        {"type": "error", "payload": {"detail": "..."}}
    """
    await manager.connect(websocket, session_id)
    try:
        while True:
            raw = await websocket.receive_json()
            try:
                msg = WSMessage(**raw)
            except Exception as exc:
                await manager.send_json(websocket, {
                    "type": "error",
                    "payload": {"detail": f"Invalid message format: {exc}"},
                })
                continue

            if msg.type == "user_message":
                user_text = msg.payload.get("message", "")
                if not user_text:
                    await manager.send_json(websocket, {
                        "type": "error",
                        "payload": {"detail": "Empty message"},
                    })
                    continue

                # Stream start
                await manager.send_json(websocket, {"type": "stream_start", "payload": {}})

                try:
                    # Import here to avoid circular imports at module level
                    from app.db.engine import get_session_factory
                    from app.config import get_settings

                    settings = get_settings()
                    factory = get_session_factory()

                    # --- Budget enforcement (session-level for WebSocket) ---
                    tracker = CostTracker()
                    session_data = await tracker.get_session_totals(session_id)
                    session_spend = session_data["total_cost"]
                    if session_spend >= settings.COST_BUDGET_PER_SESSION:
                        await manager.send_json(websocket, {
                            "type": "error",
                            "payload": {
                                "detail": (
                                    f"Session cost budget exceeded: "
                                    f"${session_spend:.4f} spent of "
                                    f"${settings.COST_BUDGET_PER_SESSION:.2f} limit"
                                ),
                                "code": 429,
                            },
                        })
                        continue

                    async with factory() as db:
                        svc = ChatService(db=db, settings=settings, user=None)

                        async def on_chunk(chunk: str) -> None:
                            await manager.send_json(websocket, {
                                "type": "stream_chunk",
                                "payload": {"content": chunk},
                            })

                        async def on_tool_call(tool_name: str, tool_args: dict) -> None:
                            await manager.send_json(websocket, {
                                "type": "tool_call",
                                "payload": {"tool_name": tool_name, "tool_args": tool_args},
                            })

                        async def on_tool_result(tool_name: str, result: str) -> None:
                            await manager.send_json(websocket, {
                                "type": "tool_result",
                                "payload": {"tool_name": tool_name, "result": result},
                            })

                        async def on_approval_request(approval_id: str, tool_name: str, tool_args: dict) -> None:
                            await manager.send_json(websocket, {
                                "type": "approval_request",
                                "payload": {
                                    "approval_id": approval_id,
                                    "tool_name": tool_name,
                                    "tool_args": tool_args,
                                },
                            })

                        result = await svc.invoke_streaming(
                            session_id=session_id,
                            user_message=user_text,
                            on_chunk=on_chunk,
                            on_tool_call=on_tool_call,
                            on_tool_result=on_tool_result,
                            on_approval_request=on_approval_request,
                        )

                        await db.commit()

                    # Stream end
                    await manager.send_json(websocket, {
                        "type": "stream_end",
                        "payload": {
                            "message_id": str(result.get("message_id", "")),
                            "token_count": result.get("token_count", 0),
                            "cost": result.get("cost", 0.0),
                        },
                    })

                except Exception as exc:
                    logger.exception("Error processing chat message via WebSocket")
                    await manager.send_json(websocket, {
                        "type": "error",
                        "payload": {"detail": str(exc)},
                    })

            elif msg.type == "approval_response":
                approval_id = msg.payload.get("approval_id")
                action = msg.payload.get("action")
                if not approval_id or not action:
                    await manager.send_json(websocket, {
                        "type": "error",
                        "payload": {"detail": "Missing approval_id or action"},
                    })
                    continue

                try:
                    from app.db.engine import get_session_factory
                    from app.services.approval_service import ApprovalService

                    factory = get_session_factory()
                    async with factory() as db:
                        approval_svc = ApprovalService(db)
                        result = await approval_svc.process_response(
                            approval_id=uuid.UUID(approval_id),
                            action=action,
                            responded_by=None,
                        )
                        await db.commit()

                    await manager.send_json(websocket, {
                        "type": "tool_result",
                        "payload": {"approval_id": approval_id, "action": action, "status": "processed"},
                    })

                except Exception as exc:
                    logger.exception("Error processing approval response via WebSocket")
                    await manager.send_json(websocket, {
                        "type": "error",
                        "payload": {"detail": str(exc)},
                    })

            else:
                await manager.send_json(websocket, {
                    "type": "error",
                    "payload": {"detail": f"Unknown message type: {msg.type}"},
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception:
        manager.disconnect(websocket, session_id)
        logger.exception("WebSocket error for session %s", session_id)
