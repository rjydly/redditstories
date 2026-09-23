import os
import random
import asyncio
import requests
import whisper
import edge_tts
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip

def get_reddit_story():
    """
    Extreu de forma pública i gratuïta (sense API keys) la millor
    història del dia d'AskReddit.
    """
    url = "https://www.reddit.com/r/AskReddit/top.json?t=day&limit=25"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                
                # Unim títol i text eliminant salts de línia sobrants
                full_text = f"{title}. {selftext}".strip()
                clean_text = " ".join(full_text.split())
                
                # Filtrem per a una durada ideal en vídeo curt (uns 35-50 segons)
                if 200 <= len(clean_text) <= 500:
                    print(f"Història trobada a AskReddit: {clean_text[:60]}...")
                    return clean_text
    except Exception as e:
        print(f"Error connectant a Reddit: {e}")

    print("Utilitzant història alternativa per defecte.")
    return "What is a fact so ridiculous that it sounds completely fake, but is actually one hundred percent true?"

async def generate_audio(text, output_audio="audio.mp3"):
    """
    Genera la veu en off amb edge-tts de Microsoft de forma gratuïta.
    """
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_audio)
    print("Àudio generat correctament.")

def get_word_timestamps(audio_path):
    """
    Analitza l'àudio amb el model Whisper per obtenir
    el minutatge exacte de cada paraula.
    """
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

def build_video(gameplay_path="gameplay.mp4", audio_path="audio.mp3", output_path="final_video.mp4"):
    """
    Munta el vídeo vertical 9:16 sincronitzant àudio, fons i subtítols.
    """
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    video = VideoFileClip(gameplay_path)
    
    # Agafem un segment aleatori del gameplay que coincideixi amb la durada de l'àudio
    if video.duration > audio_duration:
        start_time = random.uniform(0, video.duration - audio_duration - 1)
        background = video.subclipped(start_time, start_time + audio_duration)
    else:
        background = video.subclipped(0, audio_duration)
        
    # Assegurem la resolució vertical de 1080x1920
    background = background.resized(new_size=(1080, 1920))
    background = background.with_audio(audio)
    
    words = get_word_timestamps(audio_path)
    subtitle_clips = []
    
    # Creació dels subtítols centrats en majúscules
    for item in words:
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
    print("Vídeo generat amb èxit!")

if __name__ == "__main__":
    story = get_reddit_story()
    asyncio.run(generate_audio(story, "audio.mp3"))
    build_video()
