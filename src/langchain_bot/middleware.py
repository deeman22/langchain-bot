from datetime import datetime

from langchain.agents.middleware import (
    wrap_model_call,
    wrap_tool_call,
)


def _ts():
    """Return a formatted timestamp."""
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _preview(value, max_length=120):
    """Create a short one-line preview."""
    if value is None:
        return ""

    text = str(value).replace("\n", " ")

    if len(text) > max_length:
        return text[:max_length] + "..."

    return text


@wrap_model_call
def model_logging_middleware(request, handler):
    """
    Log model requests and responses.
    """

    messages = request.state.get(
        "messages",
        []
    )

    print(
        f"[{_ts()}] MODEL REQUEST | "
        f"messages={len(messages)}"
    )

    if messages:

        last_message = messages[-1]

        print(
            f"[{_ts()}] MODEL REQUEST | "
            f"last_message="
            f"{_preview(last_message.content)}"
        )

    try:

        response = handler(request)

        result_messages = getattr(
            response,
            "result",
            []
        )

        if result_messages:

            last_response = result_messages[-1]

            print(
                f"[{_ts()}] MODEL RESPONSE | "
                f"{_preview(last_response.content)}"
            )

            tool_calls = getattr(
                last_response,
                "tool_calls",
                []
            )

            if tool_calls:

                print(
                    f"[{_ts()}] MODEL RESPONSE | "
                    f"tool_calls={tool_calls}"
                )

        else:

            print(
                f"[{_ts()}] MODEL RESPONSE | "
                "no messages returned"
            )

        return response

    except Exception as e:

        print(
            f"[{_ts()}] MODEL ERROR | "
            f"{type(e).__name__}: {e}"
        )

        raise


@wrap_tool_call
def tool_logging_middleware(request, handler):
    """
    Log tool calls and their results.
    """

    tool_call = getattr(
        request,
        "tool_call",
        {}
    )

    print(
        f"[{_ts()}] TOOL | "
        f"name={tool_call.get('name')} | "
        f"args={tool_call.get('args')}"
    )

    try:

        response = handler(request)

        print(
            f"[{_ts()}] TOOL SUCCESS | "
            f"{_preview(response.content)}"
        )

        return response

    except Exception as e:

        print(
            f"[{_ts()}] TOOL ERROR | "
            f"{type(e).__name__}: {e}"
        )

        raise


def get_logging_middleware():
    """
    Return all logging middleware.
    """

    return [
        model_logging_middleware,
        tool_logging_middleware,
    ]


__all__ = [
    "get_logging_middleware",
]