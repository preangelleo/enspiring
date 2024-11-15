from ghost_blog import *


token = TELEGRAM_BOT_TOKEN
chat_id = OWNER_CHAT_ID
user_parameters = user_parameters_realtime(chat_id, engine)
query = "Today's breaking news."
formatted_response = get_news_results(query)
system_prompt = SYSTEM_PROMPT_SEARCH_RESULTS_POLISH.replace('_user_prompt_placeholder_', query)
formatted_response = openai_gpt_chat(formatted_response, system_prompt, chat_id, ASSISTANT_MAIN_MODEL, user_parameters, token)
# formatted_response = ollama_gpt_chat_basic(formatted_response, system_prompt, model = "llama3.2")
print(formatted_response)