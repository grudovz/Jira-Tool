"""
LLM integration for story analysis.
Supports Azure OpenAI (enterprise, recommended for company data) and Ollama (local, offline).

Configure via .env:
  AI_PROVIDER=azure   → set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
  AI_PROVIDER=ollama  → set OLLAMA_BASE_URL (default http://localhost:11434/v1), OLLAMA_MODEL

The app works without any AI configuration — is_available() returns False and the UI
disables the Analyse button rather than crashing.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

_AI_PROVIDER = os.getenv("AI_PROVIDER", "azure").lower()

_SYSTEM_PROMPT = """You are a senior software engineer and business analyst reviewing JIRA user stories.
Analyse the provided user story and give structured feedback on:
1. Clarity — is the story clear and unambiguous?
2. Completeness — are acceptance criteria present and testable?
3. Scope — is it appropriately sized for a single sprint?
4. INVEST — does it satisfy Independent, Negotiable, Valuable, Estimable, Small, Testable?
5. Suggestions — specific improvements to wording or structure.

Be concise. Flag issues directly. Do not add praise unless warranted."""


def is_available() -> bool:
    """Return True if the configured AI provider has the required credentials in the environment."""
    if _AI_PROVIDER == "ollama":
        return True  # Ollama is local; connectivity is checked at call time, not here
    # Azure requires both endpoint and key
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))


def _get_client():
    """Return (client, model_name) for the configured provider."""
    from openai import AzureOpenAI, OpenAI

    if _AI_PROVIDER == "ollama":
        client = OpenAI(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key="ollama",
        )
        return client, os.getenv("OLLAMA_MODEL", "phi4")

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in .env")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-02-01",
    )
    return client, os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")


def analyse_story(title: str, description: str, acceptance_criteria: Optional[str] = None) -> str:
    """
    Send a story to the LLM for quality analysis.
    Returns the analysis as a plain text string.
    Raises RuntimeError if the provider is not configured.
    """
    if not is_available():
        raise RuntimeError(
            "AI provider is not configured. Set AI_PROVIDER and related keys in .env."
        )

    story_text = f"Title: {title}\n\nDescription:\n{description or '(none provided)'}"
    if acceptance_criteria:
        story_text += f"\n\nAcceptance Criteria:\n{acceptance_criteria}"

    client, model = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": story_text},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content or ""
