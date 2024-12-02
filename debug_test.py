from ghost_blog import *


def text_auto_blog_post(chat_id: str, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), model=ASSISTANT_MAIN_MODEL_BEST, user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

    post_language = user_parameters.get('default_post_language') or 'English'
    post_type = user_parameters.get('default_post_type') or 'page'
    visibility = user_parameters.get('default_post_visibility') or 'public'
    audio_switch = user_parameters.get('default_audio_switch') or 'off'
    publish_status = user_parameters.get('default_publish_status') or 'published'
    cartoon_style = user_parameters.get('cartoon_style') or 'Pixar Style'
    default_image_model = user_parameters.get('default_image_model') or 'Blackforest'
    user_name = user_parameters.get('name') or 'User'

    system_prompt_auto_post = user_parameters.get('system_prompt_auto_post') or ''
    if not system_prompt_auto_post: return send_message(chat_id, f"Sorry, you haven't set the system prompt for auto post. Please set it first.", token)

    series_name = user_parameters.get('auto_post_series_name') or ''
    if not series_name: return send_message(chat_id, f"Sorry, you haven't set the series name for auto post. Please set it first.", token)

    titles_list_string_prefix = 'TITLES AND EXCERPTS OF ALL PREVIOUS ENTRIES:\n'
    titles_list_string = ''
    try: df = pd.read_sql(text(f"SELECT title, custom_excerpt FROM creator_auto_posts WHERE chat_id = :chat_id AND series_name = :series_name ORDER BY updated_time ASC LIMIT 365"), engine, params={'chat_id': chat_id, 'series_name': series_name})
    except: df = pd.DataFrame()
    if not df.empty: 
        yestoday_title = df['title'].values[0]
        titles_list_string += "\n".join([f"- {row['title']}: {row['custom_excerpt']}" for _, row in df.iterrows()])
    else: 
        yestoday_title = ''
        titles_list_string += 'There is no previous entries. You are generating the first entry.'

    titles_list_string = calculate_token_and_cut_input_string(titles_list_string, model)
    titles_list_string = titles_list_string_prefix + titles_list_string

    print(f"yestoday_title: {yestoday_title}\n\n")
    print(titles_list_string)

    day_count = df.shape[0] + 1

    # get the latest 3 posts from creator_auto_posts with the same chat_id, series_name
    try: df = pd.read_sql(text(f"SELECT title, generated_journal, updated_time FROM creator_auto_posts WHERE chat_id = :chat_id AND series_name = :series_name ORDER BY updated_time DESC LIMIT 3"), engine, params={'chat_id': chat_id, 'series_name': series_name})
    except: df = pd.DataFrame()
    if not df.empty:
        # reorder do ascending order
        df = df.sort_values(by='updated_time', ascending=True)
        generated_journal = "\n\n\n\n".join([f"Title: {row['title']}\n\n{row['generated_journal']}" for _, row in df.iterrows()])
    else: generated_journal = ''

    generated_journal_token = calculate_token(generated_journal)
    print(f"generated_journal_token: {generated_journal_token}\n\n")

    auto_prompt = f"Today is Day {day_count}, below is the titles of all previous entires and the latest 3 entries."
    if yestoday_title: auto_prompt = f"Title of yestory's entry: {yestoday_title}, follow yesterday's entry but start a new sector.\n\n" + auto_prompt

    auto_prompt += f"\n\n{titles_list_string}\n\n{generated_journal}"

    print(f"auto_prompt: \n\n\n\n{auto_prompt}")



chat_id = DOLLARPLUS_CHAT_ID
user_parameters = user_parameters_realtime(chat_id, engine)
text_auto_blog_post(chat_id, engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), model=ASSISTANT_MAIN_MODEL_BEST, user_parameters = user_parameters)
