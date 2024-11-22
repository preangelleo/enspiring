from ghost_blog import *

token = TELEGRAM_BOT_TOKEN
chat_id = DOLLARPLUS_CHAT_ID
model=ASSISTANT_MAIN_MODEL_BEST
# user_parameters = user_parameters_realtime(chat_id, engine)

# r = auto_blog_post(DOLLARPLUS_CHAT_ID, engine, os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"), ASSISTANT_MAIN_MODEL, user_parameters_realtime(DOLLARPLUS_CHAT_ID, engine))
# print(r)
msg_text = 'Yqian.thinkdifferent@gmail.com'
user_name = 'Elena Q. @Q_seetheworld'
chat_id = '5686221456'
user_parameters = user_parameters_realtime(chat_id, engine)
post_journal_to_ghost_creator_front('Aha Curiosity', chat_id, engine, token, ASSISTANT_MAIN_MODEL_BEST, 0, user_parameters, is_journal = True)