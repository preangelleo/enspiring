from assistant_thread import *


def get_transcript_from_youtube_url(youtube_url: str, video_temp_dir = video_dir, chat_id = OWNER_CHAT_ID, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine):
    response_dict = {'status': False, 'reason': 'Failed to download video file from YouTube link.'}
    if not youtube_url: return "No url was provided."
    reply_dict = download_youtube_video(youtube_url, video_temp_dir, chat_id, token, engine)
    if not reply_dict: 
        response_dict['reason'] = f"Failed to download video file from YouTube link. What you input is: {youtube_url}, it's not a valid YouTube link."
        return response_dict

    post_url = reply_dict.get('URL')
    if post_url: 
        response_dict['status'] = True
        response_dict['reason'] = f"Your transcript has been processed and posted online previously. You can copy the transcript from the following link: \n{post_url}"
        return response_dict

    if not reply_dict.get('Status'): 
        response_dict['reason'] = reply_dict.get('Reason')
        return response_dict

    mp3_file_path = reply_dict.get('Output_Audio_File')
    srt_file_path = reply_dict.get('Output_Srt_File')
    vtt_file_path = reply_dict.get('Output_Vtt_File')
    subtitle_format = reply_dict.get('Subtitle_Format')
    
    current_folder = os.path.dirname(mp3_file_path)

    reply_dict['current_folder'] = current_folder
    reply_dict['mp3_file_path'] = mp3_file_path
    reply_dict['chat_id'] = chat_id

    assembly_json_file_path = mp3_file_path.replace(".mp3", "_assembly.json")
    subtitle_file_path = srt_file_path if subtitle_format == 'srt' else vtt_file_path

    cleaned_text = ''
    if not os.path.isfile(subtitle_file_path):
        if os.path.isfile(mp3_file_path):
            
            if not os.path.isfile(assembly_json_file_path): 
                try: transcribe_audio_file(mp3_file_path, assembly_json_file_path, chat_id, ASSEMBLYAI_API_KEY, engine)
                except Exception as e: return response_dict
                
                if not os.path.isfile(assembly_json_file_path): 
                    response_dict['reason'] = "Failed to get assembly json file from audio file!"
                    return response_dict

            cleaned_text, transcript_file_path_raw = get_raw_text_from_json(assembly_json_file_path)

    else: cleaned_text = subtitle_to_text(subtitle_file_path)

    if cleaned_text:
        response_dict['status'] = True
        response_dict['cleaned_text'] = cleaned_text
        return response_dict
    else:
        response_dict['reason'] = "Failed to get transcript from the audio file."
        return response_dict
    

def delete_given_post_id(post_id, api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    # Split the key into ID and SECRET
    id, secret = api_key.split(':')
    
    # Create a JWT (expires in 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create the JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Delete the post with the given ID
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    response = requests.delete(f'{api_url}/ghost/api/admin/posts/{post_id}/', headers=headers)
    
    if response.status_code == 204: return f"Succesfully deleted post with ID: {post_id}"
    else: return f"Failed to delete post with ID: {post_id} - {response.status_code} {response.text}"


def delete_given_post_id_type(post_id, post_type, api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    # Split the key into ID and SECRET
    id, secret = api_key.split(':')
    
    # Create a JWT (expires in 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create the JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Delete the post with the given ID
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    post_type_key = f"{post_type}s"

    response = requests.delete(f'{api_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers)
    
    if response.status_code == 204: return f"Succesfully deleted {post_type}"
    else: return f"Failed to delete post with ID: {post_id} - {response.status_code} {response.text}"


def get_post_updated_at(post_id: str, post_type: str = 'page', api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    # Split the key into ID and SECRET
    id, secret = api_key.split(':')

    # Create a JWT (expires in 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create the JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Fetch the existing post data to get the `updated_at` field
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    get_post_response = requests.get(f'{api_url}/ghost/api/admin/{post_type}s/{post_id}/', headers=headers)

    if get_post_response.status_code != 200:
        return f"Failed to retrieve post data: \n{get_post_response.status_code} {get_post_response.text}"

    post_data = get_post_response.json()
    updated_at = post_data[f'{post_type}s'][0]['updated_at']  # Retrieve the updated_at field
    
    return updated_at


def update_blog_post_feature_img_to_ghost(post_id: str, cover_png_file_path: str, post_type: str = 'post', api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    post_type_key = f"{post_type}s"

    # Split the key into ID and SECRET
    id, secret = api_key.split(':')

    # Create a JWT (expires in 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create the JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Fetch the existing post data to get the `updated_at` field
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    get_post_response = requests.get(f'{api_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers)

    if get_post_response.status_code != 200:
        return f"Failed to retrieve post data: \n{get_post_response.status_code} {get_post_response.text}"

    post_data = get_post_response.json()
    updated_at = post_data[post_type_key][0]['updated_at']  # Retrieve the updated_at field

    # Check and determine the correct MIME type for the image
    mime_type, _ = mimetypes.guess_type(cover_png_file_path)
    if mime_type is None: mime_type = 'image/png'  # Default to PNG if the MIME type can't be determined

    # Upload the cover image
    with open(cover_png_file_path, 'rb') as img:
        headers = {
            'Authorization': f'Ghost {token}',
            'Accept-Version': 'v3'
        }
        files = {
            'file': (cover_png_file_path, img, mime_type),  # Attach correct MIME type
            'ref': (None, cover_png_file_path)  # 'ref' is optional based on the API
        }
        image_response = requests.post(f'{api_url}/ghost/api/admin/images/upload/', headers=headers, files=files)

    if image_response.status_code == 201: image_url = image_response.json()['images'][0]['url']
    else: return

    # Prepare the post data with the `updated_at` field and the new feature image
    post_data = {
        post_type_key: [{
            "feature_image": image_url,  # Set the uploaded image as the feature image
            "updated_at": updated_at  # Include the original updated_at field
        }]
    }

    # Send the PUT request to update the blog post's feature image
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    response = requests.put(f'{api_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers, json=post_data)

    # Check the response status
    if response.status_code == 200: return response.json()[post_type_key][0]['url']
    else: return f"Failed to update post feature image: \n{response.status_code} {response.text}"


def generate_post_text_file(reply_dict: dict):
    blog_post_text_file_path = reply_dict.get('Output_Video_File', '').replace('.mp4', '_final.txt')
    video_summary = reply_dict.get('video_summary', '')
    vocabularies = reply_dict.get('vocabularies', '')
    paragraphed_transcript = reply_dict.get('paragraphed_transcript', '')
    youtube_link = reply_dict.get('Youtube_Link', '')
    title = reply_dict.get('Official_Title', '')
    youtube_string = f"{youtube_link}\n> Please remember to turn on the CC button to view the subtitles."
    final_text_list = [title, video_summary, youtube_string, vocabularies, title, paragraphed_transcript]
    final_text_string = '\n\n'.join(final_text_list)
    # save to a file blog_post_text_file_path
    with open(blog_post_text_file_path, 'w', encoding='utf-8') as f: f.write(final_text_string)
    return blog_post_text_file_path


def extract_youtube_link_from_lines(lines):
    # 定义匹配 YouTube 链接的正则表达式
    youtube_regex = r"(https?://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+)"
    
    # 使用列表推导式找出匹配的链接行
    youtube_links = [re.search(youtube_regex, line).group(0) for line in lines if re.search(youtube_regex, line)]
    
    # 返回第一个匹配的链接，如果没有则返回 None
    return youtube_links[0] if youtube_links else None


def extract_words_list(text):
    words_list = []
    lines = text.split('\n\n')
    for line in lines[1:]:
        if not line: continue
        # 取出 . 和 [ 之间的内容，放入 words_list
        word = re.search(r"\. (.*?) \[", line)
        if word: 
            word = word.group(1)
            words_list.append(word.strip().capitalize())
    if not words_list: print(f"Can't find words_list from the text by []: {lines[1]}")
    for line in lines[1:]:
        if not line: continue
        # 取出 . 和 [ 之间的内容，放入 words_list
        word = re.search(r"\. (.*?) \(", line)
        if word: 
            word = word.group(1)
            words_list.append(word.strip().capitalize())
    if not words_list: print(f"Can't find words_list from the text by (): {lines[1]}")
    return words_list


def upload_audio_to_ghost(api_key, ghost_url, audio_file_path):
    # Split API key into ID and Secret
    id, secret = api_key.split(':')

    # Token expiration time (current time + 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    # Create JWT payload
    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Guess MIME type for the audio file
    mime_type, _ = mimetypes.guess_type(audio_file_path)
    if mime_type is None:
        mime_type = 'audio/mpeg'  # Default to MP3 if the MIME type can't be determined

    # Open the audio file and prepare for upload
    with open(audio_file_path, 'rb') as audio:
        headers = {
            'Authorization': f'Ghost {token}',
            'Accept-Version': 'v3'
        }
        files = {
            'file': (audio_file_path, audio, mime_type)
        }

        # Upload audio file to Ghost
        audio_upload_url = f'{ghost_url}/ghost/api/admin/media/upload/'  # Adjust endpoint if needed
        response = requests.post(audio_upload_url, headers=headers, files=files)

    # Handle the response
    if response.status_code == 201:
        # Successful upload, return the URL of the uploaded audio
        audio_url = response.json()['media'][0]['url']
        return {
            'Status': True,
            'URL': audio_url
        }
    else:
        return {
            'Status': False,
            'Reason': f"Failed to upload audio: {response.status_code} {response.text}"
        }


def openai_gpt_structured_output(prompt: str, system_prompt: str, chat_id: str, model = ASSISTANT_MAIN_MODEL_BEST, engine = engine, user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    class PostContents(BaseModel):
        title: str
        article: str
        excerpt: str
        tags: str
        midjourney_prompt: str

    openai_api_key = user_parameters.get('openai_api_key', '') or os.getenv("OPENAI_API_KEY_BACKUP")
    client = OpenAI(api_key=openai_api_key)

    try: completion = client.beta.chat.completions.parse(model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], response_format=PostContents)
    except Exception as e: 
        send_debug_to_laogege(f"openai_gpt_structured_output() failed: >> \n\n{e}")
        return {}
    
    # Get the input token and output token and total token

    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    model_price_input = OPENAI_MODEL_PRICING.get(model, {}).get('input', 0)
    model_price_output = OPENAI_MODEL_PRICING.get(model, {}).get('output', 0)
    cost_input = model_price_input * prompt_tokens
    cost_output = model_price_output * completion_tokens
    cost_total = cost_input + cost_output

    update_chat_id_monthly_consumption(chat_id, cost_total, engine)
    
    event = completion.choices[0].message.parsed
    event_dict = event.model_dump()

    return event_dict


def openai_gpt_structured_output_translate(prompt: str, system_prompt: str, chat_id, model = ASSISTANT_MAIN_MODEL, engine = engine, user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    class PostContents(BaseModel):
        title: str
        excerpt: str
        tags: str
        article: str

    openai_api_key = user_parameters.get('openai_api_key', '') or os.getenv("OPENAI_API_KEY_BACKUP")
    client = OpenAI(api_key=openai_api_key)

    try: completion = client.beta.chat.completions.parse(model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}], response_format=PostContents)
    except Exception as e: 
        send_debug_to_laogege(f"openai_gpt_structured_output_translate() failed: >> \n\n{e}")
        return 
    
    # Get the input token and output token and total token

    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    model_price_input = OPENAI_MODEL_PRICING.get(model, {}).get('input', 0)
    model_price_output = OPENAI_MODEL_PRICING.get(model, {}).get('output', 0)
    cost_input = model_price_input * prompt_tokens
    cost_output = model_price_output * completion_tokens
    cost_total = cost_input + cost_output

    update_chat_id_monthly_consumption(chat_id, cost_total, engine)
    
    event = completion.choices[0].message.parsed
    event_dict = event.model_dump()

    return event_dict


def send_blog_post_from_dict(content_dict: dict, api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL, engine=engine, user_parameters={}):
    current_folder = content_dict.get('current_folder', video_dir)

    cover_png_file_path, blog_post_text_file_path, blackblock_png_file_path, just_png_file_path = '', '', '', ''
    # From current_folder get _final.txt, _final.png and _blackblock.png
    for files in os.listdir(current_folder):
        if files.endswith('_final.txt'): blog_post_text_file_path = os.path.join(current_folder, files)
        if files.endswith('_final.png'): cover_png_file_path = os.path.join(current_folder, files)
        if files.endswith('_blackblock.png'): blackblock_png_file_path = os.path.join(current_folder, files)
        if files.endswith('.png'): just_png_file_path = os.path.join(current_folder, files)

    cover_png_file_path = just_png_file_path if not cover_png_file_path else blackblock_png_file_path

    if not os.path.isfile(blog_post_text_file_path): return f"Can't find the blog post text file: {blog_post_text_file_path}"
    if not os.path.isfile(cover_png_file_path): return f"Can't find the cover image file: {cover_png_file_path}"

    with open(blog_post_text_file_path, 'r', encoding='utf-8') as f: text_content = f.read()
    lines = text_content.split('\n')
    title = lines[0].strip()
    lines = lines[1:]

    # Extract the video_id from the content_dict or the lines
    video_id = content_dict.get('Video_ID', '')
    if not video_id:
        youtube_link = extract_youtube_link_from_lines(lines)
        video_id = get_video_id(youtube_link)
        if not video_id:
            for files in os.listdir(current_folder):
                if files.endswith('_url.txt'):
                    with open(os.path.join(current_folder, files), 'r', encoding='utf-8') as f: url_lines = f.readlines()
                    youtube_link = extract_youtube_link_from_lines(url_lines)
                    video_id = get_video_id(youtube_link)
                    break

        content_dict['Video_ID'] = video_id

    if not video_id: return f"From current folder: {current_folder}, can't find the video_id"
    
    # Check if the video_id already exists in the table
    with engine.connect() as connection:
        try:
            # Use a connection from the engine to execute a parameterized query
            query = text(f"""SELECT Official_Title, URL, Post_ID FROM {VIDEO_ID_AND_POST_ID_AND_URL_TABLE_NAME} WHERE Video_ID = :video_id""")
            df = pd.read_sql_query(query, connection, params={'video_id': video_id})
            if not df.empty: 
                post_id = df['Post_ID'].values[0]
                url = df['URL'].values[0]

                content_dict['Status'] = True
                content_dict['Post_ID'] = post_id
                content_dict['URL'] = url
                return content_dict
            
        except Exception as e: print(f"Error in reading the table: {VIDEO_ID_AND_POST_ID_AND_URL_TABLE_NAME} - {e}")

    words_list = content_dict.get('words_list', [])

    if not words_list:
        vocabulary_text = content_dict.get('vocabularies', '')
        if not vocabulary_text:
            for file in os.listdir(current_folder):
                if file.endswith('_vocabulary.txt'):
                    print(f"Found the vocabulary file: {file}")
                    with open(os.path.join(current_folder, file), 'r', encoding='utf-8') as f: vocabulary_text = f.read()
                    break
        words_list = extract_words_list(vocabulary_text)
        content_dict['words_list'] = words_list
        
    if not words_list: return f"Can't find words_list for video_id: {video_id}"

    chat_id = content_dict.get('chat_id') or LAOGEGE_CHAT_ID
    channel_title = content_dict.get('Channel_Title', '')

    author_id = user_parameters.get('author_id') or AUTHOR_ID_LAOGEGE

    tags = content_dict.get('transcript_tags', []) + [channel_title]
    if not tags:
        hot_tags_string = ', '.join(HOT_TAGS_LIST)
        tags_system_prompt = f"""Based on the transcript, come up with 6 tags for the video post that will help increase its visibility and reach on social media platforms. Choose 3 from ({hot_tags_string}), make another 3 tags that are relevant to the video content. Output only the tags in text format, no markdown or special formatting. A python function will extract the tags directly from your response, split with ','. So don't put any other words besids tags, not even quotation. Output sample:
        Entrepreneurship, Finance, Global, Harvard, Innovation, Inspiration
        """
        tags_text = openai_gpt_chat(tags_system_prompt, text_content, chat_id, ASSISTANT_MAIN_MODEL, user_parameters)
        tags = tags_text.split(', ')
        content_dict['transcript_tags'] = tags

    if not tags: return f"Can't find the tags for video_id: {video_id}, neither from content_dict nor from the transcript"

    tag_links = []
    for tag in tags:
        tag_name = tag.lower().replace(' ', '-')
        tag_url = f'https://enspiring.ai/tag/{tag_name}'
        tag_capitalized = tag.title()
        tag_link = f'<a href="{tag_url}">{tag_capitalized}</a>'
        tag_links.append(tag_link)

    tags_html = "<p>" + ', '.join(tag_links) + "</p>"

    id, secret = api_key.split(':')
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})
    mime_type, _ = mimetypes.guess_type(cover_png_file_path)
    if mime_type is None: mime_type = 'image/png'  # Default to PNG if the MIME type can't be determined

    with open(cover_png_file_path, 'rb') as img:
        headers = {
            'Authorization': f'Ghost {token}',
            'Accept-Version': 'v3'
        }
        files = {
            'file': (cover_png_file_path, img, mime_type),  # Attach correct MIME type
            'ref': (None, cover_png_file_path)  # 'ref' is optional based on the API
        }
        image_response = requests.post(f'{api_url}/ghost/api/admin/images/upload/', headers=headers, files=files)

    if image_response.status_code == 201: image_url = image_response.json()['images'][0]['url']
    else:
        content_dict.update({'Reason': f"Failed to upload image: {image_response.status_code} {image_response.text}", 'Status': False})
        return content_dict

    def convert_youtube_urls_to_iframes(text):
        youtube_regex = r"(https?://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]+))"
        youtube_embed_template = '<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
        
        def embed_replacement(match):
            video_id = match.group(2)
            return youtube_embed_template.format(video_id=video_id)
        
        return re.sub(youtube_regex, embed_replacement, text)

    def highlight_words_in_list(line, words_list):
        if not words_list: return line
        if line == title: return line
        for word in words_list:
            # Lowercase both the line and the word for matching and then replace it in the original case
            line = re.sub(rf'\b{re.escape(word)}\b', f'<strong>{word}</strong>', line, flags=re.IGNORECASE)
        return line

    def process_line(line: str):
        line = line.strip()
        line_lower = line.lower()
        line = highlight_words_in_list(line, words_list)
        if line_lower == 'main takeaways from the video:' or line_lower == 'key vocabularies and common phrases:': return f"<h2>{line}</h2><p></p>"
        elif line == title: return f"<hr><h1>{line}</h1><p></p>"
        elif line.startswith('>'):
            line = line[1:].strip()
            return f"<blockquote>{line}</blockquote>"
        elif line.startswith('-'):
            line = line[1:].strip()
            return f'<div class="kg-callout-card"><div class="kg-callout-emoji">💡</div><div class="kg-callout-text">{line}</div></div>'
        elif line.startswith('Please remember to turn on the CC button'): return f"<blockquote><span style='font-style: italic; color: grey;'>{line}</span></blockquote>"
        return f"<p>{convert_youtube_urls_to_iframes(line)}</p>"
    
    html_body = ''.join([process_line(line) for line in lines if line.strip()]) + tags_html
    final_title = 'ENSPIRING.ai: ' + title.encode('ascii', 'ignore').decode()

    post_type = content_dict.get('post_type', 'page')
    post_type_key = f"{post_type}s"

    visibility = content_dict.get('visibility', 'paid')
    featured = content_dict.get('featured', False)

    post_data = {
        post_type_key: [{
                        "title": final_title,
                        "slug": video_id,
                        "html": html_body,
                        "tags": tags,
                        "status": "published",  # Set status to 'published'
                        "visibility": visibility,
                        "featured": featured,
                        "authors": [{"id": author_id}],
                        "type": post_type,
                        "feature_image": image_url  # Set the uploaded image as the feature image
                        }]
                    }

    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(f'{api_url}/ghost/api/admin/{post_type_key}/?source=html', headers=headers, json=post_data)
    if response.status_code == 201: 
        print("Blog post published successfully!")
        try: 
            url = response.json()[post_type_key][0]['url']
            post_id = response.json()[post_type_key][0]['id']
            print(f"Post URL: {url}")
            print(f"Post ID: {post_id}")
            content_dict['Status'] = True
            content_dict['Post_ID'] = post_id
            content_dict['URL'] = url
            video_summary = content_dict.get('video_summary', '')
            paragraphed_transcript = content_dict.get('paragraphed_transcript', '') or text_content
            transcript_tags = content_dict.get('transcript_tags', [])
            transcript_tags = ', '.join(transcript_tags)
            words_list = content_dict.get('words_list', [])
            words_list = ', '.join(words_list)
            transcript_id = content_dict.get('transcript_id', '')
            append_to_video_id_and_post_id_and_url_table(chat_id, title, url, video_id, post_id, post_type, visibility, video_summary, paragraphed_transcript, transcript_tags, words_list, transcript_id, engine)
        except Exception as e: content_dict['Reason'] = f"Error in getting URL: \n{e}"
    else: content_dict['Reason'] = f"Failed to publish post: \n{response.status_code} {response.text}"

    posted_json_file_path = os.path.join(current_folder, f'{video_id}_posted.json')
    content_dict['Posted_JSON_File'] = posted_json_file_path
    content_dict['send_to_enspiring_ai'] = True
    content_dict['post_type'] = post_type
    content_dict['visibility'] = visibility
    content_dict['featured'] = featured
    content_dict['author_id'] = author_id

    with open(posted_json_file_path, 'w', encoding='utf-8') as f: json.dump(content_dict, f, indent=4)
    return content_dict


def append_to_video_id_and_post_id_and_url_table(chat_id, title, url, video_id, post_id, post_type, visibility, video_summary, paragraphed_transcript, transcript_tags, words_list, transcript_id, engine=engine):
    query = text("""
        INSERT INTO enspiring_video_and_post_id (chat_id, Official_Title, URL, Video_ID, Post_ID, type, visibility, video_summary, paragraphed_transcript, transcript_tags, words_list, transcript_id)
        VALUES (:chat_id, :title, :url, :video_id, :post_id, :post_type, :visibility, :video_summary, :paragraphed_transcript, :transcript_tags, :words_list, :transcript_id)
        ON DUPLICATE KEY UPDATE
            chat_id = VALUES(chat_id),
            Official_Title = VALUES(Official_Title),
            URL = VALUES(URL),
            Post_ID = VALUES(Post_ID),
            type = VALUES(type),
            visibility = VALUES(visibility),
            video_summary = VALUES(video_summary),
            paragraphed_transcript = VALUES(paragraphed_transcript),
            transcript_tags = VALUES(transcript_tags),
            words_list = VALUES(words_list),
            transcript_id = VALUES(transcript_id);
    """)

    with engine.begin() as conn:
        try: conn.execute(query, {"chat_id": chat_id, "title": title, "url": url, "video_id": video_id, "post_id": post_id, "post_type": post_type, "visibility": visibility, "video_summary": video_summary, "paragraphed_transcript": paragraphed_transcript, "transcript_tags": transcript_tags, "words_list": words_list, "transcript_id": transcript_id})
        except Exception as e: send_debug_to_laogege(f"ERROR: append_to_video_id_and_post_id_and_url_table() e: >>> {e}")

        update_query = text("""UPDATE video_id_check_history SET Status = 'Completed' WHERE Video_ID = :video_id """)
        conn.execute(update_query, {'video_id': video_id})
    
    return 
    

def upload_image_to_ghost(cover_png_file_path: str, api_key: str, api_url: str):
    id, secret = api_key.split(':')
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)
    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})
    mime_type, _ = mimetypes.guess_type(cover_png_file_path)
    if mime_type is None: mime_type = 'image/png'  # Default to PNG if the MIME type can't be determined
    with open(cover_png_file_path, 'rb') as img:
        headers = {
            'Authorization': f'Ghost {token}',
            'Accept-Version': 'v3'
        }
        files = {
            'file': (cover_png_file_path, img, mime_type),  # Attach correct MIME type
            'ref': (None, cover_png_file_path)  # 'ref' is optional based on the API
        }
        image_response = requests.post(f'{api_url}/ghost/api/admin/images/upload/', headers=headers, files=files)
    if image_response.status_code == 201: return image_response.json()['images'][0]['url']
    else: return ''


def set_page_visibility_direclty_in_table(post_id: str, visitiblity: str, engine=engine):
    with engine.begin() as conn: conn.execute(text(f"UPDATE posts SET visibility = '{visitiblity}' WHERE id = :post_id"), {'post_id': post_id})
    return f"Visibility set to {visitiblity} successfully!"


def embed_audio_to_html(audio_url: str, title: str):
    audio_embed_html = f"""
    <div class="kg-card kg-audio-card">
        <img src="" alt="audio-thumbnail" class="kg-audio-thumbnail kg-audio-hide">
        <div class="kg-audio-thumbnail placeholder">
            <svg width="24" height="24" fill="none">
                <path fill-rule="evenodd" clip-rule="evenodd" d="M7.5 15.33a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm-2.25.75a2.25 2.25 0 1 1 4.5 0 2.25 2.25 0 0 1-4.5 0ZM15 13.83a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm-2.25.75a2.25 2.25 0 1 1 4.5 0 2.25 2.25 0 0 1-4.5 0Z"></path>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M14.486 6.81A2.25 2.25 0 0 1 17.25 9v5.579a.75.75 0 0 1-1.5 0v-5.58a.75.75 0 0 0-.932-.727.755.755 0 0 1-.059.013l-4.465.744a.75.75 0 0 0-.544.72v6.33a.75.75 0 0 1-1.5 0v-6.33a2.25 2.25 0 0 1 1.763-2.194l4.473-.746Z"></path>
                <path fill-rule="evenodd" clip-rule="evenodd" d="M3 1.5a.75.75 0 0 0-.75.75v19.5a.75.75 0 0 0 .75.75h18a.75.75 0 0 0 .75-.75V5.133a.75.75 0 0 0-.225-.535l-.002-.002-3-2.883A.75.75 0 0 0 18 1.5H3ZM1.409.659A2.25 2.25 0 0 1 3 0h15a2.25 2.25 0 0 1 1.568.637l.003.002 3 2.883a2.25 2.25 0 0 1 .679 1.61V21.75A2.25 2.25 0 0 1 21 24H3a2.25 2.25 0 0 1-2.25-2.25V2.25c0-.597.237-1.169.659-1.591Z"></path>
            </svg>
        </div>
        <div class="kg-audio-player-container">
            <audio src="{audio_url}" preload="metadata" controls></audio>
            <div class="kg-audio-title">Story Audio for {title}</div>
            <div class="kg-audio-player">
                <button class="kg-audio-play-icon" aria-label="Play audio">
                    <svg viewBox="0 0 24 24"><path d="M23.14 10.608 2.253.164A1.559 1.559 0 0 0 0 1.557v20.887a1.558 1.558 0 0 0 2.253 1.392L23.14 13.393a1.557 1.557 0 0 0 0-2.785Z"></path></svg>
                </button>
                <button class="kg-audio-pause-icon kg-audio-hide" aria-label="Pause audio">
                    <svg viewBox="0 0 24 24"><rect x="3" y="1" width="7" height="22" rx="1.5" ry="1.5"></rect><rect x="14" y="1" width="7" height="22" rx="1.5" ry="1.5"></rect></svg>
                </button>
                <span class="kg-audio-current-time">0:00</span>
                <div class="kg-audio-time">/<span class="kg-audio-duration">--:--</span></div>
                <input type="range" class="kg-audio-seek-slider" max="100" value="0">
                <button class="kg-audio-playback-rate" aria-label="Adjust playback speed">1×</button>
                <button class="kg-audio-unmute-icon" aria-label="Unmute">
                    <svg viewBox="0 0 24 24"><path d="M15.189 2.021a9.728 9.728 0 0 0-7.924 4.85.249.249 0 0 1-.221.133H5.25a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h1.794a.249.249 0 0 1 .221.133 9.73 9.73 0 0 0 7.924 4.85h.06a1 1 0 0 0 1-1V3.02a1 1 0 0 0-1.06-.998Z"></path></svg>
                </button>
                <button class="kg-audio-mute-icon kg-audio-hide" aria-label="Mute">
                    <svg viewBox="0 0 24 24"><path d="M16.177 4.3a.248.248 0 0 0 .073-.176v-1.1a1 1 0 0 0-1.061-1 9.728 9.728 0 0 0-7.924 4.85.249.249 0 0 1-.221.133H5.25a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h.114a.251.251 0 0 0 .177-.073ZM23.707 1.706A1 1 0 0 0 22.293.292l-22 22a1 1 0 0 0 0 1.414l.009.009a1 1 0 0 0 1.405-.009l6.63-6.631A.251.251 0 0 1 8.515 17a.245.245 0 0 1 .177.075 10.081 10.081 0 0 0 6.5 2.92 1 1 0 0 0 1.061-1V9.266a.247.247 0 0 1 .073-.176Z"></path></svg>
                </button>
                <input type="range" class="kg-audio-volume-slider" max="100" value="100">
            </div>
        </div>
    </div>
    """
    return audio_embed_html


def post_words_story_to_ghost(words_list: list, chat_id: str, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    author_id = user_parameters.get('author_id')
    if not author_id: return send_message(chat_id, "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't sent your email address to the bot to /activate your telegram account.", token, message_id)

    starting_time = time.time()

    cartoon_style_default = user_parameters.get('cartoon_style', '')
    cartoon_style = cartoon_style_default if cartoon_style_default else 'Pixar Style'

    ranking = user_parameters.get('ranking') or 0

    date_today = str(datetime.now().date())

    if chat_id not in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID, DANLI_CHAT_ID]:
        df = pd.read_sql(text(f"SELECT title, slug FROM user_stories WHERE chat_id = :chat_id AND date_today = :date_today"), engine, params={'chat_id': chat_id, 'date_today': date_today})
        if not df.empty:
            title = df['title'].values[0]
            url = f"{ghost_url}/{df['slug'].values[0]}"
            return send_message_markdown(chat_id, f"[{title}]({url})\nYou can generate one story per day. Please check the previous story and wait for the next day to generate a new story.", token, message_id)

    post_type, visibility = 'page', 'public'
    words_list_str = ', '.join(words_list)

    sytem_prompt_for_story_generation = SYSTEM_PROMPT_WORDS_CHECKED_TODAY.replace('_cartoon_style_place_holder_', cartoon_style)
    
    generated_story = openai_gpt_chat(sytem_prompt_for_story_generation, words_list_str, chat_id, model, user_parameters)
    if not generated_story: return send_message(chat_id, "Failed to generate story from the words you checked today.", token, message_id)

    # split by 'MIDJOURNEY PROMPT:'
    generated_story_list = generated_story.split('MIDJOURNEY_PROMPT:')
    generated_story = generated_story_list[0].strip().strip('*')
    midjourney_prompt = generated_story_list[-1].strip()
    midjourney_prompt = midjourney_prompt.replace('*', '')

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    # image_id = ''
    # if ranking >= 4:
    #     try: image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    #     except: print("Failed to generate image for the midjourney prompt.")

    tag_links = []
    for tag in words_list:
        tag_name = tag.lower().replace(' ', '-')
        tag_url = f'{ghost_url}/tag/{tag_name}'
        tag_capitalized = tag.title()
        tag_link = f'<a href="{tag_url}">{tag_capitalized}</a>'
        tag_links.append(tag_link)
    tags_html = "<p>" + ', '.join(tag_links) + "</p>"

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }

    lines = generated_story.split('\n')
    title = lines[0].strip()
    if not title:
        print("Failed to get the title from the generated story.")
        return send_message(chat_id, "Failed to get the title from the generated story.", token, message_id)
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()
    
    content_lines = lines[1:]
    content = '\n'.join(content_lines)

    slug = generate_youtube_slug(length=11)

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    midjourney_prompt_html = f"<blockquote>{midjourney_prompt}</blockquote>"

    md = MarkdownIt()
    html_story_content = md.render(content)
    html_content = html_story_content + midjourney_prompt_html + tags_html

    user_story_audio_dir = os.path.join(story_audio, chat_id)

    audio_file_path = generate_story_voice(generated_story, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = 'english')
    if audio_file_path and os.path.isfile(audio_file_path): 
        upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
        if upload_result['Status']: html_content = embed_audio_to_html(upload_result['URL'], title) + html_content
        else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {content[:200]}......")
    else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {content[:200]}......")

    user_name = user_parameters.get('name') or 'User'

    feature_image = ''
    # is_midjourney = ''
    # if image_id: is_midjourney = "The cover image of your story will be updated soon once the image is generated by `Midjourney AI`."
    # else: 
    try: feature_image = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)
    except: send_message(chat_id, "Failed to generate image for the story, maybe you can try out /generate_image_blackforest or /generate_image_midjourney commands.", token)
    
    if not feature_image: feature_image = upload_image_to_ghost(openai_image_generation(midjourney_prompt, chat_id, model="dall-e-3", size = "1792x1024", quality="standard", user_parameters = user_parameters), admin_api_key, ghost_url)
    if not feature_image: feature_image = "https://enspiring.ai/content/images/size/w1000/2024/10/The-limits-of-my-language-mean-the-limits-of-my-world.---Ludwig-Wittgenstein-1600-1.png"

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "tags": words_list,
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "custom_excerpt": f"A generative story based on vocabularies {user_name.title()} checked on {date_today} by {model}.",
        "authors": [{"id": author_id}],
        "feature_image": feature_image
    }

    if post_type in ['page', 'post']: post_data = {post_type_key: [post_content_dict]}
    else: return send_message(chat_id, "Invalid post_type; Please use 'post' or 'page'.", token, message_id)

    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        finishing_time = time.time()
        consumed_seconds = int(finishing_time - starting_time)

        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        url_markdown = f"HERE's YOUR STORY OF TODAY:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`\n\n"
        send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'words_list': [words_list_str],
            'prompt': [generated_story],
            'hash_md5': [slug],
            'date_today': [date_today]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('user_stories', con=engine, if_exists='append', index=False)
        webhook_push_table_name('user_stories', chat_id)

        if not cartoon_style_default: callback_cartoon_style_setup(chat_id, token)
        # if image_id:
        #     with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"STORY OF THE DAY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your story based on the words you checked today. If you intend to keep this post private, do not share the LINK with others.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

# Cover Image Prompt:
{midjourney_prompt}
"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_message(chat_id, f"Failed to create post: {response.status_code} {response.text}", token, message_id)

    return


def create_story_and_post_to_ghost(user_prompt: str, chat_id: str, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    ranking = user_parameters.get('ranking') or 0
    tier = user_parameters.get('tier') or 'Free'
    user_name = user_parameters.get('name') or 'User'

    if not ranking >= 5: return send_message(chat_id, f"Sorry, {user_name}, as a /{tier} member, you are not qualified to generate your own tailored story. Please upgrade to /Diamond or above to enjoy this premium feature.", token)
    
    starting_time = time.time()

    author_id = user_parameters.get('author_id')
    if not author_id: return send_message(chat_id, "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't sent your email address to the bot to /activate your telegram account.", token, message_id)

    cartoon_style_default = user_parameters.get('cartoon_style', '')
    cartoon_style = cartoon_style_default if cartoon_style_default else 'Pixar Style'

    date_today = str(datetime.now().date())

    if chat_id not in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID, DANLI_CHAT_ID]:
        df = pd.read_sql(text(f"SELECT title, slug FROM user_stories_tailored WHERE chat_id = :chat_id AND date_today = :date_today"), engine, params={'chat_id': chat_id, 'date_today': date_today})
        if not df.empty:
            title = df['title'].values[0]
            url = f"{ghost_url}/{df['slug'].values[0]}"
            return send_message_markdown(chat_id, f"[{title}]({url})\nYou can generate one tailored story per day. Please check the previous story and wait for the next day to generate a new story.", token, message_id)

    post_type, visibility = 'page', 'public'

    sytem_prompt_for_story_generation = SYSTEM_PROMPT_USER_TAILORED_STORY.replace('_cartoon_style_place_holder_', cartoon_style)
    generated_story = openai_gpt_chat(sytem_prompt_for_story_generation, user_prompt, chat_id, model, user_parameters)
    if not generated_story: return send_message(chat_id, "Failed to generate story from the words you checked today.", token, message_id)

    # split by 'MIDJOURNEY PROMPT:'
    generated_story_list = generated_story.split('MIDJOURNEY_PROMPT:')
    generated_story = generated_story_list[0].strip().strip('*')
    midjourney_prompt = generated_story_list[-1].strip()
    midjourney_prompt = midjourney_prompt.replace('*', '')

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    slug = generate_youtube_slug(length=11)

    # image_id = ''
    # try: image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    # except: print("Failed to generate image for the midjourney prompt.")
    feature_image = ''
    try: feature_image = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)
    except Exception as e: 
        send_message(chat_id, "Failed to generate image for the story, maybe you can try it manually by clicking the above buttons.", token)
        send_debug_to_laogege(f"ERROR: create_story_and_post_to_ghost() e: >>> {e}")

    if not feature_image: feature_image = "https://enspiring.ai/content/images/size/w1000/2024/10/The-limits-of-my-language-mean-the-limits-of-my-world.---Ludwig-Wittgenstein-1600-1.png"

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }

    lines = generated_story.split('\n')
    title = lines[0].strip()
    if not title: return send_message(chat_id, "Failed to get the title from the generated story.", token, message_id)
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()
    
    content_lines = lines[1:]
    content = '\n'.join(content_lines)

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    midjourney_prompt_html = f"<blockquote>{midjourney_prompt}</blockquote>"
    user_prompt = f"# User prompt for the story: \n\n{user_prompt}"
    user_prompt_html = f'<hr><div class="kg-callout-card"><div class="kg-callout-emoji">💡</div><div class="kg-callout-text">{user_prompt}</div></div>'

    md = MarkdownIt()
    html_story_content = md.render(content)
    html_content = html_story_content + midjourney_prompt_html + user_prompt_html

    user_story_audio_dir = os.path.join(story_audio, chat_id)

    audio_file_path = generate_story_voice(generated_story, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = 'english')
    if audio_file_path and os.path.isfile(audio_file_path): 
        upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
        if upload_result['Status']: html_content = embed_audio_to_html(upload_result['URL'], title) + html_content
        else: send_debug_to_laogege(f"create_story_and_post_to_ghost() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {content[:200]}......")
    else: send_debug_to_laogege(f"create_story_and_post_to_ghost() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {content[:200]}......")

    user_name = user_parameters.get('name') or 'User'

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "custom_excerpt": f"A tailor made generative story based on {user_name.title()}'s prompt by {model}.",
        "authors": [{"id": author_id}],
        "feature_image": feature_image
    }

    if post_type in ['page', 'post']: post_data = {post_type_key: [post_content_dict]}
    else: return send_message(chat_id, "Invalid post_type; Please use 'post' or 'page'.", token, message_id)

    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        finishing_time = time.time()
        consumed_seconds = int(finishing_time - starting_time)

        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        url_markdown = f"HERE's YOUR TAILOR MADE STORY:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`."
        # if image_id: url_markdown += "\n\nThe cover image of your story will be updated soon once the image is generated by `Midjourney AI`."
        send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'user_prompt': [user_prompt],
            'generated_story': [generated_story],
            'hash_md5': [slug],
            'date_today': [date_today]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('user_stories_tailored', con=engine, if_exists='append', index=False)
        webhook_push_table_name('user_stories_tailored', chat_id)

        if not cartoon_style_default: callback_cartoon_style_setup(chat_id, token)

        # if image_id:
        #     with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"TAILOR MADE STORY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your story based on your prompt. If you intend to keep this post private, do not share the LINK with others.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

# Cover Image Prompt:
{midjourney_prompt}

{user_prompt}
"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_message(chat_id, f"Failed to create post: {response.status_code} {response.text}", token, message_id)
    return


def post_journal_to_ghost(prompt: str, chat_id: str, img_url: str = '', admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)
    starting_time = time.time()
    
    author_id = user_parameters.get('author_id')
    if not author_id: return send_message(chat_id, "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't sent your email address to the bot to /activate your telegram account.", token, message_id)

    slug = generate_youtube_slug(length=11)
    
    date_today = str(datetime.now().date())

    if chat_id not in [OWNER_CHAT_ID, LAOGEGE_CHAT_ID, DANLI_CHAT_ID, DOLLARPLUS_CHAT_ID]:
        df = pd.read_sql(text(f"SELECT title, slug FROM user_journals WHERE chat_id = :chat_id AND date_today = :date_today"), engine, params={'chat_id': chat_id, 'date_today': date_today})
        if not df.empty:
            title = df['title'].values[0]
            url = f"{ghost_url}/{df['slug'].values[0]}"
            return send_message_markdown(chat_id, f"[{title}]({url})\nYou can generate one story per day. Please check the previous story and wait for the next day to generate a new story.", token, message_id)

    post_type, visibility = 'page', 'public'

    gpt_prompt = f"User prompt:\n{prompt}"
    try:
        file_path = search_news_bing(prompt, count = 5, market = "en-US", freshness = "Day", output_dir = news_dir, chat_id = chat_id, token = token, engine = engine)
        if file_path and os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as f: 
                news_reference = f.read()
                gpt_prompt += f"\n\nAnd here's today's online search results from the given prompt, ignore the irrelevant contents and take only the relevant contents as a reference for your post generation.\n{news_reference}"
    except Exception as e: send_debug_to_laogege(f"post_journal_to_ghost() >> Error in searching news: \n\n{e}")

    cartoon_style = user_parameters.get('cartoon_style') or 'Pixar Style'
    system_prompt_creator = SYSTEM_PROMPT_GHOST_MARKDOWN_CREATOR.replace('_Language_Placeholder_', 'English').replace('_cartoon_style_place_holder_', cartoon_style)
    system_prompt_creator = system_prompt_creator.replace('_words_length_placeholder_', '1000 ~ 3000')
    generated_journal = openai_gpt_chat(system_prompt_creator, gpt_prompt, chat_id, model, user_parameters)
    length_of_characters = len(generated_journal)
    print(f"Length of characters in the generated journal: {length_of_characters}")

    # split by 'MIDJOURNEY PROMPT:'
    generated_journal_list = generated_journal.split('MIDJOURNEY_PROMPT:')
    generated_journal = generated_journal_list[0].strip().strip('*')
    midjourney_prompt = generated_journal_list[-1].strip()
    midjourney_prompt = midjourney_prompt.replace('*', '')

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    # image_id = ''
    # try: image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    # except: print("Failed to generate image for the midjourney prompt.")

    if img_url:
        if 'enspiring.ai' not in img_url: 
            output_dir = os.path.join(working_dir, chat_id)
            current_timestamp_string = datetime.now().timestamp()
            current_timestamp_string = str(current_timestamp_string).replace('.', '')
            cover_png_file_path = os.path.join(output_dir, f'{current_timestamp_string}.png')

            cover_png_file_path = download_and_convert_image(img_url, cover_png_file_path)
            img_url = upload_image_to_ghost(cover_png_file_path, admin_api_key, ghost_url)
    else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)
    if not img_url: img_url = 'https://enspiring.ai/content/images/size/w1000/2024/10/stephen-covey.png'

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }

    lines = generated_journal.split('\n')
    title = lines[0].strip()
    if not title: return send_message(chat_id, "Failed to get the title from the generated story.", token, message_id)
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()
    
    content = '\n'.join(lines[1:])

    md = MarkdownIt()
    html_content = md.render(content)

    user_story_audio_dir = os.path.join(story_audio, chat_id)

    audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = 'english')
    if audio_file_path and os.path.isfile(audio_file_path): 
        upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
        if upload_result['Status']: html_content = embed_audio_to_html(upload_result['URL'], title) + html_content
        else: send_debug_to_laogege(f"post_journal_to_ghost() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {content[:200]}......")
    else: send_debug_to_laogege(f"post_journal_to_ghost() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {content[:200]}......")

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    midjourney_prompt_html = f"<blockquote>{midjourney_prompt}</blockquote>"
    html_content += midjourney_prompt_html
    
    user_name = user_parameters.get('name') or 'User'

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "custom_excerpt": f"A generative journal based on {user_name.title()}'s prompt on {date_today} by {model}",
        "authors": [{"id": author_id}],
        "feature_image": img_url
    }

    if post_type in ['page', 'post']: post_data = {post_type_key: [post_content_dict]}
    else: return send_message(chat_id, "Invalid post_type; Please use 'post' or 'page'.", token, message_id)

    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        post_id = response.json()[post_type_key][0]['id']
        url = response.json()[post_type_key][0]['url']
        consumed_seconds = int(time.time() - starting_time)
        url_markdown = f"HERE's YOUR JOURNAL OF TODAY:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`."
        # if image_id: url_markdown += "\n\nThe cover image of your journal will be updated soon once the image is generated by `Midjourney AI`."
        send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'prompt': [generated_journal],
            'hash_md5': [slug],
            'date_today': [date_today]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('user_journals', con=engine, if_exists='append', index=False)

        # if image_id:
        #     with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"JOURNAL OF THE DAY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your journal based on the prompt you sent. If you intend to keep this post private, do not share the LINK with others.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_message(chat_id, f"Failed to create post: {response.status_code} {response.text}", token, message_id)


# Create a new function to retrieve all 4 upscaled images for table rows that img_updated = 0 and update the table with the new upscaled URLs
def retrieve_all_upscaled_images_crontab(midjourney_images_dir = midjourney_images_dir, midjourney_token=IMAGEAPI_MIDJOURNEY, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine):
    df = pd.read_sql(text(f"SELECT * FROM image_midjourney WHERE img_updated = 0"), engine)
    if df.empty: return logging.info("No images to retrieve.")
    for _, row in df.iterrows():
        image_id = row['image_id']
        chat_id = row['chat_id']
        working_folder = os.path.join(midjourney_images_dir, chat_id)
        upscaled_filepath = retrieve_all_upscaled_images(image_id, working_folder, midjourney_token)
        if upscaled_filepath and len(upscaled_filepath) >= 1: 
            with engine.begin() as conn: 
                i = 1
                for png_file_path in upscaled_filepath:
                    upscaled_url = upload_image_to_ghost(png_file_path, admin_api_key, ghost_url)
                    if upscaled_url: conn.execute(text(f"UPDATE `image_midjourney` SET `upscaled_url_{str(i)}` = :upscaled_url WHERE `image_id` = :image_id"), {'upscaled_url': upscaled_url, 'image_id': image_id})
                    i += 1
                conn.execute(text(f"UPDATE `image_midjourney` SET `img_updated` = 1 WHERE `image_id` = :image_id"), {'image_id': image_id})
    return logging.info("All images are retrieved and updated successfully.")


def update_story_cover_image_to_ghost_webhook(payload: dict, midjourney_images_dir = midjourney_images_dir, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")):
    print(f"Starting update_story_cover_image_to_ghost_webhook() function.")
    image_id = payload.get('id')
    df = pd.read_sql(text("SELECT title, post_url, post_id, chat_id, post_type FROM image_midjourney WHERE post_updated = 0 AND img_updated = 0 AND image_id = :image_id"), engine, params={'image_id': image_id})
    if df.empty: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Can't find the image_id: {image_id} in the `image_midjourney` table.")

    chat_id = df['chat_id'].values[0]
    post_type = df['post_type'].values[0]
    if not post_type: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Failed to get post_type for chat_id: {chat_id}")

    post_url = df['post_url'].values[0]
    title = df['title'].values[0]

    user_parameters = user_parameters_realtime(chat_id, engine)
    if not user_parameters: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Failed to get user_parameters for chat_id: {chat_id}")

    upscaled_filepath = save_upscaled_images_from_webhook(payload, midjourney_images_dir)

    if post_type in ['user', 'telegram']:
        for png_file_path in upscaled_filepath: send_document_from_file(chat_id, png_file_path, 'Image generated by Midjourney.', token)
        return
    
    post_id = df['post_id'].values[0]
    if not post_id: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Failed to get post_id for /chat_{chat_id}")

    user_admin_api_key = user_parameters.get('ghost_admin_api_key') or admin_api_key
    user_ghost_url = user_parameters.get('ghost_api_url') or ghost_url
    user_name = user_parameters.get('name') or 'User'

    if upscaled_filepath: 
        upscaled_image_list = []
        for png_file_path in upscaled_filepath:
            upscaled_url = upload_image_to_ghost(png_file_path, user_admin_api_key, user_ghost_url)
            if upscaled_url: upscaled_image_list.append(upscaled_url)

        if upscaled_image_list:
            update_query = """UPDATE `image_midjourney` SET `img_updated` = 1, {} WHERE `image_id` = :image_id"""
            
            # Creating parts of the query to dynamically update the columns
            url_columns = []
            params = {'image_id': image_id}
            
            for i, url in enumerate(upscaled_image_list):
                column_name = f'upscaled_url_{i + 1}'
                url_columns.append(f"`{column_name}` = :{column_name}")
                params[column_name] = url

            set_columns = ", ".join(url_columns)
            update_query = update_query.format(set_columns)
            with engine.begin() as conn: conn.execute(text(update_query), params)

            reply_dict = update_story_cover_image_to_ghost(post_id, upscaled_image_list[0], post_type, user_admin_api_key, user_ghost_url)
            if reply_dict['Status'] and image_midjourney_posted_updated(post_id, engine): 
                url_markdown = f"The cover image for your article is updated. \n[{title}]({post_url})"
                if post_type == 'page' and user_ghost_url != ghost_url and user_admin_api_key != admin_api_key: 
                    edit_url = f"{user_ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
                    edit_url_markdown = f"[HERE]({edit_url})"
                    url_markdown = f"{url_markdown}\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."
                    callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)
                else: callback_tweet_post(chat_id, url_markdown, post_id, token, user_parameters, is_markdown=True, is_creator = False)
            else: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Failed to update the cover image for user {user_name} / {chat_id} / image_id: {image_id}.\n\n{reply_dict['Message']}")
    else: return send_debug_to_laogege(f"update_story_cover_image_to_ghost_webhook() >> Failed to retrieve the upscaled images for user {user_name} / {chat_id} / image_id: {image_id}.")


def update_story_cover_image_to_ghost(post_id: str, image_url: str, post_type: str = 'page', api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    post_type_key = f"{post_type}s"

    # Split the key into ID and SECRET
    id, secret = api_key.split(':')

    # Create a JWT (expires in 5 minutes)
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)

    payload = {
        'iat': iat.timestamp(),
        'exp': exp.timestamp(),
        'aud': '/admin/'
    }

    # Create the JWT token
    token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    # Fetch the existing post data to get the `updated_at` field
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    get_post_response = requests.get(f'{api_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers)

    if get_post_response.status_code != 200: return {'Status': False, 'Message': f"Failed to retrieve post data: \n{get_post_response.status_code} {get_post_response.text}"}

    post_data = get_post_response.json()
    updated_at = post_data[post_type_key][0]['updated_at']  # Retrieve the updated_at field

    # Prepare the post data with the `updated_at` field and the new feature image
    post_data = {
        post_type_key: [{
            "feature_image": image_url,  # Set the provided image URL as the feature image
            "updated_at": updated_at  # Include the original updated_at field
        }]
    }

    # Send the PUT request to update the blog post's feature image
    headers = {
        'Authorization': f'Ghost {token}',
        'Content-Type': 'application/json'
    }

    response = requests.put(f'{api_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers, json=post_data)

    # Check the response status
    if response.status_code == 200: return {'Status': True, 'Message': response.json()[post_type_key][0]['url']}
    else: return {'Status': False, 'Message': f"Failed to update post feature image: \n{response.status_code} {response.text}"}


def first_cover_image_blackforest(image_prompt, output_file, api_key=GHOST_ADMIN_API_KEY, api_url=GHOST_API_URL):
    output_file = generate_image_replicate(image_prompt, output_file)
    return upload_image_to_ghost(output_file, api_key, api_url)


def retrieved_lastest_cover_image_by_id(image_id, url, midjourney_images_dir = midjourney_images_dir, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine):
    image_filepath = retrieve_image_midjourney_webhook(image_id, url, midjourney_images_dir)
    grid_image_url = upload_image_to_ghost(image_filepath, admin_api_key, ghost_url)
    with engine.begin() as conn: conn.execute(text(f"UPDATE `image_midjourney` SET `grid_image_url` = :grid_image_url WHERE `image_id` = :image_id"), {'grid_image_url': grid_image_url, 'image_id': image_id})
    return grid_image_url


def update_story_cover_image_to_ghost_crontab(midjourney_images_dir = midjourney_images_dir, midjourney_token=IMAGEAPI_MIDJOURNEY, token=TELEGRAM_BOT_TOKEN, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL):
    retrieve_all_upscaled_images_crontab(midjourney_images_dir, midjourney_token, admin_api_key, ghost_url, engine)
    df = pd.read_sql(text("SELECT * FROM image_midjourney WHERE post_updated = 0 AND img_updated = 1"), engine)
    if df.empty: return logging.info("No images to update.")
    for _, row in df.iterrows():
        post_id = row['post_id']
        chat_id = row['chat_id']
        upscaled_url_1 = row['upscaled_url_1']
        reply_dict = update_story_cover_image_to_ghost(post_id, upscaled_url_1, 'page', admin_api_key, ghost_url)
        if reply_dict['Status'] and image_midjourney_posted_updated(post_id, engine): return send_message(chat_id, f" for your story is updated.\n{reply_dict['Message']}", token)
        else: logging.error(reply_dict['Message'])
    return logging.info("All stories are updated successfully.")


def create_ghost_headers(admin_api_key: str = BLOG_POST_ADMIN_API_KEY):
    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }
    return headers


def post_news_to_ghost(prompt: str, chat_id: str, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    starting_time = time.time()
    response_dict = {'status': False, 'message': 'Failed to post news to Ghost.'}

    author_id = user_parameters.get('author_id')
    if not author_id: 
        response_dict['message'] = "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't sent your email address to the bot to /activate your telegram account."
        return response_dict
    
    ranking = user_parameters.get('ranking') or 0
    tier = user_parameters.get('tier') or 'Free'
    if not ranking >= 5: 
        response_dict['message'] = f"Sorry, as a /{tier} member, you are not qualified to generate your own tailored news. Please upgrade to /Diamond or above to enjoy this premium feature."
        return response_dict
    
    date_today = str(datetime.now().date())
    prompt = f"{prompt} on {date_today}"

    post_type, visibility = 'page', 'public'

    # Generate news content using the provided function
    generated_news = search_keywords_and_summarize_by_gpt(prompt, chat_id, model, user_parameters, token)
    if not generated_news: 
        response_dict['message'] = "Failed to generate news based on the prompt provided."
        return response_dict

    # split by 'MIDJOURNEY PROMPT:'
    generated_news_list = generated_news.split('MIDJOURNEY_PROMPT:')
    generated_news = generated_news_list[0].strip().strip()
    midjourney_prompt = generated_news_list[-1].strip()
    midjourney_prompt = midjourney_prompt.replace('*', '')

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    # Extract title from generated content
    lines = generated_news.split('\n')
    title = lines[0].strip()
    if not title: 
        response_dict['message'] = "Failed to get the title from the generated news."
        return response_dict
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()

    content_lines = lines[1:]
    content = '\n'.join(content_lines)

    slug = generate_youtube_slug(length=11)

    # Generate feature image using OpenAI image generation
    feature_image = ''
    output_file = os.path.join(midjourney_images_dir, chat_id, f"{slug}.png")
    try: feature_image = first_cover_image_blackforest(midjourney_prompt, output_file, admin_api_key, ghost_url)
    except: send_message(chat_id, f"Failed to generate image for you, may be you can try /generate_image_blackforest or /generate_midjourney_image command to generate the image.", token)

    if not feature_image: feature_image = "https://enspiring.ai/content/images/size/w1000/2024/10/news_background.png"

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }

    # Convert the content to HTML
    md = MarkdownIt()
    html_story_content = md.render(content)
    html_content = html_story_content

    user_story_audio_dir = os.path.join(story_audio, chat_id)

    voice_gender = user_parameters.get('audio_play_default') or 'nova'
    voince_gender = AZURE_VOICE_FEMALE if voice_gender == 'nova' else AZURE_VOICE_MALE

    audio_file_path = azure_text_to_speech(generated_news, user_story_audio_dir, service_region = "westus", speech_key = AZURE_VOICE_API_KEY_1, voice_name = voince_gender, engine = engine, token = token, user_parameters = user_parameters)
    if audio_file_path and os.path.isfile(audio_file_path): 
        upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
        if upload_result['Status']: html_content = embed_audio_to_html(upload_result['URL'], title) + html_content

    user_name = user_parameters.get('name') or 'User'

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "authors": [{"id": author_id}],
        "feature_image": feature_image
    }

    if post_type in ['page', 'post']: post_data = {post_type_key: [post_content_dict]}
    else:
        response_dict['message'] = "Invalid post_type; Please use 'post' or 'page'." 
        return response_dict

    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        finishing_time = time.time()
        consumed_seconds = int(finishing_time - starting_time)

        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        url_markdown = f"HERE'S YOUR NEWS OF TODAY:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds."
        send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        response_dict['status'] = True
        response_dict['message'] = f"{title} {url}"
        response_dict['title_url'] = f"{title} {url}"

        # Save data to user_news table
        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'post_id': [post_id],
            'slug': [returned_slug],
            'user_prompt': [prompt],
            'generated_news': [generated_news],
            'hash_md5': [slug],
            'date_today': [date_today]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('user_news', con=engine, if_exists='append', index=False)

        email_subject = f"NEWS OF THE DAY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,\n\nHere's your news article based on the prompt '{prompt}'. If you intend to keep this post private, do not share the LINK with others.\n\n# [{title}]({url})\n\nIf you can't open the link above, please copy and paste below url into your browser:\n{url}"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: response_dict['message'] = f"Failed to create post: {response.status_code} {response.text}"
    return response_dict


def post_journal_to_ghost_creator(prompt: str, chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_MAIN_MODEL, message_id = '', user_parameters = {}, is_journal = True):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token, message_id)

    post_language = user_parameters.get('default_post_language') or 'English'
    post_type = user_parameters.get('default_post_type') or 'page'
    visibility = user_parameters.get('default_post_visibility') or 'public'
    audio_switch = user_parameters.get('default_audio_switch') or 'off'
    publish_status = user_parameters.get('default_publish_status') or 'published'
    cartoon_style = user_parameters.get('cartoon_style') or 'Pixar Style'
    default_image_model = user_parameters.get('default_image_model') or 'Blackforest'
    user_name = user_parameters.get('name') or 'User'

    starting_time = time.time()
    date_today = str(datetime.now().date())

    my_writing_style = user_parameters.get('writing_style_sample') if user_parameters.get('writing_style_sample') else MY_WRITING_STYLE_AND_FORMATTING_STYLE_DEFAULT
    system_prompt_creator = SYSTEM_PROMPT_CONTENT_CREATOR_STRUCTURED_OUTPUT.replace('_Language_Placeholder_', post_language).replace('_cartoon_style_place_holder_', cartoon_style).replace('_my_writing_style_placeholder_', my_writing_style)
    system_prompt_creator = system_prompt_creator.replace('_words_length_placeholder_', '3000 ~ 6000') if is_journal else system_prompt_creator.replace('_words_length_placeholder_', '1000 ~ 3000')

    event_dict = openai_gpt_structured_output(prompt, system_prompt_creator, chat_id, model, engine, user_parameters)
    if not event_dict: return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    title = event_dict.get('title', '')
    custom_excerpt = event_dict.get('excerpt', '') or ''
    generated_journal = event_dict.get('article', '')
    midjourney_prompt = event_dict.get('midjourney_prompt', '')

    if not all([title, generated_journal, midjourney_prompt]): return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    if title in generated_journal: generated_journal = '\n'.join(generated_journal.split('\n')[1:]).strip()
    if midjourney_prompt in generated_journal: generated_journal = generated_journal.replace(midjourney_prompt, '').strip()

    title = title.replace('#', '').replace('*', '').strip()
    midjourney_prompt = midjourney_prompt.replace('*', '').replace('#', '').strip()

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', default_image_model, suffix = f'The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    slug = generate_youtube_slug(length=11)

    image_id, img_url = '', ''
    if default_image_model == 'Midjourney': 
        if '--ar' not in midjourney_prompt: midjourney_prompt += ' --ar 16:9'
        image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    md = MarkdownIt()
    html_content = md.render(generated_journal)

    audio_url = ''
    if audio_switch == 'on':
        user_story_audio_dir = os.path.join(story_audio, chat_id)
        audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
        if audio_file_path and os.path.isfile(audio_file_path): 
            upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
            if upload_result['Status']: 
                audio_url = upload_result['URL']
                html_content = embed_audio_to_html(audio_url, title) + html_content
            else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")
        else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

    if not custom_excerpt: custom_excerpt = f"Generated on {date_today} by {model}"

    tags = ['Journal'] if is_journal else ['Story']
    tags_from_article = event_dict.get('tags', '')
    if tags_from_article: 
        tags += tags_from_article.split(',')
        tags = [tag.strip() for tag in tags]
        tags = list(set(tags))

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "tags": tags,
        "html": html_content,
        "status": publish_status,
        "custom_excerpt": custom_excerpt,
        "visibility": visibility,
        "type": post_type
    }

    if img_url: post_content_dict['feature_image'] = img_url

    post_data = {post_type_key: [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        consumed_seconds = int(time.time() - starting_time)
        journal_or_story = 'journal' if is_journal else 'story'

        url_markdown = f"HERE's YOUR {journal_or_story.upper()}:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by {model}"

        if img_url:
            edit_url = f"{ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
            edit_url_markdown = f"[HERE]({edit_url})"
            url_markdown += f"\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."

            if post_type == 'page': callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)

        elif image_id: 
            url_markdown += "\n\nThe cover image of your journal will be updated soon once the image is generated by Midjourney AI."
            send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'post_id': [post_id],
            'image_id': [image_id],
            'post_url': [url],
            'tags': [', '.join(tags)],
            'feature_image': [img_url],
            'audio_url': [audio_url],
            'user_prompt': [prompt[:60000]],
            'custom_excerpt': [custom_excerpt[:255]],
            'generated_journal': [generated_journal],
            'midjourney_prompt': [midjourney_prompt],
            'date_today': [date_today],
            'updated_time': [datetime.now()],
            'visibility': [visibility],
            'status': [publish_status],
            'featured': [0]
        }

        df = pd.DataFrame(data_dict)
        df.to_sql('creator_journals', engine, if_exists='append', index=False)

        if img_url and post_type == 'post': callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters, 'creator_journals')

        if image_id:
            with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"JOURNAL: {title}" if is_journal else f"STORY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your {journal_or_story} based on the prompt you sent. As your default setting, the type of this article is `{post_type}`, the visibility is `{visibility}`, cartoon style is `{cartoon_style}`, the audio embeded switch is `{audio_switch}`, the language is `{post_language}` and the image modle is `{default_image_model}`.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

Midjourney prompt generated by AI:
{midjourney_prompt}

Prompt you sent:
{prompt}

AI generated {journal_or_story} in raw text:
{generated_journal}"""
        
        return send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create post: \n{response.status_code} {response.text}")


def post_news_to_ghost_creator(prompt: str, chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_DOCUMENT_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token, message_id)

    post_language = user_parameters.get('default_post_language') or 'English'
    post_type = user_parameters.get('default_post_type') or 'page'
    visibility = user_parameters.get('default_post_visibility') or 'public'
    audio_switch = user_parameters.get('default_audio_switch') or 'off'
    publish_status = user_parameters.get('default_publish_status') or 'published'
    default_image_model = user_parameters.get('default_image_model') or 'Blackforest'
    
    user_name = user_parameters.get('name') or 'User'

    starting_time = time.time()
    date_today = str(datetime.now().date())

    # Generate news content using the provided function
    generated_news = search_keywords_and_summarize_by_gpt(prompt, chat_id, model, user_parameters, token)
    if not generated_news: return send_message(chat_id, f"Failed to generate news based on the prompt provided. Prompt:\n\n{prompt}", token, message_id)

    # split by 'MIDJOURNEY PROMPT:'
    generated_news_list = generated_news.split('MIDJOURNEY_PROMPT:')
    generated_news = generated_news_list[0].strip().strip()
    midjourney_prompt = generated_news_list[-1].strip()
    midjourney_prompt = midjourney_prompt.replace('*', '')

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    slug = generate_youtube_slug(length=11)
    image_id, img_url = '', ''
    if default_image_model == 'Midjourney': 
        if '--ar' not in midjourney_prompt: midjourney_prompt += ' --ar 16:9'
        image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    lines = generated_news.split('\n')
    title = lines[0].strip()
    if not title: return send_debug_to_laogege(f"post_news_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to get the title from the generated story.")
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()
    
    content = '\n'.join(lines[1:])

    md = MarkdownIt()
    html_content = md.render(content)

    audio_url = ''
    if audio_switch == 'on':
        user_story_audio_dir = os.path.join(story_audio, chat_id)
        audio_file_path = generate_story_voice(generated_news, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
        if audio_file_path and os.path.isfile(audio_file_path): 
            upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
            if upload_result['Status']: 
                audio_url = upload_result['URL']
                html_content = embed_audio_to_html(audio_url, title) + html_content
            else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {content[:200]}......")
        else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {content[:200]}......")

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "tags": ['News'],
        "html": html_content,
        "status": publish_status,
        "visibility": visibility,
        "custom_excerpt": f"Generated on {date_today} by {model}",
        "type": post_type
    }
    if img_url: post_content_dict['feature_image'] = img_url

    post_data = {post_type_key: [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))

    if response.status_code in [200, 201]:
        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']

        with engine.begin() as conn: conn.execute(text("UPDATE user_news_jobs SET job_status = :status WHERE user_prompt = :user_prompt AND chat_id = :chat_id"), {'user_prompt': prompt, 'status': 'completed', 'chat_id': chat_id})
        
        consumed_seconds = int(time.time() - starting_time)

        url_markdown =  f"HERE's YOUR NEWS:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`"

        if img_url:
            edit_url = f"{ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
            edit_url_markdown = f"[HERE]({edit_url})"
            url_markdown += f"\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."

            if post_type == 'page': callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)

        elif image_id: 
            url_markdown += "\n\nThe cover image of your news will be updated soon once the image is generated by `Midjourney AI`."
            send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'post_id': [post_id],
            'image_id': [image_id],
            'post_url': [url],
            'tags': ['News'],
            'feature_image': [img_url],
            'audio_url': [audio_url],
            'user_prompt': [prompt],
            'generated_journal': [generated_news],
            'midjourney_prompt': [midjourney_prompt],
            'date_today': [date_today],
            'updated_time': [datetime.now()],
            'visibility': [visibility],
            'status': [publish_status],
            'featured': [0]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('creator_journals', engine, if_exists='append', index=False)

        if img_url and post_type == 'post': callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters, 'creator_journals')

        if image_id:
            with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"NEWS: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your news based on the prompt you sent. As your default setting, the type of this article is `{post_type}`, the visibility is `{visibility}`, the audio embeded switch is `{audio_switch}`, the language is `{post_language}` and the image modle is `{default_image_model}`.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

Midjourney prompt generated by AI:
{midjourney_prompt}

Prompt you sent:
{prompt}

AI generated news in raw text:
{generated_news}"""
        
        return send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_debug_to_laogege(f"post_news_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create news: \n{response.status_code} {response.text}")


# Local ubuntu task
def post_youtube_to_ghost_creator(youtube_url: str, chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_MAIN_MODEL, message_id = '', user_parameters = {}, paragraphed_transcript = '', official_title = ''):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

    post_language = 'English'
    post_type = user_parameters.get('default_post_type') or 'page'
    visibility = user_parameters.get('default_post_visibility') or 'public'
    audio_switch = user_parameters.get('default_audio_switch') or 'off'
    publish_status = user_parameters.get('default_publish_status') or 'published'
    cartoon_style = user_parameters.get('cartoon_style') or 'Pixar Style'
    user_name = user_parameters.get('name') or 'User'
    video_duration_limit = user_parameters.get('video_duration_limit') or 3600
    default_image_model = user_parameters.get('default_image_model') or 'Blackforest'

    starting_time = time.time()
    date_today = str(datetime.now().date())
    # from youtube url get video_id
    video_id = youtube_url.split('=')[-1]

    if not official_title: official_title = 'YouTube Video'
    official_title = f"{official_title[:30]}..."
    send_message_markdown(chat_id, f"Now generating the article based on the youtube link you provided: \n\n[{official_title}]({youtube_url})", token, message_id)

    if not paragraphed_transcript:
        df = pd.read_sql(text("SELECT Official_Title, paragraphed_transcript FROM enspiring_video_and_post_id WHERE Video_ID = :video_id"), engine, params={'video_id': video_id})
        if not df.empty and df['paragraphed_transcript'].values[0]: paragraphed_transcript = df['paragraphed_transcript'].values[0]
        else:
            video_dir = os.path.join(video_dir_creator, chat_id)
            reply_dict = download_youtube_video(youtube_url, video_dir, chat_id, token, engine, user_parameters)
            paragraphed_transcript = reply_dict.get('paragraphed_transcript', '')
            if not paragraphed_transcript:
                official_title = reply_dict.get('Official_Title', '')
                file_url = reply_dict.get('Output_Audio_File')
                if not file_url or not os.path.isfile(file_url): return send_message(chat_id, reply_dict['Reason'], token)

                Duration = reply_dict.get('Duration', 3600)
                if Duration > video_duration_limit: return send_message(chat_id, f"Sorry, the video duration is too long. The maximum duration allowed is {video_duration_limit} seconds.", token)

                response_dict = get_final_paragraphs_from_table(video_id, chat_id, file_url, int(Duration * 0.05), wait_delta=2, api_key=ASSEMBLYAI_API_KEY, webhook_url=ASSEMBLYAI_WEBHOOK_ENDPOINT, parameters_dict=reply_dict)
                if not response_dict.get('paragraphed_transcript'): return send_message_markdown(chat_id, response_dict.get('message'), token)
                paragraphed_transcript = response_dict.get('paragraphed_transcript', '')
    
    if not paragraphed_transcript: return send_message(chat_id, "Failed to get the transcript from the video.", token)

    my_writing_style = user_parameters.get('writing_style_sample') if user_parameters.get('writing_style_sample') else MY_WRITING_STYLE_AND_FORMATTING_STYLE_DEFAULT
    system_prompt_creator = SYSTEM_PROMPT_CONTENT_CREATOR_STRUCTURED_OUTPUT.replace('_Language_Placeholder_', post_language).replace('_cartoon_style_place_holder_', cartoon_style).replace('_my_writing_style_placeholder_', my_writing_style)

    system_prompt_creator = system_prompt_creator.replace('_words_length_placeholder_', '3000 ~ 6000')

    event_dict = openai_gpt_structured_output(paragraphed_transcript, system_prompt_creator, chat_id, model, engine, user_parameters)
    if not event_dict: return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    title = event_dict.get('title', '')
    generated_journal = event_dict.get('article', '')
    midjourney_prompt = event_dict.get('midjourney_prompt', '')

    if not all([title, generated_journal, midjourney_prompt]): return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    if title in generated_journal: generated_journal = '\n'.join(generated_journal.split('\n')[1:]).strip()
    if midjourney_prompt in generated_journal: generated_journal = generated_journal.replace(midjourney_prompt, '').strip()

    title = title.replace('#', '').replace('*', '').strip()
    midjourney_prompt = midjourney_prompt.replace('*', '').replace('#', '').strip()

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    slug = video_id
    image_id, img_url = '', ''
    if default_image_model == 'Midjourney': 
        if '--ar' not in midjourney_prompt: midjourney_prompt += ' --ar 16:9'
        image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    md = MarkdownIt()
    html_content = md.render(generated_journal)

    audio_url = ''
    if audio_switch == 'on':
        user_story_audio_dir = os.path.join(story_audio, chat_id)
        audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
        if audio_file_path and os.path.isfile(audio_file_path): 
            upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
            if upload_result['Status']: 
                audio_url = upload_result['URL']
                html_content = embed_audio_to_html(audio_url, title) + html_content
            else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")
        else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")

    html_content += f'<p><iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe></p>'

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

    custom_excerpt = event_dict.get('excerpt', '') or ''
    if not custom_excerpt: custom_excerpt = f"Generated on {date_today} by {model}"

    tags = 'YouTube, ' + event_dict.get('tags', '')
    tags = tags.split(',')
    tags = [tag.strip() for tag in tags]
    tags = list(set(tags))

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "html": html_content,
        "tags": tags,
        "status": publish_status,
        "visibility": visibility,
        "custom_excerpt": custom_excerpt,
        "type": post_type
    }

    if img_url: post_content_dict['feature_image'] = img_url

    post_data = {post_type_key: [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))

    if response.status_code in [200, 201]:
        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']

        consumed_seconds = int(time.time() - starting_time)
        url_markdown = f"HERE's YOUR YOUTUBE POST:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`"

        if img_url:
            edit_url = f"{ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
            edit_url_markdown = f"[HERE]({edit_url})"
            url_markdown += f"\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."

            if post_type == 'page': callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)

        elif image_id: 
            url_markdown += "\n\nThe cover image of your article will be updated soon once the image is generated by `Midjourney AI`."
            send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [returned_slug],
            'post_id': [post_id],
            'image_id': [image_id],
            'post_url': [url],
            'tags': [', '.join(tags)],
            'feature_image': [img_url],
            'audio_url': [audio_url],
            'user_prompt': [paragraphed_transcript],
            'youtube_url': [youtube_url],
            'generated_journal': [generated_journal],
            'midjourney_prompt': [midjourney_prompt],
            'custom_excerpt': [custom_excerpt[:255]],
            'date_today': [date_today],
            'updated_time': [datetime.now()],
            'visibility': [visibility],
            'status': [publish_status],
            'featured': [0]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('creator_journals', engine, if_exists='append', index=False)

        if img_url and post_type == 'post': callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters, 'creator_journals')

        with engine.begin() as conn: 
            conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url AND chat_id = :chat_id"), {'status': 'completed', 'youtube_url': youtube_url, 'chat_id': chat_id})
            if image_id: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"YOUTUBE: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your article based on the youtube url you sent. As your default setting, the type of this article is `{post_type}`, the visibility is `{visibility}`, the audio embeded switch is `{audio_switch}` and the image modle is `{default_image_model}`.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

Youtube url you sent:
{youtube_url}
"""
        
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

        return "Completed"

    else: 
        if not paragraphed_transcript:
            with engine.begin() as conn: conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url AND chat_id = :chat_id"), {'youtube_url': youtube_url, 'status': 'failed', 'chat_id': chat_id})
        return send_debug_to_laogege(f"post_news_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create news: \n{response.status_code} {response.text}")


def create_stories_list_html_post_to_ghost(chat_id: str, admin_api_key=BLOG_POST_ADMIN_API_KEY, ghost_url=BLOG_POST_API_URL, engine=engine, token=TELEGRAM_BOT_TOKEN, message_id='', user_parameters={}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    post_type, visibility = 'page', 'public'
    user_name = user_parameters.get('name') or 'User'
    user_name = user_name.title()

    author_id = user_parameters.get('author_id')
    if not author_id: return send_message(chat_id, "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't activated your telegram by sending your subscribed email address to me.\n/get_premium", token, message_id)

    # Generate Ghost JWT token
    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    payload = {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/v5/admin/'}
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'alg': 'HS256', 'kid': key_id})

    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    new_slug = generate_youtube_slug(length=11)

    # Get the last update date to set as a threshold
    df_last_post = pd.read_sql(text("""SELECT updated_time FROM user_stories_list WHERE chat_id = :chat_id ORDER BY updated_time DESC LIMIT 1"""), engine, params={'chat_id': chat_id})
    date_threshold = df_last_post['updated_time'].iloc[0].date() if not df_last_post.empty else datetime(2024, 10, 1).date()

    # Fetch stories from all tables after the date threshold
    query = f"""
    SELECT 
        user_stories.title,
        user_stories.slug,
        user_stories.updated_time,
        posts.feature_image AS feature_image,
        posts.custom_excerpt
    FROM 
        user_stories
    LEFT JOIN 
        posts ON user_stories.slug = posts.slug
    LEFT JOIN 
        chat_id_parameters ON user_stories.chat_id = chat_id_parameters.id
    WHERE 
        user_stories.chat_id = :chat_id
        AND user_stories.updated_time > :date_threshold

    UNION ALL

    SELECT 
        user_news.title,
        user_news.slug,
        user_news.updated_time,
        posts.feature_image AS feature_image,
        posts.custom_excerpt
    FROM 
        user_news
    LEFT JOIN 
        posts ON user_news.slug = posts.slug
    LEFT JOIN 
        chat_id_parameters ON user_news.chat_id = chat_id_parameters.id
    WHERE 
        user_news.chat_id = :chat_id
        AND user_news.updated_time > :date_threshold

    UNION ALL

    SELECT 
        user_journals.title,
        user_journals.slug,
        user_journals.updated_time,
        posts.feature_image AS feature_image,
        posts.custom_excerpt
    FROM 
        user_journals
    LEFT JOIN 
        posts ON user_journals.slug = posts.slug
    LEFT JOIN 
        chat_id_parameters ON user_journals.chat_id = chat_id_parameters.id
    WHERE 
        user_journals.chat_id = :chat_id
        AND user_journals.updated_time > :date_threshold

    UNION ALL

    SELECT 
        user_stories_tailored.title,
        user_stories_tailored.slug,
        user_stories_tailored.updated_time,
        posts.feature_image AS feature_image,
        posts.custom_excerpt
    FROM 
        user_stories_tailored
    LEFT JOIN 
        posts ON user_stories_tailored.slug = posts.slug
    LEFT JOIN 
        chat_id_parameters ON user_stories_tailored.chat_id = chat_id_parameters.id
    WHERE 
        user_stories_tailored.chat_id = :chat_id
        AND user_stories_tailored.updated_time > :date_threshold

    ORDER BY 
        updated_time ASC
    LIMIT 30;
    """

    # Execute the query
    df = pd.read_sql(text(query), engine, params={'chat_id': chat_id, 'date_threshold': date_threshold})
    if df.empty or df.shape[0] < 30: return send_message(chat_id, f"Sorry, {user_name}, you can only post a list of stories with exactly 30 stories. Since the last time you posted, you currently have only {df.shape[0]} new stories.", token, message_id)

    earliest_date = df['updated_time'].min()
    latest_date = df['updated_time'].max()

    # Generate HTML bookmarks for each story
    html_bookmarks = []
    for _, row in df.iterrows():
        story_title, slug, feature_image, custom_excerpt = row["title"], row["slug"], row["feature_image"], row.get("custom_excerpt") or f"A generative story based on {user_name}'s prompt."
        story_url = f"{BLOG_BASE_URL}/{slug}"
        
        bookmark_card = f"""
        <figure class="kg-card kg-bookmark-card">
            <a class="kg-bookmark-container" href="{story_url}">
                <div class="kg-bookmark-content">
                    <div class="kg-bookmark-title">{story_title}</div>
                    <div class="kg-bookmark-description">{custom_excerpt}</div>
                    <div class="kg-bookmark-metadata">
                        <span class="kg-bookmark-author">{user_name}</span>
                        <span class="kg-bookmark-publisher">Your Story Archive</span>
                    </div>
                </div>
                <div class="kg-bookmark-thumbnail">
                    <img src="{feature_image}" alt="" onerror="this.style.display = 'none'">
                </div>
            </a>
        </figure>
        """
        html_bookmarks.append(bookmark_card)

    html_content = "\n".join(html_bookmarks)
    feature_image = "https://enspiring.ai/content/images/size/w1200/2024/10/stories_list.png"
    title = f"{user_name.title()}'s Story Archive"

    post_content_dict = {
        "title": title,
        "slug": new_slug,
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "custom_excerpt": f"A list of stories by {user_name.title()} from {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}",
        "authors": [{"id": author_id}],
        "feature_image": feature_image
    }

    post_data = {f"{post_type}s": [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type}s/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        url = response.json()[f"{post_type}s"][0]['url']
        post_id = response.json()[f"{post_type}s"][0]['id']
        url_markdown = f"Here's your stories list from {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}:\n[{title}]({url})\nP.S. You can only post a list of stories with exactly 30 stories."
        send_message_markdown(chat_id, url_markdown, token, message_id)

        returned_slug = url.replace(f'{ghost_url}/', '').rstrip('/')
        data_dict = {
            'chat_id': [chat_id],
            'post_id': [post_id],
            'post_type': [post_type],
            'slug': [returned_slug],
            'html': [html_content],
            'updated_time': [latest_date],
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('user_stories_list', con=engine, if_exists='append', index=False)

        email_subject = f"TAILOR MADE STORY: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your stories archive from {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}:

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)
    else: return send_message(chat_id, f"Failed to create post: {response.status_code} {response.text}", token, message_id)
    return


# from creator_journals read out generated_journal where post_id = given post_id, repost to ghost as a new post with post_type = 'post', use same image
def repost_journal_to_ghost_creator(chat_id: str, post_id: int, engine = engine, token = TELEGRAM_BOT_TOKEN, model = ASSISTANT_MAIN_MODEL, user_parameters = {}, need_translate = False):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)
    df = pd.read_sql(text("SELECT * FROM creator_journals WHERE chat_id = :chat_id AND post_id = :post_id"), engine, params={'chat_id': chat_id, 'post_id': post_id})
    if df.empty: return send_debug_to_laogege(f"repost_journal_to_ghost() chat_id {chat_id} >> Failed to find the journal with post_id: {post_id}")

    title = df['title'].values[0]
    url = df['post_url'].values[0]
    tags = df['tags'].values[0]
    image_id = df['image_id'].values[0]
    image_url = df['feature_image'].values[0]
    custom_excerpt = df['custom_excerpt'].values[0]
    generated_journal = df['generated_journal'].values[0]
    midjourney_prompt = df['midjourney_prompt'].values[0]

    admin_api_key = user_parameters.get('ghost_admin_api_key', '')
    ghost_url = user_parameters.get('ghost_api_url', '')
    if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

    if title in generated_journal: generated_journal = '\n'.join(generated_journal.split('\n')[1:]).strip()
    if midjourney_prompt in generated_journal: generated_journal = generated_journal.replace(midjourney_prompt, '').strip()
    
    translated_journal, prefix = '', ''
    post_language = user_parameters.get('mother_language') or 'English'
    if need_translate and post_language != 'English':
        send_message(chat_id, f"Translating the article into {post_language}...", token)
        system_prompt = SYSTEM_PROMPT_CONTENT_TRANSLATOR_STRUCTURED_OUTPUT.replace('_Language_Placeholder_', post_language)

        content_to_translate = f"TITLE:\n{title} \n\nEXCERPT:\n{custom_excerpt}\n\nARTICLE:\n{generated_journal}"
        event_dict = openai_gpt_structured_output_translate(content_to_translate, system_prompt, chat_id, model, engine, user_parameters)
        if not event_dict: send_debug_to_laogege(f"repost_journal_to_ghost() chat_id {chat_id} >> Failed to translate the journal with post_id: {post_id}")

        title = event_dict.get('title', '') or title
        custom_excerpt = event_dict.get('excerpt', '') or custom_excerpt
        translated_journal = event_dict.get('article', '') or generated_journal
        new_tags = event_dict.get('tags', '')

        generated_journal = translated_journal
        prefix = f'<div style="border-left: 4px solid #ccc; padding-left: 10px; font-style: italic; color: #555; margin-bottom: 20px;">Click <a href="{url}" target="_blank" style="color: #555; text-decoration: underline;">HERE</a> to read the original article in English.</div>'

    post_type = 'post'
    visibility = user_parameters.get('default_post_visibility') or 'public'
    audio_switch = user_parameters.get('default_audio_switch') or 'on'
    publish_status = user_parameters.get('default_publish_status') or 'published'
    user_name = user_parameters.get('name') or 'User'

    date_today = str(datetime.now().date())

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    slug = generate_youtube_slug(length=11)

    md = MarkdownIt()
    html_content = md.render(generated_journal)
    if prefix: html_content = prefix + html_content

    audio_url = ''
    if audio_switch == 'on':
        if not need_translate:
            df = pd.read_sql(text("SELECT audio_url FROM creator_journals WHERE chat_id = :chat_id AND post_id = :post_id"), engine, params={'chat_id': chat_id, 'post_id': post_id})
            if not df.empty: 
                audio_url = df['audio_url'].values[0]
                if audio_url: html_content = embed_audio_to_html(audio_url, title) + html_content
        if not audio_url:
            user_story_audio_dir = os.path.join(story_audio, chat_id)
            audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
            if audio_file_path and os.path.isfile(audio_file_path): 
                upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
                if upload_result['Status']: html_content = embed_audio_to_html(upload_result['URL'], title) + html_content
                else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")
            else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")

    html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

    if not image_url and image_id:
        df_img = pd.read_sql(text("SELECT upscaled_url_1 FROM image_midjourney WHERE image_id = :image_id"), engine, params={'image_id': image_id})
        if not df_img.empty: image_url = df_img['upscaled_url_1'].values[0]

    if not custom_excerpt: custom_excerpt = f"Generated on {date_today} by {model}"

    tags += new_tags
    if tags:
        tags = tags.split(',')
        tags = [tag.strip() for tag in tags]
        tags = list(set(tags))
    else: tags = ['Journal']

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "tags": tags,
        "html": html_content,
        "status": publish_status,
        "custom_excerpt": custom_excerpt,
        "visibility": visibility,
        "type": post_type
    }

    if image_url: post_content_dict['feature_image'] = image_url

    post_data = {post_type_key: [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        
        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'slug': [slug],
            'post_type': [post_type],
            'post_id': [post_id],
            'image_id': [image_id],
            'post_url': [url],
            'tags': [', '.join(tags)],
            'audio_url': [audio_url],
            'custom_excerpt': [custom_excerpt[:255]],
            'feature_image': [image_url],
            'article': [generated_journal],
            'date_today': [date_today],
            'updated_time': [datetime.now()],
            'visibility': [visibility],
            'status': [publish_status],
            'featured': [0]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('creator_journals_repost', engine, if_exists='append', index=False)

        url_markdown = f"HERE's YOUR REPOSTED ARTICLE:\n[{title}]({url})"
        callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters, 'creator_journals_repost')

        title = title.replace('-', ' ')
        email_subject = f"POST: {title}"
        markdown_text = f"""message = f"**Hi {user_name.title()},**\n\nYour latest post has just been published!\n\n# [{title}]({url})\n\nIf you're unable to open the link above, please copy and paste the following URL into your browser:\n{url}\n\n**Article Content (Raw Text):**\n{generated_journal}"""
        return send_notifition_to_email(email_subject, markdown_text, user_parameters)
    else: return send_debug_to_laogege(f"post_news_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create news: \n{response.status_code} {response.text}")


def update_post_details(post_id: str, post_type: str = 'post', status: str = None, visibility: str = None, featured: bool = None, admin_api_key=GHOST_ADMIN_API_KEY, ghost_url=GHOST_API_URL):
    post_type_key = f"{post_type}s"
    
    # Get the `updated_at` timestamp using the `get_post_updated_at` function
    updated_at = get_post_updated_at(post_id, post_type, admin_api_key, ghost_url)
    if "Failed" in updated_at: return {'Status': False, 'Message': updated_at}  # Return the error message if retrieval fails
    
    # Prepare the post data with only provided fields and the `updated_at` field
    post_content_dict = {"updated_at": updated_at}
    if status is not None: post_content_dict["status"] = status
    if visibility is not None: post_content_dict["visibility"] = visibility
    if featured is not None: post_content_dict["featured"] =  True if featured == 1 else False

    post_data = {post_type_key: [post_content_dict]}

    # Split the key into ID and SECRET
    id, secret = admin_api_key.split(':')
    
    # Create a JWT ghost_token
    iat = datetime.now(tz=timezone.utc)
    exp = iat + timedelta(minutes=5)
    payload = {'iat': iat.timestamp(), 'exp': exp.timestamp(), 'aud': '/admin/'}
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers={'kid': id})

    headers = {'Authorization': f'Ghost {ghost_token}', 'Content-Type': 'application/json'}

    # Send the PUT request to update the post
    response = requests.put(f'{ghost_url}/ghost/api/admin/{post_type_key}/{post_id}/', headers=headers, json=post_data)

    # Check the response status
    if response.status_code == 200: return {'Status': True, 'Message': response.json()[post_type_key][0]['url']}
    else: return {'Status': False, 'Message': f"Failed to update post details: \n{response.status_code} {response.text}"}


def post_journal_to_ghost_creator_front(prompt, chat_id, engine, token, model = ASSISTANT_MAIN_MODEL, message_id = '', user_parameters = {}, is_journal=True):
    suffix = ''
    mother_language = user_parameters.get('mother_language') or 'English'
    if mother_language == 'English': suffix = f"\n\nYour /mother_language is set to default value -- `English`. Meaning you won't have a `Publish to Post in Mother Language` button in your notification once your article is generated. If you want to have a translated version of your generated article, please click /mother_language to set your mother language."
    send_message(chat_id, f"Creating the journal based on your prompt, please wait about 120 seconds...{suffix}", token)
    message_id = str(int(message_id) + 1) if message_id else ''
    return post_journal_to_ghost_creator(prompt, chat_id, engine, token, model, message_id, user_parameters, is_journal)


def post_news_to_ghost_creator_front(user_prompt, chat_id, engine, token, user_parameters):
    mother_language = user_parameters.get('mother_language') or 'English'
    date_today = str(datetime.now().date())
    df = pd.DataFrame({'user_prompt': [user_prompt], 'chat_id': [chat_id], 'job_status': ['pending'], 'job_type': ['news'], 'date': [date_today]})
    df.to_sql('user_news_jobs', engine, if_exists='append', index=False)
    webhook_push_table_name('user_news_jobs', chat_id)
    suffix = ''
    if mother_language == 'English': suffix = f"\n\nYour /mother_language is set to default value -- `English`. Meaning you won't have a `Publish to Post in Mother Language` button in your notification once your article is generated. If you want to have a translated version of your generated article, please click /mother_language to set your mother language."
    return send_message(chat_id, f"Your request to post the news to your own website has been received. It will be processed soon. You will be notified once it's done.{suffix}", token)


def handle_url_input(url: str, chat_id: str = OWNER_CHAT_ID, model = ASSISTANT_MAIN_MODEL_BEST, user_parameters = {}, token = TELEGRAM_BOT_TOKEN):
    ranking = user_parameters.get('ranking') or 0
    if ranking < 5: return send_message(chat_id, "Sorry, you don't have permission to use this `url to post` feature. \n/get_premium", token)

    if 'weixin.qq.com' in url: return send_message(chat_id, "Sorry, I can't handle WeChat URLs at the moment.", token)

    content = scrape_content(url)
    if not content: return send_message(chat_id, f"Failed to scrape content from the url {url}", token)

    user_folder = os.path.join(working_dir, chat_id)
    current_time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(user_folder, f'web_scraped_content_{current_time_stamp}.txt')
    with open(file_path, 'w', encoding='utf-8') as f: f.write(content)

    send_document_from_file(chat_id, file_path, '', token)
    send_message(chat_id, f"Now the AI Bot is generating the article based on the content scraped from the webpage. Please wait...\n\nThe quality of the generated article is highly dependent on the quality of the content scraped from the webpage.\n\nIf you think the scraped content is incomplete, you can try copy paste the content to a .txt file and send it to me, putting `journal` into the caption box.", token)

    prompt = f"Based on the following article scraped from a webpage, write a blog post that conveys my thoughts, analysis, insights, and personal reflections inspired by it. If you want to mention the source of the article, please use [Title]({url}) format.\n\n{content}"
    return post_journal_to_ghost_creator(prompt, chat_id, engine, token, model, '', user_parameters, is_journal = True)


def handle_new_posts(entry_link, chat_id=OWNER_CHAT_ID, model=ASSISTANT_MAIN_MODEL_BEST, user_parameters={}, token = TELEGRAM_BOT_TOKEN, feed_title = '', entry_title = ''):
    content = scrape_content(entry_link)
    if not content: return send_debug_to_laogege(f"handle_new_posts() >> Failed to scrape content from the entry_link {entry_link}")

    prompt = f"Based on the following article, write a blog post that conveys my thoughts, analysis, insights, and personal reflections inspired by it. If possible, introduce the author naturally in suitable places throughout the text, and offer praise for his/her accomplishments and contributions where appropriate. At the beginning of the post, add a quotation start with > as marddown blockquote to indicate the source of the article. '> Click [HERE]({entry_link}) to read the original article.'"

    # rephrased_content = openai_gpt_chat(SYSTEM_PROMPT_POLISH_WEB_CONTENT, content, chat_id, model, user_parameters, token)
    if feed_title: prompt += f"{feed_title}'s latest article "
    if entry_title: prompt += f"[{entry_title}]({entry_link})"

    prompt += f"\n\n{content}"
    
    return post_journal_to_ghost_creator(prompt, chat_id, engine, token, model, '', user_parameters, is_journal = True)


# Update an rss_feed in the database
def update_feeds_and_handle_new_posts(chat_id = OWNER_CHAT_ID, model = ASSISTANT_MAIN_MODEL, user_parameters = {}, token = TELEGRAM_BOT_TOKEN):
    # Read RSS URLs from the database
    df = pd.read_sql('SELECT feed_title, feed_link, last_update_time FROM rss_feeds', con=engine)
    if df.empty: return 

    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    for _, row in df.iterrows():
        feed_link = row['feed_link']
        feed_title = row['feed_title'] if row['feed_title'] and row['feed_title'] != 'none' else ''
        last_update_time = row['last_update_time']
        
        # Parse the RSS feed
        feed = feedparser.parse(feed_link)
        max_published_time = last_update_time
        
        # Iterate through the feed entries (i.e., articles)
        for entry in feed.entries:
            entry_published = datetime.strptime(entry.published, '%Y-%m-%dT%H:%M:%SZ') if 'published' in entry else None
            if entry_published and entry_published > last_update_time:
                if entry_published > max_published_time: max_published_time = entry_published

                if entry.link: 
                    try: handle_new_posts(entry.link, chat_id, model, user_parameters, token, feed_title, entry.title)
                    except Exception as e: send_debug_to_laogege(f"update_feeds_and_handle_new_posts() >> Failed to handle new entry_link {entry.link}, code: {e}")
        
        # Update the last update time in the database
        with engine.begin() as conn: conn.execute(text("""UPDATE rss_feeds SET last_update_time = :max_published_time WHERE feed_link = :feed_link"""), {'max_published_time': max_published_time, 'feed_link': feed_link})


def proof_read_ghost(user_prompt: str, chat_id: str, admin_api_key = BLOG_POST_ADMIN_API_KEY, ghost_url = BLOG_POST_API_URL, engine = engine, token = TELEGRAM_BOT_TOKEN, model = ASSISTANT_MAIN_MODEL, message_id = '', user_parameters = {}):
    if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

    ranking = user_parameters.get('ranking') or 0
    tier = user_parameters.get('tier') or 'Free'
    user_name = user_parameters.get('name') or 'User'

    if not ranking >= 4: return send_message(chat_id, f"Sorry, {user_name}, as a /{tier} member, you are not qualified to use `proof_read` feature. Please upgrade to /Diamond or higher tier to use this feature.", token, message_id)
    
    starting_time = time.time()

    author_id = user_parameters.get('author_id')
    if not author_id: return send_message(chat_id, "Failed to find or create author, maybe you are not an author (paid member) yet, or you haven't sent your email address to the bot to /activate your telegram account.", token, message_id)

    date_today = str(datetime.now().date())

    post_type, visibility = 'page', 'public'

    # model = "claude-3-5-sonnet-20241022"
    # proof_read_result = cloude_basic(user_prompt, SYSTEM_PROMPT_PROOF_READING_GHOST, model = model, api_key = CLOUDE_API_KEY)
    system_prompt = read_prompt_by_name('SYSTEM_PROMPT_PROOF_READING_GHOST', engine)
    proof_read_result = openai_gpt_chat(system_prompt, user_prompt, chat_id, model, user_parameters)
    if not proof_read_result: return send_message(chat_id, "Failed to generate the proof read result.", token, message_id)

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)

    headers = {
        'Authorization': f'Ghost {ghost_token}',
        'Content-Type': 'application/json'
    }

    lines = proof_read_result.split('\n')
    title = lines[0].strip()
    if not title: return send_message(chat_id, "Failed to get the title from the generated story.", token)
    
    title = title.replace('#', '').strip()
    title = title.replace('*', '').strip()
    
    content_lines = lines[1:]
    content = '\n'.join(content_lines)

    md = MarkdownIt()
    html_content = md.render(content)

    user_name = user_parameters.get('name') or 'User'

    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": generate_youtube_slug(length=11),
        "html": html_content,
        "status": "published",
        "visibility": visibility,
        "type": post_type,
        "custom_excerpt": f"This page is only for proof reading review by {user_name.title()}, delete once reviewed.",
        "authors": [{"id": author_id}],
        "feature_image": "https://enspiring.ai/content/images/size/w1200/2024/11/proofreading-1.png"
    }

    if post_type in ['page', 'post']: post_data = {post_type_key: [post_content_dict]}
    else: return send_message(chat_id, "Invalid post_type; Please use 'post' or 'page'.", token, message_id)

    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        finishing_time = time.time()
        consumed_seconds = int(finishing_time - starting_time)

        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        url_markdown = f"PROOF READING REVIEW:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`."

        # send_message_markdown(chat_id, url_markdown, token)
        callback_delete_proof_reading(chat_id, post_id, post_type, url_markdown, token, message_id, is_markdown = True)

        data_dict = {
            'chat_id': [chat_id],
            'title': [title],
            'post_id': [post_id],
            'url': [url],
            'user_prompt': [user_prompt],
            'proof_read_result': [content],
            'date_today': [date_today]
        }
        df = pd.DataFrame(data_dict)
        df.to_sql('proof_read_records', con=engine, if_exists='append', index=False)

        email_subject = f"PROOF READING: {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your proof reading result. If you intend to keep this post private, do not share the LINK with others.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}
"""
        send_notifition_to_email(email_subject, markdown_text, user_parameters)

        proof_read_result = proof_read_result.replace('*', '')
        saving_folder = os.path.join(working_dir, chat_id)
        current_time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(saving_folder, f'Refined_article_{current_time_stamp}.txt')
        with open(file_path, 'w', encoding='utf-8') as f: f.write(proof_read_result)
        send_document_from_file(chat_id, file_path, '', token)

    else: return send_message(chat_id, f"Failed to create proof reading review page: {response.status_code} {response.text}", token, message_id)
    return


def auto_blog_post(chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_MAIN_MODEL_BEST, user_parameters = {}):
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

    titles_list_string = 'TITLES OF ALL PREVIOUS ENTRIES:\n'
    try: df = pd.read_sql(text(f"SELECT title FROM creator_auto_posts WHERE chat_id = :chat_id AND series_name = :series_name ORDER BY updated_time DESC LIMIT 365"), engine, params={'chat_id': chat_id, 'series_name': series_name})
    except: df = pd.DataFrame()
    if not df.empty: titles_list_string += '\n'.join(df['title'].tolist())
    else: titles_list_string += 'There is no previous entries. You are generating the first entry.'

    day_count = df.shape[0] + 1

    # get the latest 3 posts from creator_auto_posts with the same chat_id, series_name
    try: df = pd.read_sql(text(f"SELECT first_response, updated_time FROM creator_auto_posts WHERE chat_id = :chat_id AND series_name = :series_name ORDER BY updated_time DESC LIMIT 3"), engine, params={'chat_id': chat_id, 'series_name': series_name})
    except: df = pd.DataFrame()
    if not df.empty:
        # reorder do ascending order
        df = df.sort_values(by='updated_time', ascending=True)
        first_response = df['first_response'].tolist()
        first_response = '\n\n'.join(first_response)
    else: first_response = ''

    auto_prompt = f"BELOW IS THE TITLES OF ALL PREVIOUS ENTRIES AND THE LATEST 3 ENTRIESn.\n\n{titles_list_string}\n\n{first_response}"

    starting_time = time.time()
    date_today = str(datetime.now().date())

    first_response = openai_gpt_chat(system_prompt_auto_post, auto_prompt, chat_id, model, user_parameters, token)

    my_writing_style = user_parameters.get('writing_style_sample') if user_parameters.get('writing_style_sample') else MY_WRITING_STYLE_AND_FORMATTING_STYLE_DEFAULT
    system_prompt_creator = SYSTEM_PROMPT_AUTO_POST_STRUCTURED_OUTPUT.replace('_Language_Placeholder_', post_language).replace('_cartoon_style_place_holder_', cartoon_style).replace('_my_writing_style_placeholder_', my_writing_style)
    
    event_dict = openai_gpt_structured_output(first_response, system_prompt_creator, chat_id, model, engine, user_parameters)
    if not event_dict: return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    title = event_dict.get('title', '')
    custom_excerpt = event_dict.get('excerpt', '') or ''
    generated_journal = event_dict.get('article', '')
    midjourney_prompt = event_dict.get('midjourney_prompt', '')
    tags = event_dict.get('tags', '')

    if not all([title, generated_journal, midjourney_prompt]): return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

    if title in generated_journal: generated_journal = '\n'.join(generated_journal.split('\n')[1:]).strip()
    if midjourney_prompt in generated_journal: generated_journal = generated_journal.replace(midjourney_prompt, '').strip()

    title = title.replace('#', '').replace('*', '').strip()
    midjourney_prompt = midjourney_prompt.replace('*', '').replace('#', '').strip()

    callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', default_image_model, suffix = f'The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

    if chat_id == DOLLARPLUS_CHAT_ID and series_name == 'The Eternal Drift': 
        if 'day ' not in title.lower() or ':' not in title: title = f"Day {day_count}: {title}"
        slug = f"day_{day_count}"
    else: slug = generate_youtube_slug(length=11)

    image_id, img_url = '', ''
    if default_image_model == 'Midjourney': 
        if '--ar' not in midjourney_prompt: midjourney_prompt += ' --ar 16:9'
        image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
    else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)

    key_id, secret = admin_api_key.split(':')
    iat = int(time.time())
    header = {'alg': 'HS256', 'kid': key_id}
    payload = {
        'iat': iat,
        'exp': iat + 5 * 60,  # Token expires in 5 minutes
        'aud': '/v5/admin/'
    }
    ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
    headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

    md = MarkdownIt()
    html_content = md.render(generated_journal)

    audio_url = ''

    user_story_audio_dir = os.path.join(story_audio, chat_id)
    audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
    if audio_file_path and os.path.isfile(audio_file_path): 
        upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
        if upload_result['Status']: 
            audio_url = upload_result['URL']
            html_content = embed_audio_to_html(audio_url, title) + html_content
        else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")
    else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")

    midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
    html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

    if not custom_excerpt: custom_excerpt = f"Generated on {date_today} by {model}"

    if tags:
        tags = tags.split(',')
        tags = [tag.strip() for tag in tags]
        tags = [tag for tag in tags if tag]
        tags = list(set(tags))
    else: tags = ['Journal']


    post_type_key = f"{post_type}s"
    post_content_dict = {
        "title": title,
        "slug": slug,
        "tags": tags,
        "html": html_content,
        "status": publish_status,
        "custom_excerpt": custom_excerpt,
        "visibility": visibility,
        "featured": True,
        "type": post_type
    }

    if img_url: post_content_dict['feature_image'] = img_url

    post_data = {post_type_key: [post_content_dict]}
    api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

    response = requests.post(api_url, headers=headers, data=json.dumps(post_data))
    if response.status_code in [200, 201]:
        url = response.json()[post_type_key][0]['url']
        post_id = response.json()[post_type_key][0]['id']
        consumed_seconds = int(time.time() - starting_time)
        journal_or_story = 'Auto Post'

        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
            print(f"Ops, the url is not https, I have changed it to {url}")


        url_markdown = f"AUTONOMOUS POST:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by {model}"

        if img_url:
            edit_url = f"{ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
            edit_url_markdown = f"[HERE]({edit_url})"
            url_markdown += f"\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."

            if post_type == 'page': callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)

        elif image_id: 
            url_markdown += "\n\nThe cover image of your journal will be updated soon once the image is generated by Midjourney AI."
            send_message_markdown(chat_id, url_markdown, token)

        returned_slug = url.replace(f'{ghost_url}/', '')
        if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

        data_dict = {
            'chat_id': [chat_id],
            'series_name': [series_name],
            'title': [title],
            'slug': [returned_slug],
            'post_id': [post_id],
            'post_type': [post_type],
            'image_id': [image_id],
            'post_url': [url],
            'tags': [', '.join(tags)],
            'feature_image': [img_url],
            'audio_url': [audio_url],
            'first_response': [first_response],
            'custom_excerpt': [custom_excerpt[:255]],
            'generated_journal': [generated_journal],
            'midjourney_prompt': [midjourney_prompt],
            'system_prompt_auto_post': [system_prompt_auto_post],
            'date_today': [date_today],
            'updated_time': [datetime.now()],
            'visibility': [visibility],
            'status': [publish_status],
            'featured': [1]

        }

        df = pd.DataFrame(data_dict)
        df.to_sql('creator_auto_posts', engine, if_exists='append', index=False)

        if img_url and post_type == 'post': 
            callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters, 'creator_auto_posts')
            post_to_twitter_by_chat_id(chat_id, custom_excerpt[:180], url, token, user_parameters)

        if image_id:
            with engine.begin() as conn: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

        title = title.replace('-', ' ')
        email_subject = f"{journal_or_story.upper()} {title}"
        markdown_text = f"""**Hi {user_name.title()}**,

Here's your {journal_or_story} based on the system_prompt you set. As your default setting, the type of this article is `{post_type}`, the visibility is `{visibility}`, cartoon style is `{cartoon_style}`, the audio embeded switch is `{audio_switch}`, the language is `{post_language}` and the image modle is `{default_image_model}`.

# [{title}]({url})

If you can't open the link above, please copy and paste below url into your browser:
{url}

Midjourney prompt generated by AI:
{midjourney_prompt}

AI generated {journal_or_story} in raw text:
{generated_journal}"""
        
        return send_notifition_to_email(email_subject, markdown_text, user_parameters)

    else: return send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create post: \n{response.status_code} {response.text}")



if __name__ == "__main__":
    print("Testing GHOST blog post!")
