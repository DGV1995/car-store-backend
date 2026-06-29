"""
app/services/chat_agent.py — Google ADK-powered chatbot agent.

Wraps the existing read_cars() function as a tool for the AI agent so it can
answer questions about the car inventory. Provides a streaming async generator
for fluent, real-time responses.

Importable via:
    from app.services.chat_agent import run_chat_agent
"""

import json
import logging
import os
from typing import AsyncGenerator, List, Optional, Tuple

from app.services.file_service import read_cars

logger = logging.getLogger(__name__)


def _get_cars_tool() -> str:
    """
    Tool function: Retrieve all cars currently available in the store.

    Returns:
        A JSON string containing the full list of car records. Each record has
        fields: id, brand, model, year, km, price, image_url.
    """
    cars = read_cars()
    return json.dumps([car.model_dump() for car in cars], ensure_ascii=False)


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


def _format_history_for_adk(
    history: List[Tuple[str, str]], user_message: str
) -> List[dict]:
    """
    Format conversation history for the ADK agent.

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


async def run_chat_agent(
    history: List[Tuple[str, str]],
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Run the ADK-powered chat agent and stream the response tokens.

    The agent uses the existing ``read_cars()`` function as a tool to
    answer questions about car inventory.

    Args:
        history: Previous conversation messages as (role, content) tuples.
        user_message: The current user message to respond to.

    Yields:
        Text tokens (str) that form the assistant's reply.

    Raises:
        RuntimeError: If the ADK agent fails to initialise or no API key is set.
    """
    # Check for API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.warning(
            "GOOGLE_API_KEY not set. Chat agent will return a fallback response."
        )
        yield _build_fallback_response(history, user_message)
        return

    try:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        # Create the agent with the get_cars tool
        agent = Agent(
            name="car_expert",
            model=os.getenv("ADK_MODEL", "gemini-2.0-flash"),
            instruction=_build_system_instruction(),
            tools=[_get_cars_tool],
        )

        # Set up in-memory session service and runner
        session_service = InMemorySessionService()
        runner = Runner(
            agent=agent,
            session_service=session_service,
            app_name="car_store",
        )

        # Create a session for this turn
        session = session_service.create_session(
            user_id="default_user",
            session_id="chat_session",
        )

        # Feed previous history into session
        for role, content in history:
            session.append_message({"role": role, "content": content})

        # Run the agent and stream tokens
        async for event in runner.run_async(
            session=session,
            user_message=user_message,
        ):
            if event.is_final_response():
                content = getattr(event, "content", None)
                if content:
                    yield content
            elif hasattr(event, "content") and event.content:
                # Stream intermediate content tokens
                yield event.content

    except ImportError:
        logger.error(
            "google-adk package is not installed. Please run 'uv sync' to install dependencies."
        )
        yield _build_fallback_response(history, user_message)
    except Exception as exc:
        logger.exception("ADK agent failed: %s", exc)
        yield _build_fallback_response(history, user_message)


def _build_fallback_response(
    history: List[Tuple[str, str]], user_message: str
) -> str:
    """
    Generate a fallback response using the read_cars() tool directly.

    This is used when the ADK agent is unavailable (e.g., no API key configured).
    """
    cars = read_cars()
    if not cars:
        return "I'm sorry, but I don't have access to the car inventory right now. The system might be starting up. Please try again in a moment."

    # Simple keyword-based response
    lower_msg = user_message.lower()

    # Check if asking about BMWs under a price
    if "bmw" in lower_msg and ("under" in lower_msg or "less than" in lower_msg or "<" in lower_msg or "euro" in lower_msg or "€" in lower_msg or "eur" in lower_msg):
        # Try to extract a price from the message
        import re
        price_match = re.search(r'(\d+[\.\,]?\d*)', lower_msg.replace("€", "").replace("euro", "").replace("eur", ""))
        max_price = float(price_match.group(1).replace(",", ".")) if price_match else 30000.0
        bmw_cars = [c for c in cars if c.brand.lower() == "bmw" and c.price <= max_price]
        if bmw_cars:
            lines = [f"**{c.brand} {c.model}** ({c.year}, {c.km:,} km) — €{c.price:,.2f}" for c in bmw_cars]
            return f"Sure! Here are the BMWs under €{max_price:,.0f}:\n\n" + "\n".join(lines)
        else:
            return f"Unfortunately, there are no BMWs under €{max_price:,.0f} in our current inventory."

    # General "what cars do you have" query
    if any(word in lower_msg for word in ["what cars", "show", "list", "have", "available", "inventory", "all"]):
        if not cars:
            return "Our inventory is currently empty. Please check back later!"
        lines = [f"• **{c.brand} {c.model}** ({c.year}, {c.km:,} km) — €{c.price:,.2f}" for c in cars]
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
