"""
app/services/chat_agent.py — LiteLLM-powered chatbot agent.

Wraps the existing read_cars() function as context for the LLM so it can
answer questions about the car inventory. Provides a streaming async generator
for fluent, real-time responses.

Importable via:
    from app.services.chat_agent import run_chat_agent
"""

import json
import logging
from typing import AsyncGenerator, List, Tuple

from app.config import settings
from app.services.file_service import read_cars

logger = logging.getLogger(__name__)


def _get_cars_data() -> str:
    """
    Retrieve all cars currently available in the store as a JSON string.

    Returns:
        A JSON string containing the full list of car records. Each record has
        fields: id, brand, model, year, km, price, image_url.
    """
    cars = read_cars()
    return json.dumps([car.model_dump() for car in cars], ensure_ascii=False)


def _build_system_instruction() -> str:
    """Build the system instruction for the chat agent, including inventory data."""
    cars_json = _get_cars_data()
    return (
        "You are a helpful car expert assistant at a car store. "
        "You have access to the store's complete car inventory which is "
        "provided below as a JSON array. Use this data to answer user questions. "
        "Be friendly and informative. When discussing cars, provide useful "
        "details like brand, model, year, kilometers, and price. Format your "
        "responses in a clear, conversational way.\n\n"
        "Current car inventory:\n"
        f"{cars_json}\n\n"
        "If the user asks about cars that match certain criteria (brand, price "
        "range, year, etc.), analyse the inventory data and respond with the "
        "matching cars. If no cars match, let the user know politely."
    )


def _build_messages(
    history: List[Tuple[str, str]],
    user_message: str,
) -> list[dict]:
    """
    Build the messages list for the LiteLLM completion call.

    Args:
        history: Previous messages as (role, content) tuples.
        user_message: The current user message to append.

    Returns:
        A list of message dicts with "role" and "content" keys.
    """
    messages = [{"role": "system", "content": _build_system_instruction()}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


async def run_chat_agent(
    history: List[Tuple[str, str]],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Run the LiteLLM-powered chat agent and stream the response tokens.

    The agent uses the car inventory data (fetched via ``read_cars()``) as
    context in the system prompt to answer questions about the store.

    Args:
        history: Previous conversation messages as (role, content) tuples.
        user_message: The current user message to respond to.

    Yields:
        Text tokens (str) that form the assistant's reply.

    Raises:
        RuntimeError: If no API key is configured.
    """
    # Check for API key via the centralised settings
    api_key = settings.deepseek_api_key
    if not api_key:
        logger.warning(
            "DEEPSEEK_API_KEY not set. Chat agent will return a fallback response."
        )
        yield _build_fallback_response(history, user_message)
        return

    model = settings.deepseek_model

    try:
        from litellm import acompletion

        messages = _build_messages(history, user_message)

        response = await acompletion(
            model=model,
            api_key=api_key,
            messages=messages,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except ImportError:
        logger.error(
            "litellm package is not installed. Please run 'uv sync' to install dependencies."
        )
        yield _build_fallback_response(history, user_message)
    except Exception as exc:
        logger.exception("LiteLLM agent failed: %s", exc)
        yield _build_fallback_response(history, user_message)


def _build_fallback_response(
    history: List[Tuple[str, str]], user_message: str
) -> str:
    """
    Generate a fallback response using the read_cars() tool directly.

    This is used when the LiteLLM agent is unavailable (e.g., no API key
    configured or the model call fails).
    """
    cars = read_cars()
    if not cars:
        return (
            "I'm sorry, but I don't have access to the car inventory right now. "
            "The system might be starting up. Please try again in a moment."
        )

    # Simple keyword-based response
    lower_msg = user_message.lower()

    # Check if asking about BMWs under a price
    if "bmw" in lower_msg and (
        "under" in lower_msg
        or "less than" in lower_msg
        or "<" in lower_msg
        or "euro" in lower_msg
        or "€" in lower_msg
        or "eur" in lower_msg
    ):
        # Try to extract a price from the message
        import re

        price_match = re.search(
            r"(\d+[\.\,]?\d*)",
            lower_msg.replace("€", "").replace("euro", "").replace("eur", ""),
        )
        max_price = float(price_match.group(1).replace(",", ".")) if price_match else 30000.0
        bmw_cars = [c for c in cars if c.brand.lower() == "bmw" and c.price <= max_price]
        if bmw_cars:
            lines = [
                f"**{c.brand} {c.model}** ({c.year}, {c.km:,} km) — €{c.price:,.2f}"
                for c in bmw_cars
            ]
            return f"Sure! Here are the BMWs under €{max_price:,.0f}:\n\n" + "\n".join(lines)
        else:
            return (
                f"Unfortunately, there are no BMWs under €{max_price:,.0f} "
                f"in our current inventory."
            )

    # General "what cars do you have" query
    if any(
        word in lower_msg
        for word in ["what cars", "show", "list", "have", "available", "inventory", "all"]
    ):
        if not cars:
            return "Our inventory is currently empty. Please check back later!"
        lines = [
            f"• **{c.brand} {c.model}** ({c.year}, {c.km:,} km) — €{c.price:,.2f}"
            for c in cars
        ]
        return f"Here are all the cars we currently have in stock:\n\n" + "\n".join(lines)

    # Default generic response
    if cars:
        return (
            f"We currently have {len(cars)} car(s) in our inventory. "
            f"You can ask me things like 'What cars do you have?' or "
            f"'Show me BMWs under 30000€' to get specific information!"
        )
    return (
        "Hello! I'm the car store assistant. I can help you find information "
        "about our car inventory. Feel free to ask me what cars we have available!"
    )
