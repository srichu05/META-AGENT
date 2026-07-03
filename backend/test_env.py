from dotenv import load_dotenv
import os

load_dotenv()

print("Testing .env file loading...")
print(f"GROQ_API_KEY: {os.getenv('GROQ_API_KEY')[:20]}..." if os.getenv('GROQ_API_KEY') else "NOT FOUND")
print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')[:20]}..." if os.getenv('OPENAI_API_KEY') else "NOT FOUND")
print(f"COHERE_API_KEY: {os.getenv('COHERE_API_KEY')[:20]}..." if os.getenv('COHERE_API_KEY') else "NOT FOUND")
print(f"HUGGING_FACE_API_KEY: {os.getenv('HUGGING_FACE_API_KEY')[:20]}..." if os.getenv('HUGGING_FACE_API_KEY') else "NOT FOUND")
