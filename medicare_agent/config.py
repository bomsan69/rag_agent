"""Configuration management for Medicare AI Chatbot."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-large",
        env="OPENAI_EMBEDDING_MODEL"
    )

    # Tavily Search Configuration
    tavily_api_key: str | None = Field(default=None, env="TAVILY_API_KEY")
    enable_web_search: bool = Field(default=True, env="ENABLE_WEB_SEARCH")
    web_search_max_results: int = Field(default=5, env="WEB_SEARCH_MAX_RESULTS")

    # Application Configuration
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Document Configuration
    medicare_doc_version: str = Field(default="2026", env="MEDICARE_DOC_VERSION")
    medicare_pdf_path: str = Field(
        default="./docs/medicare_manual.pdf",
        env="MEDICARE_PDF_PATH"
    )

    # Index Configuration
    index_path: str = Field(default="./data/indexes", env="INDEX_PATH")
    chunk_size: int = Field(default=600, env="CHUNK_SIZE")  # Reduced for better precision
    chunk_overlap: int = Field(default=300, env="CHUNK_OVERLAP")  # Increased for context continuity
    top_k_retrieval: int = Field(default=20, env="TOP_K_RETRIEVAL")  # Increased for better recall
    top_k_rerank: int = Field(default=8, env="TOP_K_RERANK")  # Increased for more evidence

    # Performance Optimization
    enable_query_expansion: bool = Field(default=True, env="ENABLE_QUERY_EXPANSION")  # Enabled for better retrieval
    enable_intent_classification: bool = Field(default=True, env="ENABLE_INTENT_CLASSIFICATION")
    enable_verification: bool = Field(default=True, env="ENABLE_VERIFICATION")
    skip_verification_on_stream: bool = Field(default=True, env="SKIP_VERIFICATION_ON_STREAM")
    use_fast_model_for_classification: bool = Field(default=True, env="USE_FAST_MODEL_FOR_CLASSIFICATION")
    fast_model: str = Field(default="gpt-3.5-turbo", env="FAST_MODEL")

    # Retrieval weights for hybrid search
    bm25_weight: float = Field(default=0.3, env="BM25_WEIGHT")  # Keyword search weight
    vector_weight: float = Field(default=0.7, env="VECTOR_WEIGHT")  # Semantic search weight

    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
