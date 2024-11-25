from ghost_blog import *

dish_list = ['The Canellioni', ' Venetian Kebabs', ' Gabbriello Ravioli', ' Chicken Livers', ' Manicotti Parmigiano', ' Cavatelli Alla Crema']
dishs = ', '.join(dish_list)
prompt = f"A table of Italian dishes: {dishs}"
output_file = os.path.join(midjourney_images_dir, "italian_dishes.jpg")
# r = generate_image_replicate(prompt, output_file, model = "black-forest-labs/flux-pro", width = 1024, height = 720, api_token = REPLICATE_API_TOKEN)
# print(r)

chat_id = OWNER_CHAT_ID
r = openai_image_generation(prompt, chat_id, model="dall-e-3", size = "1792x1024", quality="standard", user_parameters = user_parameters_realtime(chat_id, engine))
print(r)