"""Abstract LLM provider with OpenAI, Ollama, and Gemini implementations."""

from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str: ...


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(api_key=api_key, model=model, temperature=0.3)

    def generate(self, prompt: str, **kwargs) -> str:
        return self.llm.invoke(prompt).content


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.llm = ChatOllama(base_url=base_url, model=model, temperature=0.3)

    def generate(self, prompt: str, **kwargs) -> str:
        return self.llm.invoke(prompt).content


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-lite"):
        self.llm = ChatGoogleGenerativeAI(google_api_key=api_key, model=model, temperature=0.3)

    def generate(self, prompt: str, **kwargs) -> str:
        return self.llm.invoke(prompt).content


class LLMFactory:
    @staticmethod
    def create(provider: str = "openai", **kwargs) -> LLMProvider:
        if provider == "openai":
            return OpenAIProvider(api_key=kwargs.get("api_key", ""))
        elif provider == "ollama":
            return OllamaProvider(base_url=kwargs.get("base_url", "http://localhost:11434"))
        elif provider == "gemini":
            return GeminiProvider(api_key=kwargs.get("api_key", ""), model=kwargs.get("model", "gemini-2.0-flash-lite"))
        raise ValueError(f"Unknown provider: {provider}")
