"""
app/routers/chat.py — Chat API routes.

Endpoints:
- POST /api/chat — Send a message to the AI agent, stream the reply.
- GET  /api/chat/conversations — List all conversations sorted by most recent.
- GET  /api/chat/conversations/{id} — Get full conversation with all messages.
"""

import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.models import (
    ChatConversation,
    ChatMessage,
    ChatRequest,
    ChatRole,
    ConversationListItem,
)
from app.services.chat_agent import run_chat_agent
from app.services.conversations_service import (
    read_conversations,
    write_conversations,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    description=(
        "Send a message to the AI car expert assistant. "
        "Returns a Server-Sent Events (SSE) stream. "
        "First event sends the conversation_id, "
        "subsequent events stream reply tokens, "
        "and a final 'done' event signals completion."
    ),
)
async def chat(request: ChatRequest):
    """
    Send a message to the AI car expert assistant.

    The response is streamed as Server-Sent Events (SSE):
      - `event: conversation_id` — carries the conversation UUID
      - `event: token` — each chunk of the assistant's reply
      - `event: done` — signals the stream is complete

    If ``conversation_id`` is ``None`` a new conversation is created.
    """
    conversations = read_conversations()

    # ---- Resolve or create the conversation ----
    if request.conversation_id:
        conversation = next(
            (c for c in conversations if c.id == request.conversation_id),
            None,
        )
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{request.conversation_id}' not found.",
            )
    else:
        # Auto-generate a title from the first message (truncated)
        title = request.message[:60]
        if len(request.message) > 60:
            title += "..."
        conversation = ChatConversation(title=title)
        conversations.append(conversation)

    # ---- Append the user message ----
    user_msg = ChatMessage(role=ChatRole.user, content=request.message)
    conversation.messages.append(user_msg)
    conversation.updated_at = datetime.now(timezone.utc)

    # Persist immediately so the message is saved even if streaming fails
    write_conversations(conversations)

    # ---- Build history for the agent ----
    # All messages except the very last one (which is the current user msg)
    history: List[tuple[str, str]] = [
        (m.role.value, m.content) for m in conversation.messages[:-1]
    ]

    async def event_stream():
        """Async generator that yields SSE-formatted events."""
        # 1. Send conversation_id
        yield f"event: conversation_id\ndata: {conversation.id}\n\n"

        full_reply = ""
        try:
            async for token in run_chat_agent(history, request.message):
                full_reply += token
                # Escape the data for SSE: replace newlines
                safe_token = token.replace("\n", "\\n")
                yield f"event: token\ndata: {json.dumps(safe_token)}\n\n"
        except Exception as exc:
            # If agent fails mid-stream, send a fallback
            fallback = (
                "I'm sorry, something went wrong while processing your request. "
                "Please try again."
            )
            full_reply = fallback
            safe_fallback = fallback.replace("\n", "\\n")
            yield f"event: token\ndata: {json.dumps(safe_fallback)}\n\n"

        # 2. Persist the assistant response
        assistant_msg = ChatMessage(role=ChatRole.assistant, content=full_reply)
        conversation.messages.append(assistant_msg)
        conversation.updated_at = datetime.now(timezone.utc)

        convs = read_conversations()
        for i, c in enumerate(convs):
            if c.id == conversation.id:
                convs[i] = conversation
                break
        write_conversations(convs)

        # 3. Signal completion
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/conversations",
    response_model=List[ConversationListItem],
    status_code=status.HTTP_200_OK,
    description="List all conversations sorted by most recent updated_at.",
)
def list_conversations():
    """
    Return a list of all conversations, sorted by ``updated_at`` descending.

    Each item contains only ``id``, ``title``, and ``updated_at`` —
    the full message history is available via the individual conversation endpoint.
    """
    conversations = read_conversations()
    # Sort by most recent first
    conversations.sort(key=lambda c: c.updated_at, reverse=True)
    return [
        ConversationListItem(
            id=c.id,
            title=c.title,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ChatConversation,
    status_code=status.HTTP_200_OK,
    description="Get the full conversation including all messages.",
)
def get_conversation(conversation_id: str):
    """
    Return the full conversation object including all messages for the given ID.

    Raises ``404`` if the conversation does not exist.
    """
    conversations = read_conversations()
    conversation = next(
        (c for c in conversations if c.id == conversation_id),
        None,
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return conversation
