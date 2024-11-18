from youtube_playlist import *


if __name__ == "__main__":
    logging.info("Youtube_playlist_hourly.py >> Starting pending tasks and new videos from playlist...")
    
    try: check_video_id_check_history_for_new_videos(duration = 3600, language_limit = 'en', token = os.getenv("TELEGRAM_BOT_TOKEN_TEST"), engine = engine)
    except Exception as e: print(e)

    try: tweet_id = get_one_post_url_and_tweet(engine, twitter_enspiring)
    except Exception as e: logging.info(e)

    try: tweet_id = get_one_post_url_and_tweet(engine, twitter_preangelleo)
    except Exception as e: logging.info(e)

    if datetime.now().hour == 6: random_word_daily(token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine)

    if datetime.now().hour == 12: daily_quote(token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), engine = engine)

    if datetime.now().hour == 18: words_list_of_today(engine = engine, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"))

    if datetime.now().hour == 0: 
        try: auto_blog_post(DOLLARPLUS_CHAT_ID, engine, os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), ASSISTANT_MAIN_MODEL_BEST, user_parameters_realtime(DOLLARPLUS_CHAT_ID, engine))
        except Exception as e: send_debug_to_laogege(f"auto_blog_post() >> {e}")

        try: get_latest_videos_from_channel(CHANNEL_ID_DICT, 5, engine)
        except Exception as e: send_debug_to_laogege(f"get_latest_videos_from_channel() >> {e}")
