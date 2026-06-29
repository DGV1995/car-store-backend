"""
app/services/chat_agent.py — DeepSeek API-powered chatbot agent.

Calls the DeepSeek API (OpenAI-compatible endpoint) directly to generate
streaming responses about car inventory. Falls back to a rule-based response
when the API key is not configured.

Importable via:
    from app.services.chat_agent import run_chat_agent
"""

import json
import logging
from typing import AsyncGenerator, List, Tuple

from openai import AsyncOpenAI

from app.config import settings
from app.services.file_service import read_cars

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------


def _get_cars_tool() -> str:
    """
    Retrieve all cars currently available in the store.

    Returns:
        A JSON string containing the full list of car records. Each record has
        fields: id, brand, model, year, km, price, image_url.
    """
    cars = read_cars()
    return json.dumps([car.model_dump() for car in cars], ensure_ascii=False)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def _build_system_instruction() -> str:
    """Build the system instruction for the chat agent."""
    return (
        "You are a helpful car expert assistant at a car store. "
        "You have access to the store's complete car inventory via the get_cars function. "
        "When asked about available cars, always call the get_cars function first to get "
        "the latest inventory data. Be friendly and informative. "
        "When discussing cars, provide useful details like brand, model, year, kilometers, "
        "and price. Format your responses in a clear, conversational way.\n\n"
        "Available functions:\n"
        "- get_cars: Returns a JSON array of all cars in the inventory. "
        "Call this whenever the user asks about what cars are available, "
        "wants to filter by brand, price, or any other criteria."
    )


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------


def _build_messages(
    history: List[Tuple[str, str]], user_message: str
) -> List[dict]:
    """
    Build the messages list for the DeepSeek chat completion request.

    Args:
        history: Previous messages as (role, content) tuples.
        user_message: The current user message to append.

    Returns:
        A list of message dicts with "role" and "content" keys.
    """
    messages = [
        {"role": "system", "content": _build_system_instruction()}
    ]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


# ---------------------------------------------------------------------------
# Main streaming generator
# ---------------------------------------------------------------------------


async def run_chat_agent(
    history: List[Tuple[str, str]],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Run the DeepSeek-powered chat agent and stream the response tokens.

    The agent uses the existing ``read_cars()`` function to inject inventory
    context into the system prompt and calls the DeepSeek API via its
    OpenAI-compatible endpoint.

    Args:
        history: Previous conversation messages as (role, content) tuples.
        user_message: The current user message to respond to.

    Yields:
        Text tokens (str) that form the assistant's reply.
    """
    # Check for API key via the centralised settings
    api_key = settings.deepseek_api_key
    if not api_key:
        logger.warning(
            "DEEPSEEK_API_KEY not set. Chat agent will return a fallback response."
        )
        yield _build_fallback_response(history, user_message)
        return

    # Build the messages list
    messages = _build_messages(history, user_message)

    # Inject inventory context as a function-style tool result for the model
    try:
        cars_data = _get_cars_tool()
        # Append the inventory data as a system message so the model can
        # reason about the available stock without needing tool call mechanics.
        context_message = (
            "Here is the current car inventory (JSON):\n"
            f"{cars_data}"
        )
        messages.append({"role": "system", "content": context_message})
    except Exception as exc:
        logger.warning("Failed to read cars for context: %s", exc)

    try:
        # Initialise the OpenAI-compatible client pointed at DeepSeek
        client = AsyncOpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )

        # Stream the completion
        stream = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    except Exception as exc:
        logger.exception("DeepSeek API call failed: %s", exc)
        yield _build_fallback_response(history, user_message)


# ---------------------------------------------------------------------------
# Fallback response (rule-based, no API key required)
# ---------------------------------------------------------------------------


def _build_fallback_response(
    history: List[Tuple[str, str]], user_message: str
) -> str:
    """
    Generate a fallback response using the read_cars() tool directly.

    This is used when the DeepSeek API is unavailable (e.g., no API key
    configured or network error).
    """
    cars = read_cars()
    if not cars:
        return "I'm sorry, but I don't have access to the car inventory right now. The system might be starting up. Please try again in a moment."

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
                "in our current inventory."
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
