"""Main entry point for Medicare AI Chatbot."""

import uvicorn
from medicare_agent.config import settings


def main():
    """Run the FastAPI application."""
    print("=" * 80)
    print("Medicare AI Chatbot")
    print("=" * 80)
    print(f"Environment: {settings.app_env}")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"Docs: http://{settings.api_host}:{settings.api_port}/docs")
    print("=" * 80)

    uvicorn.run(
        "medicare_agent.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
