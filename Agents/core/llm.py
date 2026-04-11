from langchain_mistralai import ChatMistralAI
from Agents.core.config import MISTRAL_API_KEY

llm = ChatMistralAI(
    model = "mistral-small-latest",
    mistral_api_key = MISTRAL_API_KEY,
)