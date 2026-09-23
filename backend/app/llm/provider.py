"""Provider-agnostic Groq chat model factory."""
from langchain_groq import ChatGroq
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_model: ChatGroq | None = None

def get_chat_model(temperature: float = 0.1, max_tokens: int | None = None) -> ChatGroq:
    """Return a configured ChatGroq instance."""
    settings = get_settings()
    model_name = settings.groq_model
    return ChatGroq(
        model=model_name,
        api_key=settings.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=2,
    )
