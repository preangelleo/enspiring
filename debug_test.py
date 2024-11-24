from helping_page import *


chat_id = DOLLARPLUS_CHAT_ID

# auth_url = start_linkedin_auth(chat_id)
# print(auth_url)
post_excerpt = """Exploring the resilience of the human spirit amidst adversity and catastrophe, highlighting collective innovations and psychological fortitude."""
article_url = """https://www.enspiring.org/day_10/"""
title = """Day 10: The Resilience of Human Spirit: Overcoming Adversity and Catastrophe"""
image = "/Users/lgg/Downloads/day_10.png"
share_asset = handle_share_to_linkedin_button(chat_id, title, post_excerpt, article_url, image, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"))
print(share_asset)
reply = f"Clicke [HERE](https://www.linkedin.com/feed/update/{share_asset}) to view the post on LinkedIn."
send_message_markdown(chat_id, reply)