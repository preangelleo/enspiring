from helping_page import *


chat_id = DOLLARPLUS_CHAT_ID

# # auth_url = start_linkedin_auth(chat_id)
# # print(auth_url)
# post_excerpt = """Exploring the resilience of the human spirit amidst adversity and catastrophe, highlighting collective innovations and psychological fortitude."""
# article_url = """https://www.enspiring.org/day_10/"""
# title = """Day 10: The Resilience of Human Spirit: Overcoming Adversity and Catastrophe"""
# image = "/Users/lgg/Downloads/day_10.png"
# share_asset = handle_share_to_linkedin_button(chat_id, title, post_excerpt, article_url, image, token = os.getenv("TELEGRAM_BOT_TOKEN_ENSPIRING"))
# print(share_asset)
# reply = f"Clicke [HERE](https://www.linkedin.com/feed/update/{share_asset}) to view the post on LinkedIn."
# send_message_markdown(chat_id, reply)

image_path = '/root/Youtube_bot/Tg_user_downloaded/Midjourney_images/5106438350/RmXrwKydM9k.png'
base_name = os.path.basename(image_path)
print('base_name:', base_name)
feature_image = "https://leo.enspiring.org/content/images/size/w2000/2024/11/RmXrwKydM9k.png"
base_name = feature_image.split('/')[-1]
# download the image from the feature_image URL
response = requests.get(feature_image)
# Create the file path for each image
image_path = os.path.join(midjourney_images_dir, base_name)
# Save the image to the local folder
with open(image_path, 'wb') as file: file.write(response.content)
