from fastapi import APIRouter, HTTPException
import litellm
from litellm.types.utils import LlmProviders

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/providers")
async def list_providers():
    """
    List all available model providers supported by LiteLLM.

    Returns:
        List of unique provider names extracted from available models
    """
    try:
        # Extract unique providers from model names
        providers = set()
        for provider in litellm.provider_list:
            # Most models are formatted as "provider/model-name"
            providers.add(provider.value)
        return {
            "total_providers": len(providers),
            "providers": list(providers)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching providers: {str(e)}"
        )


@router.get("/providers/{provider}")
async def list_models_by_provider(provider: str):
    """
    List all available models for a specific provider.

    Args:
        provider: The provider name (e.g., 'openai', 'anthropic', 'cerebras')

    Returns:
        List of models available for the specified provider
    """
    try:
        # Filter models by provider
        provider = LlmProviders(provider.lower())
        filtered_models = litellm.models_by_provider[provider.value]

        if not filtered_models:
            raise HTTPException(
                status_code=404,
                detail=f"No models found for provider: {provider}"
            )

        return {
            "provider": provider,
            "total_models": len(filtered_models),
            "models": sorted(filtered_models)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching models for provider: {str(e)}"
        )
