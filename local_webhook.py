from youtube_playlist import *

app = Flask(__name__)

# 日志配置，方便调试
logging.basicConfig(level=logging.INFO)

def send_error_message(table_name, exception):
    token = os.getenv("TELEGRAM_BOT_TOKEN_LEOWIN")
    message = f"Webhook ERROR for:\n{table_name}\n\n{exception}"
    return send_message(OWNER_CHAT_ID, message, token)

def send_notification_message(messagg):
    token = os.getenv("TELEGRAM_BOT_TOKEN_LEOWIN")
    return send_message(LAOGEGE_CHAT_ID, messagg, token)


def handle_task(data):
    table_name = data.get('table_name')
    chat_id = data.get('chat_id')

    token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")
    engine = get_engine()

    if table_name == 'user_news_jobs': check_user_news_jobs(chat_id, engine, token)
    elif table_name == 'youtube_transcript_jobs': check_youtube_transcript_jobs(chat_id, engine, token)
    elif table_name == 'Youtube_Task': complete_pending_tasks(chat_id, engine, token)
    elif table_name == 'user_stories': get_user_stories_explained(chat_id, engine, token)
    elif table_name == 'user_stories_tailored': get_user_stories_explained_tailored(chat_id, engine, token)
    # elif table_name == 'image_midjourney': update_story_cover_image_to_ghost_crontab(midjourney_images_dir, IMAGEAPI_MIDJOURNEY, token, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL)


def handle_midjourney_update(payload):
    '''{'event': 'images.items.update', 'payload': {'id': '787bc4d8-b621-493a-86ce-b1417fd4b169', 'prompt': 'Young man named Leo, standing in front of a vibrant startup office, surrounded by technology symbols and books, confident expression, bright colors, inspirational atmosphere, Sketch Cartoon Style --ar 16:9', 'results': '52a5e235-8597-47b7-adab-52e358f06535', 'user_created': 'bb9f0084-18a0-4f22-8e09-6bfdf6b82419', 'date_created': '2024-10-28T18:05:01.602Z', 'status': 'completed', 'progress': None, 'url': 'https://cl.imagineapi.dev/assets/52a5e235-8597-47b7-adab-52e358f06535/52a5e235-8597-47b7-adab-52e358f06535.png', 'error': None, 'upscaled_urls': ['https://cl.imagineapi.dev/assets/03a70d39-f9d8-4458-91d1-af3717d49a67/03a70d39-f9d8-4458-91d1-af3717d49a67.png', 'https://cl.imagineapi.dev/assets/41d1d0a6-a916-4152-bfbc-2fa9ec0f127f/41d1d0a6-a916-4152-bfbc-2fa9ec0f127f.png', 'https://cl.imagineapi.dev/assets/e183a5dd-012d-4799-bcb1-acf47fd3f351/e183a5dd-012d-4799-bcb1-acf47fd3f351.png', 'https://cl.imagineapi.dev/assets/9b160f5c-46c3-45ce-a1c7-b13224dce868/9b160f5c-46c3-45ce-a1c7-b13224dce868.png'], 'ref': None, 'upscaled': ['03a70d39-f9d8-4458-91d1-af3717d49a67', '41d1d0a6-a916-4152-bfbc-2fa9ec0f127f', '9b160f5c-46c3-45ce-a1c7-b13224dce868', 'e183a5dd-012d-4799-bcb1-acf47fd3f351']}}'''
    status = payload.get('status')
    if not status == 'completed': return

    engine = get_engine()
    token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING")

    if payload.get('upscaled_urls'): update_story_cover_image_to_ghost_webhook(payload, midjourney_images_dir, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL, engine, token)
    if payload.get('url'): retrieved_lastest_cover_image_by_id(payload.get('id'), payload.get('url'), midjourney_images_dir, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL, engine)

    return
    

# Not using
def handle_midjourney_create(payload):
    '''{
    'event': 'images.items.create', 
    'payload': 
        {'id': '787bc4d8-b621-493a-86ce-b1417fd4b169', 
        'prompt': 'Young man named Leo, standing in front of a vibrant startup office, surrounded by technology symbols and books, confident expression, bright colors, inspirational atmosphere, Sketch Cartoon Style --ar 16:9', '
        results': None, 
        'user_created': 'bb9f0084-18a0-4f22-8e09-6bfdf6b82419', 
        'date_created': '2024-10-28T18:05:01.602Z', 
        'status': 'pending', 
        'progress': None, 
        'url': None, 
        'error': None, 
        'upscaled_urls': None, 
        'ref': None, 
        'upscaled': []}}
    '''
    status = payload.get('status')
    url = payload.get('url')
    if url and status == 'completed': 
        image_id = payload.get('id')
        engine = get_engine()
        return retrieved_lastest_cover_image_by_id(image_id, url, midjourney_images_dir, BLOG_POST_ADMIN_API_KEY, BLOG_POST_API_URL, engine)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    table_name = data.get('table_name')
    chat_id = data.get('chat_id')
    if not all([table_name, chat_id]): return jsonify({"status": "error", "message": "Invalid request"}), 400

    send_debug_to_laogege(f"INFO webhook() >> Webhook | chat_id: {chat_id} | table_name: {table_name}")
    # 启动新线程处理任务
    task_thread = threading.Thread(target=handle_task, args=(data,))
    task_thread.start()

    return jsonify({"status": "success"}), 200


@app.route('/assemblyai', methods=['POST'])
def webhook_assemblyai():
    data = request.get_json()
    transcript_id = data.get('transcript_id') or 'none'
    status = data.get('status') or 'none'
    if status == 'completed' and transcript_id != 'none': 
        # 启动新线程处理任务
        task_thread = threading.Thread(target=download_transcription, args=(transcript_id,))
        task_thread.start()

    return jsonify({"status": "success"}), 200


@app.route('/midjourney', methods=['POST'])
def webhook_midjourney():
    data = request.get_json()
    event = data.get('event', 'none')
    payload = data.get('payload', {})
    if payload.get('status', 'none') == 'completed':
        if event == 'images.items.update':
            print(f"webhook_midjourney() was just called, event: {event}")
            task_thread = threading.Thread(target=handle_midjourney_update, args=(payload,))
            task_thread.start()
    return jsonify({"status": "success"}), 200


@app.route('/test', methods=['GET'])
def test_webhook():
    """GET 路由，用于在浏览器中测试"""
    table_name = request.args.get('table_name', 'This is a test from web browser, upon receiving this message, the test is successful.')

    logging.info(f"Test endpoint called for table: {table_name}")

    # 启动新线程处理任务
    task_thread = threading.Thread(target=handle_task, args=(table_name,))
    task_thread.start()

    return jsonify({"status": "success", "message": f"Task started for {table_name}"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8686)
