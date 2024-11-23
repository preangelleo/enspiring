from helping_page import *

ASSISTANT_TOOLS = ['code_interpreter', 'file_search', 'function']
DEFAULT_PROMPT_DOCUMENT = "Please summarize the key points of the DOCUMENT."
DEFAULT_PROMPT_HTML = "First, answers the question, what's the title of this article in the latest given file_id. Then please summarize the content in English in one sentence, what's the essence the author trying to deliver. Lastly, summarize with the key writing style of the content."
DEFAULT_CONTENT_MESSAGE_CREATION = "I have uploaded the DOCUMENT for you. I want you to help me to dive into the content of the DOCUMENT."

def commands_correction(prompt, chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, user_parameters = {}):
    response = openai_gpt_chat(SYSTEM_PROMPT_COMMAND_CORRECTION, prompt, chat_id, ASSISTANT_MAIN_MODEL, user_parameters, token)
    if response.startswith('/'): return {'response': response, 'action': 'run_command', 'prefix': '/'}
    elif response  == 'no': return {'response': prompt, 'action': 'ask_gpt'}
    return {'response': response, 'action': 'send_response'}


available_functions = {
    "Vocabulary_Dictionary": check_word_in_vocabulary,
    "Post_Youtube_as_a_Blog_Post": youtube_id_download,
    "Audio_Generation": function_call_audio_generation,
    "Answer_Questions_about_the_Platform": platform_questions_and_answers_helper,
    "Calculate_with_Wolframalpha": calculate_with_wolframalpha,
    "Commands_Correction": commands_correction
} 

functions_with_audio_output = ['Vocabulary_Dictionary']
functions_with_dict_output = ['Post_Youtube_as_a_Blog_Post', 'Commands_Correction']

FUNCTIONS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "Vocabulary_Dictionary",
            "description": "Dictionary for global English students, input only take English words or expressions, do not put any other language as prompt. Output will be the [pronunciation], synonyms, and one example sentence of the word or expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user's input words or expressions to check in the dictionary"},
                },
                "required": ["prompt"]
            }
        }
    }, {
        "type": "function",
        "function": {
            "name": "Commands_Correction",
            "description": "This function will correct the user's incorrect commands to the right one. If the user's intent is clear from the prompt and there's indeed a command for this purpose.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user's input prompt which looks like a command for the bot but the reason you see this message is that the command is not correct or it's not a command."},
                },
                "required": ["prompt"]
            }
        }
    }, 
    {
        "type": "function",
        "function": {
            "name": "Post_Youtube_as_a_Blog_Post",
            "description": "Take a youtube video ID as prompt, then this function with check the database and send back the transcript blog post if it exists, if not, then ask the user to confirm the video link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The youtube video ID to check, normally it's a 11 digits string. Format looks like this: 'skX9-vN81zk'."}
                },
                "required": ["prompt"]
            }
        }
    }, {
        "type": "function",
        "function": {
            "name": "Audio_Generation",
            "description": "Generate audio with a female's voice from the user's input text (prompt).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user's input prompt to generate audio."}
                },
                "required": ["prompt"]
            }
        }
    }, {
        "type": "function",
        "function": {
            "name": "Answer_Questions_about_the_Platform",
            "description": HELP_SUMMARY,
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user's input prompt to ask questions."}
                },
                "required": ["prompt"]
            }
        }
    }, {
        "type": "function",
        "function": {
            "name": "Calculate_with_Wolframalpha",
            "description": "Takes a user prompt as input and calls the Wolfram|Alpha Short Answers API to get a quick answer",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The user's input prompt to calculate with Wolfram|Alpha."}
                },
                "required": ["prompt"]
            }
        }
    },
    ]


def create_assistant(chat_id, assistant_name, model, instructions = "None", tools_type = '', engine = engine, user_parameters = {}, token = TELEGRAM_BOT_TOKEN):
    client = OpenAI(api_key=user_parameters.get('openai_api_key'))

    tools = []
    if tools_type:
        if tools_type not in ASSISTANT_TOOLS: return send_message(chat_id, f"Invalid tools_type: {tools_type}. Please choose from {ASSISTANT_TOOLS}", token)
        if tools_type == 'function': tools = FUNCTIONS_TOOLS
        else: tools = [{"type": tools_type}]

    try: assistant = client.beta.assistants.create(name=assistant_name, instructions=instructions, model=model, tools=tools)
    except Exception as e: return remove_openai_api_key_for_chat_id(chat_id, engine, token, e)

    return store_assistant_id(chat_id, assistant_name, assistant.id, model, instructions, tools_type, engine)


def openai_gpt_function(prompt: str, chat_id: str, tools = FUNCTIONS_TOOLS, model = ASSISTANT_DOCUMENT_MODEL, engine = engine, token = TELEGRAM_BOT_TOKEN, user_parameters = {}):
    global USER_MESSAGE_HISTORY
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    ai_response = ""
    function_name = ""
    ai_prompt = prompt

    openai_api_key = user_parameters.get('openai_api_key') or OPENAI_API_KEY
    client = OpenAI(api_key=openai_api_key)

    if chat_id not in USER_MESSAGE_HISTORY: USER_MESSAGE_HISTORY[chat_id] = []

    new_message_dict = {"role": "user", "content": prompt}

    user_history = USER_MESSAGE_HISTORY[chat_id]
    user_history.append(new_message_dict)

    if len(user_history) >= 10: user_history = user_history[2:]

    if prompt.lower() in ['ice breaker', 'ice_breaker', '/ice breaker', '/ice_breaker']: 
        final_messages = [{"role": "system", "content": SYSTEM_PROMPT_ICE_BREAKER}] + user_history
        response = client.chat.completions.create(model = model, messages = final_messages)
        ai_response = response.choices[0].message.content

    elif prompt.startswith('User just sent '): 
        MESSAGE_SYSTEM_PROMPT = [{"role": "system", "content": SYSTEM_PROMPT_STICKER}]

        # 将系统消息和用户的历史记录组合
        final_messages = MESSAGE_SYSTEM_PROMPT + user_history

        response = client.chat.completions.create(
            model=model,
            messages=final_messages,
        )
        ai_response = response.choices[0].message.content

    else:
        MESSAGE_SYSTEM_PROMPT = [{"role": "system", "content": SYSTEM_PROMPT_FUNCTION_CALL_ASSISTANT}]
        
        # 将系统消息和用户的历史记录组合
        final_messages = MESSAGE_SYSTEM_PROMPT + user_history

        response = client.chat.completions.create(model=model, messages=final_messages, tools=tools,)
        if response.choices[0].message.content: callback_icebreaker_audio(chat_id, response.choices[0].message.content, token, engine, user_parameters)

        # 检查 tool_calls
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name

            arguments = json.loads(tool_call.function.arguments)
            ai_prompt = arguments.get("prompt")

            print(f"openai_gpt_function() call >> {function_name}({ai_prompt[:50]}...)")

            # 调用指定的函数
            function_to_call = available_functions.get(function_name)
            if function_to_call: ai_response = function_to_call(ai_prompt, chat_id, engine, token, user_parameters)
            else: send_debug_to_laogege(f"openai_gpt_function() failed to find function (wrong name?): {function_name}")

    if ai_response and ai_response != "DONE":
        if function_name in functions_with_audio_output: pass
        elif function_name in functions_with_dict_output:
            if function_name == 'Commands_Correction': return ai_response
            if ai_response.get('URL'):
                url = ai_response.get('URL')
                words_list = ai_response.get('words_list') or ''
                if words_list: 
                    words_list = words_list.split(',')
                    words_list = [f"{i}. /{word.strip().replace(' ', '_')}" for i, word in enumerate(words_list)]
                    words_list = '\n'.join(words_list)
                    words_list = f"\n\nWords list from this youtube:\n\n{words_list}\n\n{url}"
                    ai_response = words_list
                else: ai_response = url
            else: ai_response = ai_response.get('Reason')
            send_message(chat_id, ai_response, token)
        elif prompt.lower() in ['ice breaker', 'ice_breaker', '/ice breaker', '/ice_breaker']: callback_icebreaker_audio(chat_id, ai_response, token, engine, user_parameters)
        else:
            output_dir = os.path.join(working_dir, chat_id)
            overlength_file_path = is_overlength(ai_response, output_dir)
            if overlength_file_path: send_document_from_file(chat_id, overlength_file_path, "The text is too long, I have saved it as a txt file for you.", token)

            elif '*' in ai_response or '[' in ai_response: callback_markdown_audio(chat_id, ai_response, token, engine, is_session=False, user_parameters=user_parameters)
            elif len(ai_response) > 100: callback_text_audio(chat_id, ai_response, token, user_parameters=user_parameters)
            else: send_message(chat_id, ai_response, token)

        # Extract the token usage information
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        model_price_input = OPENAI_MODEL_PRICING.get(model, {}).get('input', 0)
        model_price_output = OPENAI_MODEL_PRICING.get(model, {}).get('output', 0)

        cost_input = model_price_input * prompt_tokens
        cost_output = model_price_output * completion_tokens
        cost_total = cost_input + cost_output

        update_chat_id_monthly_consumption(chat_id, cost_total, engine)

        # 将助手的回复加入到用户的聊天历史中
        message_with_response_dict = {"role": "assistant", "content": ai_response}
        user_history.append(message_with_response_dict)
        # 更新用户的聊天历史
        USER_MESSAGE_HISTORY[chat_id] = user_history

    return 
    

def session_function_call(chat_id, msg_text, session_name, token, engine, user_parameters = {}):
    return 


# Store assistant_id in the database for reuse
def store_assistant_id(chat_id, assistant_name, assistant_id, model, instructions = "None", tools_type = None, engine = engine):
    # Ensure no null or empty values for critical fields
    assert chat_id, "chat_id cannot be empty"
    assert assistant_name, "assistant_name cannot be empty"
    assert assistant_id, "assistant_id cannot be empty"
    assert model, "model cannot be empty"
    
    with engine.begin() as conn: 
        query = text(
            "INSERT INTO ai_assistants (assistant_name, assistant_instructions, assistant_model, assistant_tool, assistant_id, chat_id) "
            "VALUES (:assistant_name, :instructions, :model, :tools_type, :assistant_id, :chat_id) "
            "ON DUPLICATE KEY UPDATE assistant_id = :assistant_id"
        )
        parameters = {"assistant_name": assistant_name, "instructions": instructions, "model": model, "assistant_id": assistant_id, "chat_id": chat_id, "tools_type": tools_type}
        conn.execute(query, parameters)

    return assistant_id


def store_thread_id(chat_id, thread_id, engine = engine, is_creator = False):
    if is_creator: 
        with engine.begin() as conn: conn.execute(text("UPDATE chat_id_parameters SET session_thread_id_creator = :thread_id WHERE chat_id = :chat_id"), {"thread_id": thread_id, "chat_id": chat_id})
    else:
        with engine.begin() as conn: conn.execute(text("UPDATE chat_id_parameters SET session_thread_id = :thread_id WHERE chat_id = :chat_id"), {"thread_id": thread_id, "chat_id": chat_id})
    return thread_id


def create_thread_id(chat_id, engine = engine, user_parameters = {}, is_creator = False):
    openai_api_key = user_parameters.get('openai_api_key') or OPENAI_API_KEY
    client = OpenAI(api_key=openai_api_key)
    thread = client.beta.threads.create()
    thread_id = thread.id
    return store_thread_id(chat_id, thread_id, engine, is_creator)


# User must have their own openai_api_key to create an assistant for their own use
def get_or_create_assistant_id(chat_id, assistant_name, engine=engine, user_parameters = {}, token = TELEGRAM_BOT_TOKEN):
    assistant_id = ''
    openai_api_key = user_parameters.get('openai_api_key', '')
    if not openai_api_key: chat_id = OWNER_CHAT_ID

    def get_assistant_id(chat_id, assistant_name):
        with engine.connect() as conn:
            assistant_result = conn.execute(text("SELECT assistant_id FROM ai_assistants WHERE chat_id = :chat_id AND assistant_name = :assistant_name"), {"chat_id": chat_id, "assistant_name": assistant_name}).fetchone()
            return assistant_result[0] if assistant_result else ''
    
    assistant_id = get_assistant_id(chat_id, assistant_name)

    # If no assistant_id, try to find the full assistant data or create a new one
    if not assistant_id and openai_api_key:
        if assistant_name == 'session_code_interpreter': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_CODE_INTERPRETER, 'code_interpreter' , engine, user_parameters, token)
        if assistant_name == 'session_chat_casual': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_CASUAL_CHAT, '' , engine, user_parameters, token)
        if assistant_name == 'session_assistant_email': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_EMAIL_ASSISTANT_IN_BOT, '' , engine, user_parameters, token)
        if assistant_name == 'session_help': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_HELP_SESSION, 'file_search' , engine, user_parameters, token)
        if assistant_name == 'session_query_doc': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_QUERY_DOC_SESSION, 'file_search' , engine, user_parameters, token)
        if assistant_name == 'session_creator': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_CONTENT_CREATOR, 'file_search' , engine, user_parameters, token)
        if assistant_name == 'session_translator': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_CONTENT_TRANSLATOR, 'file_search' , engine, user_parameters, token)
        if assistant_name == 'assistant_email': return create_assistant(chat_id, assistant_name, ASSISTANT_MAIN_MODEL, SYSTEM_PROMPT_EMAIL_ASSISTANT, '' , engine, user_parameters, token)

    return assistant_id


# Upload DOCUMENT to the Assistant Thread and notify the user
def handle_doc_upload(chat_id, pdf_file_path, engine = engine, user_parameters = {}):
    openai_api_key = user_parameters.get('openai_api_key') or OPENAI_API_KEY
    client = OpenAI(api_key=openai_api_key)

    try:
        privious_doc_id = user_parameters.get('session_document_id', '')

        doc_id = client.files.create(file=open(pdf_file_path, "rb"), purpose="assistants").id

        update_session_document_name(chat_id, os.path.basename(pdf_file_path), doc_id, engine)

        if privious_doc_id: client.files.delete(file_id=privious_doc_id)
        return doc_id

    except Exception as e: 
        send_message(OWNER_CHAT_ID, f"Failed to upload the document. Error: {e}", os.getenv("TELEGRAM_BOT_TOKEN_TEST"))
        return False


# Run the Assistant for the user's query with status check
def run_assistant(chat_id, query, session_name, engine = engine, model = ASSISTANT_DOCUMENT_MODEL, user_parameters = {}, token = TELEGRAM_BOT_TOKEN, from_email = False):
    if session_name == 'session_code_interpreter': tools_type = 'code_interpreter'
    elif session_name in ['session_query_doc', 'session_help', 'session_creator', 'session_translator']: tools_type = 'file_search'
    elif session_name in ['session_generate_content', 'session_assistant_general']: tools_type = 'function'
    else: tools_type = ''

    if session_name in ['session_creator', 'session_translator']: session_thread_id = user_parameters.get('session_thread_id_creator') or create_thread_id(chat_id, engine, user_parameters, is_creator=True)
    else: session_thread_id = user_parameters.get('session_thread_id') or create_thread_id(chat_id, engine, user_parameters)

    if not session_thread_id: return f"Failed to get or create a thread for the `{session_name}` assistant."

    assistant_id = get_or_create_assistant_id(chat_id, session_name, engine, user_parameters, token)
    if not assistant_id: return f"Failed to get or create an assistant for the `{session_name}` assistant."

    openai_api_key = user_parameters.get('openai_api_key') or OPENAI_API_KEY
    client = OpenAI(api_key=openai_api_key)

    message_id = user_parameters.get('message_id', 0) or 0

    try:
        if not from_email: send_message_markdown(chat_id, f"`{session_name}` agent is thinking...", token, message_id)
        elif chat_id: send_message_markdown(chat_id, f"`Email Assistant` is processing your email...", os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), message_id)

        # Add the user's query to the thread
        if session_name == 'session_help': client.beta.threads.messages.create(thread_id=session_thread_id, role="user", content=query, attachments=[{"file_id": SESSION_HELP_FILE_ID, "tools": [{"type": tools_type}]}])
        elif session_name == 'session_query_doc': client.beta.threads.messages.create(thread_id=session_thread_id, role="user", content=query, attachments=[{"file_id": user_parameters.get('session_document_id'), "tools": [{"type": tools_type}]}])
        elif session_name in ['session_creator', 'session_translator']: client.beta.threads.messages.create(thread_id=session_thread_id, role="user", content=query, attachments=[{"file_id": user_parameters.get('writing_style_sample'), "tools": [{"type": tools_type}]}])
        else: client.beta.threads.messages.create(thread_id=session_thread_id, role="user", content=query)

        run = client.beta.threads.runs.create_and_poll(thread_id=session_thread_id, assistant_id=assistant_id, model=model)
        if run.status == 'completed': 
            messages = list(client.beta.threads.messages.list(thread_id=session_thread_id, run_id=run.id))
            message_content = messages[0].content[0].text

            annotations = message_content.annotations
            for annotation in annotations: message_content.value = message_content.value.replace(annotation.text, '')

            response = message_content.value

            try: # Calculate the token usage
                prompt_tokens = run.usage.prompt_tokens
                completion_tokens = run.usage.completion_tokens
                model_price_input = OPENAI_MODEL_PRICING.get(model, {}).get('input', 0)
                model_price_output = OPENAI_MODEL_PRICING.get(model, {}).get('output', 0)
                cost_input = model_price_input * prompt_tokens
                cost_output = model_price_output * completion_tokens
                cost_total = cost_input + cost_output
                update_chat_id_monthly_consumption(chat_id, cost_total, engine)
            except Exception as e: print(f"Failed to calculate token usage. Error: {str(e)}")
            
            if session_name == 'session_query_doc':
                # Save user query and assistant response to the database
                data_dict = {
                    'chat_id': [chat_id],
                    'query_and_response': [f"User Query:\n{query}\n\nAI Assistant Response:\n{response}"],
                    'session_name': [session_name],
                    'tools_type': [tools_type],
                    'session_thread_id': [session_thread_id],
                    'session_document_id': [user_parameters.get('session_document_id')],
                    'session_document_name': [user_parameters.get('session_document_name')],
                    'assistant_id': [assistant_id],
                    'updated_time': [datetime.now()],
                    'creator_posted': [0]
                }

                df = pd.DataFrame(data_dict)
                df.to_sql('query_conversation_record', engine, if_exists='append', index=False)

            return response
        
        else: return send_debug_to_laogege(f"run_assistant() >> /chat_{chat_id} >> Failed to run the assistant. Status: {run.status}\n\nUSER QUERY: \n{query[:500]}...")
    except Exception as e: return send_debug_to_laogege(f"run_assistant() >> /chat_{chat_id} >> Failed to run the assistant. Error: {str(e)}\n\nUSER QUERY: \n{query[:500]}...")


def session_conversation(chat_id: str, query: dict, session_name: str, token = TELEGRAM_BOT_TOKEN, engine = engine, model = ASSISTANT_DOCUMENT_MODEL, user_parameters = {}):

    if session_name == 'session_translation': return session_translation(query, chat_id, token, user_parameters)
    else: 
        name = user_parameters.get('name')
        mother_language = user_parameters.get('mother_language')
        user_name = user_parameters.get('user_name')
        query = f"{query}\n\nMy name is: {name}\nMy Mother language is: {mother_language}\nMy telegram handle is: {user_name}"

        response = run_assistant(chat_id, query, session_name, engine, model, user_parameters, token, from_email = False)
        if not response: return send_message(chat_id, f"Failed to run the assistant for {session_name}\nClick /session_exit to exit.", token)
    
    response = f"`{session_name}` response:\n\n{response.replace('*', '')}"
    message_id = user_parameters.get('message_id', 0) or 0

    return callback_session_audio(chat_id, response, session_name, token, engine, user_parameters, message_id, is_markdown = True)


def email_assistant_response(email_content: str, email_address: str, subject: str, characters_limits: int, prefix: str, suffix: str, chat_id: str, user_parameters = {}):
    # if the email_content is empty, return the system prompt
    if not email_content: return
    if EMAIL_DIVIDER in email_content: email_content = email_content.split(EMAIL_DIVIDER)[0]

    length_of_email_content = len(email_content)
    if length_of_email_content > characters_limits:
        email_content = email_content[:characters_limits]
        truncated_content = email_content[characters_limits:]
        truncated_information = f"\n\nFYI: Your email was too long, and part of the content has been truncated. The following content was not processed by the AI English assistant:\n{truncated_content}"
        suffix += truncated_information
    
    email_content = prefix + email_content

    reply = ''
    if chat_id: reply = run_assistant(chat_id, email_content, 'assistant_email', engine, ASSISTANT_MAIN_MODEL, user_parameters, TELEGRAM_BOT_TOKEN, from_email = True)
    else:reply = openai_gpt_chat(SYSTEM_PROMPT_EMAIL_ASSISTANT, email_content, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)

    if reply:
        reply += EMAIL_DIVIDER
        reply += suffix

        md = MarkdownIt()
        html_content = md.render(reply)
        send_email_html(email_address, subject, html_content, plain_text_content=reply)

    return


def check_gmail(imap_username = GMAIL_ADDRESS, imap_password = GMAIL_PASSWORD, engine = engine):
    print(f"Checking Gmail() >> {imap_username}")
    try:
        # 使用 IMAP 进行登录
        imap_server = imaplib.IMAP4_SSL("imap.gmail.com")
        imap_server.login(imap_username, imap_password)
        imap_server.select("inbox")

        # 搜索未读邮件
        status, messages = imap_server.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if len(email_ids) == 0: return

        # 处理未读邮件
        for email_id in email_ids:
            # 获取邮件数据
            res, msg = imap_server.fetch(email_id, "(RFC822)")
            for response_part in msg:
                if isinstance(response_part, tuple):
                    # 解析邮件内容
                    msg = email.message_from_bytes(response_part[1])
                    
                    # 获取邮件主题
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes): subject = subject.decode(encoding if encoding else "utf-8")

                    # 获取发件人
                    from_ = msg.get("From")
                    
                    # 是否需要用 re 从 from_ 中提取 email 地址？
                    email_address = extract_email(from_)

                    user_parameters = get_users_parameters_by_email(email_address, engine)
                    if not user_parameters: continue

                    '''{
                        "status": "paid",
                        "name": "Xiaoyu Wang",
                        "tier": "Gold",
                        "ranking": 5,
                        "email": "angiaou@gmail.com",
                        "chat_id": "502095251",
                        "mother_language": "Chinese",
                        "text_character_limit": 64000,
                        "daily_video_limit": 5,
                        "video_duration_limit": 3600,
                        "is_whitelist": 1
                    }'''

                    user_name = user_parameters.get('name')
                    status = user_parameters.get('status', '')
                    if not all([user_name, status]): continue

                    tier = user_parameters.get('tier', '')
                    chat_id = user_parameters.get('chat_id', '')
                    mother_language = user_parameters.get('mother_language') or 'Not Provided'
                    characters_limits = user_parameters.get('text_character_limit', 1000) or 1000

                    prefix=f"{user_name} (mother language is {mother_language}), send email and said: \n"
                    suffix = f'''If this answer seems incomplete, it might be because your email was too long. As a `{tier}` member, the maximum length for your email is {characters_limits} characters (about {int(characters_limits/5)} words). To send longer messages, you can upgrade to a higher tier.\n\n{TIER_NAME_TO_CHARACTER_LIMITS_STRING}\n\nFor more information, visit our website: {BLOG_BASE_URL}'''
                    
                    body = ''
                    # 如果邮件有多部分，获取邮件正文
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            if "attachment" not in content_disposition and content_type == "text/plain": body = part.get_payload(decode=True).decode()
                    else: body = msg.get_payload(decode=True).decode()
                    
                    if body: email_assistant_response(body, email_address, subject, characters_limits, prefix, suffix, chat_id, user_parameters)

        imap_server.logout()
    except Exception as e: send_debug_to_laogege(f"check_gmail() >> Failed to check Gmail: {str(e)}")




if __name__ == "__main__":
    print("Telegram assistant is working...")
