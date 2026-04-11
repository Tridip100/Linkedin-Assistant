import os 
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
APPOLO_API_KEY = os.getenv("APPOLO_API_KEY")
ABSTRACT_API_KEY = os.getenv("ABSTRACT_API_KEY")