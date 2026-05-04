import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

CUSTOMER_ID = int(os.getenv("CUSTOMER_ID", 101))
MERCHANT_ID = int(os.getenv("MERCHANT_ID", 1))