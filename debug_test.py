from ghost_blog import *

# 假设 engine 已经创建
# engine = create_engine('mysql+mysqlconnector://user:password@localhost/your_database_name')
# def fetch_latest_journals(engine):
#     # 使用 pandas 读取最新的20条记录
#     query = (
#         """
#         SELECT title, post_url, generated_journal 
#         FROM creator_journals 
#         ORDER BY updated_time DESC 
#         LIMIT 20
#         """
#     )
#     df = pd.read_sql(query, engine)

#     # 处理每条记录，生成 txt 文件
#     for _, row in df.iterrows():
#         title, post_url, generated_journal = row['title'], row['post_url'], row['generated_journal']
        
#         # 判断 generated_journal 是否包含特定字符串
#         if "https://www.youtube.com/embed/SEnZ5xOywb0" not in generated_journal:
#             continue

#         # 为了防止非法文件名字符，将 title 进行清理
#         safe_title = "_".join(title.split())[:50]  # 限制最大长度为50个字符，防止文件名过长
#         filename = f"{safe_title}.txt"

#         # 创建文件并写入内容
#         with open(filename, "w", encoding="utf-8") as file:
#             file.write(f"Title: {title}\n")
#             file.write(f"URL: {post_url}\n")
#             file.write(f"Journal:\n\n{generated_journal}\n")

# if __name__ == "__main__":
#     # 假设 engine 已经在其他地方定义
#     fetch_latest_journals(engine)
chat_id = LAOGEGE_CHAT_ID
# user_parameters = user_parameters_realtime(chat_id, engine)
# my_writing_style = user_parameters.get('writing_style_sample')
# print(my_writing_style)

# def post_youtube_to_ghost_creator(youtube_url: str, chat_id: str, engine = engine, token = TELEGRAM_BOT_TOKEN, model=ASSISTANT_MAIN_MODEL, message_id = '', user_parameters = {}, paragraphed_transcript = '', official_title = ''):
#     if not user_parameters: user_parameters = user_parameters_realtime(chat_id, engine)

#     admin_api_key = user_parameters.get('ghost_admin_api_key', '')
#     ghost_url = user_parameters.get('ghost_api_url', '')
#     if not all([admin_api_key, ghost_url]): return send_message(chat_id, NO_BLOG_ADMIN_API_KEY_NOTIFICATION, token)

#     post_language = 'English'
#     post_type = user_parameters.get('default_post_type') or 'page'
#     visibility = user_parameters.get('default_post_visibility') or 'public'
#     audio_switch = user_parameters.get('default_audio_switch') or 'off'
#     publish_status = user_parameters.get('default_publish_status') or 'published'
#     cartoon_style = user_parameters.get('cartoon_style') or 'Pixar Style'
#     user_name = user_parameters.get('name') or 'User'
#     video_duration_limit = user_parameters.get('video_duration_limit') or 3600
#     default_image_model = user_parameters.get('default_image_model') or 'Blackforest'

#     starting_time = time.time()
#     date_today = str(datetime.now().date())
#     # from youtube url get video_id
#     video_id = youtube_url.split('=')[-1]

#     if not official_title: official_title = 'YouTube Video'
#     official_title = f"{official_title[:30]}..."
#     send_message_markdown(chat_id, f"Now generating the article based on the youtube link you provided: \n\n[{official_title}]({youtube_url})", token, message_id)

#     if not paragraphed_transcript:
#         df = pd.read_sql(text("SELECT Official_Title, paragraphed_transcript FROM enspiring_video_and_post_id WHERE Video_ID = :video_id"), engine, params={'video_id': video_id})
#         if not df.empty and df['paragraphed_transcript'].values[0]: paragraphed_transcript = df['paragraphed_transcript'].values[0]
#         else:
#             video_dir = os.path.join(video_dir_creator, chat_id)
#             reply_dict = download_youtube_video(youtube_url, video_dir, chat_id, token, engine, user_parameters)
#             paragraphed_transcript = reply_dict.get('paragraphed_transcript', '')
#             if not paragraphed_transcript:
#                 official_title = reply_dict.get('Official_Title', '')
#                 file_url = reply_dict.get('Output_Audio_File')
#                 if not file_url or not os.path.isfile(file_url): return send_message(chat_id, reply_dict['Reason'], token)

#                 Duration = reply_dict.get('Duration', 3600)
#                 if Duration > video_duration_limit: return send_message(chat_id, f"Sorry, the video duration is too long. The maximum duration allowed is {video_duration_limit} seconds.", token)

#                 response_dict = get_final_paragraphs_from_table(video_id, chat_id, file_url, int(Duration * 0.05), wait_delta=2, api_key=ASSEMBLYAI_API_KEY, webhook_url=ASSEMBLYAI_WEBHOOK_ENDPOINT, parameters_dict=reply_dict)
#                 if not response_dict.get('paragraphed_transcript'): return send_message_markdown(chat_id, response_dict.get('message'), token)
#                 paragraphed_transcript = response_dict.get('paragraphed_transcript', '')
    
#     if not paragraphed_transcript: return send_message(chat_id, "Failed to get the transcript from the video.", token)

#     my_writing_style = user_parameters.get('writing_style_sample') if user_parameters.get('writing_style_sample') else MY_WRITING_STYLE_AND_FORMATTING_STYLE_DEFAULT
#     system_prompt_creator = SYSTEM_PROMPT_CONTENT_CREATOR_STRUCTURED_OUTPUT.replace('_Language_Placeholder_', post_language).replace('_cartoon_style_place_holder_', cartoon_style).replace('_my_writing_style_placeholder_', my_writing_style)

#     system_prompt_creator = system_prompt_creator.replace('_words_length_placeholder_', '3000 ~ 6000')

#     event_dict = openai_gpt_structured_output(paragraphed_transcript, system_prompt_creator, chat_id, model, engine, user_parameters)
#     if not event_dict: return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

#     title = event_dict.get('title', '')
#     generated_journal = event_dict.get('article', '')
#     midjourney_prompt = event_dict.get('midjourney_prompt', '')

#     if not all([title, generated_journal, midjourney_prompt]): return send_debug_to_laogege(f"post_youtube_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate the article based on the youtube link you provided.")

#     title = title.replace('#', '').replace('*', '').strip()
#     midjourney_prompt = midjourney_prompt.replace('*', '').replace('#', '').strip()

#     callback_image_prompt_audio(chat_id, midjourney_prompt, token, engine, user_parameters, '', '', suffix='The is the prompt for your cover image generation, please wait for the image to generated and the article to be published.')

#     slug = video_id
#     image_id, img_url = '', ''
#     if default_image_model == 'Midjourney': 
#         if '--ar' not in midjourney_prompt: midjourney_prompt += ' --ar 16:9'
#         image_id = generate_image_midjourney(chat_id, midjourney_prompt, post_type, IMAGEAPI_MIDJOURNEY)
#     else: img_url = first_cover_image_blackforest(midjourney_prompt, os.path.join(midjourney_images_dir, chat_id, f"{slug}.png"), admin_api_key, ghost_url)

#     key_id, secret = admin_api_key.split(':')
#     iat = int(time.time())
#     header = {'alg': 'HS256', 'kid': key_id}
#     payload = {
#         'iat': iat,
#         'exp': iat + 5 * 60,  # Token expires in 5 minutes
#         'aud': '/v5/admin/'
#     }
#     ghost_token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
#     headers = {'Authorization': f'Ghost {ghost_token}','Content-Type': 'application/json'}

#     md = MarkdownIt()
#     html_content = md.render(generated_journal)

#     audio_url = ''
#     if audio_switch == 'on':
#         user_story_audio_dir = os.path.join(story_audio, chat_id)
#         audio_file_path = generate_story_voice(generated_journal, chat_id, user_story_audio_dir, engine, token, user_parameters, language_name = post_language.lower())
#         if audio_file_path and os.path.isfile(audio_file_path): 
#             upload_result = upload_audio_to_ghost(admin_api_key, ghost_url, audio_file_path)
#             if upload_result['Status']: 
#                 audio_url = upload_result['URL']
#                 html_content = embed_audio_to_html(audio_url, title) + html_content
#             else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to upload audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")
#         else: send_debug_to_laogege(f"post_journal_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to generate audio for the article. Title: {title}\n\nContent: {generated_journal[:200]}......")

#     html_content += f'<p><iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe></p>'

#     midjourney_prompt = f"Midjourney prompt for the cover image: {midjourney_prompt}"
#     html_content += f"<blockquote>{midjourney_prompt}</blockquote>"

#     custom_excerpt = event_dict.get('excerpt', '') or ''
#     if not custom_excerpt: custom_excerpt = f"Generated on {date_today} by {model}"

#     post_type_key = f"{post_type}s"
#     post_content_dict = {
#         "title": title,
#         "slug": slug,
#         "html": html_content,
#         "tags": ['YouTube'],
#         "status": publish_status,
#         "visibility": visibility,
#         "custom_excerpt": custom_excerpt,
#         "type": post_type
#     }

#     if img_url: post_content_dict['feature_image'] = img_url

#     post_data = {post_type_key: [post_content_dict]}
#     api_url = f'{ghost_url}/ghost/api/admin/{post_type_key}/?source=html'

#     response = requests.post(api_url, headers=headers, data=json.dumps(post_data))

#     if response.status_code in [200, 201]:
#         url = response.json()[post_type_key][0]['url']
#         post_id = response.json()[post_type_key][0]['id']

#         consumed_seconds = int(time.time() - starting_time)
#         url_markdown = f"HERE's YOUR YOUTUBE POST:\n[{title}]({url})\nGenerated in {consumed_seconds} seconds by `{model}`"

#         if img_url:
#             edit_url = f"{ghost_url}/ghost/#/editor/{post_type}/{post_id}/"
#             edit_url_markdown = f"[HERE]({edit_url})"
#             url_markdown += f"\n\nIf you are satisfied with everything, please choose one of the following option; if you are not satisfied, please click {edit_url_markdown} to edit the {post_type}."

#             if post_type == 'page': callback_translate_page_to_post(chat_id, url_markdown, post_id, token, user_parameters)
#             else: callback_update_post_status(chat_id, url_markdown, post_id, token, user_parameters)

#         elif image_id: 
#             url_markdown += "\n\nThe cover image of your article will be updated soon once the image is generated by `Midjourney AI`."
#             send_message_markdown(chat_id, url_markdown, token)

#         returned_slug = url.replace(f'{ghost_url}/', '')
#         if returned_slug.endswith('/'): returned_slug = returned_slug[:-1]

#         data_dict = {
#             'chat_id': [chat_id],
#             'title': [title],
#             'slug': [returned_slug],
#             'post_id': [post_id],
#             'image_id': [image_id],
#             'post_url': [url],
#             'tags': ['YouTube'],
#             'feature_image': [img_url],
#             'audio_url': [audio_url],
#             'user_prompt': [paragraphed_transcript],
#             'youtube_url': [youtube_url],
#             'generated_journal': [generated_journal],
#             'midjourney_prompt': [midjourney_prompt],
#             'custom_excerpt': [custom_excerpt[:255]],
#             'date_today': [date_today],
#             'updated_time': [datetime.now()]
#         }
#         df = pd.DataFrame(data_dict)
#         df.to_sql('creator_journals', engine, if_exists='append', index=False)

#         with engine.begin() as conn: 
#             conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url AND chat_id = :chat_id"), {'status': 'completed', 'youtube_url': youtube_url, 'chat_id': chat_id})
#             if image_id: conn.execute(text(f"UPDATE image_midjourney SET post_id = :post_id, title = :title, slug = :slug, post_url = :url WHERE image_id = :image_id"), {'post_id': post_id, 'image_id': image_id, 'title': title, 'slug': returned_slug, 'url': url})

#         title = title.replace('-', ' ')
#         email_subject = f"YOUTUBE: {title}"
#         markdown_text = f"""**Hi {user_name.title()}**,

# Here's your article based on the youtube url you sent. As your default setting, the type of this article is `{post_type}`, the visibility is `{visibility}`, the audio embeded switch is `{audio_switch}` and the image modle is `{default_image_model}`.

# # [{title}]({url})

# If you can't open the link above, please copy and paste below url into your browser:
# {url}

# Youtube url you sent:
# {youtube_url}
# """
        
#         send_notifition_to_email(email_subject, markdown_text, user_parameters)

#         return "Completed"

#     else: 
#         if not paragraphed_transcript:
#             with engine.begin() as conn: conn.execute(text("UPDATE youtube_transcript_jobs SET job_status = :status WHERE youtube_url = :youtube_url AND chat_id = :chat_id"), {'youtube_url': youtube_url, 'status': 'failed', 'chat_id': chat_id})
#         return send_debug_to_laogege(f"post_news_to_ghost_creator() user_name {user_name} (/chat_{chat_id}) >> Failed to create news: \n{response.status_code} {response.text}")
