from ghost_blog import *

token = TELEGRAM_BOT_TOKEN
chat_id = DOLLARPLUS_CHAT_ID
model=ASSISTANT_MAIN_MODEL_BEST
# user_parameters = user_parameters_realtime(chat_id, engine)

# Adding missing commands to commands_dict

commands_dict = {
    "words_checked": "Get a list of words that you have checked today (By UTC: Coordinated Universal Time).",
    "clone_audio": "Send me /clone_audio Your text here. For example: \n\n/clone_audio Hello everyone! This is my cloned voice, and I must admit, it feels surreal...",
    "clone_audio_trick": "The tricks of cloning voice.",
    "ollama": "Send me /ollama Your text here to chat with Ollama. For example: /ollama Tell me a dirty joke.",
    "revise_text": "Send me /revise_text Your text here. I will revise the text you provide after the command. Or just use natural language to tell me what you want to revise",
    "query_doc": "Send me a document, and ask anything you want to know about the content of the file (PDF or Docx).",
    "twitter_handle": "Please send the Twitter handle exactly in below format:\n\n/twitter_handle >> @enspiring_ai",
    "get_transcript": "Send me /get_transcript your_youtube_url_here. For example: /get_transcript https://www.youtube.com/watch?v=video_id",
    "youtube_url": "Send me a Youtube video URL, I will generate a blog post for you about this youtube video.",
    "today_news": "Get the latest news summary.",
    "post_story": "Send me /post_story Your text here. For example: /post_story A boy found a magic lamp and a genie appeared.",
    "post_news": "Send me /post_news Your prompt (keywords) here. For example: /post_news Latest OpenAI news",
    "post_journal": "Send me /post_journal Your text here. For example: /post_journal I want to write a journal about ebbinghaus forgetting curve.",
    "post_stories_list": "Get a list of stories you generated previously and published online",
    "generate_audio": "Send me /generate_audio Your text here. For example: /generate_audio Hello, how are you?",
    "generate_audio_male": "Send me /generate_audio_male Your text here. For example: /generate_audio_male Hello, how are you?",
    "generate_audio_female": "Send me /generate_audio_female  Your text here. For example: /generate_audio_female Hello, how are you?",
    "generate_prompt_midjourney": "Send me /generate_prompt_midjourney Your thoughts here. For example: /generate_prompt_midjourney a cover image for a blog post about the future of AI.",
    "generate_image_dalle": "Send me /generate_image_dalle Your thoughts here. For example: /generate_image_dalle a cover image for a blog post about the future of AI.",
    "generate_image_blackforest": "Send me /generate_image_blackforest Your thoughts here. For example: /generate_image_blackforest a cover image for a blog post about the future of AI.",
    "generate_image_midjourney": "Send me /generate_midjourney_image Your prompt here. For example: /generate_midjourney_image a dog walking around a futuristic alien city.",
    "email_assistant": "Send me /email_assistant Prompt and Your email content here. For example: /email_assistant Summarize my email : Hello Leo, I'm sending this email to you because...",
    "my_writing_style": "Send me the .txt file named my_writing_style.txt to personalize your own writing style. P.S. The content should be less than 10,000 characters.",
    "proof_of_reading": "Send me the .txt file named proof_of_reading.txt to get the proof of reading.",
    "creator_post_journal": "Send me /creator_post_journal Your text here. For example: /creator_post_journal write a journal about ebbinghaus forgetting curve.",
    "creator_post_story": "Send me /creator_post_story Your text here. For example: /creator_post_story write a story about a boy and his beloved dog.",
    "creator_post_news": "Send me /creator_post_news Your prompt (keywords) here. For example: /creator_post_news Latest OpenAI news.",
    "creator_post_youtube": "Send me /creator_post_youtube Your youtube URL here. For example: /creator_post_youtube https://www.youtube.com/watch?v=video_id",
    "session_query_doc": f"Send me a document, and ask anything you want to know about the content of the file (PDF or Docx).",
    "session_code_interpreter": "In this session, I can write and execute code to assist you.",
    "session_chat_casual": "In this session, I can chat with you casually trying to be your best companion.",
    "session_assistant_email": "In this session, I can assist you in summarizing, translating your email content and drafting a reply.",
    "session_assistant_general": "In this session, I can assist you with saving or retrieving your most frequently used information and many other general tasks an assistant can do.",
    "session_help": "Click to get help on how to use the this bot.",
    "session_exit": "Click to exit the current session and return to normal chat.",
    "count": "Count words and characters in your text. Example: /count Hello, how are you?",
    "length": "Count words and characters in your text. Example: /length Hello, how are you?",
    "creator_auto_post": "Set up automatic posting with a series name. Example: /creator_auto_post The Eternal Drift",
    "default_voice": "Set your preferred default voice for audio generation.",
    "set_creator_configurations": "Click to set the configurations for the creator mode.",
    "set_daily_words_list_on": "Click to turn on the daily words list feature.",
    "set_openai_api_key": "Click to set your OpenAI API Key.",
    "set_elevenlabs_api_key": "Click to set your Elevenlabs API Key.",
    "set_google_spreadsheet": "Click to set your Google Spreadsheet.",
    "set_news_keywords": "Click to set the keywords for the news generation.",
    "set_mother_language": "Click to set your mother language.",
    "set_cartoon_style": "Click to set the cartoon style for the image generation.",
    "set_twitter_handle": "Click to set your Twitter handle.",
    "set_daily_story_voice": "Click to set the voice for the daily story.",
    "set_voice_clone_sample": "Click to set the voice clone sample.",
    "set_youtube_playlist": "Click to set your YouTube playlist.",
    "set_default_audio_gender": "Click to set the default audio gender for your generated audio.",

}

commands_dict_string = '\n'.join([f"{key}: {value}" for key, value in commands_dict.items()])
print(commands_dict_string)