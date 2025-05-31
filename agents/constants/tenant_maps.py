# Temporary tenant maps - will be removed for single tenant setup
import os

# API key maps - will be replaced with direct env vars
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
VERTEX_AI_SERVICE_ACCOUNT = os.getenv("VERTEX_AI_SERVICE_ACCOUNT")

OPENAI_MODEL = "openai/gpt-4.1-mini-2025-04-14"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
