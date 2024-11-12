from helping_page import *

# Replace with your bot's API token
TELEGRAM_BOT_TOKEN_OLLAMA = os.getenv("TELEGRAM_BOT_TOKEN_OLLAMA")
OLLAMA_BOT_HANDLE = '@ollama_gpt_bot'

PA_GROUP = '-608925807'
OLLAMA_GROUP_CHAT = '-4583101458'
OWNERS_BACKUP_GROUP = '-689754888'

ALLOWED_CHAT_IDS = [OWNERS_BACKUP_GROUP, PA_GROUP, OLLAMA_GROUP_CHAT] + WHITLIST_CHAT_ID

NO_MARKDOWN_PROMPT = "\n\nPlease avoid using markdown in your message. Just output plain text."


# Function to handle incoming Telegram updates with debug prints
async def handle_updates(token=TELEGRAM_BOT_TOKEN_OLLAMA):
    last_update_id = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"
            response = requests.get(url).json()

            for update in response.get("result", []):
                # print(json.dumps(update, indent=2))

                last_update_id = update["update_id"]
                message = update.get("message", {})
                chat_id = message["chat"]["id"]
                chat_id = str(chat_id)

                if chat_id not in ALLOWED_CHAT_IDS: 
                    send_message_basic(chat_id, "Sorry, Your are not in the whitelist.", token)
                    continue

                response_text = ''

                user_prompt = str(message.get("text", ""))

                if not user_prompt: 
                    if message.get('new_chat_participant'):
                        username = message["new_chat_participant"].get("username", "")
                        if not username: username = message["new_chat_participant"].get("first_name", "")
                        username = f"@{username}"
                        response_text = f"Welcome {username} to the chat! Now you can ask me anything, but don't forget {OLLAMA_BOT_HANDLE}"
                        send_message_basic(chat_id, response_text, token)
                        continue
                
                if 'reply_to_message' in message:
                    quoted_msg = message['reply_to_message'].get('text')  
                    if quoted_msg: user_prompt = f"{user_prompt}\n\n----------------\n\nQuoted previous message:\n\n{quoted_msg}"


                username = message["from"].get("username", "")
                if not username: username = message["from"].get("first_name", "")
                username = f"@{username}"

                chat_type = message["chat"].get("type", "none")
                if chat_type == 'group':
                    if OLLAMA_BOT_HANDLE in user_prompt: user_prompt = user_prompt.replace(OLLAMA_BOT_HANDLE, '').strip()
                    else: continue
                
                user_prompt += NO_MARKDOWN_PROMPT
                # Call ollama_gpt_chat_basic and log the input/output
                response_text = ollama_gpt_chat_basic(user_prompt, system_prompt='', model="llama3.2")
                if response_text: 
                    if chat_type == 'group': response_text = f"{username} {response_text}"
                    send_message_basic(chat_id, response_text, token)

        except Exception as e: print(f"Error occurred: {e}")
        await asyncio.sleep(1)  # Avoid flooding Telegram's API


# Run the bot
if __name__ == "__main__":
    print("Ollama Bot is running...")
    asyncio.run(handle_updates())
