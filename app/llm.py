import os
import time

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def call_llm(
    system_prompt: str,
    user_message: str,
):
    """
    Call the LLM with:
    - timeout
    - limited retry
    - usage information
    """

    base_url = os.getenv("LLM_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not base_url:
        raise ValueError(
            "LLM_BASE_URL is missing from .env"
        )

    if not api_key:
        raise ValueError(
            "LLM_API_KEY is missing from .env"
        )

    if not model:
        raise ValueError(
            "LLM_MODEL is missing from .env"
        )

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    timeout = float(
        os.getenv("LLM_TIMEOUT_SECONDS", "10")
    )

    max_retries = int(
        os.getenv("LLM_MAX_RETRIES", "2")
    )

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )

    # -----------------------------------------------------
    # RETRY LOOP
    # -----------------------------------------------------

    last_error = None

    for attempt in range(max_retries + 1):

        try:

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
                temperature=0,
            )

            # -------------------------------------------------
            # EXTRACT RESPONSE
            # -------------------------------------------------

            content = response.choices[0].message.content

            if not content:
                raise ValueError(
                    "LLM returned an empty response."
                )

            # -------------------------------------------------
            # EXTRACT USAGE
            # -------------------------------------------------

            usage = getattr(
                response,
                "usage",
                None,
            )

            usage_info = {
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
            }

            if usage:

                usage_info = {
                    "prompt_tokens": getattr(
                        usage,
                        "prompt_tokens",
                        None,
                    ),
                    "completion_tokens": getattr(
                        usage,
                        "completion_tokens",
                        None,
                    ),
                    "total_tokens": getattr(
                        usage,
                        "total_tokens",
                        None,
                    ),
                }

            # Return both model output and usage.
            return {
                "content": content,
                "usage": usage_info,
            }

        except Exception as error:

            last_error = error

            # No more attempts.
            if attempt >= max_retries:
                break

            # Small delay before retry.
            time.sleep(1)

    raise RuntimeError(
        "LLM request failed after "
        f"{max_retries + 1} attempts: "
        f"{last_error}"
    )