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


@app.route('/callback/wechat/')
def wechat_callback():
    return jsonify({"status": "success"}), 200



# Future social media callbacks can be added like this:
@app.route('/callback/twitter')
def twitter_callback():
    try:
        code = request.args.get('code')
        chat_id = request.args.get('state')
        
        if not code or not chat_id:
            send_debug_to_laogege(f"Missing code or chat_id in Twitter callback")
            return redirect("https://enspiring.ai/twitter-connect-failed")

        # Retrieve stored code verifier
        code_verifier = get_stored_verifier(chat_id)
        if not code_verifier:
            send_debug_to_laogege(f"No code verifier found for chat_id: {chat_id}")
            return redirect("https://enspiring.ai/twitter-connect-failed")

        # Exchange code for tokens using PKCE
        token_data = exchange_twitter_code_for_token(code, code_verifier)
        if not token_data:
            send_debug_to_laogege(f"Failed to exchange Twitter code for token")
            return redirect("https://enspiring.ai/twitter-connect-failed")
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        token_type = token_data.get('token_type')  # Should be 'bearer'
        expires_in = token_data.get('expires_in', 7200)  # Default 2 hours
        
        if not access_token or token_type != 'bearer':
            send_debug_to_laogege(f"Invalid token response from Twitter")
            return redirect("https://enspiring.ai/twitter-connect-failed")

        # Get user info using Twitter v2 API
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        userinfo_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers=headers,
            params={
                "user.fields": "id,name,username,profile_image_url,verified,description,public_metrics"
            }
        )
        
        if userinfo_response.status_code != 200:
            send_debug_to_laogege(f"Failed to get Twitter userinfo: {userinfo_response.text}")
            return redirect("https://enspiring.ai/twitter-connect-failed")

        user_data = userinfo_response.json().get('data', {})
        public_metrics = user_data.get('public_metrics', {})

        # Store in database
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS twitter_tokens (
                    chat_id VARCHAR(32) PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_type VARCHAR(20),
                    access_token_expires_at TIMESTAMP NOT NULL,
                    refresh_token_expires_at TIMESTAMP,
                    twitter_id VARCHAR(32),
                    username VARCHAR(255),
                    display_name VARCHAR(255),
                    profile_image_url TEXT,
                    verified BOOLEAN,
                    description TEXT,
                    followers_count INT,
                    following_count INT,
                    tweet_count INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """))

            access_token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            # Twitter refresh tokens expire in 180 days
            refresh_token_expires_at = datetime.now() + timedelta(days=180) if refresh_token else None

            connection.execute(text("""
                INSERT INTO twitter_tokens (
                    chat_id, access_token, refresh_token, token_type,
                    access_token_expires_at, refresh_token_expires_at,
                    twitter_id, username, display_name,
                    profile_image_url, verified, description,
                    followers_count, following_count, tweet_count
                ) VALUES (
                    :chat_id, :access_token, :refresh_token, :token_type,
                    :access_token_expires_at, :refresh_token_expires_at,
                    :twitter_id, :username, :display_name,
                    :profile_image_url, :verified, :description,
                    :followers_count, :following_count, :tweet_count
                )
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    refresh_token = VALUES(refresh_token),
                    token_type = VALUES(token_type),
                    access_token_expires_at = VALUES(access_token_expires_at),
                    refresh_token_expires_at = VALUES(refresh_token_expires_at),
                    twitter_id = VALUES(twitter_id),
                    username = VALUES(username),
                    display_name = VALUES(display_name),
                    profile_image_url = VALUES(profile_image_url),
                    verified = VALUES(verified),
                    description = VALUES(description),
                    followers_count = VALUES(followers_count),
                    following_count = VALUES(following_count),
                    tweet_count = VALUES(tweet_count)
            """), {
                "chat_id": chat_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": token_type,
                "access_token_expires_at": access_token_expires_at,
                "refresh_token_expires_at": refresh_token_expires_at,
                "twitter_id": user_data.get('id'),
                "username": user_data.get('username'),
                "display_name": user_data.get('name'),
                "profile_image_url": user_data.get('profile_image_url'),
                "verified": user_data.get('verified', False),
                "description": user_data.get('description'),
                "followers_count": public_metrics.get('followers_count', 0),
                "following_count": public_metrics.get('following_count', 0),
                "tweet_count": public_metrics.get('tweet_count', 0)
            })

        success_message = (
            f"Twitter authentication successful! Welcome @{user_data.get('username')}! "
            "You can now share your blog posts to Twitter. Click `Post to Twitter` again to share your blog post."
        )
        send_message_markdown(chat_id, success_message, token=TELEGRAM_BOT_TOKEN)
        
        return redirect("https://enspiring.ai/twitter-connected")

    except Exception as e:
        send_debug_to_laogege(f"Twitter callback error: {str(e)}")
        return redirect("https://enspiring.ai/twitter-connect-failed")
    

@app.route('/callback/linkedin')
def linkedin_callback():
    try:
        code = request.args.get('code')
        chat_id = request.args.get('state')
        
        if not code or not chat_id:
            send_debug_to_laogege(f"Missing code or chat_id in callback")
            return redirect("https://enspiring.ai/linkedin-connect-failed")

        # Exchange code for tokens
        token_data = exchange_linkedin_code_for_token(code)
        if not token_data: 
            send_debug_to_laogege(f"Failed to exchange LinkedIn code for token")
            return redirect("https://enspiring.ai/linkedin-connect-failed")
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        access_token_expires_in = token_data.get('expires_in', 3600)
        refresh_token_expires_in = token_data.get('refresh_token_expires_in', 31536000)

        if not access_token:
            send_debug_to_laogege(f"Failed to get LinkedIn access token")
            return redirect("https://enspiring.ai/linkedin-connect-failed")

        # Get user info from userinfo endpoint
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        userinfo_response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        if userinfo_response.status_code != 200:
            send_debug_to_laogege(f"Failed to get userinfo: {userinfo_response.text}")
            return redirect("https://enspiring.ai/linkedin-connect-failed")

        userinfo = userinfo_response.json()
        send_debug_to_laogege(f"Got userinfo: {userinfo}")

        # Handle locale dictionary
        locale_info = userinfo.get('locale', {})

        # Store in database
        with engine.begin() as connection:
            # Update schema to split locale into country and language
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS linkedin_tokens (
                    chat_id VARCHAR(32) PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    access_token_expires_at TIMESTAMP NOT NULL,
                    refresh_token_expires_at TIMESTAMP,
                    member_id VARCHAR(32),
                    full_name VARCHAR(255),
                    given_name VARCHAR(255),
                    family_name VARCHAR(255),
                    email VARCHAR(255),
                    email_verified BOOLEAN,
                    profile_picture TEXT,
                    locale_language VARCHAR(10),
                    locale_country VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """))

            access_token_expires_at = datetime.now() + timedelta(seconds=access_token_expires_in)
            refresh_token_expires_at = datetime.now() + timedelta(seconds=refresh_token_expires_in) if refresh_token else None

            upsert_query = text("""
                INSERT INTO linkedin_tokens (
                    chat_id, access_token, refresh_token, 
                    access_token_expires_at, refresh_token_expires_at,
                    member_id, full_name, given_name, family_name,
                    email, email_verified, profile_picture, 
                    locale_language, locale_country
                ) VALUES (
                    :chat_id, :access_token, :refresh_token,
                    :access_token_expires_at, :refresh_token_expires_at,
                    :member_id, :full_name, :given_name, :family_name,
                    :email, :email_verified, :profile_picture,
                    :locale_language, :locale_country
                )
                ON DUPLICATE KEY UPDATE
                    access_token = VALUES(access_token),
                    refresh_token = VALUES(refresh_token),
                    access_token_expires_at = VALUES(access_token_expires_at),
                    refresh_token_expires_at = VALUES(refresh_token_expires_at),
                    member_id = VALUES(member_id),
                    full_name = VALUES(full_name),
                    given_name = VALUES(given_name),
                    family_name = VALUES(family_name),
                    email = VALUES(email),
                    email_verified = VALUES(email_verified),
                    profile_picture = VALUES(profile_picture),
                    locale_language = VALUES(locale_language),
                    locale_country = VALUES(locale_country)
            """)

            connection.execute(upsert_query, {
                "chat_id": chat_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "access_token_expires_at": access_token_expires_at,
                "refresh_token_expires_at": refresh_token_expires_at,
                "member_id": userinfo.get('sub'),
                "full_name": userinfo.get('name'),
                "given_name": userinfo.get('given_name'),
                "family_name": userinfo.get('family_name'),
                "email": userinfo.get('email'),
                "email_verified": userinfo.get('email_verified'),
                "profile_picture": userinfo.get('picture'),
                "locale_language": locale_info.get('language'),
                "locale_country": locale_info.get('country')
            })

        # Send success message with user's name
        success_message = f"LinkedIn authentication successful! Welcome {userinfo.get('name')}! You can now share your blog posts to LinkedIn. Click `Post to Linkedin` again to share your blog post."
        send_message_markdown(chat_id, success_message, token = TELEGRAM_BOT_TOKEN)
        
        return redirect("https://enspiring.ai/linkedin-connected")

    except Exception as e:
        send_debug_to_laogege(f"LinkedIn callback error: {str(e)}")
        return redirect("https://enspiring.ai/linkedin-connect-failed")
    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8686)
