from ghost_blog import *
from ghost_deployment import *
from domain_name import *

def get_video_dimensions(video_file):
    probe = ffmpeg.probe(video_file)
    video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
    if not video_streams: raise ValueError(f"No video streams found in {video_file}")
    # Assuming the first video stream is what you want
    width = int(video_streams[0]['width'])
    height = int(video_streams[0]['height'])
    return width, height


def merge_subtitle_to_video(str_file_path, font_size=50, bar_size=0.12, logo_position='right', logo_png='Logos/Enspiring_logo.png'):
    video_file = str_file_path.replace(".srt", ".mp4")
    final_video_file = str_file_path.replace(".srt", "_subtitle.mp4")
    ass_file = str_file_path.replace(".srt", ".ass")

    # Get video dimensions
    width, height = get_video_dimensions(video_file)

    # Assuming font size 50 for 1080p video
    base_height = 1080
    font_size = int((height / base_height) * font_size)

    # Calculate bar height (used for logo scaling)
    bar_height = int(height * bar_size)

    # Load SRT subtitle file
    subs = pysubs2.load(str_file_path, encoding="utf-8")

    # Define subtitle style
    style = pysubs2.SSAStyle()
    style.fontname = "Tahoma"
    style.fontsize = font_size
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)  # White font
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)  
    style.backcolor = pysubs2.Color(169, 169, 169, 0)  
    style.bold = False
    style.italic = False
    style.underline = False
    style.borderstyle = 3  # Opaque box
    style.outline = 1      
    style.shadow = 0       # No shadow
    style.alignment = 2    # Bottom center alignment
    style.marginl = 20     # Left margin
    style.marginr = 20     # Right margin
    style.marginv = 20     # Vertical margin from bottom
    style.encoding = 1

    # Apply style to default style
    subs.styles["Default"] = style

    # Set play resolution
    subs.info["PlayResX"] = str(width)
    subs.info["PlayResY"] = str(height)

    # Set automatic wrapping
    subs.info["WrapStyle"] = "0"

    # Save as ASS file
    subs.save(ass_file)

    # Build ffmpeg filter_complex
    filter_subtitles = f"[0:v]subtitles='{ass_file}'[base_video]"
    filter_scale_logo = f"[1:v]scale=-1:{bar_height}[logo_scaled]"

    # 根据logo_position参数设置Logo的位置
    if logo_position == 'left': overlay_x = '0'
    else: overlay_x = 'main_w-overlay_w'

    filter_overlay_logo = f"[base_video][logo_scaled]overlay=x={overlay_x}:y=0"
    # 合并所有过滤器
    filter_complex = ';'.join([filter_subtitles, filter_scale_logo, filter_overlay_logo])

    # Build ffmpeg command
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', video_file,
        '-i', logo_png,
        '-filter_complex', filter_complex,
        '-c:a', 'copy',
        final_video_file
    ]

    # Run ffmpeg command
    print("Adding subtitles and Logo to video...")
    subprocess.run(ffmpeg_cmd, check=True)
    print("Processing completed!")
    return final_video_file


def punctuate_text(text, chat_id:str = OWNER_CHAT_ID, file_path=None, user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    system_prompt = "Please punctuate the following text, only adding punctuation where necessary. Do not change the wording of the text. Make paragraphs if necessary and use double line breaks to separate paragraphs."
    punctuated_text = openai_gpt_chat(system_prompt, text, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
    # Save punctuated_text to file_path if provided
    if file_path:
        with open(file_path, "w", encoding='utf-8') as f: f.write(punctuated_text)
        print("Translated text has been saved to: ", file_path)
    return punctuated_text


def get_srt_from_audio(audio_file_path, subtitle_format='srt', chars_per_caption=60, chat_id = OWNER_CHAT_ID, api_key=ASSEMBLYAI_API_KEY, engine=engine, transcript_id=None):
    print(f"正在通过 AssemblyAI 提取音频文件的字幕...")
    json_file_path = audio_file_path.split('.')[0] + '.json'
    srt_file_name = audio_file_path.split('.')[0] + '.srt'

    if not transcript_id: transcript_id = transcribe_audio_file(audio_file_path, json_file_path, chat_id, api_key, engine)

    # Construct the URL
    url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}/{subtitle_format}"

    # Set up the headers
    headers = {
        'Authorization': api_key
    }

    # Set up the query parameters
    params = {
        'chars_per_caption': chars_per_caption
    }

    # Send the GET request
    response = requests.get(url, headers=headers, params=params)

    # Check if the request was successful
    if response.status_code != 200: response.raise_for_status()

    # Save the subtitles to the output file
    with open(srt_file_name, 'w', encoding='utf-8') as f: f.write(response.text)

    print("字幕文件已经取得并保存到本地！")
    return srt_file_name


def generating_new_post_from_url(youtube_url: str, video_temp_dir = video_dir, chat_id = OWNER_CHAT_ID, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine):
    if not youtube_url: return send_message(chat_id, "No url was provided.", token)

    user_parameters = user_parameters_realtime(chat_id, engine)
    reply_dict = download_youtube_video(youtube_url, video_temp_dir, chat_id, token, engine, user_parameters)
    if not reply_dict: return send_message(chat_id, f"Failed to download video file from YouTube link. What you input is: {youtube_url}, it's not a valid YouTube link.", token)

    video_title = reply_dict.get('Official_Title')
    post_url = reply_dict.get('URL')
    if post_url: 
        short_title = reply_dict.get('Official_Title', 'title')[:30]
        final_msg = f"Mission accomplished!\n[{short_title}]({post_url})\nClick the above title to view the webpage."
        send_message_markdown(chat_id, final_msg, token)
        return post_url

    if not reply_dict.get('Status'): return reply_dict.get('Reason')

    video_duration = reply_dict.get('Duration')
    mp3_file_path = reply_dict.get('Output_Audio_File')
    srt_file_path = reply_dict.get('Output_Srt_File')
    vtt_file_path = reply_dict.get('Output_Vtt_File')
    subtitle_format = reply_dict.get('Subtitle_Format')
    
    current_folder = os.path.dirname(mp3_file_path)

    reply_dict['current_folder'] = current_folder
    reply_dict['mp3_file_path'] = mp3_file_path
    reply_dict['chat_id'] = chat_id
    reply_dict['featured'] = False
    reply_dict['post_type'] = 'post' if chat_id in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID, DOLLARPLUS_CHAT_ID] else 'page'
    reply_dict['visibility'] = 'public' if chat_id in [OWNER_CHAT_ID] else 'paid' 

    logging.info(f"download_youtube_video() successfully returned!")

    assembly_json_file_path = mp3_file_path.replace(".mp3", "_assembly.json")
    caption_json_file_path = mp3_file_path.replace(".mp3", "_caption.json")

    subtitle_file_path = srt_file_path if subtitle_format == 'srt' else vtt_file_path

    if not os.path.isfile(subtitle_file_path):
        if os.path.isfile(mp3_file_path):
            
            if not os.path.isfile(assembly_json_file_path): 
                if reply_dict.get('paragraphed_transcript') and reply_dict.get('transcript_id'):
                    language_code = identify_language(reply_dict.get('paragraphed_transcript'))
                    data  = {'id': reply_dict.get('transcript_id'), 'text': reply_dict.get('paragraphed_transcript'), 'language_code': language_code}
                    with open(assembly_json_file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
                    get_raw_text_from_json(assembly_json_file_path)
                transcribe_audio_file(mp3_file_path, assembly_json_file_path, chat_id, ASSEMBLYAI_API_KEY, engine)
                if not os.path.isfile(assembly_json_file_path): return "Failed to get assembly json file from audio file!"

            reply_dict['assembly_json_file_path'] = assembly_json_file_path
    else:
        logging.info(f"VTT subtitle downloaded directly from YouTube, title: {video_title}")
        cleaned_text = subtitle_to_text(subtitle_file_path)
        language_code = identify_language(cleaned_text)
        if not language_code.startswith('en'): return send_message(chat_id, f"This is not an English video, sorry we only support English videos. The language code is: {language_code}", token)

        srt_dict = {'text': cleaned_text, 'language_code': language_code}
        with open(caption_json_file_path, 'w', encoding='utf-8') as f: json.dump(srt_dict, f, ensure_ascii=False, indent=4)

    video_duration_in_minutes = int(video_duration) // 60
    processing_time = video_duration_in_minutes // 10
    processing_time = max(processing_time, 2)

    in_process_reply = f"Dealing with your video: \n`{video_title[:30]}...`\nThis process might take _{processing_time}_ minutes..."
    send_message_markdown(chat_id, in_process_reply, token)

    json_file_path = reply_dict['assembly_json_file_path'] if reply_dict.get('assembly_json_file_path') else caption_json_file_path

    try:
        posts_generator_reply_dict = posts_generator(json_file_path, chat_id, model="gpt-4o-2024-08-06", engine=engine)
        if not posts_generator_reply_dict.get('Status'): return posts_generator_reply_dict.get('Reason')
    except Exception as e: return send_message(chat_id, f"posts_generator() >> error code: {e}", token)

    reply_dict.update(posts_generator_reply_dict)

    if not reply_dict.get('video_summary'): return "Failed to get video summary."
    if not reply_dict.get('vocabularies'): return "Failed to get vocabularies."
    if not reply_dict.get('paragraphed_transcript'): return "Failed to get paragraphed transcript."
    if not reply_dict.get('transcript_tags'): return "Failed to get tags for the post."

    print(f"posts_generator() successfully returned with results!")

    processing_json_file_path = mp3_file_path.replace(".mp3", "_processing.json")
    with open(processing_json_file_path, 'w', encoding='utf-8') as f: json.dump(reply_dict, f, ensure_ascii=False, indent=4)

    return continue_post_from_processing_pause(processing_json_file_path, chat_id, token, engine, user_parameters)


def continue_post_from_processing_pause(processing_json_file_path: str, chat_id = OWNER_CHAT_ID, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine, user_parameters = {}):
    if not os.path.isfile(processing_json_file_path): return "The processing json file does not exist."
    with open(processing_json_file_path, 'r', encoding='utf-8') as f: reply_dict = json.load(f)

    # from processing_json_file_path get current_folder
    current_folder = os.path.dirname(processing_json_file_path)
    reply_dict['current_folder'] = current_folder

    mp3_file_path = ''
    # from current_folder get mp3_file_path
    for f in os.listdir(current_folder):
        if f.endswith('.mp3'): mp3_file_path = os.path.join(current_folder, f)
    if not mp3_file_path: return "Failed to get mp3 file path."

    reply_dict['mp3_file_path'] = mp3_file_path

    mp3_file_path_basename = os.path.basename(mp3_file_path)
    mp3_file_path = os.path.join(current_folder, mp3_file_path_basename)

    img_url = reply_dict.get('Image_URL')
    video_id = reply_dict.get('Video_ID')

    cover_png_file_path = mp3_file_path.replace('.mp3', '_cover.png')
    if not os.path.isfile(cover_png_file_path): cover_png_file_path = download_and_convert_image(img_url, cover_png_file_path)
    if not cover_png_file_path or not os.path.isfile(cover_png_file_path): return "Failed to download cover image from YouTube."

    print(f"download_and_convert_image() successfully returned!")

    blog_post_text_file_path = mp3_file_path.replace('.mp3', '_final.txt')
    if not os.path.isfile(blog_post_text_file_path): blog_post_text_file_path = generate_post_text_file(reply_dict)
    if not os.path.isfile(blog_post_text_file_path): return "Failed to generate blog post text file."

    reply_dict['blog_post_text_file_path'] = blog_post_text_file_path

    print(f"generate_post_text_file() successfully returned!")

    reply_dict_from_ghost = {}
    try: reply_dict_from_ghost = send_blog_post_from_dict(reply_dict, api_key=BLOG_POST_ADMIN_API_KEY, api_url=BLOG_POST_API_URL, engine=engine, user_parameters=user_parameters)
    except Exception as e: return send_debug_to_laogege(f"send_blog_post_from_dict() >> error code: {e}")
    if not reply_dict_from_ghost: return send_debug_to_laogege("Failed to send blog post to Ghost.")

    reply_dict.update(reply_dict_from_ghost)

    post_id = reply_dict.get('Post_ID')
    url = reply_dict.get('URL')

    print(f"send_blog_post_from_dict() successfully returned!")

    if reply_dict.get('Status') and post_id and url:
        ending_time = time.time()
        time_used = ending_time - reply_dict.get('Starting_Time')
        # time_used_in_minutes , how many minutes and seconds used
        time_used_in_minutes = time_used // 60
        time_used_in_seconds = time_used % 60

        short_title = reply_dict.get('Official_Title', 'title')[:30]

        final_msg = f"Mission accomplished in _{int(time_used_in_minutes)}m_ and _{int(time_used_in_seconds)}s_!\n[{short_title}...]({url})\nClick the above title to view the webpage."
        send_message_markdown(chat_id, final_msg, token)

        if reply_dict.get('visibility') and reply_dict.get('visibility') == 'paid':
            callback_set_page_visibility(chat_id, PUBLIC_MSG, post_id, token)

            title = reply_dict.get('Official_Title', 'title').replace('-', ' ').title()

            email_subject = f"POSTED: {title}..."
            user_name = user_parameters.get('name') or 'User'
            markdown_text = f"""**Hi {user_name.title()}**,

Here's your post based on the YOUTUBE you indicated. If you intend to keep this post private, do not share the LINK with others.

# [{title}]({url})

To make it public, send below command to the bot:
<pre style="background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 16px;">/public_{post_id}</pre>
<span style="font-size: 14px;"><i>P.S. The / before public_ command is important, please make sure to include the / when you copy the command.</i></span>

If you can't open the link above, please copy and paste below url into your browser:
{url}"""
            html_content = markdown_to_html_box(markdown_text)
            email_address = user_parameters.get('email', '')
            if email_address: send_email_html(email_address, email_subject, html_content)


    else: send_message(chat_id, reply_dict.get('Reason'), token)
    
    new_folder = os.path.join(current_folder, video_id)
    os.makedirs(new_folder, exist_ok=True)
    for f in os.listdir(current_folder): 
        new_file_path = os.path.join(current_folder, f)
        if os.path.isfile(new_file_path): shutil.move(new_file_path, new_folder)
    shutil.move(new_folder, f'{current_folder}/Published')
    return "Completed"
    

def dealing_tg_command(msg: str, chat_id: str, user_parameters, token=TELEGRAM_BOT_TOKEN, engine=engine, message_id=0):
    user_ranking = user_parameters.get('ranking') or 0
    tier = user_parameters.get('tier') or 'Free'
    email_address = user_parameters.get('email', '')
    openai_api_key = user_parameters.get('openai_api_key', '')

    if msg.startswith('/'): msg = msg[1:]

    msg_lower = msg.lower()
    length_msg = len(msg)

    if length_msg > 4000: return send_message(chat_id, "FYI, The maximum length a telegram bot can get from user's input is restricted to 4096 characters, for longer text input, the telegram server will chunk the message into multiple parts. For better interaction, please try to split your text into smaller parts and send them separately.", token)
    if msg_lower in ['chatid', 'chat_id', 'my chatid', "what's my chatid", "what's my chat id", "what's my chat_id"]: return send_message(chat_id, f"Your Chat ID is: {chat_id}", token)
    elif msg_lower in ['setting', 'settings', 'setup', 'configuration']: return main_menu_setting(chat_id, token)
    elif msg_lower in ['settings_shortcuts']: return send_message(chat_id, settings_shortcuts_keys_string, token)
    elif msg_lower in ['ice_breaker']: return openai_gpt_function('ice_breaker', chat_id, tools = FUNCTIONS_TOOLS, model = ASSISTANT_DOCUMENT_MODEL, engine = engine, token = token, user_parameters = user_parameters)
    elif msg_lower in ['help', 'session_help']: return back_to_session(chat_id, 'session_help', engine, token, user_parameters)
    elif msg_lower in ['word', 'random_word', 'random word']: return random_word(chat_id, token, engine, user_parameters)
    elif msg_lower in ['video_id', 'video id', 'video-id']: return send_message(chat_id, commands_dict.get("video_id"), token)
    elif msg_lower in ['activate', 'activation']: return send_message(chat_id, commands_dict.get("activate"), token)
    elif msg_lower in ['quote', 'random_quote', 'random quote']: return send_message(chat_id, random_quote(engine), token)
    elif msg_lower in ['random_image']: return from_gpt_to_replicate_image(chat_id, 'random image', midjourney_images_dir, token, user_parameters)
    elif msg_lower in ['UUID', 'uuid', 'unique_id', 'unique id', 'unique-id', 'random_id', 'random id']: return send_message_markdown(chat_id, f"Length 36:\n```{uuid.uuid4()}```\n\nLength 24:\n```{generate_user_id()}```", token)
    elif msg_lower in ['passwd', 'password', 'random_password', 'random password']: return send_message_markdown(chat_id, f"Without Special Characters (16):\n```{generate_password_without_special_character()}```\n\nWith Special Characters (16):\n```{generate_password()}```", token)
    elif msg_lower in ['youtube_url', 'youtube url', 'youtube-url']: return send_message(chat_id, commands_dict.get("youtube_url"), token)
    elif msg_lower in ['get_premium', 'premium', 'premium_membership']: return send_message(chat_id, commands_dict.get("get_premium"), token)
    elif msg_lower in ['generate_audio_male', 'generate_audio_female', 'generate_audio']: return send_message(chat_id, f"You need to provide text after the command. \nExample: /generate_audio_male Hello, how are you?", token)
    elif msg_lower in ['supported_file_types']: return send_message(chat_id, f"Supported file types for the /session_query_doc session: \n\n{ASSISTANT_FILE_SEARCH_SUPPORTED_FILES_STRING}", token)
    elif msg_lower in ['check_tier', 'update_tier_status', 'check tier', 'check_tier_status', 'check tier status', 'check_tier_status', 'check_tier_status']: 
        if not user_ranking: return send_message(chat_id, f"You are not currently a paid member. To learn more, click /get_premium. If you have already subscribed on {ENSPIRING_DOT_AI}, please provide the email address used for your subscription, and I will link your Telegram account to it.", token)
        return send_message(chat_id, f"Your current /tier is `/{tier}`. Your registration email address is: \n{email_address}.", token)

    elif msg_lower in ['set_openai_api_key', 'setopenaiapikey', 'openai_api_key']: return set_openai_api_key_information(user_parameters, chat_id, token)    
    elif msg_lower in ['delete_openai_api_key', 'deleteopenaiapikey']: return remove_openai_api_key_for_chat_id(chat_id, engine)
    elif msg_lower in ['openai_api_consumption']: return check_monthly_consumption(chat_id, engine)
    elif msg_lower in ['set_elevenlabs_api_key', 'setelevenlabsapikey', 'elevenlabs_api_key']: return set_elevenlabs_api_key_information(user_parameters, chat_id, token)
    elif msg_lower in ['delete_elevenlabs_api_key', 'deleteelevenlabsapikey']: return remove_elevenlabs_api_key_for_chat_id(chat_id, engine)
    elif msg_lower in ['set_creator_configurations']: return creator_menu_setting(chat_id, token)
    elif msg_lower == 'set_daily_words_list_on': return set_daily_words_list_for_chat_id(chat_id, 1, engine, msg = f"Successfully turned `on` the daily words list.", token = token)
    elif msg_lower == 'set_daily_words_list_off': return set_daily_words_list_for_chat_id(chat_id, 0, engine, msg = f"Successfully turned `off` the daily words list.", token = token)
    elif msg_lower == 'set_default_audio_gender': 
        default_voice_prompt = "Which audio voice gender do you prefer?"
        default_voice_inline_keyboard_dict = {'Male': 'default_audio_gender_male', 'Female': 'default_audio_gender_female', '<< Back to Main Menu': 'back_to_main_menu'}
        button_per_list = 2
        return send_or_edit_inline_keyboard(default_voice_prompt, default_voice_inline_keyboard_dict, chat_id, button_per_list, token)
    
    elif msg_lower == 'set_youtube_playlist': 
        if user_ranking < 3 and not openai_api_key: send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)
        else:
            current_youtube_playlist = user_parameters.get('youtube_playlist', '')
            prefix_msg = f"Your current YouTube playlist is:\n`{current_youtube_playlist[:10]}......{current_youtube_playlist[-11:]}`\nYou can always overwrite the playlist by sending a new playlist URL (in full-length)."
            notification_msg = f"Please provide the full-length YouTube playlist URL. I will check and process the videos, generate content, and post them online for you. Once posted, a private shared link will be sent to you. \n\nBased on your /tier : /{tier}, up to {int(user_ranking)} videos will be processed and posted. "
            if current_youtube_playlist: notification_msg = prefix_msg + '\n\n' + notification_msg
            suffix_msg = f"\n\nA full-length YouTube playlist URL should look like this:\n\n{FULL_LENGTH_PLAYLIST_URL}"
            notification_msg = notification_msg + suffix_msg
            send_message(chat_id, notification_msg, token)
        return
    
    elif msg_lower == 'set_voice_clone_sample': 
        current_clone_sample = user_parameters.get('voice_clone_sample', '')
        if current_clone_sample: prompt = f"Your already have a voice clone sample, however, you can always overwrite it by sending a new voice message."
        else: prompt = f"You don't have a voice clone sample yet, please click `Start Recording` to get started."
        return callback_record_voice_clone_sample(chat_id, prompt, token)


    elif msg_lower == 'set_daily_story_voice':
        elevenlabs_api_key = user_parameters.get('elevenlabs_api_key', '')
        if not elevenlabs_api_key: return send_message(chat_id, "You need to set your /elevenlabs_api_key first before using this function.", token)
        current_clone_sample = user_parameters.get('voice_clone_sample', '')
        if not current_clone_sample: return callback_record_voice_clone_sample(chat_id, "You have set up your /elevenlabs_api_key already, but you don't have a voice clone sample yet, please click `Start Recording` to get started.", token, message_id)
        prompt = "Do you want to use your own voice to read your daily story or use the default AI voice?"
        return callback_daily_story_voice_on_and_off(chat_id, prompt, token)


    elif msg_lower == 'set_daily_story_voice':
        elevenlabs_api_key = user_parameters.get('elevenlabs_api_key', '')
        if not elevenlabs_api_key: return send_message(chat_id, "You need to set your /elevenlabs_api_key first before using this function.", token)
        current_clone_sample = user_parameters.get('voice_clone_sample', '')
        if not current_clone_sample: return callback_record_voice_clone_sample(chat_id, "You have set up your /elevenlabs_api_key already, but you don't have a voice clone sample yet, please click `Start Recording` to get started.", token, message_id)
        prompt = "Do you want to use your own voice to read your daily story or use the default AI voice?"
        return callback_daily_story_voice_on_and_off(chat_id, prompt, token)

    elif msg_lower == 'clone_audio_trick': return callback_text_audio(chat_id, commands_dict.get("clone_audio_trick"), token, engine, user_parameters)

    elif msg_lower == 'proof_of_reading': return send_message(chat_id, commands_dict.get("proof_of_reading"), token)
    elif msg_lower == 'my_writing_style': 
        send_document_from_file(chat_id, 'Logos/my_writing_style.txt', 'Sample for your reference.', token)
        return send_message_markdown(chat_id, f"Click [SAMPLE PAGE](https://www.laogege.org/my_writing_style) to view the sample writing style in HTML. Or click [TUTORIAL](https://www.youtube.com/watch?v=TBa0IPDxRlE) to view the youtube tutorial", token)

    elif msg_lower == 'ghost_admin_api_key': return callback_creator_ghost_blog_api_key(chat_id, token)
    elif msg_lower == 'ghost_blog_url': return callback_creator_ghost_blog_url(chat_id, token)
    elif msg_lower == 'set_google_spreadsheet': return send_message(chat_id, f"Click below link to get a full understanding of how this function works and how to setup this feature. \n\n{GOOGLE_SPREADSHEET_SETUP_PAGE}", token)

    elif msg_lower == 'default_audio_switch': return callback_creator_default_audio_switch(chat_id, token)

    elif msg_lower.startswith('openai_api_key '):
        user_openai_api_key = msg.replace('openai_api_key', '').replace('>', '').strip()
        if len(user_openai_api_key) != 164: return send_message(chat_id, "Invalid OpenAI API Key. Please provide a valid OpenAI API Key.", token) 
        return set_openai_api_key_for_chat_id(chat_id, user_openai_api_key, message_id, engine, token)
    
    elif msg_lower.startswith('twitter_handle '):
        user_twitter_handle = msg.replace('twitter_handle', '').replace('>', '').strip()
        if not user_twitter_handle: return send_message(chat_id, "Invalid Twitter Handle. Please provide a valid Twitter Handle.", token)
        if not user_twitter_handle.startswith('@'): user_twitter_handle = f"@{user_twitter_handle}"
        user_twitter_handle = set_twitter_handle_for_chat_id(chat_id, user_twitter_handle, engine)
        if user_twitter_handle: return send_message(chat_id, f"Your Twitter Handle has been set to: {user_twitter_handle}\n\nhttps://x.com/{user_twitter_handle[1:]}", token)
        return send_message(chat_id, "Failed to set Twitter Handle. Please try again later.", token)
    

    elif msg_lower in ['today_news', 'get_news', 'news_today']:
        news_keywords = user_parameters.get('default_news_keywords', '') or 'Artificial Intelligence'
        send_message(chat_id, f"Now I'm searching and summarizing the news for your keywords: \n\n`{news_keywords}`\n\nClick /set_news_keywords to set new default keywords anytime.", token)
        date_today = str(datetime.now().date())
        df = pd.DataFrame({'user_prompt': [news_keywords], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['today_news'], 'date': [date_today]})
        df.to_sql('user_news_jobs', engine, if_exists='append', index=False)
        webhook_push_table_name('user_news_jobs', chat_id)
        return 

    elif msg_lower.startswith('set_news_keywords'):
        news_keywords = msg.replace('set_news_keywords', '').replace('>', '').strip()
        if not news_keywords: return send_message(chat_id, "Please provide the keywords you want to search for the news after /set_news_keywords >> . For example: /set_news_keywords >> Japanese Animate", token)
        return set_default_news_keywords_for_chat_id(chat_id, news_keywords, message_id, engine, token, user_parameters)


    elif msg_lower.startswith('elevenlabs_api_key '):
        user_elevenlabs_api_key = msg.replace('elevenlabs_api_key', '').replace('>', '').strip()
        if len(user_elevenlabs_api_key) != 51: return send_message(chat_id, "Invalid Eleven Labs API Key. Please provide a valid Eleven Labs API Key.", token)
        return set_elevenlabs_api_key_for_chat_id(chat_id, user_elevenlabs_api_key, message_id, engine, token, user_parameters)

    elif msg_lower in ['session_exit', 'session exit', 'exit session', 'exit_session', 'exitsession']: return exit_session_name(chat_id, engine)
    
    elif msg_lower in ['default_voice', 'default voice', 'set default voice', 'set_default_voice']: return callback_default_voice_gender_setup(chat_id, token)

    elif msg_lower.startswith('premium_'): return send_message(chat_id, f"We changed the way to /activate your telegram account. Now please submit the email address you used to subscribe the paid service on {ENSPIRING_DOT_AI} to unlock the full features of the bot.", token)
    
    elif msg_lower in ['mother_language', 'set_mother_language', 'set mother language', 'motherlanguage']: return callback_mother_language_setup(chat_id, token)
    
    elif msg_lower in ['secondary_language', 'set_secondary_language', 'set secondary language', 'secondarylanguage']: return callback_secondary_language_setup(chat_id, token)

    elif msg_lower in ['target_language', 'set_target_language', 'set target language', 'targetlanguage']: return callback_target_language_setup(chat_id, token, user_parameters)
    
    elif msg_lower in ['cartoon_style', 'set_cartoon_style', 'set cartoon style']: return callback_cartoon_style_setup(chat_id, token)

    elif msg_lower.startswith('ghost_admin_api_key '):
        user_ghost_admin_api_key = msg.replace('ghost_admin_api_key', '').replace('>', '').strip()
        if len(user_ghost_admin_api_key) != 89 or not ':' in user_ghost_admin_api_key: return send_message(chat_id, "Invalid Ghost Admin API Key. Please provide a valid Ghost Admin API Key. A valid Ghost Admin API Key looks like this: 88fd6030d898fe456dd7d20a:b6813f5ab53613a7c9efafb547fc1a681bc9b048d11645203fdf87ad5h9d8e54", token)
        split_by_colon = user_ghost_admin_api_key.split(':')
        if len(split_by_colon) != 2 or len(split_by_colon[0]) != 24 or len(split_by_colon[1]) != 64: return send_message(chat_id, "Invalid Ghost Admin API Key. Please provide a valid Ghost Admin API Key. A valid Ghost Admin API Key looks like this: 88fd6030d898fe456dd7d20a:b6813f5ab53613a7c9efafb547fc1a681bc9b048d11645203fdf87ad5h9d8e54", token)
        return set_ghost_admin_api_key(chat_id, user_ghost_admin_api_key, token, engine, message_id)


    elif msg_lower.startswith('ghost_blog_url '):
        user_ghost_blog_url = msg.replace('ghost_blog_url', '').replace('>', '').strip()
        if 'https://' not in user_ghost_blog_url or not is_valid_website_url(user_ghost_blog_url): return send_message(chat_id, "Invalid Ghost Blog URL. Please provide a valid Ghost Blog URL. A valid Ghost Blog URL is exactly your blog website url, and it looks like this: https://enspiring.ai", token)
        # remove the last / if there's any
        if user_ghost_blog_url.endswith('/'): user_ghost_blog_url = user_ghost_blog_url[:-1]
        return set_ghost_blog_url(chat_id, user_ghost_blog_url, token, engine, message_id)
    

    elif msg_lower.startswith('ollama'):
        prompt = msg.replace('ollama', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get('ollama'), token)
        response_text = ollama_gpt_chat_remote(prompt)
        response_text = f"Response from OpenSource Model Ollama: \n\n{response_text}"
        return callback_text_audio(chat_id, response_text, token, engine, user_parameters)

    
    elif msg_lower in ['tier', 'gold', 'silver', 'starter', 'free', 'owner', 'platinum', 'diamond']:
        if msg_lower == 'tier': return send_message(chat_id, TIER, token)
        if msg_lower == 'gold': return send_message(chat_id, GOLD, token)
        if msg_lower == 'silver': return send_message(chat_id, SILVER, token)
        if msg_lower == 'starter': return send_message(chat_id, STARTER, token)
        if msg_lower == 'platinum': return send_message(chat_id, PLATINUM, token)
        if msg_lower == 'diamond': return send_message(chat_id, DIAMOND, token)
        if msg_lower == 'free': return send_message(chat_id, FREE, token)
        if msg_lower == 'owner': 
            if chat_id == OWNER_CHAT_ID: return send_message(chat_id, f"You joking? You are the owner, {OWNER_HANDLE}!", token)
            else: return send_message(chat_id, f"The owner of Enspiring.ai & @Enspiring_bot is {OWNER_HANDLE}.", token)
        return
    
    elif msg_lower.startswith('words_checked'):
        if msg_lower == 'words_checked': today_date = str(datetime.now().date())
        else: 
            today_date = msg.split(' ', 1)[-1].strip()
            if not today_date: return send_message(chat_id, "Please provide the date in the format of 'YYYY-MM-DD'. For example: /words_checked 2024-10-15", token)
            today_date = today_date.replace('_', '-')
            today_date = today_date.replace(' ', '-')
            if len(today_date) < 10: return send_message(chat_id, "Please provide the date in the format of 'YYYY-MM-DD'. For example: /words_checked 2024-10-15", token)
            # check if there's two - in the date and a valid year, month, and day
            if today_date.count('-') != 2: return send_message(chat_id, "Invalid date format. Please provide the date in the format of 'YYYY-MM-DD'. For example: /words_checked 2024-10-15", token)
            try: datetime.strptime(today_date, '%Y-%m-%d')
            except: return send_message(chat_id, "Invalid date format. Please provide the date in the format of 'YYYY-MM-DD'. For example: /words_checked 2024-10-15", token)
        words_list = get_words_checked_today_for_user(chat_id, today_date, engine)
        if not words_list: return send_message(chat_id, "You have not checked any words today (UTC time). Send /words_checked YYYY-MM-DD to check the words you checked on a specific date. Or click /word to check a random word.", token)
        words_list = [f"/{word}" for word in words_list]
        words_list = set(words_list)
        inform_string = f"Words Checked on {today_date} (UTC): \n\n{' | '.join(words_list)}"
        if len(inform_string) > 4096: inform_string = inform_string[:4000] + f"\n\n...and more."
        return callback_generate_story(chat_id, inform_string, token)

    elif msg_lower in ['youtube_playlist', 'youtube playlist', 'youtube-playlist', 'playlist', 'playlist_id', 'playlist id', 'playlist-id']: 
        youtube_playlist_id = user_parameters.get('youtube_playlist', '')
        tier = user_parameters.get('tier') or 'Free'
        daily_video_limit = user_parameters.get('daily_video_limit') or 0
        if not youtube_playlist_id: return send_message(chat_id, f"Please provide the full-length YouTube playlist URL. I will check and process the videos, generate content, and post them online for you. Once posted, a private shared link will be sent to you. \n\nBased on your /tier : /{tier}, up to {int(daily_video_limit)} videos will be processed and posted. \n\nA full-length YouTube playlist URL should look like this:\n\n{FULL_LENGTH_PLAYLIST_URL}", token)
        return send_message(chat_id, f"Your YouTube Playlist ID is: \n`{youtube_playlist_id}`\n\nAs your current /tier is /{tier}, the AI bot will process {int(daily_video_limit)} English videos for you per day. None-English or none-qualified videos will be skipped.\n\n- P.S. You can send a new YouTube Playlist URL (in full-length, include the https://www.youtube.com/playlist?list= prefix) to replace the current one anytime.", token)
    
    elif msg_lower in ['total_posts']:
        total_posts = get_total_posts(engine)
        if not total_posts: return send_message(chat_id, "Failed to get the total posts.", token)
        return send_message(chat_id, f"As of {datetime.now().strftime('%Y-%m-%d %H:%M')}, we have totally posted {int(total_posts)} posts.", token)
    
    elif msg_lower.startswith('count ') or msg_lower.startswith('length '):
        if msg_lower not in ['count ', 'length ']:
            prompt = msg.replace('count ', '').replace('length ', '').strip()
            if prompt: return send_message(chat_id, f"Words Length: {len(prompt.split())}\nCharacters Length: {len(prompt)}", token)
        return send_message(chat_id, "Please provide the text after the command. Example: /count Hello, how are you?", token)
            
    elif msg_lower.startswith('help '):
        prompt = msg.split(' ', 1)[-1].strip()
        if not prompt: return send_message(chat_id, HELP_COMMAND_RESPONSE, token)
        return platform_questions_and_answers_helper(prompt, chat_id, engine, token, user_parameters)

    # if user_ranking >= 1 or openai_api_key:

    elif msg_lower.startswith('public_'):
        post_id = msg.replace('public_', '').strip()
        if not post_id: return send_message(chat_id, "Please provide the Post_ID after /public_ command, example: \n/public_6705944905bb49c9cfa85939", token)
        return set_page_visibility_direclty_in_table(post_id, 'public', engine)
    
    elif msg_lower.startswith('private_'):
        post_id = msg.split('private_')[-1].strip()
        if not post_id: return send_message(chat_id, "Please provide the Post_ID after /private_ command, example: \n/private_6705944905bb49c9cfa85939", token)
        return set_page_visibility_direclty_in_table(post_id, 'paid', engine)

    # if user_ranking >= 2 or openai_api_key:

    elif msg_lower.startswith('revise_text'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)
        
        content_to_be_process = msg.replace('revise_text', '')
        if not content_to_be_process: return send_message(chat_id, commands_dict.get("revise_text"), token)
        characters_count = len(content_to_be_process)
        if characters_count > REVISE_TEXT_CHARACTERS_LIMIT: return send_message(chat_id, f"Sorry, the content to be revised is too long, it should be less than {REVISE_TEXT_CHARACTERS_LIMIT} characters. The current content has {characters_count} characters. For longer text, you can send a txt file to me, and put 'revise' or 'refine' in the caption box.", token)
        response = openai_gpt_chat(SYSTEM_PROMPT_ENGLISH_REFINER, content_to_be_process, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
        return send_message(chat_id, response, token)
    
    elif msg_lower in ['post_stories_list']: return create_stories_list_html_post_to_ghost(chat_id, admin_api_key=BLOG_POST_ADMIN_API_KEY, ghost_url=BLOG_POST_API_URL, engine=engine, token=token, message_id=message_id, user_parameters=user_parameters)

    # if user_ranking >= 3 or openai_api_key: 

    elif msg_lower.startswith('generate_audio_'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        if 'generate_audio_male' in msg_lower: 
            user_parameters['default_audio_gender'] = 'male'
            prompt = msg.replace('generate_audio_male', '').strip()
        else: 
            user_parameters['default_audio_gender'] = 'female'
            prompt = msg.replace('generate_audio_female', '').strip()
            prompt = prompt.replace('generate_audio_', '').strip()

        if not prompt: return send_message(chat_id, commands_dict.get("audio"), token)
        else: send_message(chat_id, f"Generating audio for you...", token)

        audio_file = generate_story_voice(prompt, chat_id, audio_generated_dir, engine, token, user_parameters, language_name='')
        if audio_file and os.path.isfile(audio_file): return send_audio_from_file(chat_id, audio_file, token)
        return send_message(chat_id, "Failed to generate audio file.", token)


    elif msg_lower.startswith('translate_to_audio'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        prompt = msg.replace('translate_to_audio', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("translate_to_audio"), token)

        send_message(chat_id, f"Command received...", token)
        message_id = int(message_id) + 1 

        user_parameters['translate_to_audio'] = True
        user_parameters['message_id'] = message_id
        return session_translation(prompt, chat_id, token, user_parameters)
    

    elif msg_lower == 'session_translation': return back_to_session(chat_id, msg_lower, engine, token, user_parameters)


    elif msg_lower.startswith('inline_query_add'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''inline_query_add keyword(single word): record(could be a sentence)'''
        if msg_lower in ['inline_query_add', 'inline_query_add ']: return send_message(chat_id, "Please provide the keyword and the record after the command. Example: /inline_query_add keyword: record", token)
        if ':' not in msg: return send_message(chat_id, "Please provide the keyword and the record after the command and separate them with a colon. Example: /inline_query_add keyword: record", token)
        split_list = msg.split(':', 1)
        if len(split_list) < 2: return send_message(chat_id, "Please provide the keyword and the record after the command. Example: /inline_query_add keyword: record", token)
        keywords = split_list[0].replace('inline_query_add', '').strip()
        records = split_list[1].strip()
        return save_keywords_with_records(chat_id, keywords, records, engine, token)
    
    
    elif msg_lower.startswith('save'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        if msg_lower in ['save', 'save ']: return send_message(chat_id, "Please provide the keyword and the record after the command. Example: /save keyword: record", token)
        if ':' not in msg: return send_message(chat_id, "Please provide the keyword and the record after the command and separate them with a colon. Example: /save keyword: record", token)
        split_list = msg.split(':', 1)
        if len(split_list) < 2: return send_message(chat_id, "Please provide the keyword and the record after the command. Example: /save keyword: record", token)
        keywords = split_list[0].replace('save', '').strip()
        records = split_list[1].strip()
        return save_keywords_with_records(chat_id, keywords, records, engine, token)


    elif msg_lower.startswith('inline_query_remove'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''inline_query_remove keyword(single word)'''
        if msg_lower in ['inline_query_remove', 'inline_query_remove ']: return send_message(chat_id, "Please provide the keyword after the command. Example: /inline_query_remove keyword", token)
        keywords = msg_lower.replace('inline_query_remove_', '').strip()
        keywords = keywords.replace('inline_query_remove', '').strip()
        print(f"keywords: {keywords}")
        with engine.begin() as conn: conn.execute(text(f"DELETE FROM inline_query_record WHERE chat_id = :chat_id AND keywords = :keywords"), {'chat_id': chat_id, 'keywords': keywords})
        return send_message(chat_id, f"Successfully removed the record for the keyword: {keywords}", token)
    

    elif msg_lower.startswith('find'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''find keyword(single word)'''
        if msg_lower in ['find', 'find ']: return send_message(chat_id, "Please provide the keyword after the command. Example: /find keyword", token)
        keywords = msg_lower.replace('find', '').strip()
        return find_keywords(keywords, chat_id, engine, token)
    

    elif msg_lower.startswith('inline_query_list'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''inline_query_list'''
        df = pd.read_sql(text(f"SELECT keywords, records FROM inline_query_record WHERE chat_id = :chat_id"), engine, params={'chat_id': chat_id})
        if df.empty: return send_message(chat_id, "You have not added any inline query records yet.", token)
        keywords_records_dict = df.set_index('keywords').to_dict()['records']
        inform_string = "\n".join([f"{index+1}. {keyword} >> {record}" for index, (keyword, record) in enumerate(keywords_records_dict.items())])
        if len(inform_string) < 3000: return send_message(chat_id, inform_string, token)
        else:
            output_dir = os.path.join(working_dir, chat_id)
            today_date = str(datetime.now().date())
            file_path = os.path.join(output_dir, f"inline_query_list_{today_date}.txt")
            with open(file_path, 'w', encoding='utf-8') as f: f.write(inform_string)
            return send_document_from_file(chat_id, file_path, f"Inline Query List of {today_date}", token)
        

    elif msg_lower.startswith('get_transcript'):
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''get_transcript https://www.youtube.com/watch?v=JGwWNGJdvx8'''
        youtube_url = msg.replace('get_transcript', '').strip()
        if not youtube_url: return send_message(chat_id, commands_dict.get("get_transcript"), token)

        if not 'youtu.be/' in youtube_url and not 'youtube.com/watch?v=' in youtube_url: return send_message(chat_id, "Invalid YouTube URL.", token)
        if msg_lower in ['https://youtu.be/', 'https://www.youtube.com/watch?v=', 'http://youtu.be/', 'http://www.youtube.com/watch?v=', 'https://youtu.be', 'http://youtu.be']: return send_message(chat_id, "Invalid YouTube URL.", token)

        youtube_url = youtube_url_format(youtube_url)
        if not youtube_url: return send_message(chat_id, "Invalid YouTube URL.", token)

        video_id = youtube_url.split('=')[-1]

        df = pd.read_sql(text("SELECT paragraphed_transcript FROM enspiring_video_and_post_id WHERE Video_ID = :video_id"), engine, params={'video_id': video_id})
        if not df.empty and df['paragraphed_transcript'].values[0]:
            paragraphed_transcript = df['paragraphed_transcript'].values[0]
            output_dir = os.path.join(working_dir, chat_id)
            timestamp_now = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(output_dir, f"transcript_{timestamp_now}.txt")
            with open(file_path, 'w', encoding='utf-8') as f: f.write(paragraphed_transcript)
            return send_document_from_file(chat_id, file_path, "", token)
        else:
            date_today = str(datetime.now().date())
            df = pd.read_sql(text("SELECT youtube_url FROM youtube_transcript_jobs WHERE chat_id = :chat_id AND date = :date AND job_status != 'failed'"), engine, params={'chat_id': chat_id, 'date': date_today})
            if df.shape[0] >= user_ranking: return send_message(chat_id, f"Sorry, as a /{tier} user, you can only request {user_ranking} transcript(s) per day. Please wait until tomorrow to request more.\n\n/get_premium", token)

            # Make a df.to_sql() to save the youtube_url jobs to the database, include chat_id
            df = pd.DataFrame({'youtube_url': [youtube_url], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['transcript'], 'date': [date_today]})
            df.to_sql('youtube_transcript_jobs', engine, if_exists='append', index=False)
            webhook_push_table_name('youtube_transcript_jobs', chat_id)
            return send_message(chat_id, f"Your request to get the transcript from the YouTube video has been received. It will be processed soon. You will be notified once it's done.", token)


    elif msg_lower in ['session_chat_casual', 'casual_chat']:
        if user_ranking < 3 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)
        return back_to_session(chat_id, 'session_chat_casual', engine, token, user_parameters)

    # if user_ranking >= 4 or openai_api_key: 

    elif msg_lower.startswith('email_assistant'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        email_content = msg.replace('email_assistant', '').strip()
        if not email_content: return send_message(chat_id, commands_dict.get("email_assistant"), token)
        ai_response = openai_email_assistant(email_content, chat_id, engine, token, user_parameters)
        to_address = user_parameters.get('email', '')
        if to_address: send_email_text(to_address, "Feedback from Enspiring.AI Email Assistant", ai_response, GMAIL_ADDRESS, GMAIL_PASSWORD)
        return send_document_from_file(chat_id, wrap_text_to_file(ai_response, output_dir), "Feedback from Enspiring.AI", token)

    elif msg_lower in ['session_assistant_email', 'assistant_email', 'email_assistant']:
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        return back_to_session(chat_id, 'session_assistant_email', engine, token, user_parameters)


    elif msg_lower in ['session_query_doc', 'session_query_doc', 'query_pdf', 'query_docx', 'query_docs', 'query_document', 'query_documents']:
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)

        session_thread_id = user_parameters.get('session_thread_id', '')
        if session_thread_id: return back_to_session(chat_id, 'session_query_doc', engine, token, user_parameters)
        
        reply_prefix = commands_dict.get("session_query_doc")
        reply_body = """For example, you could ask:
- What is the main idea of this DOCUMENT?
- Can you summarize this DOCUMENT?
- Give me 5 takeaways from this DOCUMENT.
- What are the key points of this DOCUMENT?
- What is the author's main argument?
- What are the key findings of this report?
- How much revenue did the company generate?
- What's the valuation of this round?
- Who have invested in this company previously?
"""
        reply_suffix = "Important notice: Once the /supported_file_types document is uploaded, you'll enter into the /session_query_doc session. During the session, any text message you send will be hijacked and treated as a query about the document. To exit the session, simply send or click /session_exit; To come back to the session, just send or click /session_query_doc"
        return send_message(chat_id, f"{reply_prefix}\n\n{reply_body}\n\n{reply_suffix}", token)
    

    elif msg_lower in ['session_code_interpreter', 'code_interpreter']:
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        return back_to_session(chat_id, 'session_code_interpreter', engine, token, user_parameters)
    

    elif msg_lower.startswith('clone_audio'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)

        '''/clone_audio Hello everyone! This is my cloned voice, and I must admit, it feels surreal hearing myself without actually saying the words. Technology is truly amazing, isn't it? Let me know if it sounds just like me!'''
        prompt = msg.replace('clone_audio', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("clone_audio"), token)

        elevenlabs_api_key = user_parameters.get('elevenlabs_api_key', '')
        if not elevenlabs_api_key: return set_elevenlabs_api_key_information(user_parameters, chat_id, token)

        voice_sample = user_parameters.get('voice_clone_sample')
        if not voice_sample: return prompt_user_send_voice_clone_sample(chat_id, token, engine, is_redo=True, user_parameters=user_parameters)

        audio_generated_dir_user = os.path.join(audio_generated_dir, chat_id)

        audio_file = instant_clone_voice_audio_elevenlabs(prompt, chat_id, voice_sample, audio_generated_dir_user, model="eleven_turbo_v2_5", chunk_size = ELEVENLABS_CHUNK_SIZE, engine = engine, user_parameters = user_parameters)
        
        if audio_file and os.path.isfile(audio_file): return send_audio_from_file(chat_id, audio_file, token)
        else: return send_message(chat_id, "Failed to generate audio with your voice clone.", token)
    
    
    elif msg_lower.startswith('generate_system_prompt'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        user_prompt = msg.replace('generate_system_prompt', '').strip()
        if not user_prompt: return send_message(chat_id, commands_dict.get("generate_system_prompt"), token)
        send_message(chat_id, f"Refining your system prompt...", token)
        message_id += 1
        refined_system_prompt = generate_prompt(user_prompt)
        if refined_system_prompt:
            user_folder = os.path.join(working_dir, chat_id)
            timestamp_now = datetime.now().strftime('%Y%m%d_%H%M%S')
            system_prompt_filepath = os.path.join(user_folder, f"system_prompt_{timestamp_now}.txt")
            with open(system_prompt_filepath, "w", encoding='utf-8') as f: f.write(refined_system_prompt)
            send_document_from_file(chat_id, system_prompt_filepath, 'Refined System Prompt', token)
            return delete_message(chat_id, message_id, token)
        else: return send_message(chat_id, f"Failed to refine your system prompt, please try later.", token, message_id)
    

    elif msg_lower.startswith('generate_prompt_midjourney'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        user_prompt = msg.replace('generate_prompt_midjourney', '').strip()
        if not user_prompt: return send_message(chat_id, commands_dict.get("generate_prompt_midjourney"), token)
        return generate_midjourney_prompt(chat_id, user_prompt, token, engine, user_parameters)
    

    elif msg_lower.startswith('generate_prompt_blackforest'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        prompt = msg_lower.replace('generate_prompt_blackforest', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("generate_prompt_blackforest"), token)
        return from_gpt_to_replicate_image(chat_id, prompt, midjourney_images_dir, token, user_parameters, prompt_only=True)


    elif msg_lower.startswith('generate_image_dalle'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        user_prompt = msg.replace('generate_image_dalle', '').strip()
        if not user_prompt: return send_message(chat_id, commands_dict.get("generate_image_dalle"), token)
        file_path = openai_image_generation(user_prompt, chat_id, model="dall-e-3", size = "1792x1024", quality="standard", user_parameters = user_parameters)
        if file_path and os.path.isfile(file_path): return send_image_from_file(chat_id, file_path, user_prompt, token)
        else: return send_message(chat_id, "Failed to generate image.", token)

    # if user_ranking >= 5 or openai_api_key:

    elif msg_lower.startswith('creator_twitter_auth'): 
        auth_url = start_twitter_auth(chat_id)
        markdown_msg = f"Please click [HERE]({auth_url}) to authenticate your Twitter account."
        return send_message_markdown(chat_id, markdown_msg, token)
    

    elif msg_lower.startswith('creator_linkedin_auth'):
        auth_url = start_linkedin_auth(chat_id)
        markdown_msg = f"Please click [HERE]({auth_url}) to authenticate your Linkedin account."
        return send_message_markdown(chat_id, markdown_msg, token)


    elif msg_lower.startswith('creator_post_youtube'):
        if user_ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Gold or higher tier to use this function.\n\n/get_premium", token)

        '''creator_post_youtube https://www.youtube.com/watch?v=JGwWNGJdvx8'''
        youtube_url = msg.replace('creator_post_youtube', '').strip()
        if not youtube_url: return send_message(chat_id, commands_dict.get("creator_post_youtube"), token)

        if not 'youtu.be/' in youtube_url and not 'youtube.com/watch?v=' in youtube_url: return send_message(chat_id, "Invalid YouTube URL.", token)
        if msg_lower in ['https://youtu.be/', 'https://www.youtube.com/watch?v=', 'http://youtu.be/', 'http://www.youtube.com/watch?v=', 'https://youtu.be', 'http://youtu.be']: return send_message(chat_id, "Invalid YouTube URL.", token)

        youtube_url = youtube_url_format(youtube_url)
        if not youtube_url: return send_message(chat_id, "Invalid YouTube URL.", token)

        video_id = youtube_url.split('=')[-1]

        date_today = str(datetime.now().date())
        df = pd.DataFrame({'youtube_url': [youtube_url], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['creator_post_youtube'], 'date': [date_today]})
        df.to_sql('youtube_transcript_jobs', engine, if_exists='append', index=False)
        send_message_markdown(chat_id, f"Your request to get the transcript from the [YouTube Video]({youtube_url}) has been received. It will be processed soon. You will be notified once it's done.", token)
        return webhook_push_table_name('youtube_transcript_jobs', chat_id)

    
    elif msg_lower.startswith('generate_image_blackforest'):
        prompt = msg_lower.replace('generate_image_blackforest', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("generate_image_blackforest"), token)
        return from_gpt_to_replicate_image(chat_id, prompt, midjourney_images_dir, token, user_parameters)
    

    elif msg_lower.startswith('generate_image_midjourney'):
        if user_ranking < 4 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Platinum or higher tier to use this function.\n\n/get_premium", token)
        user_prompt = msg.replace('generate_midjourney_image', '').strip()
        if not user_prompt: return send_message(chat_id, commands_dict.get("generate_image_midjourney"), token)

        image_id = generate_image_midjourney(chat_id, user_prompt, 'user', midjourney_token = IMAGEAPI_MIDJOURNEY)
        if image_id: send_message_markdown(chat_id, f"Your image generation request has been submitted to Midjourney bot. The image ID is: `{image_id[:6]}...{image_id[-6:]}`. All four images will be send to you once generated. Click [HERE](https://docs.midjourney.com/docs/prompts) to learn more about how to create a better `Midjourney Prompt`", token)
        return
    

    elif msg_lower.startswith('post_journal'):
        if user_ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        img_url = ''
        prompt = msg.replace('post_journal', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("post_journal"), token)
        if '/' in prompt: 
            img_url = find_url(prompt)
            if img_url: prompt = prompt.replace(img_url, '').strip()

        send_message(chat_id, f"Generating the journal based on your prompt, please wait about 120 seconds...", token)
        message_id = str(int(message_id) + 1) if message_id else ''
        return post_journal_to_ghost(prompt, chat_id, img_url, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = token, model = ASSISTANT_MAIN_MODEL, message_id = message_id, user_parameters = user_parameters)


    elif msg_lower.startswith('creator_auto_post'):
        if user_ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        series_name = msg.replace('creator_auto_post', '').strip()
        if not series_name: return send_message(chat_id, f"You have to set a series name for you autonomous posting job. Example: /creator_auto_post The Eternal Drift", token)
        else: 
            if update_auto_post_series_name(chat_id, series_name, engine): return send_message(chat_id, f"Your autonomous posting series name has been set to: \n\n{series_name}", token)
            else: return send_message(chat_id, f"Failed to set the series name for your autonomous posting job. Please try again later.", token)
            

    elif msg_lower.startswith('creator_post_journal'): return post_journal_to_ghost_creator_front(msg, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, message_id, user_parameters, is_journal = True)


    elif msg_lower.startswith('creator_post_story'):
        is_url = find_url(prompt)
        if is_url: return handle_url_input(is_url, chat_id, ASSISTANT_MAIN_MODEL_BEST, user_parameters, token)
        else: return post_journal_to_ghost_creator_front(prompt, chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, message_id, user_parameters, is_journal = False)


    elif msg_lower.startswith('creator_post_news'): return post_news_to_ghost_creator_front(msg, chat_id, engine, token, user_parameters)


    elif msg_lower.startswith('post_story'):
        if user_ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)

        '''/post_story An epic adventure with a brave young girl named Ava, who discovers a hidden, magical world beneath her village, full of strange creatures and unexpected allies'''
        prompt = msg.replace('post_story', '').strip()
        if not prompt: return send_message(chat_id, commands_dict.get("post_story"), token)
        send_message(chat_id, f"Generating the story based on your prompt, please wait about 120 seconds...", token)
        message_id = str(int(message_id) + 1) if message_id else ''
        return create_story_and_post_to_ghost(prompt, chat_id, admin_api_key=BLOG_POST_ADMIN_API_KEY, ghost_url=BLOG_POST_API_URL, engine=engine, token=token, model=ASSISTANT_DOCUMENT_MODEL, message_id=message_id, user_parameters=user_parameters)


    elif msg_lower.startswith('post_news'):
        if user_ranking < 5 and not openai_api_key: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Diamond or higher tier to use this function.\n\n/get_premium", token)
        user_prompt = msg.replace('post_news', '').strip()
        if not user_prompt: return send_message(chat_id, commands_dict.get("post_news"), token)

        date_today = str(datetime.now().date())
        white_list_chat_ids = get_white_listed_chat_ids(engine)
        
        if chat_id not in white_list_chat_ids:
            df = pd.read_sql(text(f"SELECT user_prompt, job_status FROM user_news_jobs WHERE chat_id = :chat_id AND date = :date AND job_status != 'failed'"), engine, params={'chat_id': chat_id, 'date': date_today})
            if not df.empty: return send_message(chat_id, f"You already have a task with prompt: {df['user_prompt'].values[0]} and status: {df['job_status'].values[0]}. You can only have one news post task per day.", token)

        # Make a df.to_sql() to save the youtube_url jobs to the database, include chat_id
        df = pd.DataFrame({'user_prompt': [user_prompt], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['news'], 'date': [date_today]})
        df.to_sql('user_news_jobs', engine, if_exists='append', index=False)
        webhook_push_table_name('user_news_jobs', chat_id)
        return send_message(chat_id, f"Your request to post the news has been received. It will be processed soon. You will be notified once it's done.")
    

    elif user_ranking >= 66 or chat_id in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID]:
        print(f"This is the owner only function area...")
        chat_id_consumption_list = []
        this_month = str(datetime.now().month)

        if 'consumption' in msg_lower:
            with engine.connect() as conn:
                query = text(f"SELECT chat_id, name, `{this_month}` FROM chat_id_parameters WHERE chat_id IS NOT NULL ORDER BY `{this_month}` DESC")
                df = pd.read_sql(query, conn)
                if df.empty: return send_message(chat_id, "Failed to get the consumption data.", token)
                total_spent = df[this_month].sum().round(3)
                for index, row in df.iterrows():
                    if row[this_month] == 0: continue
                    if not row['name']: continue
                    consumption_value = round(row[this_month], 3)
                    inform_string = f"{index+1}. {row['name'].capitalize()} >> {consumption_value} usd"
                    chat_id_consumption_list.append(inform_string)
            if chat_id_consumption_list: 
                prefix = f"Total spent in month {this_month} is {total_spent} usd.\n"
                chat_id_consumption_list.insert(0, prefix)
                send_message(chat_id, '\n'.join(chat_id_consumption_list), token)
            else: send_message(chat_id, f"No consumption data found for month {this_month}", token)
            return

        elif msg_lower.startswith('domain_verification'):
            '''/domain_verification domain_name'''
            domain_name_verification_string = msg.replace('domain_verification', '').strip()
            if not domain_name_verification_string: return send_message(chat_id, "Please provide the domain name after the command. Example: /domain_verification your_domain_name", token)
            domain_name_verification_string_list = domain_name_verification_string.split(' ')
            if len(domain_name_verification_string_list) < 2: return send_message(chat_id, "Please provide the domain name and the verification string after the command. Example: /domain_verification your_domain_name your_verification_string", token)
            verification_string = domain_name_verification_string_list[-1].strip()
            domain_name = domain_name_verification_string_list[0].strip()
            reply = domain_verification(domain_name, verification_string)
            return send_message(chat_id, reply, token)
        
        elif msg_lower.startswith('google-site-verification='):
            domain_name_verification_string_list = msg.split(' ')
            if len(domain_name_verification_string_list) < 2: return send_message(chat_id, "Please provide the domain name and the verification string after the command. Example: google-site-verification=your_verification_string your_domain_name", token)
            verification_string = domain_name_verification_string_list[0].strip()
            domain_name = domain_name_verification_string_list[-1].strip()
            reply = domain_verification(domain_name, verification_string)
            return send_message(chat_id, reply, token)


        elif msg_lower.startswith('point_subdomain'):
            print(f"point_subdomain command...")
            '''/point_subdomain sub.domainname new_ip'''
            domain_name_subdomain_new_ip = msg_lower.replace('point_subdomain', '').strip()
            if not domain_name_subdomain_new_ip: return send_message(chat_id, "Please provide the domain name, subdomain and the new IP address after the command. Example: /point_subdomain your_domain_name your_subdomain your_new_ip", token)
            subdomain_name_new_ip_list = domain_name_subdomain_new_ip.split(' ')
            if len(subdomain_name_new_ip_list) < 2: return send_message(chat_id, "Please provide subdomain and the new IP address after the command. Example: /point_subdomain api.sumatman.ai your_new_ip", token)
            domain_name = subdomain_name_new_ip_list[0].strip()
            ip_address = subdomain_name_new_ip_list[-1].strip()
            # from get subdomain and domain name
            subdomain = domain_name.split('.', 1)[0]
            domain_name = domain_name.replace(f"{subdomain}.", '').strip()
            if not all([domain_name, subdomain, ip_address]): return send_message(chat_id, "Please provide the domain name, subdomain and the new IP address after the command. Example: /point_subdomain your_domain_name your_subdomain your_new_ip", token)
            api = NameComAPI(DOMAIN_NAME_USERNAME, DOMAIN_NAME_TOKEN)
            result = update_subdomain_a_record(api, domain_name, subdomain, ip_address)
            return send_message(chat_id, f"Result: {result['message']}", token)
        

        elif msg_lower.startswith('create_ghost_blog'):
            sub_domain_name_with_user_chat_id = msg.replace('create_ghost_blog', '').strip()
            if not sub_domain_name_with_user_chat_id: return send_message(chat_id, "Please provide the domain name and user chat_id after the command. Example: /create_ghost_blog sub_domain_name user_chat_id", token)
            sub_domain_name_with_user_chat_id_list = sub_domain_name_with_user_chat_id.split(' ')
            if len(sub_domain_name_with_user_chat_id_list) < 2: return send_message(chat_id, "Please provide the domain name and user chat_id after the command. Example: /create_ghost_blog sub_domain_name user_chat_id", token)
            sub_domain_name = sub_domain_name_with_user_chat_id_list[0].strip()
            user_chat_id = sub_domain_name_with_user_chat_id_list[1].strip()
            send_message(chat_id, f"Creating the Ghost blog for /chat_{user_chat_id}...", token)
            return create_ghost_blog(sub_domain_name, user_chat_id, token, engine)
        
        
        elif msg_lower.startswith('remove_ghost_instance'):
            sub_domain_name = msg.replace('remove_ghost_instance', '').strip()
            if not sub_domain_name: return send_message(chat_id, "Please provide the sub_domain_name after the command. Example: /remove_ghost_instance sub_domain_name", token)
            return remove_ghost_user(chat_id)
        

        elif msg_lower.startswith('set_ghost_api_key'):
            ghost_admin_api_key_and_chat_id = msg.replace('set_ghost_api_key', '').strip()
            if not ghost_admin_api_key_and_chat_id: return send_message(chat_id, "Please provide the Ghost admin key after the command. Example: /set_ghost_api_key your_ghost_admin_key user_chat_id", token)
            ghost_admin_api_key_and_chat_id_list = ghost_admin_api_key_and_chat_id.split(' ')
            if len(ghost_admin_api_key_and_chat_id_list) < 2: return send_message(chat_id, "Please provide the Ghost admin key and user chat_id after the command. Example: /set_ghost_api_key your_ghost_admin_key user_chat_id", token)
            ghost_admin_api_key = ghost_admin_api_key_and_chat_id_list[0].strip()
            user_chat_id = ghost_admin_api_key_and_chat_id_list[1].strip()
            return set_ghost_admin_api_key(user_chat_id, ghost_admin_api_key, token, engine, message_id=0)
        

        elif msg_lower.startswith('set_ghost_url'):
            ghost_url_and_chat_id = msg.replace('set_ghost_url', '').strip()
            if not ghost_url_and_chat_id: return send_message(chat_id, "Please provide the Ghost URL after the command. Example: /set_ghost_url your_ghost_url user_chat_id", token)
            ghost_url_and_chat_id_list = ghost_url_and_chat_id.split(' ')
            if len(ghost_url_and_chat_id_list) < 2: return send_message(chat_id, "Please provide the Ghost URL and user chat_id after the command. Example: /set_ghost_url your_ghost_url user_chat_id", token)
            ghost_url = ghost_url_and_chat_id_list[0].strip()
            user_chat_id = ghost_url_and_chat_id_list[-1].strip()
            return set_ghost_blog_url(user_chat_id, ghost_url, token, engine, message_id=0)
        

        elif msg_lower.startswith('get_chat_id'):
            user_name = msg.replace('get_chat_id', '').strip()
            if not user_name: return send_message(chat_id, "Please provide the user's name after the command. Example: /get_chat_id Danli", token)
            df = pd.read_sql(text("SELECT chat_id FROM chat_id_parameters WHERE LOWER(name) = LOWER(:name)"), engine, params={'name': user_name})
            if df.empty: return send_message(chat_id, f"No such user found with the name: {user_name}", token)
            user_chat_id = df['chat_id'].values[0]
            return send_message(chat_id, f"{user_name} \n/chat_{user_chat_id}\n/simulate {user_chat_id} message here.", token)


        elif msg_lower.startswith('create_author_id'):
            '''/create_author_id user_chat_id'''
            user_chat_id = msg.replace('create_author_id', '').strip()
            if not user_chat_id: return send_message(chat_id, "Please provide the user's chat_id after the command.", token)
            author_id = create_or_get_author_in_ghost_for_chat_id(user_chat_id, engine)
            return send_message(chat_id, author_id, token)
        
        elif msg_lower.startswith('renew_vocabulary_chinese'):
            word = msg.replace('renew_vocabulary_chinese', '').strip()
            if not word: return send_message(chat_id, "Please provide the word after the command.", token)
            return renew_vocabulary_chinese(word, chat_id, engine, token, user_parameters)

        elif msg_lower.startswith('set_email'):
            '''/set_email 7714656152 email_address'''
            msg_list = msg.split(' ', 2)
            if len(msg_list) < 3: return send_message(chat_id, "Please provide the chat_id and the email address after the /set_email command. Like this: /set_email 7714656152 user@gmail.com", token)
            user_chat_id = msg_list[1].strip()
            email_address = msg_list[2].strip()
            if update_user_email_address(email_address, user_chat_id, engine=engine): return send_message(chat_id, f"Email address for chat_id {user_chat_id} has been updated to: {email_address}", token)

        elif msg_lower.startswith('chat_'):
            user_chat_id = msg_lower.replace('chat_', '').strip()
            if not user_chat_id: return send_message(chat_id, "Please append user_chat_id after the /chat_ command.", token)
            return get_chat_id_parameters(str(user_chat_id), engine, token, chat_id)

        elif msg_lower.startswith('change_phonetic'):
            '''/change_phonetic admirer [ədˈmaɪərər]'''
            msg_list = msg.split(' ', 2)
            if len(msg_list) < 3: return send_message(chat_id, "Please provide the word and the phonetic voice after the /change_phonetic command.", token)
            word = msg_list[1].strip().lower()
            phonetic = msg_list[2].strip()
            if change_phonetic(word, phonetic, engine): return send_message(chat_id, f"Phonetics of /{word} has been changed to {phonetic}.", token)

        elif msg_lower.startswith('add_channel ') or msg_lower.startswith('adc '):
            channel_handle = msg.split('add_channel ')[-1].strip() if msg_lower.startswith('add_channel ') else msg.split('adc ')[-1].strip()
            if channel_handle.startswith('@'): channel_handle = channel_handle[1:]
            response = add_youtube_channel_handle(channel_handle, engine)
            return send_message(chat_id, response, token)
        
        elif msg_lower.startswith('alter_channel_ ') or msg_lower.startswith('atc_'):
            split_list = msg.split(' ', 1)
            if len(split_list) < 2: return send_message(chat_id, "Please provide the new title after the command. For example: /alter_channel_handle New Title", token)
            real_handle = split_list[0].replace('alter_channel_', '').strip() if msg_lower.startswith('alter_channel_') else split_list[0].replace('atc_', '').strip()
            new_title = split_list[1].strip()
            if real_handle.startswith('@'): real_handle = real_handle[1:]
            response =  change_channel_title_by_channel_handle(real_handle, new_title, engine)
            return send_message(chat_id, response, token)
        
        elif msg_lower.startswith('drop_channel_') or msg_lower.startswith('dpc_'):
            channel_handle = msg.split('drop_channel_')[-1].strip() if msg_lower.startswith('drop_channel_') else msg.split('dpc_')[-1].strip()
            if not channel_handle: return "Please provide the channel handle after the command."
            if channel_handle.startswith('@'): channel_handle = channel_handle[1:]
            response =  drop_channel_by_channel_handle(channel_handle, engine)
            return send_message(chat_id, response, token)
        
        elif msg_lower.startswith('get_channel_list'): 
            result_string = get_handle_and_tile(engine)
            return send_message(chat_id, result_string, token)

        elif msg_lower.startswith('clone_leo'): 
            input_text = msg.split('clone_leo')[1].strip()
            if not input_text: return send_message(chat_id, "Please provide text after /clone_leo command.", token)
            else: 
                audio_generated_dir_user = os.path.join(audio_generated_dir, chat_id)
                output_file = chinese_audio_generation(input_text, model_id=FISH_AUDIO_ID_LEOWANG_CHINESE, api_key=FISH_AUDIO_API_KEY, output_dir=audio_generated_dir_user)
                if os.path.isfile(output_file): return send_audio_from_file(chat_id, output_file, token)

        elif msg_lower.startswith('clone_danli'): 
            input_text = msg.split('clone_danli')[1].strip()
            if not input_text: return send_message(chat_id, "Please provide text after /clone_danli command.", token)
            else:
                audio_generated_dir_user = os.path.join(audio_generated_dir, chat_id)
                output_file = chinese_audio_generation(input_text, model_id=FISH_AUDIO_ID_DANLI_CHINESE, api_key=FISH_AUDIO_API_KEY, output_dir=audio_generated_dir_user)
                if os.path.isfile(output_file): return send_audio_from_file(chat_id, output_file, token)

        elif msg_lower.startswith('group_message'):
            group_message = msg.replace('group_message', '').strip()
            return group_tg_message(group_message, token, engine)

        elif msg_lower in ['', 'set menu', 'setmenu']: return set_telegram_menu(token, chat_id)

        elif msg_lower in ['current_online_users', 'current_online']: 
            df = pd.read_sql(text("SELECT count(*) FROM chat_id_parameters WHERE chat_id IS NOT NULL"), engine)
            return send_message(chat_id, f"Current online users: {df['count(*)'].values[0]}", token)

        elif msg_lower.startswith('delete_'):
            post_id_or_video_id = msg.split('delete_')[-1].strip()
            print(f"post_id_or_video_id: {post_id_or_video_id}")
            if len(post_id_or_video_id) == 11: 
                video_id = post_id_or_video_id
                df = get_row_from_table_by_video_id(video_id, engine=engine)
                if df.empty: return "Failed to find the video ID in the database."
                post_id = df['Post_ID'].values[0]
                response = delete_given_post_id(post_id)
                return send_message(chat_id, response, token)
            else:
                post_id = post_id_or_video_id
                if not post_id: return send_message(chat_id, "Please provide the post ID after /delete_ command, example: /delete_66f9004d68bdd900018404d2", token)
                df = get_row_from_table_by_post_id(post_id, engine)
                if df.empty: return send_message(chat_id, "Failed to find the post ID in the database.", token)
                response =  delete_given_post_id(post_id)
                return send_message(chat_id, response, token)
        
        elif msg_lower in ['commands', 'commands_list', 'owner_commands', 'owner_commands_list']:
            # make a list of supported owner only commands list
            owner_commands_list = ['consumption', 'get_channel_list', 'add_channel', 'drop_channel_', 'alter_channel_', 'group_message', 'set_menu', 'current_online_users', 'delete_post', 'delete_video_id', 'clone_leo', 'clone_danli', 'setmenu', 'group_message', 'create_author_id', 'renew_vocabulary_chinese', 'set_email', 'change_phonetic', 'chat_chatid', 'inline_query_add', 'inline_query_remove', 'inline_query_list']
            clickable_list = [f"/{command}" for command in owner_commands_list]
            string_list = '\n'.join(clickable_list)
            return send_message(chat_id, f"Owner only commands list: \n\n{string_list}", token)

    msg = msg.replace('_', ' ')
    msg_lower = msg.lower()
    
    if length_msg < 21 and msg_lower not in GREETINGS_OR_ANSWERS:
        if msg_lower in WORDS_SET or is_all_english_letters(msg): return check_word_in_vocabulary(msg_lower, chat_id, engine, token, user_parameters)

    return openai_gpt_function(msg, chat_id, tools = FUNCTIONS_TOOLS, model = ASSISTANT_DOCUMENT_MODEL, engine = engine, token = token, user_parameters = user_parameters)
    

def is_all_english_letters(input_string: str) -> bool:
    pattern = r'^[a-zA-Z]+$'
    return bool(re.match(pattern, input_string))


def dealing_tg_command_http(msg: str, chat_id: str, user_parameters, token=TELEGRAM_BOT_TOKEN, engine=engine, message_id=0):
    user_ranking = user_parameters.get('ranking') or 0
    openai_api_key = user_parameters.get('openai_api_key', '')
    api_key = user_parameters['ghost_admin_api_key']
    api_url = user_parameters['ghost_api_url']
    user_ranking = user_parameters.get('ranking') or 0

    msg_lower = msg.lower()

    if msg_lower.startswith("https://docs.google.com/spreadsheets/d/"):
        if user_ranking < 2: return send_message(chat_id, f"As a /{tier} user, you are not qualified to use this function. You need to upgrade to /Silver or higher tier to use this function.\n\n/get_premium", token)

        google_sheet_id = msg.replace("https://docs.google.com/spreadsheets/d/", "").split("/")[0]
        if not google_sheet_id: return send_message(chat_id, "Incomplete Google Sheet URL.", token)

        google_sheet_id = set_spreadsheet_id_for_chat_id(chat_id, google_sheet_id, engine)
        if not google_sheet_id: return send_message(chat_id, "Failed to set the Google Sheet ID for the chat_id.", token)
        
        replay_markdown = f"Your Google Spreadsheet ID has been set to```{google_sheet_id[:10]}......{google_sheet_id[-11:]}```\n\nNow please download and rename your Google Spreadsheet Credentials JSON file to: <`google_sheet_credentials.json`> and send it to me."
        send_message_markdown(chat_id, replay_markdown, token)
        return delete_message(chat_id, message_id, token)
    

    elif 'youtube.com/playlist?list=' in msg_lower:
        playlist_id = msg.split("list=")[1].split("&")[0]
        if not playlist_id: return send_message(chat_id, "Invalid YouTube Playlist URL.", token)

        set_youtube_playlist_for_chat_id(chat_id, playlist_id, engine)
        
        tier = user_parameters.get('tier') or 'Free'
        daily_video_limit = user_parameters.get('daily_video_limit') or 0
        video_duration_limit = user_parameters.get('video_duration_limit') or 0

        inform_msg = f"Your YouTube Playlist ID has been set to: \n`{playlist_id}`\n\nAs your /tier is /{tier}, the AI bot will process {int(daily_video_limit)} English videos for you per day, and each video should be less than {int(video_duration_limit//60)} minutes and longer than {int(SHORTEST_LENGTH_PER_VIDEO//60)} minutes. None-English or none-qualified videos will be skipped."
        send_message(chat_id, inform_msg, token)

        return delete_message(chat_id, message_id, token)


    elif 'youtu' in msg_lower:
        if not 'youtu.be/' in msg_lower and not 'youtube.com/watch?v=' in msg_lower: return send_message(chat_id, "Invalid YouTube URL.", token)
        if msg_lower in ['https://youtu.be/', 'https://www.youtube.com/watch?v=', 'http://youtu.be/', 'http://www.youtube.com/watch?v=', 'https://youtu.be', 'http://youtu.be']: return send_message(chat_id, "Invalid YouTube URL.", token)

        youtube_url = youtube_url_format(msg)
        if not youtube_url: return send_message(chat_id, "Invalid YouTube URL.", token)

        video_id = youtube_url.split('v=')[-1]

        response_dict = youtube_id_download(video_id, chat_id, engine, token, user_parameters)
        if response_dict.get('URL'):
            url = response_dict.get('URL')
            words_list = response_dict.get('words_list') or ''
            if words_list: 
                words_list = words_list.split(',')
                words_list = [f"{i}. /{word.strip().replace(' ', '_')}" for i, word in enumerate(words_list)]
                words_list = '\n'.join(words_list)
                words_list = f"\n\nWords list from this youtube:\n\n{words_list}\n\n{url}"
                return send_message(chat_id, words_list, token)
            return send_message(chat_id, url, token)
                
        return send_message_markdown(chat_id, response_dict.get('Reason'), token)
    

    elif BLOG_BASE_URL in msg_lower:
        if not msg.endswith('/'): msg += '/'
        df = pd.read_sql(text(f"SELECT words_list FROM `{VIDEO_ID_AND_POST_ID_AND_URL_TABLE_NAME}` WHERE URL = :url"), engine, params={'url': msg})
        if not df.empty:
            words_list = df['words_list'].values[0]
            if words_list: 
                words_list = words_list.split(',')
                words_list = [f"{i}. /{word.strip().replace(' ', '_')}" for i, word in enumerate(words_list)]
                words_list = '\n'.join(words_list)
                words_list = f"\n\nWords list from this youtube:\n\n{words_list}"
                return send_message(chat_id, words_list, token)
            
        return send_message(chat_id, f"Sorry, no words list found for this link.", token)
    
    if api_key and api_url:
        is_url = find_url(msg_lower)
        
        if is_url: return handle_url_input(is_url, chat_id, ASSISTANT_MAIN_MODEL_BEST, user_parameters, token)
        else: return send_message(chat_id, "Sorry, I can't process your link.", token)

    return


# From given Title, search a cover image from Bing and make a blackblock image with logo and title, and put it to the search result image, creating a new cover image
def dealing_tg_photo(cover_png_file_path: str, video_title: str, chat_id: str, engine=engine, token=TELEGRAM_BOT_TOKEN):
    with engine.connect() as conn:
        query = f"SELECT Post_ID, Official_Title FROM `{VIDEO_ID_AND_POST_ID_AND_URL_TABLE_NAME}` WHERE Official_Title = :video_title"
        df = pd.read_sql(text(query), conn, params={'video_title': video_title})
        if df.empty: return send_message(chat_id, "Failed to find the post ID from the database.", token)

        post_id = df['Post_ID'].values[0]
        if not post_id: return send_message(chat_id, "Failed to get the post ID from the database.", token)

        cover_png_file_path = crop_image(cover_png_file_path)
        if not os.path.isfile(cover_png_file_path): return send_message(chat_id, "Failed to crop the image.", token)

        reply = update_blog_post_feature_img_to_ghost(post_id, cover_png_file_path)

    return send_message(chat_id, reply)



if __name__ == "__main__":
    print("Running subtitle_process.py")
