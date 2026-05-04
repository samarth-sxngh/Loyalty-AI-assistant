import json
import logging
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, CUSTOMER_ID, MERCHANT_ID
from agent.prompts import SYSTEM_PROMPT
from tools.loyalty_tools import (
    get_points_balance,
    get_expiring_points,
    get_available_coupons,
    get_recent_loyalty_activity,
    check_redemption_eligibility,
    check_missing_points,
    get_last_transaction,
)

client = Groq(api_key=GROQ_API_KEY)


logging.basicConfig(
    filename='agent_queries.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

#Guardrails 
PRIVACY_KEYWORDS = [
    "another customer", "other customer", "someone else",
    "other user", "another user", "different customer",
    "customer 102", "customer 103"
]

OFF_TOPIC_KEYWORDS = [
    "joke", "politics", "weather", "news", "cricket",
    "movie", "song", "recipe", "stock", "crypto",
    "tell me about", "what is", "who is", "explain"
]

LOYALTY_KEYWORDS = [
    "points", "coupon", "reward", "redeem", "transaction",
    "purchase", "expire", "balance", "discount", "earn",
    "loyalty", "activity", "history", "last purchase"
]


def is_privacy_violation(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in PRIVACY_KEYWORDS)


def is_off_topic(message: str) -> bool:
    message_lower = message.lower()
    has_loyalty = any(keyword in message_lower for keyword in LOYALTY_KEYWORDS)
    has_off_topic = any(keyword in message_lower for keyword in OFF_TOPIC_KEYWORDS)
    return has_off_topic and not has_loyalty


def sanitize_input(message: str) -> str:
    """Basic prompt injection prevention."""
    dangerous = ["<", ">", "{", "}", "SELECT", "DROP", "INSERT", "DELETE", "--"]
    for d in dangerous:
        message = message.replace(d, "")
    return message.strip()


#Tool definitions for Groq function calling 
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_points_balance",
            "description": "Get the customer's loyalty points balance including total, available, redeemed and expired points.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_expiring_points",
            "description": "Get points that are expiring soon (within 60 days) for the customer.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_coupons",
            "description": "Get all active coupons currently available to the customer.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_loyalty_activity",
            "description": "Get the customer's recent loyalty activity including points earned, redeemed and expired.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_redemption_eligibility",
            "description": "Check if the customer is eligible to redeem their loyalty points.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_missing_points",
            "description": "Check why the customer did not receive points for a transaction. Returns denied or pending transactions.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_last_transaction",
            "description": "Get the details of the customer's most recent purchase transaction.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


def dispatch_tool(tool_name: str) -> str:
    """Calls the right Python function and returns result as JSON string."""
    args = {"customer_id": CUSTOMER_ID, "merchant_id": MERCHANT_ID}

    tool_map = {
        "get_points_balance": get_points_balance,
        "get_expiring_points": get_expiring_points,
        "get_available_coupons": get_available_coupons,
        "get_recent_loyalty_activity": get_recent_loyalty_activity,
        "check_redemption_eligibility": check_redemption_eligibility,
        "check_missing_points": check_missing_points,
        "get_last_transaction": get_last_transaction,
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = tool_map[tool_name](**args)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Main chat function ────────────────────────────────────────
def chat(user_message: str, history: list) -> str:
    """
    Takes a user message and conversation history.
    Returns the assistant's response as a string.
    """

    # Guardrail 1 — privacy check
    if is_privacy_violation(user_message):
        resp = "I can only help with loyalty information linked to your own account."
        logging.info(f"Query: {user_message} | Tools Called: [] | Response: {resp}")
        return resp

    # Guardrail 2 — off-topic check
    if is_off_topic(user_message):
        resp = "I can help you with loyalty points, coupons, rewards, and purchase-related questions only."
        logging.info(f"Query: {user_message} | Tools Called: [] | Response: {resp}")
        return resp

    # Guardrail 3 — sanitize input
    clean_message = sanitize_input(user_message)

    # Build message history for the LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": clean_message})

    # First LLM call — may return a tool call
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=1024
    )

    response_message = response.choices[0].message

    # If LLM wants to call a tool
    if response_message.tool_calls:
        # Add assistant's tool call message to history
        messages.append(response_message)

        tools_called = []
        # Execute each tool call
        for tool_call in response_message.tool_calls:
            tools_called.append(tool_call.function.name)
            tool_result = dispatch_tool(tool_call.function.name)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": tool_result
            })

        # Second LLM call — generate final natural language response
        final_response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=1024
        )
        resp = final_response.choices[0].message.content
        logging.info(f"Query: {user_message} | Tools Called: {tools_called} | Response: {resp}")
        return resp

    # If no tool call needed
    resp = response_message.content
    logging.info(f"Query: {user_message} | Tools Called: [] | Response: {resp}")
    return resp