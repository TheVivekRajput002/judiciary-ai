from fastapi import HTTPException, status


class LexiAIError(Exception):
    """Base exception for LexiAI."""
    pass


class DocumentNotFoundError(LexiAIError):
    pass


class SessionNotFoundError(LexiAIError):
    pass


class IngestionError(LexiAIError):
    pass


class RetrievalError(LexiAIError):
    pass


class PipelineError(LexiAIError):
    """Raised when a LangGraph node fails."""
    def __init__(self, stage: str, message: str):
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


class OutOfDomainError(LexiAIError):
    """Raised when query is outside the legal domain."""
    pass


class InsufficientEvidenceError(LexiAIError):
    pass


def http_not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def http_bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def http_server_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
