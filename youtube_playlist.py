from subtitle_process import *

logging.basicConfig(filename='yt.log', level=logging.INFO, format='%(asctime)s %(message)s')

CHANNEL_ID_DICT = get_channel_id_dict(engine = engine)


def get_latest_videos_from_playlists_and_insert_to_youtube_task_table(max_results=10, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine):
    hour = datetime.today().hour
    youtube_api_key = YOUTUBE_API_KEY_POOL[(hour) % 7]
    youtube_client = googleapiclient.discovery.build("youtube", "v3", developerKey=youtube_api_key)

    logging.info(f"get_latest_videos_from_playlists() was called ...")

    existing_video_ids = set()
    # from chat_id_parameters get playlists_dict (key), chat_id (value) dict
    with engine.connect() as conn:
        query = text("SELECT youtube_playlist, chat_id FROM chat_id_parameters WHERE youtube_playlist IS NOT NULL AND chat_id IS NOT NULL")
        df = pd.read_sql(query, conn)
        if df.empty: return logging.info("No user playlists found from table chat_id_parameters.")

        playlists_dict = dict(zip(df['youtube_playlist'], df['chat_id']))

        query_1 = text("SELECT Video_ID FROM video_id_check_history")
        df_1 = pd.read_sql(query_1, conn)
        existing_video_ids.update(df_1['Video_ID'].tolist())

        query_2 = text("SELECT Video_ID, Official_Title, URL FROM enspiring_video_and_post_id")
        df_2 = pd.read_sql(query_2, conn)
        existing_video_ids.update(df_2['Video_ID'].tolist())

    # Step 2: Load cutoff_date for each chat_id from a JSON file if available
    try:
        with open('cutoff_dates.json', 'r') as file: cutoff_dates = json.load(file)
    except FileNotFoundError: cutoff_dates = {}

    count = 0
    for playlist_id, chat_id in playlists_dict.items():
        cutoff_date = cutoff_dates.get(str(chat_id))
        if cutoff_date: cutoff_date = datetime.strptime(cutoff_date, '%Y-%m-%dT%H:%M:%SZ')

        try:
            # Step 3: Get the latest videos from the playlist
            request = youtube_client.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=max_results
            )
            response = request.execute()
        except Exception as e:
            if 'quotaExceeded' in str(e):
                current_api_key_name = YOUTUBE_API_KEY_REVERSED_DICT[youtube_api_key]
                alert_msg = f"YouTube API {current_api_key_name} quota exceeded. Please try again 24 hours later."
                send_message(OWNER_CHAT_ID, alert_msg, token)
                return logging.info(alert_msg)
            else: return logging.info(f"Error fetching videos from playlist ID {playlist_id}: {e}")

        video_ids = []
        latest_video_date = None
        for item in response.get('items', []):
            video_id = item['snippet']['resourceId']['videoId']
            playlist_added_at = item['snippet']['publishedAt']
            playlist_added_at_date = datetime.strptime(playlist_added_at, '%Y-%m-%dT%H:%M:%SZ')

            # Add to video_ids if cutoff_date is None or the video was added to the playlist after the cutoff_date
            if cutoff_date is None or playlist_added_at_date > cutoff_date: video_ids.append(video_id)

            # Update latest_video_date to the most recent video added time
            if latest_video_date is None or playlist_added_at_date > latest_video_date: latest_video_date = playlist_added_at_date

        if latest_video_date:
            cutoff_dates[str(chat_id)] = latest_video_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            with open('cutoff_dates.json', 'w') as file: json.dump(cutoff_dates, file, indent=4)

        video_ids = [item['snippet']['resourceId']['videoId'] for item in response.get('items', []) if item['snippet']['resourceId']['kind'] == 'youtube#video']

        # Remove existing video_ids
        new_video_ids = [video_id for video_id in video_ids if video_id not in existing_video_ids]

        # Step 4: Fetch all video details in one request
        if new_video_ids:
            user_parameters = user_parameters_realtime(chat_id, engine)
            try:
                request = youtube_client.videos().list(
                    part="snippet, contentDetails, statistics, status, player",
                    id=','.join(new_video_ids)
                )
                response = request.execute()
            except Exception as e:
                if 'quotaExceeded' in str(e):
                    current_api_key_name = YOUTUBE_API_KEY_REVERSED_DICT[youtube_api_key]
                    alert_msg = f"YouTube API {current_api_key_name} quota exceeded. Please try again 24 hours later."
                    send_message(OWNER_CHAT_ID, alert_msg, token)
                    return logging.info(alert_msg)
                else: return logging.info(f"Error fetching video details for video IDs {new_video_ids}: {e}") 

            for item in response.get('items', []):
                video_id = item['id']
                snippet = item['snippet']
                content_details = item['contentDetails']
                status = item['status']
                player = item['player']

                # Extract required fields
                reply_dict = {
                    'Video_ID': video_id,
                    'Official_Title': snippet['title'],
                    'Duration': convert_duration_to_seconds(content_details['duration']),
                    'Language': snippet.get('defaultAudioLanguage', 'Unknown').lower(),
                    'Channel_Title': snippet.get('channelTitle', 'Unknown'),
                    'Channel_ID': snippet.get('channelId', 'Unknown'),
                    'Video_Description': snippet.get('description', 'No description available'),
                    'Subtitle': content_details.get('caption', 'false'),
                    'Definition': content_details.get('definition', 'sd'),
                    'License': status.get('license', 'youtube'),
                    'Embeddable': status.get('embeddable', False),
                    'Embed_HTML': player.get('embedHtml', '')
                }

                # 获取封面图片链接
                thumbnails = snippet.get('thumbnails', {})
                if 'maxres' in thumbnails: reply_dict['Image_URL'] = thumbnails['maxres']['url']
                elif 'high' in thumbnails: reply_dict['Image_URL'] = thumbnails['high']['url']
                elif 'medium' in thumbnails: reply_dict['Image_URL'] = thumbnails['medium']['url']
                elif 'default' in thumbnails: reply_dict['Image_URL'] = thumbnails['default']['url']

                # Append video details to history
                df = pd.DataFrame([reply_dict])
                df.to_sql('video_id_check_history', engine, if_exists='append', index=False)

                youtube_url = f"https://www.youtube.com/watch?v={video_id}"

                video_duration_limit = user_parameters.get('video_duration_limit') or 0
                daily_video_limit = user_parameters.get('daily_video_limit') or 0
                tier = user_parameters.get('tier') or 'Free'

                # Check if the video meets the user's requirements
                if reply_dict['Duration'] > video_duration_limit: 
                    inform_msg = f"Your video duration is {int(reply_dict['Duration']//60)} minutes, but your /tier /{tier} has a limit of {int(video_duration_limit//60)} minutes. Therefore, this video will not be processed.\n\nVideo Title & URL:\n>> {reply_dict['Official_Title'][:30]}...\n\n{youtube_url}"
                    send_message(chat_id, inform_msg, token)
                    continue

                if reply_dict['Duration'] < SHORTEST_LENGTH_PER_VIDEO:
                    inform_msg = f"Your video duration is {int(reply_dict['Duration']//60)} minutes, but the minimum length for processing is {int(SHORTEST_LENGTH_PER_VIDEO//60)} minutes. Therefore, this video will not be processed.\n\nVideo Title & URL:\n>> {reply_dict['Official_Title'][:30]}...\n\n{youtube_url}"
                    send_message(chat_id, inform_msg, token)
                    continue

                if not reply_dict['Language'].startswith(VIDEO_LANGUAGE_LIMIT): 
                    inform_msg = f"According to Youtube API response, your video language is `{reply_dict['Language']}`, but the we only process English original videos. Therefore, this video will not be processed.\n\nVideo Title & URL:\n>> {reply_dict['Official_Title'][:30]}...\n\n{youtube_url}"
                    send_message(chat_id, inform_msg, token)
                    continue
                
                logging.info(f"New video detected: {reply_dict['Official_Title']}, Video ID: {video_id}, will be inserted into the task list...")

                result_dict = insert_new_task_to_youtube_task_table_df(video_id, reply_dict['Official_Title'], chat_id, engine)
                if result_dict['Status'] == True: inform_msg = f"New task has been inserted into the task list. Roughly it will take 5 minutes to process the video. Please wait patiently. You will get a notification once the process is started. \n\nYour /tier /{tier} allows {int(daily_video_limit)} video process(es) per day, including the videos saved in your /youtube_playlist. The extra videos will be processed in the next 24 hours, starting from the latest submission and so on.\n\nVideo Title & URL:\n>> {reply_dict['Official_Title'][:30]}...\n\n{youtube_url}"
                else: inform_msg = result_dict['Reason']
                send_message(chat_id, inform_msg, token)
                count += 1
    return


# Function to get the latest 5 videos from a YouTube channel using the YouTube client and save them to video_id_check_history
def get_latest_videos_from_channel(channel_id_dict: dict = CHANNEL_ID_DICT, max_results = 50, engine = engine):

    hour = datetime.today().hour
    youtube_api_key = YOUTUBE_API_KEY_POOL[(hour+1) % 7]
    youtube_client = googleapiclient.discovery.build("youtube", "v3", developerKey = youtube_api_key)

    logging.info(f"get_latest_videos_from_channel() was called ...")

    # Step 1: Get all existing Video_IDs from the database to create a unique list for checking
    existing_video_ids = set()
    with engine.connect() as conn:
        query_1 = text("SELECT Video_ID FROM video_id_check_history")
        df_1 = pd.read_sql(query_1, conn)
        existing_video_ids.update(df_1['Video_ID'].tolist())

        query_2 = text("SELECT Video_ID FROM enspiring_video_and_post_id")
        df_2 = pd.read_sql(query_2, conn)
        existing_video_ids.update(df_2['Video_ID'].tolist())

    for channel_id in channel_id_dict:
        try:
            # Step 3: Get the latest videos from the channel
            request = youtube_client.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                maxResults=max_results
            )
            response = request.execute()
        except Exception as e:
            if 'quotaExceeded' in str(e): 
                current_api_key_name = YOUTUBE_API_KEY_REVERSED_DICT[youtube_api_key]
                alert_msg = f"YouTube API `{current_api_key_name}` quota exceeded. Please try again 24 hours later."
                send_message(OWNER_CHAT_ID, alert_msg)
                return 0
            else: logging.info(f"Error fetching videos from channel ID {channel_id}: {e}")
            return 0
        
        video_ids = [item['id']['videoId'] for item in response.get('items', []) if item['id']['kind'] == 'youtube#video']

        # remove existing video_ids
        video_ids = [video_id for video_id in video_ids if video_id not in existing_video_ids]

        len_video_ids = len(video_ids)
        channel_title = channel_id_dict[channel_id]
        print(f"Channel Title: {channel_title} got Video IDs: {len_video_ids}")

        # Step 4: Fetch all video details in one request
        if video_ids:
            try:
                request = youtube_client.videos().list(
                    part="snippet, contentDetails, statistics, status, player",
                    id=','.join(video_ids)
                )
                response = request.execute()
            except Exception as e:
                if 'quotaExceeded' in str(e): 
                    logging.info(f"2 YouTube API (YOUTUBE_API_KEY_ENSPIRING_AI) quota exceeded. Please try again 24 hours later.")
                    return 0
                else: logging.info(f"Error fetching video details for video IDs {video_ids}: {e}")
                return 0

            with engine.connect() as conn:
                for item in response.get('items', []):
                    video_id = item['id']
                    snippet = item['snippet']
                    content_details = item['contentDetails']
                    status = item['status']
                    player = item['player']

                    # Extract required fields
                    reply_dict = {
                        'Video_ID': video_id,
                        'Official_Title': snippet['title'],
                        'Duration': convert_duration_to_seconds(content_details['duration']),
                        'Language': snippet.get('defaultAudioLanguage', 'Unknown').lower(),
                        'Channel_Title': snippet.get('channelTitle', 'Unknown'),
                        'Channel_ID': snippet.get('channelId', 'Unknown'),
                        'Video_Description': snippet.get('description', 'No description available'),
                        'Subtitle': content_details.get('caption', 'false'),
                        'Definition': content_details.get('definition', 'sd'),
                        'License': status.get('license', 'youtube'),
                        'Embeddable': status.get('embeddable', False),
                        'Embed_HTML': player.get('embedHtml', '')
                    }

                    # 获取封面图片链接
                    thumbnails = snippet.get('thumbnails', {})
                    if 'maxres' in thumbnails: reply_dict['Image_URL'] = thumbnails['maxres']['url']
                    elif 'high' in thumbnails: reply_dict['Image_URL'] = thumbnails['high']['url']
                    elif 'medium' in thumbnails: reply_dict['Image_URL'] = thumbnails['medium']['url']
                    elif 'default' in thumbnails: reply_dict['Image_URL'] = thumbnails['default']['url']

                    # Append video details to history
                    df = pd.DataFrame([reply_dict])
                    df.to_sql('video_id_check_history', engine, if_exists='append', index=False)

    return 0


def check_video_id_check_history_for_new_videos(duration = 3600, language_limit = 'en', token = os.getenv("TELEGRAM_BOT_TOKEN_TEST"), engine = engine):
    with engine.connect() as conn:
        query_str = """SELECT vh.Video_ID, vh.Official_Title FROM video_id_check_history vh 
                      LEFT JOIN enspiring_video_and_post_id vp ON vh.Video_ID = vp.Video_ID 
                      WHERE vp.Video_ID IS NULL 
                      AND vh.Status IS NULL 
                      AND vh.Channel_ID IS NOT NULL 
                      AND vh.Embeddable = 1 
                      AND vh.Duration < :duration 
                      AND vh.Duration > 480 
                      AND (vh.Language = :language_limit OR vh.Language LIKE :language_limit_start) 
                      ORDER BY RAND() 
                      LIMIT 2"""
        
        query = text(query_str)
        params = {'duration': duration, 'language_limit': language_limit, 'language_limit_start': language_limit + '%'}
        df = pd.read_sql(query, conn, params=params)
        if df.empty: return 0

        i = 0
        for _, row in df.iterrows():
            video_id = row['Video_ID']
            official_title = row['Official_Title']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            if i == 0: generating_new_post_from_url(video_url, video_dir, OWNER_CHAT_ID, token, engine)
            elif i == 1: 
                chat_id = LAOGEGE_CHAT_ID
                date_today = str(datetime.now().date())
                df = pd.DataFrame({'youtube_url': [video_url], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['creator_post_youtube'], 'date': [date_today]})
                df.to_sql('youtube_transcript_jobs', engine, if_exists='append', index=False)
                post_youtube_to_ghost_creator(video_url, chat_id, engine, os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), ASSISTANT_MAIN_MODEL_BEST, '', user_parameters_realtime(chat_id, engine), '', official_title)

            i += 1

    return 1


def complete_pending_tasks(chat_id, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    pending_tasks_df = fetch_recent_pending_tasks(chat_id, engine)
    if pending_tasks_df.empty: return

    completed_task_count = fetch_recent_completed_tasks(chat_id, engine)
    user_parameters = user_parameters_realtime(chat_id, engine)

    daily_video_limit = user_parameters.get('ranking') or 0
    remain_quota = daily_video_limit - completed_task_count
    if chat_id in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID]: remain_quota = 5
    if remain_quota <= 0: return

    pending_tasks_df = pending_tasks_df.sort_values(by='Added_Date_Time', ascending=False)
    pending_tasks_df = pending_tasks_df.head(int(remain_quota))

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    
    for _, task_dict in pending_tasks_df.iterrows():
        video_url = f"https://www.youtube.com/watch?v={task_dict['Video_ID']}"
        official_title = task_dict['Official_Title']

        if chat_id != OWNER_CHAT_ID and all([admin_api_key, ghost_url]): status = post_youtube_to_ghost_creator(video_url, chat_id, engine, token, ASSISTANT_MAIN_MODEL, '', user_parameters, '', official_title)
        else: status = generating_new_post_from_url(video_url, video_dir, chat_id, token, engine)

        if status and status == 'Completed': update_task_status_in_youtube_task_table_df(task_dict['Video_ID'], 'Completed', engine)
        else: update_task_status_in_youtube_task_table_df(task_dict['Video_ID'], 'Failed', engine)

    return


def check_youtube_transcript_jobs(chat_id, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    df = pd.read_sql(text("SELECT * FROM youtube_transcript_jobs WHERE job_status = 'pending' AND chat_id = :chat_id"), engine, params={'chat_id': chat_id})
    if df.empty: return
    
    processed_youtube_urls = []
    for _, row in df.iterrows():
        youtube_url = row['youtube_url']
        job_type = row['job_type']
        with engine.begin() as conn: conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url"), {'youtube_url': youtube_url, 'status': 'processing'})

        if job_type == 'transcript':
            if youtube_url in processed_youtube_urls: continue
            processed_youtube_urls.append(youtube_url)

            response_dict = get_transcript_from_youtube_url(youtube_url, video_dir, chat_id, token, engine)
            cleaned_text = response_dict.get('cleaned_text')

            status = 'completed' if response_dict.get('status') else 'failed'
            with engine.begin() as conn: conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url"), {'youtube_url': youtube_url, 'status': status})

            if not cleaned_text: 
                send_message(chat_id, response_dict.get('reason'), token)
                continue
        
            length_text = len(cleaned_text)
            if length_text > 2000:
                output_dir = os.path.join(working_dir, chat_id)
                timestamp_now = datetime.now().strftime('%Y%m%d_%H%M%S')
                file_path = os.path.join(output_dir, f"transcript_{timestamp_now}.txt")
                with open(file_path, 'w', encoding='utf-8') as f: f.write(cleaned_text)
                send_document_from_file(chat_id, file_path, "", token)
            else: send_message(chat_id, cleaned_text, token)

        elif job_type == 'creator_post_youtube':
            if youtube_url in processed_youtube_urls: continue
            processed_youtube_urls.append(youtube_url)
            
            send_debug_to_laogege(f"Processing creator_post_youtube job for chat_id: /chat_{chat_id} and youtube_url: {youtube_url}")

            try: post_youtube_to_ghost_creator(youtube_url, chat_id, engine, token, ASSISTANT_MAIN_MODEL)
            except Exception as e: send_debug_to_laogege(f"Error in check_youtube_transcript_jobs() >> chat_id: /chat_{chat_id} >> youtube_url: {youtube_url}\n\n{e}")

        else: continue



def check_user_news_jobs(chat_id, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    print("check_user_news_jobs() was called...")
    df = pd.read_sql(text("SELECT * FROM user_news_jobs WHERE job_status = 'pending' AND chat_id = :chat_id"), engine, params={'chat_id': chat_id})
    if df.empty: return

    user_parameters = user_parameters_realtime(chat_id, engine)

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')

    for _, row in df.iterrows():
        user_prompt = row['user_prompt']
        with engine.begin() as conn: conn.execute(text("UPDATE user_news_jobs SET job_status = :status WHERE user_prompt = :user_prompt AND chat_id = :chat_id"), {'user_prompt': user_prompt, 'status': 'processing', 'chat_id': chat_id})

        if admin_api_key and ghost_url and chat_id != OWNER_CHAT_ID: 
            try: post_news_to_ghost_creator(user_prompt, chat_id, engine, token, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = user_parameters)
            except Exception as e: send_debug_to_laogege(f"Error in check_user_news_jobs() >> /chat_{chat_id} >> user_prompt: {user_prompt}\n\n{e}")
            continue

        response_dict = post_news_to_ghost(user_prompt, chat_id, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = token, model = ASSISTANT_DOCUMENT_MODEL, user_parameters = user_parameters)
        status = 'failed' if not response_dict.get('status') else 'completed'
        
        with engine.begin() as conn: conn.execute(text("UPDATE user_news_jobs SET job_status = :status WHERE user_prompt = :user_prompt AND chat_id = :chat_id"), {'user_prompt': user_prompt, 'status': status, 'chat_id': chat_id})
        
        if response_dict.get('title_url'): twitter_post(response_dict.get('title_url'), **twitter_enspiring)

    return


# get prompt form user_stories table where explained = 0
def get_user_stories_explained(chat_id, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    df = pd.read_sql(text("SELECT * FROM user_stories WHERE explained = 0 AND chat_id = :chat_id"), engine, params={'chat_id': chat_id})
    if df.empty: return

    user_parameters = user_parameters_realtime(chat_id, engine)
    mother_language = user_parameters.get('mother_language')
    if not mother_language or mother_language == 'English': return

    email_address = user_parameters.get('email', '')
    if not email_address: return

    user_name = user_parameters.get('name') or 'User'
    
    for _, row in df.iterrows():
        user_prompt = row['prompt']
        if not user_prompt: continue

        user_prompt = f"Mother Language is {mother_language}. \nStory to be explained: \n\n{user_prompt}"
        try:
            # response_text = ollama_gpt_chat_basic(user_prompt, system_prompt=OLLAMA_SYSTEM_PROMPT_EXPLAIN_STORY, model="llama3.2")
            response_text = openai_gpt_chat(OLLAMA_SYSTEM_PROMPT_EXPLAIN_STORY, user_prompt, chat_id, model=ASSISTANT_DOCUMENT_MODEL, user_parameters=user_parameters)

            if response_text:
                email_subject = f"STORY EXPLAINED: {row['title']}"
                response_text = response_text.replace('*', '').replace('#', '')
                response_text = f"Hello {user_name},\n\nHere is the explanation for your story: \n\n{response_text}"
                send_email_text(email_address, email_subject, response_text)

                with engine.begin() as conn: conn.execute(text("UPDATE user_stories SET explained = 1 WHERE slug = :slug"), {'slug': row['slug']})

        except Exception as e: send_message(OWNER_CHAT_ID, f"Error occurred in get_user_stories_explained: {e}", token)

    return


def get_user_stories_explained_tailored(chat_id, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    df = pd.read_sql(text("SELECT * FROM user_stories_tailored WHERE explained = 0 AND chat_id = :chat_id"), engine, params={'chat_id': chat_id})
    if df.empty: return

    user_parameters = user_parameters_realtime(chat_id, engine)

    mother_language = user_parameters.get('mother_language')
    if not mother_language or mother_language == 'English': return

    email_address = user_parameters.get('email')
    if not email_address: return
    
    user_name = user_parameters.get('name') or 'User'

    for _, row in df.iterrows():

        generated_story = row['generated_story']
        if not generated_story: continue

        user_prompt = f"Mother Language is {mother_language}. \nStory to be explained: \n\n{generated_story}"

        try:
            # response_text = ollama_gpt_chat_basic(user_prompt, system_prompt=OLLAMA_SYSTEM_PROMPT_EXPLAIN_STORY, model="llama3.2")
            response_text = openai_gpt_chat(OLLAMA_SYSTEM_PROMPT_EXPLAIN_STORY, user_prompt, chat_id, model=ASSISTANT_DOCUMENT_MODEL, user_parameters = user_parameters)

            if response_text:
                email_subject = f"STORY EXPLAINED: {row['title']}"
                response_text = response_text.replace('*', '').replace('#', '')
                response_text = f"Hello {user_name},\n\nHere is the explanation for your story: \n\n{response_text}"
                send_email_text(email_address, email_subject, response_text)
                
                with engine.begin() as conn: conn.execute(text("UPDATE user_stories_tailored SET explained = 1 WHERE slug = :slug"), {'slug': row['slug']})
        except Exception as e: send_message(OWNER_CHAT_ID, f"Error occurred in get_user_stories_explained_tailored: {e}", token)
    return



# Start monitoring the playlist
if __name__ == "__main__":
    print("Youtube_playlisty.py >> Starting pending tasks and new videos from playlist...")
    token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")

    try: get_latest_videos_from_playlists_and_insert_to_youtube_task_table(max_results = 10, token = token, engine = engine)
    except Exception as e: send_debug_to_laogege(f"ERROR when get latest videos and inserted into Youtube Task table, code:\n\n{e}")

    if which_ubuntu == 'TB': 
        try: check_gmail(imap_username = GMAIL_ADDRESS, imap_password = GMAIL_PASSWORD, engine = engine)
        except Exception as e: send_debug_to_laogege(f"{GMAIL_ADDRESS} ERROR when checking, code:\n\n{e}")

        try: update_feeds_and_handle_new_posts(chat_id = LAOGEGE_CHAT_ID, model = ASSISTANT_MAIN_MODEL_BEST, user_parameters = {}, token = token)
        except Exception as e: send_debug_to_laogege(f"ERROR when updating feeds and handling new posts, code:\n\n{e}")
