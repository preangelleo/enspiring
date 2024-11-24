from helping_page import *


chat_id = DOLLARPLUS_CHAT_ID
token = TELEGRAM_BOT_TOKEN
user_parameters = user_parameters_realtime(chat_id, engine)


title = 'Day 12: A Legacy of Art and Creativity: The Imprint of Human Expression'
post_excerpt = 'Art and creativity have shaped human civilization by reflecting and inspiring emotion, thought, and societal evolution.'
article_url = 'https://www.enspiring.org/day_12'
image = '/Users/lgg/Downloads/day_12.png'

r = handle_share_to_twitter_button(chat_id, title, post_excerpt, article_url, image, token)