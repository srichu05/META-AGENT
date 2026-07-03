from utils.api_client import APIClient

if __name__ == "__main__":
    c = APIClient()
    prompt = "A bakery sells cupcakes for $3 each. If Sarah buys 8 cupcakes and pays with a $50 bill, how much change does she receive?"
    result = c.call_best_available_api(prompt, max_tokens=256, temperature=0.1)
    print("\n--- Result ---")
    print(result)
