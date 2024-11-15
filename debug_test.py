from ghost_blog import *


token = TELEGRAM_BOT_TOKEN
chat_id = OWNER_CHAT_ID
user_prompt = "no cloak of invisibility"
response_text = ollama_gpt_chat_remote(user_prompt)
print(response_text)