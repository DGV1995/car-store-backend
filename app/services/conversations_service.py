"""
app/services/conversations_service.py — JSON file persistence for chat conversations.

Provides functions to read and write the list of conversations from/to a JSON file.

Importable via:
    from app.services.conversations_service import read_conversations, write_conversations
"""

import json
import os
from typing import List

from app.models import ChatConversation

DATA_DIR = "data"
CONVERSATIONS_FILE = os.path.join(DATA_DIR, "conversations.json")


def _ensure_data_file() -> None:
    """Create the data directory and conversations.json file if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def read_conversations() -> List[ChatConversation]:
    """
    Read all conversations from the JSON file.

    Returns:
        A list of ChatConversation objects.
        Returns an empty list if the file is missing, empty, or malformed.
    """
    _ensure_data_file()
    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [ChatConversation(**item) for item in data]
    except (json.JSONDecodeError, FileNotFoundError, IOError):
        return []


def write_conversations(conversations: List[ChatConversation]) -> None:
    """
    Write a list of conversations to the JSON file.

    Args:
        conversations: List of ChatConversation objects to persist.
    """
    _ensure_data_file()
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            [conv.model_dump(mode="json") for conv in conversations],
            f,
            indent=2,
            ensure_ascii=False,
        )
