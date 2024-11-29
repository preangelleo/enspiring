from subtitle_process import *


def load_words_set(engine = engine):
    global WORDS_SET
    with engine.connect() as conn:
        query = """SELECT `word` FROM `vocabulary_new`"""
        df = pd.read_sql(text(query), conn)
        if not df.empty: 
            WORDS_SET = set(df['word'].tolist())  # Convert list to set for faster lookup
            return WORDS_SET
    return set()

load_words_set()

# 定义一个线程池来处理不同用户的任务
executor = ThreadPoolExecutor(max_workers=100)

''' Telegram's sendChatAction API provides several possible actions that you can use to indicate different statuses. Here are the available actions:

typing - Shows that the bot is "typing…" (ideal for text responses).
upload_photo - Indicates that the bot is uploading a photo.
record_video - Shows that the bot is recording a video.
upload_video - Indicates that the bot is uploading a video.
record_audio - Shows that the bot is recording audio (voice message).
upload_audio - Indicates that the bot is uploading an audio file.
upload_document - Shows that the bot is uploading a document (useful for sending files).
find_location - Indicates that the bot is finding a location.
record_video_note - Shows that the bot is recording a video note.
upload_video_note - Indicates that the bot is uploading a video note.
'''

def send_typing_action(chat_id: str, action = "typing", token = TELEGRAM_BOT_TOKEN):
    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    params = {
        "chat_id": chat_id,
        "action": action
    }
    try: requests.post(url, params=params)
    except: pass


# Function to handle the callback query and navigate between menus
def handle_callback_query(callback_query, token=TELEGRAM_BOT_TOKEN, engine=engine):
    answer_callback_query(callback_query["id"], token)

    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    update_message = callback_query["message"]

    chat_id = str(chat_id)
    message_id = int(message_id)

    # Send typing status
    send_typing_action(chat_id, action = "typing", token = token)

    user_parameters = user_parameters_realtime(chat_id, engine)
    if user_parameters.get('is_blacklist'): return 

    ranking = user_parameters.get('ranking') or 0
    tier = user_parameters.get('tier') or 'Free'
    openai_api_key = user_parameters.get('openai_api_key', '')

    callback_data = callback_query["data"]
    callback_data = str(callback_data)

    first_name = update_message['chat'].get('first_name', '')
    last_name = update_message['chat'].get('last_name', '')
    user_handle = update_message['chat'].get('username', '')
    if user_handle: user_handle = f"@{user_handle}"
    user_name = " ".join([i for i in [first_name, last_name, user_handle] if i])

    if callback_data == 'back_to_main_menu': main_menu_setting(chat_id, token, message_id)

    elif callback_data == 'set_creator_configurations': 
        if ranking < 5: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        else: creator_menu_setting(chat_id, token, message_id)

    elif callback_data == 'set_daily_words_list_on_off': callback_daily_words_list_on_off(chat_id, token, message_id)
    elif callback_data == 'set_daily_words_list_on': set_daily_words_list_for_chat_id(chat_id, 1, engine)
    elif callback_data == 'set_daily_words_list_off': set_daily_words_list_for_chat_id(chat_id, 0, engine)

    elif callback_data == 'creator_default_post_language': callback_creator_post_language_setup(chat_id, token, message_id)
    elif callback_data == 'creator_default_post_type': callback_creator_default_post_type(chat_id, token, message_id)
    elif callback_data == 'creator_default_post_visibility': callback_creator_default_post_visibility(chat_id, token, message_id)
    elif callback_data == 'creator_default_audio_switch': callback_creator_default_audio_switch(chat_id, token, message_id)
    elif callback_data == 'creator_default_clone_voice': callback_creator_default_clone_voice(chat_id, token, message_id)
    elif callback_data == 'creator_default_publish_status': callback_creator_default_publish_status(chat_id, token, message_id)
    elif callback_data == 'creator_ghost_blog_api_key': callback_creator_ghost_blog_api_key(chat_id, token, message_id)
    elif callback_data == 'creator_ghost_blog_url': callback_creator_ghost_blog_url(chat_id, token, message_id)
    elif callback_data == 'creator_default_image_model': callback_creator_default_image_model(chat_id, token, message_id)
    elif callback_data == 'creator_slug_style': callback_creator_slug_style(chat_id, token, message_id)

    elif callback_data.startswith('tweet_'):
        post_id = callback_data.split('_')[-1]
        if not post_id: return send_message(chat_id, "Failed to get the post ID, please try again later.", token)
        if callback_data.startswith('tweet_creator_page_'): table_name = 'creator_journals'
        elif callback_data.startswith('tweet_creator_auto_'): table_name = 'creator_auto_posts'
        elif callback_data.startswith('tweet_creator_post_'): table_name = 'creator_journals_repost'
        elif callback_data.startswith('tweet_user_journals'): table_name = 'user_journals'
        elif callback_data.startswith('tweet_user_stories_tailored'): table_name = 'user_stories_tailored'
        elif callback_data.startswith('tweet_user_stories'): table_name = 'user_stories'
        else: table_name = 'image_midjourney'
            
        df = pd.read_sql(text(f"SELECT title, custom_excerpt, post_url FROM `{table_name}` WHERE post_id = :post_id;"), engine, params={"post_id": post_id})
        if df.empty: return send_message(chat_id, "Failed to get the post details, please try again later.", token)

        title, url, custom_excerpt = df['title'].values[0], df['post_url'].values[0], df['custom_excerpt'].values[0]
        if not all([title, url]): return send_message(chat_id, "Failed to get the post details, please try again later.", token)

        if custom_excerpt: title = custom_excerpt

        tweet_result = handle_share_to_twitter_button(chat_id, title, url, token)
        if tweet_result and tweet_result.startswith('http'):
            reply = f"Click [HERE]({tweet_result}) to view the tweet."
            return send_message_markdown(chat_id, reply, token)
        else: return send_message(chat_id, "Failed to share the post to Twitter, please try again later.", token)
    

    elif callback_data.startswith('linkedin_'):
        post_id = callback_data.split('_')[-1]
        if not post_id: return send_message(chat_id, "Failed to get the post ID, please try again later.", token)

        if callback_data.startswith('linkedin_creator_page_'): table_name = 'creator_journals'
        elif callback_data.startswith('linkedin_creator_auto_'): table_name = 'creator_auto_posts'
        elif callback_data.startswith('linkedin_creator_post_'): table_name = 'creator_journals_repost'
        elif callback_data.startswith('linkedin_user_journals'): table_name = 'user_journals'
        elif callback_data.startswith('linkedin_user_stories_tailored'): table_name = 'user_stories_tailored'
        elif callback_data.startswith('linkedin_user_stories'): table_name = 'user_stories'
        else: table_name = 'image_midjourney'
            
        df = pd.read_sql(text(f"SELECT title, custom_excerpt, post_url, image_path, feature_image FROM `{table_name}` WHERE post_id = :post_id;"), engine, params={"post_id": post_id})
        if df.empty: return send_message(chat_id, "Failed to get the post details, please try again later.", token)

        title, url, custom_excerpt, image_path = df['title'].values[0], df['post_url'].values[0], df['custom_excerpt'].values[0], df['image_path'].values[0]
        if not all([title, url]): return send_message(chat_id, "Failed to get the post details, please try again later.", token)

        if not os.path.isfile(image_path):
            feature_image = df['feature_image'].values[0]
            if feature_image: 
                try:
                    base_name = feature_image.split('/')[-1]
                    # download the image from the feature_image URL
                    response = requests.get(feature_image)
                    # Create the file path for each image
                    image_path = os.path.join(midjourney_images_dir, base_name)
                    # Save the image to the local folder
                    with open(image_path, 'wb') as file: file.write(response.content)
                except: image_path = ''

        share_asset = handle_share_to_linkedin_button(chat_id, title, custom_excerpt, url, image_path, token)
        if share_asset and share_asset.startswith('urn:li:share:'):
            reply = f"Clicke [HERE](https://www.linkedin.com/feed/update/{share_asset}) to view the post on LinkedIn."
            return send_message_markdown(chat_id, reply, token)
        return


    elif callback_data.startswith('creator_unfeatured_') or callback_data.startswith('creator_featured_') or callback_data.startswith('creator_public_') or callback_data.startswith('creator_private_') or callback_data.startswith('creator_publish_') or callback_data.startswith('creator_unpublish_'):
        if ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)

        admin_api_key = user_parameters.get('ghost_admin_api_key', '')
        ghost_url = user_parameters.get('ghost_api_url', '')
        if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

        status, visibility, featured = None, None, None
        split_data = callback_data.split('_')
        if len(split_data) < 4: return send_message(chat_id, "Failed to update post details, please try again later.", token)

        callback_data_parameters = split_data[1]
        post_type = split_data[2]
        post_id = split_data[3]

        suffix = f"Hi {user_name}, your {post_type} has been _setup_placeholder_ successfully. You can also manage the visitiblity, publish status, or featured status manually at your Ghost Dashboard at {ghost_url}/ghost."
        
        if callback_data_parameters == 'unfeatured': 
            featured = 0
            success_message = suffix.replace('_setup_placeholder_', '`unfeatured`')
        elif callback_data_parameters == 'featured': 
            featured = 1
            success_message = suffix.replace('_setup_placeholder_', '`featured`')
        elif callback_data_parameters == 'public': 
            visibility = 'public'
            success_message = suffix.replace('_setup_placeholder_', 'set to `public`')
        elif callback_data_parameters == 'private': 
            visibility = 'paid'
            success_message = suffix.replace('_setup_placeholder_', 'set to `paid menbers only`')
        elif callback_data_parameters == 'publish': 
            status = 'published'
            success_message = suffix.replace('_setup_placeholder_', '`published`')
        elif callback_data_parameters == 'unpublish': 
            status = 'draft'
            success_message = suffix.replace('_setup_placeholder_', '`unpublished` (set to `draft`)')

        reply_dict = update_post_details(post_id, post_type, status, visibility, featured, admin_api_key, ghost_url)
        if not reply_dict['Status']: return send_message(chat_id, reply_dict['Message'], token)

        return callback_tweet_post(chat_id, success_message, post_id, token, user_parameters, is_markdown=False, is_creator = True)

    elif callback_data.startswith('creator_default_post_type_'):
        default_post_type = callback_data.replace('creator_default_post_type_', '').strip()
        default_post_type = set_default_post_type_for_chat_id(chat_id, default_post_type, engine)
        if default_post_type: send_message(chat_id, f"Default post type set to `{default_post_type}` successfully.", token)
        else: send_message(chat_id, "Failed to set default post type, please try again.", token)

    elif callback_data.startswith('creator_default_post_visibility_'):
        default_post_visibility = callback_data.replace('creator_default_post_visibility_', '').strip()
        default_post_visibility = set_default_post_visibility_for_chat_id(chat_id, default_post_visibility, engine)
        if default_post_visibility: send_message(chat_id, f"Default post visibility set to `{default_post_visibility}` successfully.", token)
        else: send_message(chat_id, "Failed to set default post visibility, please try again.", token)
    
    elif callback_data.startswith('creator_default_publish_status_'):
        default_publish_status = callback_data.replace('creator_default_publish_status_', '').strip()
        default_publish_status = set_default_publish_status_for_chat_id(chat_id, default_publish_status, engine)
        if default_publish_status: send_message(chat_id, f"Default publish status set to `{default_publish_status}` successfully.", token)
        else: send_message(chat_id, "Failed to set default publish status, please try again.", token)
    
    elif callback_data.startswith('post_language_'):
        post_language = callback_data.replace('post_language_', '').strip()
        post_language = set_post_language_for_chat_id(chat_id, post_language, engine)
        if post_language: send_message(chat_id, f"Default post language set to `{post_language}` successfully.", token)
        else: send_message(chat_id, "Failed to set default post language, please try again.", token)
    
    elif callback_data.startswith('creator_default_audio_switch_'):
        default_audio_switch = callback_data.replace('creator_default_audio_switch_', '').strip()
        default_audio_switch = set_default_audio_switch_for_chat_id(chat_id, default_audio_switch, engine)
        if default_audio_switch: send_message(chat_id, f"Default audio switch set to `{default_audio_switch}` successfully.", token)
        else: send_message(chat_id, "Failed to set default audio switch, please try again.", token)

    elif callback_data.startswith('creator_slug_style_'):
        slug_style = callback_data.replace('creator_slug_style_', '').strip()
        slug_style = set_slug_style_for_chat_id(chat_id, slug_style, engine)
        if slug_style == 'on': send_message(chat_id, f"Slug style set to `Generated from Title` successfully.", token)
        else: send_message(chat_id, "Slug style set to `Short Slug` successfully.", token)

    elif callback_data.startswith('creator_writing_style'): return set_creator_writing_style_information(user_parameters, chat_id, token, engine, message_id)

    elif callback_data.startswith('set_news_keywords'): return set_news_keywords_information(user_parameters, chat_id, token, engine, message_id)

    elif callback_data.startswith('creator_default_clone_voice_'):
        elevenlabs_api_key = user_parameters.get('elevenlabs_api_key', '')
        if not elevenlabs_api_key: return set_elevenlabs_api_key_information(user_parameters, chat_id, token, message_id)

        voice_clone_sample = user_parameters.get('voice_clone_sample', '')
        if not voice_clone_sample: return callback_record_voice_clone_sample(chat_id, "You have set up your /elevenlabs_api_key already, but you don't have a voice clone sample yet, please click `Start Recording` to get started. Only after you submitted your voice clone sample, then you can choose to use your own voice for your blog posts.", token, message_id)

        default_clone_voice = callback_data.replace('creator_default_clone_voice_', '').strip()
        if default_clone_voice == 'on': default_value = 1
        elif default_value == 'off': default_value = 0
        else: return send_message(chat_id, "Failed to set default clone voice, please try again.", token)

        default_value = set_default_clone_voice_for_chat_id(chat_id, default_value, engine)
        if default_value in [0, 1]: send_message(chat_id, f"Default clone voice set to `{default_clone_voice}` successfully.", token)
        else: send_message(chat_id, "Failed to set default clone voice, please try again.", token)

    elif callback_data.startswith('creator_translate_to_post_'): 
        post_id = callback_data.replace('creator_translate_to_post_', '').strip()
        return repost_journal_to_ghost_creator(chat_id, post_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, user_parameters, need_translate = True)

    elif callback_data.startswith('creator_page_to_post_'):
        post_id = callback_data.replace('creator_page_to_post_', '').strip()
        return repost_journal_to_ghost_creator(chat_id, post_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, user_parameters, need_translate = False)
    
    elif callback_data.startswith('creator_default_image_model_'):
        image_model = callback_data.replace('creator_default_image_model_', '').strip().capitalize()

        image_model = set_default_image_model_for_chat_id(chat_id, image_model, engine)
        
        if image_model: send_message(chat_id, f"Default image model set to `{image_model}` successfully.", token)
        else: send_message(chat_id, "Failed to set default image model, please try again.", token)
        
        return send_debug_to_laogege(f"/chat_{chat_id} just set image_model to `{image_model}`")

    elif callback_data == 'creator_post_doc':
        if ranking < 5 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        
        admin_api_key = user_parameters.get('ghost_admin_api_key', '')
        ghost_url = user_parameters.get('ghost_api_url', '')
        if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

        session_name = user_parameters.get('session_name', '')
        session_document_name = user_parameters.get('session_document_name', '')
        session_document_id = user_parameters.get('session_document_id', '')

        df_history = pd.read_sql(text("SELECT query_and_response, creator_posted FROM query_conversation_record WHERE chat_id = :chat_id AND session_name = :session_name AND session_document_id = :session_document_id ORDER BY updated_time ASC;"), engine, params={"chat_id": chat_id, "session_name": session_name, "session_document_id": session_document_id})
        
        if df_history.empty: return send_message(chat_id, f"No conversation history found for document: `{session_document_name}`, please query with the document for at least 1 time, then you can generate a journal based on your query and the response of `{session_name}` assistant.", token)
        creator_posted = df_history['creator_posted'].values[0]

        if creator_posted and not openai_api_key: return send_message(chat_id, f"Without your own `/openai_api_key`, you can only generate one journal for each document. Please set your own `/openai_api_key` to generate more journals.", token)
        
        conversation_history = "\n\n\n\n".join(df_history['query_and_response'].tolist())

        if not conversation_history: return send_message(chat_id, f"No conversation history found for document: `{session_document_name}`, please query with the document for at least 1 time, then you can generate a journal based on your query and the response of `{session_name}` assistant.", token)

        query = "I want to write a journal about this document. Now please give me the key points and main ideas of the document along with supportive details and evidence as much as possible. And anything you believe is important to be included in the journal or interesting to be shared with others."
        
        send_message(chat_id, f"Generating a journal based on the conversation history with document `{session_document_name}`, please wait about 300 seconds...", token)

        if len(conversation_history) < PDF_TO_POST_CHARACTER_LIMIT - 1000:
            try: conversation_history += f"\n\n\n\nUser Query:\n{query}\n\nAI Assistant Response:\n{run_assistant(chat_id, query, session_name, engine, ASSISTANT_DOCUMENT_MODEL, user_parameters)}"
            except: pass

        saving_folder = os.path.join(working_dir, chat_id)

        file_basename = session_document_name.split('.')[0]
        current_timestamp_int = int(datetime.now().timestamp())
        saving_filepath = os.path.join(saving_folder, f"{file_basename[:20]}_{current_timestamp_int}.txt")
        with open(saving_filepath, "w") as f: f.write(conversation_history)
        send_document_from_file(chat_id, saving_filepath, f"Here's your conversation history with documents `{session_document_name}`, just for your reference, AI assistent is still working...", token)
        
        conversation_history = conversation_history[:PDF_TO_POST_CHARACTER_LIMIT]
        prompt = f"Here's my conversation history with AI assistant about my document `{session_document_name}`, now please generate a journal based on our conversation. Try to include all of the information we discussed, you can reorganize, rephrase, and add more details to make it more like a journal. But do not drop any important information from my conversation history.\n\n"
        prompt += conversation_history
        with engine.begin() as conn: conn.execute(text("UPDATE query_conversation_record SET creator_posted = 1 WHERE chat_id = :chat_id AND session_name = :session_name AND session_document_id = :session_document_id;"), {"chat_id": chat_id, "session_name": session_name, "session_document_id": session_document_id})
        return post_journal_to_ghost_creator(prompt, chat_id, engine, token, model = ASSISTANT_MAIN_MODEL_BEST, message_id = '', user_parameters = user_parameters, is_journal=True)

    # Main menu setting functions below

    elif callback_data == "cancel_settings": delete_message(chat_id, message_id, token)
    elif callback_data == 'set_elevenlabs_api_key': set_elevenlabs_api_key_information(user_parameters, chat_id, token, message_id)
    elif callback_data == 'set_openai_api_key': set_openai_api_key_information(user_parameters, chat_id, token, message_id)
    elif callback_data == 'set_twitter_handle': set_twitter_handle_information(user_parameters, chat_id, token, message_id)

    elif callback_data == 'delete_elevenlabs_api_key': remove_elevenlabs_api_key_for_chat_id(chat_id, engine)
    elif callback_data == 'delete_openai_api_key': remove_openai_api_key_for_chat_id(chat_id, engine)
    elif callback_data == 'delete_writing_style_sample': remove_writing_style_sample_for_chat_id(chat_id, engine)

    elif callback_data.startswith('delete_proof_reading_'): 
        post_type_id = callback_data.replace('delete_proof_reading_', '').strip()
        post_type = post_type_id.split('_')[0]
        post_id = post_type_id.split('_')[-1]
        if post_type not in ['post', 'page']: return send_message(chat_id, "Failed to delete the proof reading, please try again later.", token)
        response = delete_given_post_id_type(post_id, post_type, api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL)
        return send_message(chat_id, response, token)

    elif callback_data == 'set_daily_story_voice':
        elevenlabs_api_key = user_parameters.get('elevenlabs_api_key', '')
        if not elevenlabs_api_key: return send_message(chat_id, "You need to set your /elevenlabs_api_key first before using this function.", token)
        current_clone_sample = user_parameters.get('voice_clone_sample', '')
        if not current_clone_sample: return callback_record_voice_clone_sample(chat_id, "You have set up your /elevenlabs_api_key already, but you don't have a voice clone sample yet, please click `Start Recording` to get started.", token, message_id)
        prompt = "Do you want to use your own voice to read your daily story or use the default AI voice?"
        return callback_daily_story_voice_on_and_off(chat_id, prompt, token, message_id)
    
    elif callback_data == 'daily_story_voice_on':
        set_daily_story_voice_for_chat_id(chat_id, daily_story_voice = 1, engine = engine)
        send_message(chat_id, "Daily story voice has been set to use your own voice successfully.", token, message_id)
    
    elif callback_data == 'daily_story_voice_off':
        set_daily_story_voice_for_chat_id(chat_id, daily_story_voice = 0, engine = engine)
        send_message(chat_id, "Daily story voice has been set to use the AI voice successfully.", token, message_id)

    elif callback_data == 'set_youtube_playlist':
        if ranking < 3 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)
        else:
            tier = user_parameters.get('tier') or 'Free'
            current_youtube_playlist = user_parameters.get('youtube_playlist', '')
            prefix_msg = f"Your current YouTube playlist is:\n`{current_youtube_playlist[:10]}......{current_youtube_playlist[-11:]}`\nYou can always overwrite the playlist by sending a new playlist URL (in full-length)."
            notification_msg = f"Please provide the full-length YouTube playlist URL. I will check and process the videos, generate content, and post them online for you. Once posted, a private shared link will be sent to you. \n\nBased on your /tier : /{tier}, up to {int(ranking)} videos will be processed and posted. "
            if current_youtube_playlist: notification_msg = prefix_msg + '\n\n' + notification_msg
            suffix_msg = f"\n\nA full-length YouTube playlist URL should look like this:\n\n{FULL_LENGTH_PLAYLIST_URL}"
            notification_msg = notification_msg + suffix_msg
            send_message(chat_id, notification_msg, token)

    elif callback_data == 'set_google_spreadsheet': 
        if ranking < 2 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        else: send_message(chat_id, f"Click below link to get a full understanding of how this function works and how to setup this feature. \n\n{GOOGLE_SPREADSHEET_SETUP_PAGE}", token)

    elif callback_data == 'set_mother_language': callback_mother_language_setup(chat_id, token, message_id)
    elif callback_data == 'set_secondary_language': callback_secondary_language_setup(chat_id, token, message_id)
    elif callback_data == 'set_target_language': callback_target_language_setup(chat_id, token, message_id)
    elif callback_data == 'set_cartoon_style': callback_cartoon_style_setup(chat_id, token, message_id)

    elif callback_data == 'set_default_audio_gender':
        # Sub-menu for setting default audio voice
        default_voice_prompt = "Which audio voice gender do you prefer?"
        default_voice_inline_keyboard_dict = {'Male': 'default_audio_gender_male', 'Female': 'default_audio_gender_female', '<< Back to Main Menu': 'back_to_main_menu'}
        button_per_list = 2
        send_or_edit_inline_keyboard(default_voice_prompt, default_voice_inline_keyboard_dict, chat_id, button_per_list, token, message_id)

    elif callback_data == 'set_voice_clone_sample': 
        current_clone_sample = user_parameters.get('voice_clone_sample', '')
        if current_clone_sample: prompt = f"Your already have a voice clone sample, however, you can always overwrite it by sending a new voice message."
        else: prompt = f"You don't have a voice clone sample yet, please click `Start Recording` to get started."
        callback_record_voice_clone_sample(chat_id, prompt, token, message_id)

    elif callback_data == 'record_voice_clone_sample': prompt_user_send_voice_clone_sample(chat_id, token, engine, is_redo=True, user_parameters=user_parameters)

    elif callback_data == 'exit_session': exit_session_name(chat_id, engine)

    elif callback_data == 'ice_breaker': 
        if ranking < 1 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Starter or higher tier to use this function.\n\n/get_premium", token)
        else: openai_gpt_function(callback_data, chat_id, tools = FUNCTIONS_TOOLS, model = ASSISTANT_DOCUMENT_MODEL, engine = engine, token = token, user_parameters = user_parameters)

    elif callback_data.startswith('set_secondary_language_'):
        secondary_language = callback_data.replace('set_secondary_language_', '').strip()
        secondary_language = set_secondary_language_for_chat_id(chat_id, secondary_language, engine)
        if secondary_language: send_message_markdown(chat_id, f"Secondary language set to `{secondary_language}` successfully.", token, message_id)
        else: send_message(chat_id, "Failed to set secondary language, please try again.", token)

    elif callback_data.startswith('set_target_language_'):
        target_language = callback_data.replace('set_target_language_', '').strip()
        target_language = set_target_language_for_chat_id(chat_id, target_language, engine)
        if target_language: send_message_markdown(chat_id, f"Target language set to `{target_language}` successfully.", token, message_id)
        else: send_message(chat_id, "Failed to set target language, please try again.", token)

    # Actual setting functions below
    elif callback_data in REVERSED_CARTOON_STYLE_DICT:
        cartoon_style = REVERSED_CARTOON_STYLE_DICT[callback_data]
        cartoon_style = set_cartoon_style_for_chat_id(chat_id, cartoon_style, engine)
        if cartoon_style: send_message_markdown(chat_id, f"Cartoon style set to `{cartoon_style}` successfully.", token, message_id)
        else: send_message(chat_id, "Failed to set cartoon style, please try again.", token)

    elif callback_data.startswith('set_mother_language_'): 
        mother_language = callback_data.replace('set_mother_language_', '').strip()
        mother_language = set_mother_language_for_chat_id(chat_id, mother_language, engine)
        if mother_language: send_message_markdown(chat_id, f"Mother language set to `{mother_language}` successfully.", token, message_id)
        else: send_message(chat_id, "Failed to set mother language, please try again.", token)

    elif callback_data.startswith('default_audio_gender_'):
        gender = callback_data.replace('default_audio_gender_', '').strip()
        if gender not in ['male', 'female']: gender = 'male'
        gender = set_default_audio_gender_for_chat_id(chat_id, gender, engine)
        if gender: send_message_markdown(chat_id, f"Your default generated audio gender has been set to `{gender.capitalize()}`.")
        else: 
            send_message(chat_id, f"Failed to set the default audio gender, please contact {OWNER_HANDLE}")
            send_debug_to_laogege(f"/chat_{chat_id} failed to set the default audio gender to {callback_data.replace('default_audio_gender_', '').strip()}")

    elif callback_data.startswith('public_') or callback_data.startswith('private_'):
        post_id = callback_data.split('_')[-1]
        if callback_data.startswith('public_'): send_message(chat_id, set_page_visibility_direclty_in_table(post_id, 'public', engine), token)
        elif callback_data.startswith('private_'): send_message(chat_id, set_page_visibility_direclty_in_table(post_id, 'public', engine), token)


    elif callback_data.startswith('generate_audio_'):
        if ranking < 2 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        else:
            vocabulary = callback_data.replace('generate_audio_', '').strip()
            generated_explanation = get_explanation_for_audio_generation(vocabulary, engine)

            if generated_explanation: 
                audio_file = generate_story_voice(generated_explanation, chat_id, audio_generated_dir, engine, token, user_parameters, 'English')
                if audio_file and os.path.isfile(audio_file): return send_audio_from_file(chat_id, audio_file, token)

            return send_message(chat_id, "Failed to generate audio file.", token)
    
    elif callback_data in ['random_word']: random_word(chat_id, token, engine, user_parameters)
    
    elif callback_data.startswith('markdown_audio_'):
        if ranking < 2 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        else:
            hash_md5 = callback_data.replace('markdown_audio_', '').strip()
            # from hash_md5 to get the prompt from table 'markdown_text'
            query = f"SELECT prompt, language FROM markdown_text WHERE hash_md5 = :hash_md5"
            df = pd.read_sql(text(query), engine, params={"hash_md5": hash_md5})
            if df.empty: send_message(chat_id, "Failed to get the text to generate audio, sorry. You can try quote previous message text and send /audio to me.", token)
            else:
                send_message(chat_id, "Generating audio now...", token)
                prompt = df['prompt'].values[0]
                language = df['language'].values[0]

                audio_file = generate_story_voice(prompt, chat_id, audio_generated_dir, engine, token, user_parameters, language)

                if audio_file and os.path.isfile(audio_file): return send_audio_from_file(chat_id, audio_file, token)
                return send_message(chat_id, "Failed to generate audio file.", token)


    elif callback_data.startswith('generate_image_'):
        if ranking < 5 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        else:
            '''text_audioinline_keyboard_dict = {'Generate with Midjourney': f'generate_image_blackforest_{hash_md5}', 'Generate with Blackforest': f'generate_image_midjourney_{hash_md5}', 'Play Audio': f'markdown_audio_{hash_md5}'}'''
            split_list = callback_data.split('_')
            image_model = split_list[-2]
            hash_md5 = split_list[-1]
            query = f"SELECT prompt FROM markdown_text WHERE hash_md5 = :hash_md5"
            df = pd.read_sql(text(query), engine, params={"hash_md5": hash_md5})
            if df.empty: send_message(chat_id, "Failed to get the text to generate image, sorry. You can try quote previous message text and send /image to me.", token)
            else:
                user_prompt = df['prompt'].values[0]
                if image_model == 'midjourney': 
                    if not "--ar 16:9" in user_prompt: user_prompt += " --ar 16:9"
                    image_id = generate_image_midjourney(chat_id, user_prompt, 'user', midjourney_token = IMAGEAPI_MIDJOURNEY)
                    if image_id: send_message_markdown(chat_id, f"Your image generation request has been submitted to Midjourney bot. The image ID is: `{image_id[:6]}...{image_id[-6:]}`. All four images will be send to you once generated. Click [HERE](https://docs.midjourney.com/docs/prompts) to learn more about how to create a better `Midjourney Prompt`", token)
                elif image_model == 'blackforest':
                    user_image_folder = os.path.join(midjourney_images_dir)
                    output_file = os.path.join(user_image_folder, f"{hash_md5}.png")
                    output_file = generate_image_replicate(user_prompt, output_file=output_file)
                    if output_file and os.path.isfile(output_file): send_document_from_file(chat_id, output_file, 'Image generated by Blackforest Flux Pro.', token)
                elif image_model == 'dalle':
                    output_file = openai_image_generation(user_prompt, chat_id, model="dall-e-3", size = "1792x1024", quality="standard", user_parameters = user_parameters)
                    if output_file and os.path.isfile(output_file): send_document_from_file(chat_id, output_file, 'Image generated by OpenAI DALL-E.', token)
        return 


    elif callback_data.startswith('translate_to_'):
        if ranking < 2 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        else:
            callback_split = callback_data.split('_')
            hash_md5 = callback_split[-1]
            target_language = callback_split[-2]

            # from hash_md5 to get the prompt from table 'markdown_text'
            query = f"SELECT prompt, language FROM markdown_text WHERE hash_md5 = :hash_md5"
            df = pd.read_sql(text(query), engine, params={"hash_md5": hash_md5})
            if df.empty: send_message(chat_id, "Failed to get the text to generate audio, sorry. You can try quote previous message text and send /audio to me.", token)
            else:
                prompt = df['prompt'].values[0]
                language = df['language'].values[0]

                if target_language == language: return send_message(chat_id, f"The target language ({target_language}) is the same as the original language ({language}), no need to translate.", token)

                secondary_language = user_parameters.get('secondary_language', target_language) or target_language
                mother_language = user_parameters.get('mother_language', 'English') or 'English'

                next_language = mother_language if mother_language != target_language else secondary_language if secondary_language != target_language else ''

                send_message_markdown(chat_id, f"Translating `{language}` to `{target_language}`...", token)

                system_prompt = SYSTEM_PROMPT_TRANSLATOR.replace('_mother_language_placeholder_', target_language)
                translated_prompt = openai_gpt_chat(system_prompt, prompt, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
                
                message_id = user_parameters.get('message_id')
                message_id = message_id + 1 if message_id else None

                return callback_translation_audio(chat_id, translated_prompt, token, engine, user_parameters, message_id, language, next_language, is_markdown = False)


    elif callback_data.startswith('generate_story_'):
        if ranking < 3 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)
        else:
            today_date = callback_data[15:]
            words_list = get_words_checked_today_for_user(chat_id, today_date, engine)
            send_message(chat_id, f"Generating a story based on the words you've checked today, please wait about 120 seconds...", token)
            message_id = str(int(message_id) + 1)
            return post_words_story_to_ghost(words_list, chat_id, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = token, model=ASSISTANT_DOCUMENT_MODEL, message_id = message_id, user_parameters = user_parameters)
            
    elif callback_data.startswith('explain_'):
        if ranking < 2 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        else:
            # remove explain_ from the callback_data
            callback_data = callback_data[8:]
            commands_list = callback_data.split('_in_')
            vocabulary = commands_list[0]
            target_language = commands_list[1]
            if target_language == 'Chinese': from_vocabulary_chinese_get_explanation(vocabulary, chat_id, engine, token, user_parameters)
            else:
                send_message_markdown(chat_id, f"Generating `{vocabulary}` explanation in {target_language}...", token)
                message_id = int(message_id) + 1

                explanation = get_explanation_in_mother_language(vocabulary, chat_id, target_language, model=ASSISTANT_MAIN_MODEL, engine = engine, user_parameters=user_parameters)
                
                if explanation: 
                    mother_language = user_parameters.get('mother_language', 'English') or 'English'
                    secondary_language = user_parameters.get('secondary_language', 'English') or 'English'
                    next_language = mother_language if mother_language != target_language else secondary_language if secondary_language != target_language else ''
                    return callback_translation_audio(chat_id, explanation, token, engine, user_parameters, message_id, target_language, next_language, is_markdown = False)
                
                else: send_message(chat_id, "Failed to generate the explanation, please try again.", token, message_id)
                

    elif callback_data.startswith('renew_vocabulary_'):
        if ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        else: return renew_vocabulary_chinese(callback_data.replace('renew_vocabulary_', '').strip(), chat_id, engine, token, user_parameters)


    elif callback_data.startswith('vocabulary_examples_'):
        if ranking < 1 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Starter or higher tier to use this function.\n\n/get_premium", token)
        else:
            vocabulary = callback_data[20:]
            examples = check_examples_in_table(vocabulary, chat_id, engine, user_parameters)
            if examples: callback_text_audio(chat_id, examples[:4000], token, engine, user_parameters)
            else: send_message(chat_id, "Failed to get the examples, please try again.", token)

    # Owner functions below
    if chat_id in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID]:

        if callback_data.startswith('add_whitelist_') or callback_data.startswith('add_blacklist_'):
            user_chat_id = callback_data.split('_')[-1]
            if callback_data.startswith('add_whitelist_'): 
                parameters = set_is_whitelist_for_chat_id(user_chat_id, 1, engine, token)
                print(f"New parameters: {json.dumps(parameters, indent=4)}")
                send_message(user_chat_id, f"You has been added to the whitelist by {OWNER_HANDLE}", token)
                send_message(OWNER_CHAT_ID, f"User /chat_{user_chat_id} has been added to the whitelist.", token)

            elif callback_data.startswith('add_blacklist_'):
                parameters= set_is_blacklist_for_chat_id(user_chat_id, 1, engine)
                print(f"New parameters: {json.dumps(parameters, indent=4)}")
                send_message(user_chat_id, f"You has been added to the blacklist by {OWNER_HANDLE}", token)
                send_message(OWNER_CHAT_ID, f"User /chat_{user_chat_id} has been added to the blacklist.", token)

        elif callback_data.startswith('remove_whitelist_') or callback_data.startswith('remove_blacklist_'):
            user_chat_id = callback_data.split('_')[-1]
            if callback_data.startswith('remove_whitelist_'): 
                parameters = set_is_whitelist_for_chat_id(user_chat_id, 0, engine, token)
                print(f"New parameters: {json.dumps(parameters, indent=4)}")
                send_message(user_chat_id, f"You has been removed from the whitelist by {OWNER_HANDLE}", token)
                send_message(OWNER_CHAT_ID, f"User /chat_{user_chat_id} has been removed from the whitelist.", token)

            elif callback_data.startswith('remove_blacklist_'):
                parameters = set_is_blacklist_for_chat_id(user_chat_id, 0, engine)
                print(f"New parameters: {json.dumps(parameters, indent=4)}")
                send_message(user_chat_id, f"You has been removed from the blacklist by {OWNER_HANDLE}", token)
                send_message(OWNER_CHAT_ID, f"User /chat_{user_chat_id} has been removed from the blacklist.", token)

    return 


# 用来处理每个用户消息的异步函数
def handle_message(update, token, engine = engine):
    update_message = update.get('message', {})
    chat_id = update_message['chat']['id']
    chat_id = str(chat_id)
    
    send_typing_action(chat_id, action = "typing", token = token)

    user_parameters = user_parameters_realtime(chat_id, engine)
    if user_parameters.get('is_blacklist', 0): return send_message(chat_id, f"You are in the blacklist, please contact {OWNER_HANDLE} for more information.", token)

    user_ranking = int(user_parameters.get('ranking') or 0)
    tier = user_parameters.get('tier') or 'Free'
    openai_api_key = user_parameters.get('openai_api_key', '')

    consumption_limit = USER_SPEND_LIMIT_MONTHLY_BY_RANKING.get(user_ranking, 1)
    this_month = str(datetime.now().month)
    user_spend_this_month = user_parameters.get(this_month) or 0

    if user_spend_this_month >= consumption_limit: return send_message(chat_id, f"Sorry, you have reached the monthly limit of conversation, your /tier is /{tier}, the total cost of calling OpenAI GPT model of your /{tier} should  be less than {int(consumption_limit)} usd per month. However, you've already cost {round(user_spend_this_month, 2)} usd this month. Please consider upgrading your /tier to get higher limit.\n/get_premium", token)

    msg_text = update_message.get('text', '')
    message_id = update_message.get('message_id')
    message_id = int(message_id)
    caption, reply, img_file_id, doc_file_id, voice_file_id, video_file_id, animation_file_id, audio_file_id, sticker_file_id, contact, location, poll = '', '',  None, None, None, None, None, None, None, None, None, None
    
    if update_message['chat'].get('username', ''): user_name = f"@{update_message['chat'].get('username', '')}"
    else: user_name = " ".join([i for i in [update_message['chat'].get('first_name', ''), update_message['chat'].get('last_name', '')] if i])

    if not user_parameters.get('email'):
        if is_valid_email(msg_text): return create_activation_webhook_button(msg_text, chat_id, user_name, token, engine)
        if user_parameters.get('is_whitelist'): send_message(chat_id, f"""Hi {user_name}, welcome to the {ENSPIRING_DOT_AI} Telegram AI English Coach & Assistant! \n\nAlthough you're on the whitelist, it's recommended to set up your email address to unlock the full potential of this powerful AI bot. Please send me your email address and confirm the 'Activate Now' button from your inbox. Once activated, you will no longer receive this reminder message.""", token)
        else: send_message(chat_id, f"""Hi {user_name}, welcome to the {ENSPIRING_DOT_AI} Telegram AI English Coach & Assistant! If you've subscribed to the premium service on {ENSPIRING_DOT_AI}, please send me the email address you used for your subscription to /activate your telegram account. Once activated, you will no longer receive this reminder message. If you haven't subscribed yet, click /get_premium for more information.""", token)

    output_dir = os.path.join(working_dir, chat_id)
    user_parameters['chat_id'] = chat_id
    user_parameters['message_id'] = message_id
    user_parameters['user_name'] = user_name

    # Check if the message is a reply to another message
    if 'reply_to_message' in update_message:
        quoted_msg = update_message['reply_to_message'].get('text')
        caption = msg_text
        if 'photo' in update_message['reply_to_message']: img_file_id = update_message['reply_to_message']['photo'][-1].get('file_id')
        if 'document' in update_message['reply_to_message']: doc_file_id = update_message['reply_to_message']['document'].get('file_id')
        if 'video' in update_message['reply_to_message']: video_file_id = update_message['reply_to_message']['video'].get('file_id')       
        if 'voice' in update_message['reply_to_message']: voice_file_id = update_message['reply_to_message']['voice'].get('file_id')
        if 'audio' in update_message['reply_to_message']: audio_file_id = update_message['reply_to_message']['audio'].get('file_id')       
        if quoted_msg: msg_text = f"{msg_text}\n\n----------------\n\nQuoted previous message:\n\n{quoted_msg}"

    if msg_text:
        if chat_id == OWNER_CHAT_ID and msg_text.startswith('/simulate '):
            user_chat_id_msg = msg_text.replace('/simulate ', '').strip()
            if ' ' in user_chat_id_msg: 
                chat_id, msg_text = user_chat_id_msg.split(' ', 1)
                chat_id = str(chat_id)
                user_name = get_name_by_chat_id(chat_id, engine = engine)
                if not user_name: return send_message(chat_id, f"Can't find chat_id {chat_id} from the table.", token)
                else: send_message(OWNER_CHAT_ID, f"Simulating `{user_name}` /chat_{chat_id} sending message: \n\n{msg_text}", token)

                output_dir = os.path.join(working_dir, chat_id)

                user_parameters['message_id'] = 0
                user_parameters['chat_id'] = chat_id
                user_parameters['user_name'] = user_name

                return dealing_tg_command(msg_text, chat_id, user_parameters, token, engine, message_id)

        elif msg_text == '/start': 
            send_message_markdown(chat_id, WELCOME_MESSAGE, token)
            create_chat_directories(chat_id)
            alert_to_owner = f"New user {user_name} just started the bot, take action if necessary.\n/chat_{chat_id}\n\n/create_ghost_blog {user_name.replace(' ', '_')} {chat_id}"
            return callback_whitelist_blacklist_setup(chat_id, alert_to_owner, token)
        
        elif msg_text in ['/setting', '/settings', 'setup']: return main_menu_setting(chat_id, token)
        elif msg_text.startswith("/"): return dealing_tg_command(msg_text[1:], chat_id, user_parameters, token, engine, message_id)
        elif msg_text.lower().startswith("http"): return dealing_tg_command_http(msg_text.split()[0], chat_id, user_parameters, token, engine, message_id)
        
        elif msg_text.lower() not in GREETINGS_OR_ANSWERS and msg_text.lower() in WORDS_SET: return check_word_in_vocabulary(msg_text, chat_id, engine, token, user_parameters)

        session_name = user_parameters.get('session_name', '')
        if session_name: 
            send_message_markdown(chat_id, f"Back to `{session_name}`", token)
            user_parameters['message_id'] += 1
            return session_conversation(chat_id, msg_text, session_name, token, engine, ASSISTANT_DOCUMENT_MODEL, user_parameters)

    if 'animation' in update_message: animation_file_id = update_message['animation'].get('file_id')
    elif 'photo' in update_message: img_file_id = update_message['photo'][-1].get('file_id')
    elif 'document' in update_message: doc_file_id = update_message['document'].get('file_id')
    elif 'video' in update_message: video_file_id = update_message['video'].get('file_id')
    elif 'voice' in update_message: voice_file_id = update_message['voice'].get('file_id')
    elif 'audio' in update_message: audio_file_id = update_message['audio'].get('file_id')
    elif 'sticker' in update_message: sticker_file_id = update_message['sticker'].get('file_id')
    elif 'contact' in update_message: contact = update_message['contact']
    elif 'location' in update_message: location = update_message['location']
    elif 'poll' in update_message: poll = update_message['poll']


    if img_file_id:  # If the message contains an image
        print(f"Image file id: {img_file_id}")
        if not user_ranking >= 3 and not openai_api_key: reply = f"Sorry, this function is only for /Gold or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
        else:
            img_folder = os.path.join(output_dir, 'images')
            photo_file_name = str(int(datetime.now().timestamp())) + '.jpg'

            file_path = download_image(img_file_id, img_folder, photo_file_name, token=token)
            print(f"File path: {file_path}")
            if os.path.isfile(file_path): 
                if caption and caption.lower() in ['mirror', 'flip', 'mirror image', 'flip image']:
                    file_path = mirror_image(file_path)
                    if os.path.isfile(file_path): send_image_from_file(chat_id, file_path, "Here is the mirrored image.", token)
                    return
                
                elif caption and caption.startswith('cover'):
                    slug = caption.replace('cover', '').strip()
                    if not slug: return send_message(chat_id, "You need to provide a slug for the cover image.", token)

                    reply_dict = change_cover_image_by_url(chat_id, slug, file_path, user_parameters)
                    if reply_dict['Status']:  reply_dict['Message'] = f"Cover image updated successfully:\n{reply_dict['Message']}"
                    return send_message(chat_id, reply_dict['Message'], token)

                send_message(chat_id, "Image received, extracting text from the image now...", token)
                message_id += 1
                cleaned_text = azure_cognitive_ai_extract_text(file_path)
                if cleaned_text: 
                    system_prompt = f"You are professional text editor, you will get text extracted by orc from the image, and you will reorganize, reparagraph the text to make it more human readable and understandable."
                    cleaned_text = openai_gpt_chat(system_prompt, cleaned_text, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
                    send_message_markdown(chat_id, f"Text extracted from the image:\n\n{cleaned_text[:4000]}", token, message_id)
                    caption = caption if caption else update_message.get('caption')
                    if caption and caption.lower() in ['creator_post_journal', 'creator_post_story', 'creator_post_news', 'journal', 'story', 'news']:
                        if caption.lower() in ['journal', 'creator_post_journal']: post_journal_to_ghost_creator_front(cleaned_text, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, message_id, user_parameters, is_journal = True)
                        elif caption.lower() in ['story', 'creator_post_story']: post_journal_to_ghost_creator_front(cleaned_text, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, message_id, user_parameters, is_journal = False)
                        elif caption.lower() in ['news', 'creator_post_news']: post_news_to_ghost_creator_front(cleaned_text, chat_id, engine, token, user_parameters)
                        
                        return
                    
                    elif not caption or caption.lower() in ['menu', 'dish', 'food', 'visualize', 'food menu', 'menu dish', 'menu food', 'food dish', 'dish menu', 'dish food']:
                        dish_list = openai_gpt_chat(SYSTEM_PROMPT_MENU_DISH_LIST, cleaned_text, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
                        if dish_list: 
                            dish_list = dish_list.split('\n')
                            dish_list = [dish.strip('\n').strip() for dish in dish_list if dish.strip('\n').strip()]
                            length_dish_list = len(dish_list)
                            if length_dish_list > 9: notification_msg = f"Found {length_dish_list} dishes in the menu, but only the first 9 dishes will be visualized."
                            else: notification_msg = f"Found {length_dish_list} dishes in the menu, visualizing the dishes now..."
                            send_message(chat_id, notification_msg, token)
                            
                            for index, dish in enumerate(dish_list):
                                if index >= 9: break

                                dish_description_list = dish.split(':')

                                dish_name = dish_description_list[0].strip().lower()
                                if not dish_name: continue

                                dish_description = dish_description_list[-1].strip()

                                dish_name = dish_name.replace(' ', '_').replace('\\', '_').replace('/', '_')
                                output_file = os.path.join(dish_images_dir, f"{dish_name}.jpg")

                                dish_name_with_price = dish_name + ' ' + dish_description

                                if not os.path.isfile(output_file): 
                                    try: output_file = generate_image_replicate(f"A Dish of {dish}", output_file, model = "black-forest-labs/flux-pro", width = 1024, height = 720, api_token = REPLICATE_API_TOKEN)
                                    except Exception as e: print(f"Error in generating image for dish: {e}")
                                
                                if os.path.isfile(output_file): send_image_from_file(chat_id, output_file, f"{index + 1}/{length_dish_list}. /{dish_name_with_price}", token)
                        return

                    elif user_ranking >= 3: 
                        slug = caption.replace(BLOG_BASE_URL, '').replace('/', '').strip()
                        df = query_user_post_id_with_slug(slug, chat_id, engine)
                        if not df.empty:
                            post_id = df['id'].values[0]
                            file_path = crop_image(file_path, crop_to_width=1600, crop_to_height=900, vertical_crop_top=True)
                            image_url = upload_image_to_ghost(file_path, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL)
                            reply_dict = update_story_cover_image_to_ghost(post_id, image_url, 'page', BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL)
                            if reply_dict['Status'] and image_midjourney_posted_updated(post_id, engine): return send_message(chat_id, f"The cover image for your story is updated.\n{reply_dict['Message']}", token)
                            return 
                    
                    elif user_ranking >= 66: 
                        caption = caption.replace('/', '').strip()
                        caption = caption.replace(' ', '_')
                        if caption.lower() in ['group_send_image', 'send_to_group', 'group_image', 'send_group_image', 'send_image_group']: send_img_to_everyone(file_path, token, engine)
                        else: reply = dealing_tg_photo(file_path, caption, chat_id, engine, token)
                        return 

                else: reply = "You need to provide a caption for the image. So I know what to do with it."


    elif doc_file_id:  # If the message contains a document
        print(f"Document file id: {doc_file_id}")
        if not user_ranking >= 3 and not openai_api_key: reply = f"Sorry, this function is only for /Gold or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
        else:
            doc_folder = os.path.join(output_dir, 'documents')
        
            doc_name = update_message.get('document').get('file_name')
            print(f"Document name: {doc_name}")

            file_path = download_file(doc_file_id, doc_folder, doc_name, token)
            if not file_path or not os.path.isfile(file_path): return send_message(chat_id, f"Failed to download the file. File name: \n\n{doc_name}", token)

            caption = caption if caption else update_message.get('caption') or 'no_caption'
        
            _, file_extension = os.path.splitext(file_path)
            file_extension = file_extension.lower()
            print(f"File extension: {file_extension}")


            if file_extension in ['.json']:
                if doc_name in ['google_sheet_credentials.json', 'google_sheet_credentials.json.json']:
                    new_folder = os.path.join(output_dir, 'google_sheet_credentials')
                    if not os.path.exists(new_folder): os.makedirs(new_folder)
                    new_file_path = os.path.join(new_folder, 'google_sheet_credentials.json')
                    os.rename(file_path, new_file_path)
                    delete_message(chat_id, message_id, token)
                    set_credentials_json_for_chat_id(chat_id, new_file_path, engine)
                    return send_message(chat_id, "Google Sheet credentials file has been set successfully.", token)
                return send_message(chat_id, ".json file is received, but the name is not correct, if you want to setup your google sreadsheet credentials, please name the file as `google_sheet_credentials.json`", token)


            elif doc_name in ["creator_post_journal.txt", "creator_post_news.txt", "creator_post_story.txt", "journal.txt", "story.txt", "news.txt"] or caption in ['creator_post_journal', 'creator_post_news', 'creator_post_story', 'news', 'journal', 'story']:
                with open(file_path, 'r') as f: prompt_text = f.read()
                
                if doc_name in ["creator_post_journal.txt", "journal.txt"] or caption in ['creator_post_journal', 'journal']: post_journal_to_ghost_creator_front(prompt_text, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, '', user_parameters, is_journal = True)
                elif doc_name in ["creator_post_story.txt", "story.txt"] or caption in ['creator_post_story', 'story']: post_journal_to_ghost_creator_front(prompt_text, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, '', user_parameters, is_journal = False)
                elif doc_name in ["creator_post_news.txt""news.txt"] or caption in ['creator_post_news', 'news']: post_news_to_ghost_creator_front(prompt_text, chat_id, engine, token, user_parameters)
                return 
            
            
            elif doc_name in ["my_writing_style.txt"] or caption in ['my_writing_style', 'writing style', 'my writing style']:
                print(f"Writing style file path: {file_path}")
                if not user_ranking >= 5 and not openai_api_key: reply = f"Sorry, this function is only for /Diamond or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
                else:
                    with open(file_path, "r", encoding="utf-8") as file: writing_style_sample = file.read()
                    writing_style_sample = writing_style_sample[:10000]
                    user_parameters['writing_style_sample'] = update_writing_style_sample(chat_id, writing_style_sample, engine)
                    return send_message(chat_id, f"Your writing style file has been received. Now you can use \n/creator_post_journal \n/creator_post_news \n/creator_post_story\n/creator_post_youtube\ncommands to generate content based on your writing style.", token)


            elif doc_name in ["system_prompt_auto_post.txt"] or caption in ['system_prompt_auto_post']:
                if not user_ranking >= 5 and not openai_api_key: reply = f"Sorry, this function is only for /Diamond or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
                else:
                    with open(file_path, "r", encoding="utf-8") as file: system_prompt_auto_post = file.read()
                    user_parameters['system_prompt_auto_post'] = update_system_prompt_auto_post(chat_id, system_prompt_auto_post, engine)
                    return send_message(chat_id, f"Your system prompt for you auto post has been updated. Now please send \n\n/creator_auto_post series_name \n\nto get it started.", token)


            elif doc_name in ["proof_of_reading.txt", "proof_reading.txt", "proof_read.txt"] or caption in ['proof_of_reading', 'proof of reading', 'proof_read', 'proof_reading']:
                print(f"Proof of reading file path: {file_path}")
                if not user_ranking >= 4 and not openai_api_key: reply = f"Sorry, this function is only for /Platinum or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
                else:
                    send_message(chat_id, "Proof reading file received, the AI assistant is proofreading the content, please wait 1~2 minutes...", token)
                    with open(file_path, "r", encoding="utf-8") as file: text_content = file.read()
                    return proof_read_ghost(text_content, chat_id, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL, engine, token, ASSISTANT_MAIN_MODEL, message_id + 1, user_parameters)


            elif doc_name in ["generate_audio.txt", "generate_audio_male.txt", "generate_audio_female.txt"] or caption in ['generate_audio_female', 'generate_audio_male', 'generate_audio']:
                if not user_ranking >= 3 and not openai_api_key: reply = f"Sorry, this function is only for /Gold or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
                else:
                    send_message(chat_id, "Audio generation file received, the AI assistant is generating the audio, please wait 1~2 minutes...", token)
                    with open(file_path, "r", encoding="utf-8") as file: text_content = file.read()

                    language_code = identify_language(text_content)
                    language_name = REVERSED_LANGUAGE_DICT.get(language_code, 'english') or 'english'
                    send_message(chat_id, f"Detected language: {language_name.capitalize()}, generating...", token, message_id + 1)

                    default_audio_gender = user_parameters.get('default_audio_gender') or 'male'
                    voice_name = SUPPORTED_LANGUAGE_AZURE_VOICE_DICT.get(language_name, {}).get(default_audio_gender, [AZURE_VOICE_MALE]) or [AZURE_VOICE_MALE]
                    voice_name = voice_name[0]
                    audio_file = azure_text_to_speech(text_content, audio_file_path, service_region = "westus", speech_key = AZURE_VOICE_API_KEY_1, voice_name = voice_name, engine = engine, token = token, user_parameters = user_parameters)
                    
                    if audio_file and os.path.isfile(audio_file): return send_audio_from_file(chat_id, audio_file, token)
                    else: return send_message(chat_id, "Failed to generate the audio, please try again later.", token)


            elif file_extension in ASSISTANT_FILE_SEARCH_SUPPORTED_FILES: 
                if user_ranking < 4: return send_message(chat_id, f"Sorry, this function is only for /Platinum or above users, and your /tier is /{tier}\n\n{commands_dict.get('get_premium')}", token)

                if file_extension in ['.docx', '.pdf']:
                    doc_id = handle_doc_upload(chat_id, file_path, engine, user_parameters)
                    if not doc_id: return send_message(chat_id, "OpenAI failed to process the document, maybe it's too big or the doc type is not supported.", token)
                    session_name = 'session_query_doc'
                    update_session_name(chat_id, session_name, engine)
                    send_message_markdown(chat_id, f"You just entered in `{session_name}` session. Now the AI assistant is summarizing the key points of this DOCUMENT:\n\n`{doc_name}`", token)
                    user_parameters['session_document_id'] = doc_id
                    user_parameters['message_id'] += 1
                    return session_conversation(chat_id, DEFAULT_PROMPT_DOCUMENT, session_name, token, engine, model = ASSISTANT_DOCUMENT_MODEL, user_parameters = user_parameters)

            elif file_extension not in TELEGRAM_SUPPORTED_FILES: return send_message(chat_id, f"Sorry, the file format is not supported so far. Talk to {OWNER_HANDLE} if you want to add this feature. Supported file types: \n\n{TOTAL_SUPPORTED_FILES_STRING}", token)

            elif caption in ['subtitle to text'] and file_extension in ['.srt', '.vtt']:
                sub_content = subtitle_to_text(file_path)
                current_folder = os.path.dirname(file_path)
                # save to a txt file
                txt_file_path = os.path.join(current_folder, 'text_from_subtitle.txt')
                with open(txt_file_path, 'w') as f: f.write(sub_content)
                return send_document_from_file(chat_id, txt_file_path, "Here is the text file extracted from the subtitle file.", token)


            elif caption in COUNT_COMMANDS:
                words_len, character_len = 0, 0
                txt_file_path = ''

                if file_extension == '.txt': 
                    words_len, character_len, text = count_words(file_path)
                    if words_len and character_len: reply = send_message(chat_id, f"Your file contains {words_len} words and {character_len} characters.", token)
                    if txt_file_path: reply = send_document_from_file(chat_id, txt_file_path, "Here is the text file extracted from the document.", token)
            
            
            elif caption in REVISE_COMMANDS:
                if file_extension in ['.txt']: 
                    reply = revise_text(file_path, chat_id, REVISE_TEXT_CHARACTERS_LIMIT, user_parameters)
                    if reply.endswith('.txt') and os.path.isfile(reply): reply = send_document_from_file(chat_id, reply, "Mission Accomplished!", token)

            else:
                starting_time = datetime.now()
                if caption in SUPPORTED_LANGUAGE_DICT:
                    words_limit = TRANSLATE_SRT_WORDS_LIMIT
                    if file_extension in ['.srt', '.vtt']: 
                        if user_ranking < 4: return send_message(chat_id, f"Sorry, this function is only for /Platinum or above users, and your /tier is /{tier}\n\n{commands_dict.get('get_premium')}", token)

                        try:
                            send_message(chat_id, f"Translating the srt file to {caption.capitalize()}, this process may take 1~10 minutes, depending on the file size, please wait patiently...", token)
                            file_path_cn = translate_srt_file(file_path, caption, chat_id, TRANSLATE_SRT_WORDS_LIMIT, engine, user_parameters)
                            if os.path.isfile(file_path_cn): 
                                finishing_time = datetime.now()
                                time_used = finishing_time - starting_time
                                time_used_seconds = int(time_used.total_seconds())
                                reply = send_document_from_file(chat_id, file_path_cn, f"Mission Accomplished! in {time_used_seconds} seconds", token)
                        except Exception as e: reply = f"Failed to translate the srt file, maybe it's too long, limit is 8000 words.\n\nError code:\n{e}"

                    elif file_extension == '.txt': 
                        send_message(chat_id, f"Translating the text file to {caption.capitalize()}, this process may take 1~10 minutes, depending on the file size, please wait patiently...", token)
                        words_limit = 8000
                        try:
                            reply = translate_long_text_file(file_path, caption, chat_id, words_limit, user_parameters)
                            if reply.endswith('.txt') and os.path.isfile(reply): 
                                finishing_time = datetime.now()
                                time_used = finishing_time - starting_time
                                time_used_seconds = int(time_used.total_seconds())
                                reply = send_document_from_file(chat_id, reply, f"TRANSLATION: Mission Accomplished! in {time_used_seconds} seconds", token)
                        except Exception as e: reply = f"Failed to translate the txt file, maybe it's too long, limit is {words_limit} words.\n\nError code:\n{e}"
                        return send_message(chat_id, reply, token)

                else: reply = f"Sorry, your inputed caption is not a supported language or code. The supported languages are:\n\n{SUPPORTED_LANGUAGE_STRING}\n\nYou can either put the language name or the language code in the caption box when you send the document file."

    elif voice_file_id:  # If the message contains an audio file
        print(f"Voice file id: {voice_file_id}")
        if not user_ranking >= 2 and not openai_api_key: reply = f"Sorry, this function is only for /Silver or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
        else:
            voice_folder = os.path.join(output_dir, 'voice')
            voice_file_name = str(int(datetime.now().timestamp())) + '.ogg'

            send_message(chat_id, "Voice file received, downloading...", token)
            message_id += 1
            user_parameters['message_id'] = message_id

            file_path = download_file(voice_file_id, voice_folder, voice_file_name, token)
            if not file_path or not os.path.isfile(file_path): reply = "Failed to read out the file."
            else:
                if user_parameters.get('is_waiting_for') and user_parameters.get('is_waiting_for') == 'voice_clone_sample': return save_clone_voice_sample(file_path, chat_id, engine, token)
                else:
                    send_message(chat_id, "Transcribing the voice file, this process may take a while, please wait patiently...", token, message_id)
                    msg_text = whisper_speech_to_text(file_path, chat_id, model='whisper-1', engine=engine, user_parameters=user_parameters)
                    if not msg_text: reply = "Failed to transcribe the audio file."
                    elif user_parameters.get('session_name', ''):  return session_conversation(chat_id, msg_text, user_parameters.get('session_name', ''), token, engine, ASSISTANT_DOCUMENT_MODEL, user_parameters)
                    else: send_message(chat_id, f"You just said:\n------\n{msg_text}", token, message_id)

    elif audio_file_id:  # If the message contains an audio file
        print(f"Audio file id: {audio_file_id}")
        if not user_ranking >= 3 and not openai_api_key: reply = f"Sorry, this function is only for /Gold or above users but your current /tier is /{tier}\n\n{commands_dict.get('get_premium')}"
        else:
            audio_folder = os.path.join(output_dir, 'music')
            audio_file_name = update_message.get('audio').get('file_name')

            file_path = download_file(audio_file_id, audio_folder, audio_file_name, token)
            if not file_path or not os.path.isfile(file_path): reply = "Failed to download the audio file."
            else:
                file_size = os.path.getsize(file_path)
                if file_size > 100 * 1024 * 1024: reply = "The audio file is too large, please upload a file smaller than 100MB."
                else:
                    caption = caption if caption else update_message.get('caption', '')
                    if not caption: caption = 'transcript'
                    if caption.startswith('/'): caption = caption[1:].strip()
                    if not caption: caption = 'transcript'

                    audio_file_path = file_path
                    json_file_path = file_path.split('.')[0] + '.json'
                    srt_file_name = file_path.split('.')[0] + '.srt'
                    starting_time = datetime.now()

                    if caption in ['srt', 'subtitle', 'subtitles']:
                        send_message(chat_id, "Generating the srt file, this process may take 2~3 minutes, please wait patiently...", token)
                        srt_file_name = get_srt_from_audio(audio_file_path, subtitle_format='srt', chars_per_caption=60, chat_id=chat_id, api_key=ASSEMBLYAI_API_KEY, engine=engine, transcript_id=transcript_id)
                        if srt_file_name: 
                            finishing_time = datetime.now()
                            time_used = finishing_time - starting_time
                            time_used_seconds = int(time_used.total_seconds())
                            return send_document_from_file(chat_id, srt_file_name, f"SUBTITLE: Mission Accomplished! in {time_used_seconds} seconds", token)

                    elif caption == 'transcript' or caption in SUPPORTED_LANGUAGE_DICT:
                        send_message(chat_id, "Transcribing the audio file, this process may take 2~3 minutes, please wait patiently...", token)
                        transcript_id = transcribe_audio_file(audio_file_path, json_file_path, chat_id, ASSEMBLYAI_API_KEY, engine)
                        transcript_text, transcript_file_path_raw = get_raw_text_from_json(json_file_path)

                        if transcript_text:
                            send_message(chat_id, "Reorganizing the transcript, this process may take 1~2 minutes, please wait patiently...", token, str(int(message_id) + 1))
                            punctuated_text = punctuate_text(transcript_text, chat_id, '', user_parameters)
                            file_path_txt = transcript_text[:30] + '.txt'
                            file_path_txt = os.path.join(audio_folder, file_path_txt)
                            with open(file_path_txt, 'w') as f: f.write(punctuated_text)
                            if os.path.isfile(file_path_txt): send_document_from_file(chat_id, file_path_txt, "TRANSCRIPTION: Finished!", token)
                            else: return send_message(chat_id, "Failed to generate the txt file, please try again later.", token)

                            if caption == 'transcript': return
                            elif caption in SUPPORTED_LANGUAGE_DICT:
                                send_message(chat_id, f"{caption.title()} a supported language, now translating the text to {caption}, this process may take 1~3 minutes, depending on the file size, please wait patiently...", token)
                                try:
                                    file_path_translated = translate_long_text_file(file_path_txt, caption, chat_id, words_limit = 8000, user_parameters = user_parameters)
                                    if os.path.isfile(file_path_translated): 
                                        finishing_time = datetime.now()
                                        time_used = finishing_time - starting_time
                                        time_used_seconds = int(time_used.total_seconds())
                                        return send_document_from_file(chat_id, file_path_translated, f"TRANSLATION: Mission Accomplished! in {time_used_seconds} seconds", token)
                                except Exception as e: reply = f"Failed to translate the txt file, maybe it's too long, limit is 8000 words.\n\nError code:\n{e}"
                            else: reply  = f"Sorry, the caption is not a supported language or code. The supported languages are:\n\n{LANGUAGE_SRING}\n\nYou can only put the language name in the caption box when you send the audio file. Otherwise, I don't know what to do with it."
                        else: reply = f"Failed to transcribe the audio file. Maybe it's too long or the quality is too low."

    elif sticker_file_id: 
        '''Received message: 
        {
        "update_id": 843019561,
        "message": {
            "message_id": 2383,
            "from": {
                "id": 2118900665,
                "is_bot": false,
                "first_name": "Old_Bro_Leo",
                "username": "laogege6",
                "language_code": "en",
                "is_premium": true
            },
            "chat": {
                "id": 2118900665,
                "first_name": "Old_Bro_Leo",
                "username": "laogege6",
                "type": "private"
            },
            "date": 1729095275,
            "sticker": {
                "width": 512,
                "height": 512,
                "emoji": "\ud83d\udc4d",
                "set_name": "Homer_Jay_Simpson",
                "is_animated": false,
                "is_video": false,
                "type": "regular",
                "thumbnail": {
                    "file_id": "AAMCAgADGQEAAglPZw_mazv2WdNFSyp-_znQNc5TZ3sAAoYDAAJHFWgJfRJ-DwrwgZYBAAdtAAM2BA",
                    "file_unique_id": "AQADhgMAAkcVaAly",
                    "file_size": 6324,
                    "width": 128,
                    "height": 128
                },
                "thumb": {
                    "file_id": "AAMCAgADGQEAAglPZw_mazv2WdNFSyp-_znQNc5TZ3sAAoYDAAJHFWgJfRJ-DwrwgZYBAAdtAAM2BA",
                    "file_unique_id": "AQADhgMAAkcVaAly",
                    "file_size": 6324,
                    "width": 128,
                    "height": 128
                },
                "file_id": "CAACAgIAAxkBAAIJT2cP5ms79lnTRUsqfv850DXOU2d7AAKGAwACRxVoCX0Sfg8K8IGWNgQ",
                "file_unique_id": "AgADhgMAAkcVaAk",
                "file_size": 38432
            }}}'''    
        emoji = update_message['sticker'].get('emoji', '')
        set_name = update_message['sticker'].get('set_name', '')
        msg_text = f"User just sent a sticker from the set {set_name}, emoji: {emoji}"

    elif animation_file_id: 
        '''Received message: {
            "update_id": 843019584,
            "message": {
                "message_id": 2423,
                "from": {
                    "id": 2118900665,
                    "is_bot": false,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "language_code": "en",
                    "is_premium": true
                },
                "chat": {
                    "id": 2118900665,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "type": "private"
                },
                "date": 1729099574,
                "animation": {
                    "file_name": "homer-simpson-thinking.mp4",
                    "mime_type": "video/mp4",
                    "duration": 3,
                    "width": 320,
                    "height": 276,
                    "file_id": "CgACAgQAAxkBAAIJUWcP5pSWKy0X4ST9cND2Y-awXScbAAIfAwACBeu1UgeOY5kibqF2NgQ",
                    "file_unique_id": "AgADHwMAAgXrtVI",
                    "file_size": 138924
                },
                "document": {
                    "file_name": "homer-simpson-thinking.mp4",
                    "mime_type": "video/mp4",
                    "file_id": "CgACAgQAAxkBAAIJUWcP5pSWKy0X4ST9cND2Y-awXScbAAIfAwACBeu1UgeOY5kibqF2NgQ",
                    "file_unique_id": "AgADHwMAAgXrtVI",
                    "file_size": 138924
                }
            }
        }'''
        file_name = update_message['animation'].get('file_name', '')
        mime_type = update_message['animation'].get('mime_type', '')
        msg_text = f"User just sent an animation meme: {file_name}, type: {mime_type}"

    elif contact: 
        ''' Received message: {
            "update_id": 843019592,
            "message": {
                "message_id": 2439,
                "from": {
                    "id": 2118900665,
                    "is_bot": false,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "language_code": "en",
                    "is_premium": true
                },
                "chat": {
                    "id": 2118900665,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "type": "private"
                },
                "date": 1729100406,
                "contact": {
                    "phone_number": "+8613701959595",
                    "first_name": "Allen\u6731\u5578\u864e",
                    "vcard": "BEGIN:VCARD \nVERSION:3.0 \nPRODID:-//Apple Inc.//iPhone OS 18.0.1//EN \nN:;Allen\u6731\u5578\u864e;;; \nFN:Allen\u6731\u5578\u864e \nitem1.EMAIL;type=INTERNET;type=pref:allen.xh.zhu@gmail.com \nitem1.X-ABLabel:\u5176\u4ed6 \nitem2.EMAIL;type=INTERNET:allen@gsrventures.cn \nitem2.X-ABLabel:\u5176\u4ed6 \nitem3.EMAIL;type=INTERNET:xiaohu_zhu@yahoo.com \nitem3.X-ABLabel:\u5176\u4ed6 \nitem4.TEL;type=pref:+8613701959595 \nitem4.X-ABLabel:\u79fb\u52a8\u7535\u8bdd \nADR;type=HOME;type=pref:;;\u5317\u4eac\u6d77\u6dc0\u533a\u4e2d\u5173\u6751\u4e1c\u8def1\u53f7\u6e05\u534e\u79d1\u6280\u56ed\u79d1\u6280\u5927\u53a6907\u5ba4\\n;;;; \nEND:VCARD \n",
                    "user_id": 5387969301
                }
            }
        }'''
        msg_text = f"User just sent a contact: {contact.get('first_name', '')}, {contact.get('last_name', '')}, phone number: {contact.get('phone_number', '')}"
        vcard_data = contact.get('vcard', '')
        if vcard_data: 
            formatted_response = extract_vcard_info(vcard_data)
            if formatted_response: send_message(chat_id, formatted_response, token)

    elif poll:
        poll_summary = wrap_poll_message_to_string(poll)
        msg_text = f"User just sent a poll: {poll_summary}"

    elif location: 
        ''' Received message: {
            "update_id": 843019599,
            "message": {
                "message_id": 2453,
                "from": {
                    "id": 2118900665,
                    "is_bot": false,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "language_code": "en",
                    "is_premium": true
                },
                "chat": {
                    "id": 2118900665,
                    "first_name": "Old_Bro_Leo",
                    "username": "laogege6",
                    "type": "private"
                },
                "date": 1729101889,
                "location": {
                    "latitude": 37.431836,
                    "longitude": -122.20115
                },
                "venue": {
                    "location": {
                        "latitude": 37.431836,
                        "longitude": -122.20115
                    },
                    "title": "Flea Street Cafe",
                    "address": "3607 Alameda De Las Pulgas",
                    "foursquare_id": "4ac7f846f964a520ecba20e3",
                    "foursquare_type": "food/newamerican"
                }
            }
        }'''
        latitude = location.get('latitude', '')
        longitude = location.get('longitude', '')
        venue = update_message.get('venue', '')
        if venue: 
            venue_title = venue.get('title', '')
            venue_address = venue.get('address', '')
            venue_foursquare_type = venue.get('foursquare_type', '')
            msg_text = f"User just sent a location with latitude: {latitude}, longitude: {longitude}, venue: {venue_title}, address: {venue_address}, foursquare_type: {venue_foursquare_type}, maybe he/she is here or want to talk about this place."
        else: msg_text = f"User just sent a location with latitude: {latitude}, longitude: {longitude}, maybe he/she is here or want to talk about this place."
        
    elif video_file_id: reply = "I'm sorry, I can't process video files directly. Please send me a youtube link or youtube video ID instead."

    if reply:
        if reply == 'DONE': return
        else : return send_message(chat_id, reply, token)
    else:
        ai_response = openai_gpt_function(msg_text, chat_id, tools = FUNCTIONS_TOOLS, model = ASSISTANT_MAIN_MODEL, engine = engine, token = token, user_parameters = user_parameters)
        if ai_response and isinstance(ai_response, dict): 
            action = ai_response.get('action', '')
            reply = ai_response.get('response', '')
            if action == 'run_command': return dealing_tg_command(reply[1:], chat_id, user_parameters, token, engine, message_id)
            elif action == 'ask_gpt': reply = openai_gpt_chat(f"Try your best to assistant the user, follow user's prompt.", msg_text, chat_id, model = ASSISTANT_MAIN_MODEL, user_parameters = user_parameters, token = token) 
            return send_message(chat_id, reply, token)
        

def handle_update(update, token, engine = engine):
    callback_query = update.get("callback_query")
    if callback_query: 
        try: handle_callback_query(callback_query, token, engine)
        except Exception as e: print(f"Error in handle_callback_query: {e}")

    elif update.get("message"): 
        try: handle_message(update, token, engine)
        except Exception as e: print(f"Error in handle_message: {e}")

    elif "inline_query" in update:
        try: handle_inline_query(update["inline_query"], token, engine)
        except Exception as e: print(f"Error in handle_inline_query: {e}")

    return 


# 使用多线程处理每条消息
async def telegram_bot():
    token = TELEGRAM_BOT_TOKEN
    last_update_id = None

    while True:
        updates = await asyncio.to_thread(get_updates, token, last_update_id)
        for update in updates:
            if 'message' in update or 'callback_query' in update or 'inline_query' in update:
                last_update_id = update['update_id'] + 1

                # 将每个用户的任务提交到线程池中执行
                asyncio.get_event_loop().run_in_executor(executor, handle_update, update, token, engine)


if __name__ == "__main__":
    print("Telegram bot is working...")
    asyncio.run(telegram_bot())
