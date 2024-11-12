from helping_page import *
from queue import Queue
from flask import Flask, redirect, jsonify, request

app = Flask(__name__)

# 日志配置，方便调试
logging.basicConfig(level=logging.INFO)
def send_error_message(exception): return send_message_basic(OWNER_CHAT_ID, exception, token = os.getenv("TELEGRAM_BOT_TOKEN_LEOWIN"))


def handle_task(task_to_do, function_name, function_parameters = {}):
    try: print(f"handle_task() >> task_to_do: {task_to_do}, function_name: {function_name}, function_parameters: {function_parameters}")
    except Exception as e: send_error_message(e)


def test_print(data): 
    task_to_do = data.get('task_to_do', 'none')
    function_name= data.get('function_name', 'none')
    function_parameters = data.get('function_parameters', {})
    print(f"test_print() >> task_to_do: {task_to_do}, function_name: {function_name}, function_parameters: {function_parameters}")
    return 


def handle_activation(email_address, activation_code, chat_id):
    with engine.begin() as connection:
        is_whitelist, is_blacklist = 0, 0
        existence_check_result = connection.execute(text("SELECT id, status, name, tier, is_whitelist, is_blacklist FROM chat_id_parameters WHERE chat_id = :chat_id"), {'chat_id': chat_id}).fetchone()
        if existence_check_result:
            user_id, user_status, user_name, user_tier, is_whitelist, is_blacklist = existence_check_result
            if is_blacklist: 
                send_message_basic(chat_id, "You are blacklisted from using the bot", token = TELEGRAM_BOT_TOKEN)
                return False

        query = text(f"""
            SELECT m.id, m.status, m.name, COALESCE(p.name, 'Free') as user_tier
            FROM members m
            LEFT JOIN members_products mp ON m.id = mp.member_id
            LEFT JOIN products p ON mp.product_id = p.id
            WHERE m.email = :email_address""")

        result = connection.execute(query, {'email_address': email_address}).fetchone()
        if result: user_id, user_status, user_name, user_tier = result

        activation_code_base = ACTIVATION_CODE_CREATION_CODE + str(email_address)
        user_activation_code = hashlib.md5(activation_code_base.encode()).hexdigest()
        if user_activation_code != activation_code: 
            send_message_basic(chat_id, "Invalid activation code", token = TELEGRAM_BOT_TOKEN)
            return False

        if is_whitelist: user_tier = 'Diamond'
        if chat_id == OWNER_CHAT_ID: user_tier = 'Owner'

        user_ranking = TIER_RANKING_MAP.get(user_tier, 0)
        
        upsert_query = text("""
            INSERT INTO chat_id_parameters (id, chat_id, email, status, name, tier, ranking, activation_code, activation_status, audio_play_default, text_character_limit, daily_video_limit, video_duration_limit)
            VALUES (:user_id, :chat_id, :email_address, :user_status, :user_name, :user_tier, :user_ranking, :activation_code, :activation_status, :audio_play_default, :text_character_limit, :daily_video_limit, :video_duration_limit)
            ON DUPLICATE KEY UPDATE
            email = VALUES(email), status = VALUES(status), name = VALUES(name), tier = VALUES(tier), ranking = VALUES(ranking), activation_code = VALUES(activation_code), activation_status = VALUES(activation_status), audio_play_default = VALUES(audio_play_default), text_character_limit = VALUES(text_character_limit), daily_video_limit = VALUES(daily_video_limit), video_duration_limit = VALUES(video_duration_limit)""")

        connection.execute(upsert_query, {"user_id": user_id, "chat_id": chat_id, "email_address": email_address, "user_status": user_status, "user_name": user_name, "user_tier": user_tier, "user_ranking": user_ranking, "activation_code": activation_code, "activation_status": 1, "audio_play_default": 'nova', "text_character_limit": RANKING_TO_CHARACTER_LIMITS.get(user_ranking, 0), "daily_video_limit": user_ranking, "video_duration_limit": USER_RANKING_TO_VIDEO_DURATION_LIMIT.get(user_ranking, 0)})

    try: create_or_get_author_in_ghost_for_chat_id(chat_id, engine)
    except: send_error_message(f"Failed to create new author in Ghost for chat_id: {chat_id}")

    email_content = f"""Dear {user_name},\n\nYour telegram account has been successfully activated. You can now start using {ENSPIRING_BOT_URL} bot on Telegram. If you have any questions or need help, please feel free to contact us via this email or on Telegram.\n\nBest regards,\n{ENSPIRING_DOT_AI}"""
    send_email_text(email_address, f"{ENSPIRING_DOT_AI} Activated Successfully!", email_content, GMAIL_ADDRESS, GMAIL_PASSWORD)
    send_message_basic(chat_id, f"Activation successful! Welcome, {user_name}! 🎉 You are now a /{user_tier} user. Your daily video limit is {user_ranking}, and your video duration limit is {USER_RANKING_TO_VIDEO_DURATION_LIMIT.get(user_ranking, 0)} seconds. Don't forget to click /settings to customize your preferences.", token = TELEGRAM_BOT_TOKEN)
    return True


@app.route('/users_parameters', methods=['POST'])
def webhook_users_parameters():
    data = request.get_json()
    if not isinstance(data, dict): return jsonify({"status": "error", "message": "Invalid data format"}), 400

    task_to_do = data.get('task_to_do', '')
    function_name= data.get('function_name', '')
    function_parameters = data.get('function_parameters', {})

    if not all([task_to_do, function_name]): return jsonify({"status": "error", "message": "Missing parameters"}), 400

    task_thread = threading.Thread(target=handle_task, args=(task_to_do, function_name, function_parameters))
    task_thread.start()
    return jsonify({"status": "success"}), 200


@app.route('/activation', methods=['GET'])
def webhook_activation():
    email_address = request.args.get('email_address')
    activation_code = request.args.get('activation_code')
    chat_id = request.args.get('chat_id')
    if chat_id: chat_id = str(chat_id)

    # Check for missing parameters
    if not all([email_address, activation_code, chat_id]): return redirect("https://enspiring.ai/failed")

    # Queue to capture the result
    result_queue = Queue()

    # Start the activation in a new thread, passing the queue
    def activation_task():
        success = handle_activation(email_address, activation_code, chat_id)
        result_queue.put(success)

    task_thread = threading.Thread(target=activation_task)
    task_thread.start()
    task_thread.join()  # Wait for the thread to finish

    # Retrieve the result from the queue
    activation_successful = result_queue.get()

    # Redirect based on the activation result
    if activation_successful: return redirect("https://enspiring.ai/succeed")
    else: return redirect("https://enspiring.ai/failed")


@app.route('/test', methods=['POST'])
def webhook_test():
    data = request.get_json()
    if not isinstance(data, dict): return jsonify({"status": "error", "message": "Invalid data format"}), 400

    task_thread = threading.Thread(target=test_print, args=(data,))
    task_thread.start()
    return jsonify({"status": "success", "message": "An email confirmation or notification has been sent to your email address, please check your email inbox."}), 200



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8686)
