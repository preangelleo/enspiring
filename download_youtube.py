from helping_page import *

if __name__ == '__main__':

    video_temp_dir = """Temp"""

    youtube_link = input("Enter a YouTube link (Enter 'q' to quit): ")
    if not youtube_link or youtube_link.lower() == 'q': sys.exit(0)
    else: output_audio_file = download_youtube_audio_on_mac_mp4(youtube_link)