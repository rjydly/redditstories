import os
import random
import asyncio
import praw
import whisper
import edge_tts
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

# 1. CONFIGURACIÓ DE REDDIT
def get_reddit_story():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="script:viral_shorts_bot:v1.0 (by /u/reddit_username)"
    )
    
    subreddit = reddit.subreddit("AskReddit")
    # Busquem els millors posts del dia
    for submission in subreddit.top(time_filter="day", limit=20):
        # Filtrem posts de text de mida ideal per a un vídeo de 40-60 segons (entre 300 i 600 caràcters)
        text = f"{submission.title}. {submission.selftext}".strip()
        # Si no té cos de text, busquem el primer comentari més votat
        if len(submission.selftext) < 50:
            submission.comments.replace_more(limit=0)
            best_comments = [c.body for c in submission.comments if len(c.body) > 100]
            if best_comments:
                text = f"{submission.title}. {best_comments[0]}"
                
        # Neteja de caràcters estranys o links
        clean_text = " ".join(text.split())
        if 200 <= len(clean_text) <= 500:
            print(f"Història seleccionada: {clean_text[:60]}...")
            return clean_text
            
    # Text de seguretat per si falla Reddit
    return "What is a fact so ridiculous that it sounds completely fake, but is actually one hundred percent true?"

# 2. GENERACIÓ DE VEU (TTS)
async def generate_audio(text, output_audio="audio.mp3"):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_audio)
    print("Àudio generat amb èxit.")

# 3. TRANSCRIURE I EXTREURE SUBTÍTOLS (WHISPER)
def get_word_timestamps(audio_path):
    print("Transcribint àudio amb Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)
    
    words_data = []
    for segment in result["segments"]:
        for word in segment["words"]:
            words_data.append({
                "word": word["word"].strip().upper(),
                "start": word["start"],
                "end": word["end"]
            })
    return words_data

# 4. EDICIÓ DEL VÍDEO
def build_video(gameplay_path="gameplay.mp4", audio_path="audio.mp3", output_path="final_video.mp4"):
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    video = VideoFileClip(gameplay_path)
    
    # Si el gameplay és més llarg, agafem un tros aleatori
    if video.duration > audio_duration:
        start_time = random.uniform(0, video.duration - audio_duration - 1)
        background = video.subclipped(start_time, start_time + audio_duration)
    else:
        background = video.subclipped(0, audio_duration)
        
    # Assegurem la resolució vertical 9:16 (1080x1920)
    background = background.resized(new_size=(1080, 1920))
    background = background.with_audio(audio)
    
    # Generem els subtítols
    words = get_word_timestamps(audio_path)
    subtitle_clips = []
    
    for item in words:
        # Creació de TextClip compatible amb MoviePy v2
        txt_clip = (
            TextClip(
                text=item["word"],
                font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                font_size=80,
                color="yellow",
                stroke_color="black",
                stroke_width=4
            )
            .with_position(("center", "center"))
            .with_start(item["start"])
            .with_end(item["end"])
        )
        subtitle_clips.append(txt_clip)
        
    # Muntatge final
    final_video = CompositeVideoClip([background] + subtitle_clips)
    
    print("Renderitzant el vídeo final...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )
    print("Vídeo llest!")

if __name__ == "__main__":
    story = get_reddit_story()
    asyncio.run(generate_audio(story, "audio.mp3"))
    build_video()
