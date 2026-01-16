"""LLM factory functions for multi-provider support."""

import logging
from langchain_openai import ChatOpenAI
from medicare_agent.config import settings

logger = logging.getLogger(__name__)


def get_llm(streaming: bool = False, temperature: float = 0) -> ChatOpenAI:
    """Get LLM instance based on RUN_MODEL setting.

    Args:
        streaming: Whether to enable streaming
        temperature: Temperature for generation

    Returns:
        ChatOpenAI instance configured for the selected provider
    """
    provider = settings.run_model

    if provider == "openai":
        logger.info(f"Using OpenAI model: {settings.openai_model}")
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
            streaming=streaming
        )

    elif provider == "vllm":
        logger.info(f"Using vLLM model: {settings.vllm_model} at {settings.vllm_base_url}")
        return ChatOpenAI(
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            model=settings.vllm_model,
            temperature=temperature,
            streaming=streaming
        )

    elif provider == "openrouter":
        logger.info(f"Using OpenRouter model: {settings.openrouter_model}")
        return ChatOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            temperature=temperature,
            streaming=streaming
        )

    else:
        raise ValueError(f"Unsupported RUN_MODEL: {provider}. Use 'openai', 'openrouter', or 'vllm'")


def get_fast_llm(temperature: float = 0) -> ChatOpenAI:
    """Get fast LLM for classification and query expansion.

    Uses gpt-3.5-turbo for OpenAI, or falls back to main model for other providers.

    Args:
        temperature: Temperature for generation

    Returns:
        ChatOpenAI instance for fast operations
    """
    provider = settings.run_model

    if provider == "openai" and settings.use_fast_model_for_classification:
        logger.info(f"Using fast OpenAI model: {settings.fast_model}")
        return ChatOpenAI(
            model=settings.fast_model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key
        )
    else:
        # For vLLM and OpenRouter, use the main model
        return get_llm(streaming=False, temperature=temperature)


def get_current_provider() -> str:
    """Get the current LLM provider name.

    Returns:
        Provider name: 'openai', 'openrouter', or 'vllm'
    """
    return settings.run_model


def get_current_model_name() -> str:
    """Get the current model name based on provider.

    Returns:
        Model name string
    """
    provider = settings.run_model

    if provider == "openai":
        return settings.openai_model
    elif provider == "vllm":
        return settings.vllm_model
    elif provider == "openrouter":
        return settings.openrouter_model
    else:
        return "unknown"
