"""
Text model catalog and availability gating.

Single source of truth for which text LLMs the frontend dropdown can show
and which provider routes each model. Availability is gated by the API
keys currently present in the environment so the UI never offers a model
we can't actually call.
"""

import os


OPENROUTER_TEXT_MODELS = [
    {
        "value": "deepseek/deepseek-v4-flash",
        "label": "DeepSeek V4 Flash",
        "provider": "openrouter",
    },
]

# Use Bedrock inference profile IDs (us.*), not raw foundation model IDs.
# On-demand Converse rejects bare anthropic.* IDs for newer Claude models.
BEDROCK_TEXT_MODELS = [
    {
        "value": "us.anthropic.claude-sonnet-4-6",
        "label": "Claude Sonnet 4.6",
        "provider": "bedrock",
    },
    {
        "value": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "label": "Claude Haiku 4.5",
        "provider": "bedrock",
    },
    {
        "value": "deepseek.v3.2",
        "label": "DeepSeek V3.2",
        "provider": "bedrock",
    },
]

_BEDROCK_MODEL_IDS = {m["value"] for m in BEDROCK_TEXT_MODELS}
_OPENROUTER_MODEL_IDS = {m["value"] for m in OPENROUTER_TEXT_MODELS}


def is_bedrock_model(model_id):
    return model_id in _BEDROCK_MODEL_IDS


def is_openrouter_model(model_id):
    return model_id in _OPENROUTER_MODEL_IDS


def get_available_text_models():
    """Return the list of text models the user can actually call right now,
    based on which provider API keys are set in the environment."""
    available = []
    if os.getenv("openrouter_api_key"):
        available.extend(OPENROUTER_TEXT_MODELS)
    if os.getenv("bedrock_api_key"):
        available.extend(BEDROCK_TEXT_MODELS)
    return available
