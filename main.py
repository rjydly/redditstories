import os
import random
import asyncio
import requests
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import edge_tts

def get_reddit_story():
    """
    Extreu històries virals de Reddit (AskReddit o AmItheAsshole).
    Utilitza una capçalera tipus aplicació per evitar el filtre de bots de Reddit.
    """
    subreddits = ["AskReddit", "AmItheAsshole"]
    headers = {
        "User-Agent": "script:viral_content_maker:v1.0 (by /u/system_bot)"
    }
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    selftext = post_data.get("selftext", "")
                    
                    full_text = f"{title}. {selftext}".strip()
                    clean_text = " ".join(full_text.split())
                    
                    # Ideal per a vídeos d'entre 35 i 50 segons
                    if 200 <= len(clean_text) <= 500:
                        print(f"Història trobada a r/{sub}: {clean_text[:60]}...")
                        return clean_text
        except Exception as e:
            print(f"No s'ha pogut obtenir de r/{sub}: {e}")

    print("Utilitzant història alternativa per defecte.")
    return "What is a fact so ridiculous that it sounds completely fake, but is actually one hundred percent true?"

async def generate_audio_and_timestamps(text, output_audio="audio.mp3"):
    """
    Genera l'àudio amb edge-tts i n'extreu la posició de cada paraula en nanosegons.
    """
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    words_data = []

    print("Generant veu neuronal i timestamps amb Edge-TTS...")
    with open(output_audio, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # L'offset i la durada de Microsoft s'expressen en unitats de 100ns (1s = 10.000.000 unitats)
                start = chunk["offset"] / 10_000_000
                duration = chunk["duration"] / 10_000_000
                word = chunk["text"].strip().upper()
                if word:
                    words_data.append({
                        "word": word,
                        "start": start,
                        "end": start + duration
                    })

    print(f"Àudio generat amb èxit. S'han detectat {len(words_data)} paraules.")
    return words_data

def build_video(words, gameplay_path="gameplay.mp4", audio_path="audio.mp3", output_path="final_video.mp4"):
    """
    Munta el vídeo en format 9:16 (1080x1920) sincronitzant àudio, fons i text.
    """
    if not os.path.exists(gameplay_path):
        raise FileNotFoundError(
            f"Falta el fitxer '{gameplay_path}'. Puja un vídeo vertical de gameplay "
            f"anomenat exactament '{gameplay_path}' al teu repositori."
        )

    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration
    
    video = VideoFileClip(gameplay_path)
    
    # Retallem un fragment aleatori del gameplay si aquest dura més que l'àudio
    if video.duration > audio_duration:
        start_time = random.uniform(0, video.duration - audio_duration - 1)
        background = video.subclipped(start_time, start_time + audio_duration)
    else:
        background = video.subclipped(0, audio_duration)
        
    background = background.resized(new_size=(1080, 1920))
    background = background.with_audio(audio)
    
    subtitle_clips = []
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    for item in words:
        txt_clip = (
            TextClip(
                text=item["word"],
                font=font_path,
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
    print("Procés finalitzat! El vídeo s'ha generat correctament.")

if __name__ == "__main__":
    story_text = get_reddit_story()
    words = asyncio.run(generate_audio_and_timestamps(story_text, "audio.mp3"))
    build_video(words)
