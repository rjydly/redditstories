import os
import re
import json
import random
import asyncio
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, AudioFileClip, ImageClip, TextClip, CompositeVideoClip
import edge_tts

# -------------------------------------------------------------
# 1. EXTRACCIÓ DE CONTINGUT DE REDDIT
# -------------------------------------------------------------
def fetch_candidate_posts(total_needed=15):
    """
    Extreu publicacions candidates de subreddits de relats.
    """
    subreddits = ["AskReddit", "Stories", "AmItheAsshole"]
    posts = []
    headers = {"User-Agent": "script:viral_shorts_gemini:v1.0 (by /u/system_bot)"}
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("data", {}).get("children", []):
                    p = item.get("data", {})
                    title = p.get("title", "").strip()
                    body = p.get("selftext", "").strip()
                    author = p.get("author", "reddit_user")
                    ups = p.get("ups", 1000)
                    
                    # Ignorem posts buits, fixats o excessivament llargs
                    if not body or len(body) < 120 or p.get("stickied", False):
                        continue
                    
                    posts.append({
                        "subreddit": sub,
                        "author": author,
                        "title": title,
                        "body": body,
                        "ups": ups
                    })
                    if len(posts) >= total_needed:
                        return posts
        except Exception as e:
            print(f"Error connectant a r/{sub}: {e}")
            
    return posts

# -------------------------------------------------------------
# 2. FILTRATGE AMB GEMINI AI (3 RONDES DE 5 POSTS)
# -------------------------------------------------------------
def select_story_with_gemini(posts, api_key):
    """
    Pregunta a Gemini en blocs de 5 posts fins a un màxim de 3 vegades.
    """
    if not api_key:
        print("Avís: No s'ha trobat GEMINI_API_KEY. Seleccionant el primer post per defecte.")
        p = posts[0]
        return p, f"{p['title']}. {p['body']}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    batch_size = 5
    max_rounds = 3
    
    for round_idx in range(max_rounds):
        start = round_idx * batch_size
        end = start + batch_size
        batch = posts[start:end]
        
        if not batch:
            break
            
        print(f"\n--- Avaluant Ronda {round_idx + 1} de 5 publicacions amb Gemini ---")
        
        # Preparem el resum de cada post per al prompt
        batch_descriptions = ""
        for i, p in enumerate(batch, 1):
            sample = p['body'][:300].replace('\n', ' ')
            batch_descriptions += f"\n[OPCIÓ {i}]\nTítol: {p['title']}\nInici: {sample}...\n"
            
        prompt = (
            "Ets un expert productor de contingut viral per a TikTok, Snapchat Spotlight i Reels.\n"
            "Analitza aquestes 5 publicacions de Reddit. Necessitem una història que tingui un GANXO inicial fort, "
            "sigui entretinguda, tingui un to intrigant o emocional, i sigui adequada per a un vídeo de 45-60 segons.\n"
            f"{batch_descriptions}\n"
            "INSTRUCCIONS DE RESPOSTA:\n"
            "- Si alguna opció és excel·lent, respon amb el número (1-5) i una versió polida del text en anglès llesta per ser narrada (eliminant 'TL;DR', 'AITA', enllaços i paraules complexes).\n"
            "- Si CAP de les 5 opcions té prou qualitat o ganxo viral, respon amb 'selected': null.\n"
            "Respon EXCLUSIVAMENT en format JSON vàlid:\n"
            "{\n"
            '  "selected": 1, // o null si cap és bona\n'
            '  "narration": "El text net per ser narrat per la veu en off..."\n'
            "}"
        )
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"}
        }
        
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                data = res.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_response)
                
                selected = parsed.get("selected")
                narration = parsed.get("narration", "")
                
                if selected and isinstance(selected, int) and 1 <= selected <= len(batch):
                    chosen_post = batch[selected - 1]
                    print(f"Gemini ha escollit l'Opció {selected}: {chosen_post['title'][:50]}...")
                    return chosen_post, narration
                else:
                    print("Gemini ha determinat que cap d'aquestes 5 és prou bona. Provant el següent bloc...")
            else:
                print(f"Error resposta Gemini API: {res.text}")
        except Exception as e:
            print(f"Error connectant amb Gemini: {e}")

    # Si després de 3 rondes cap el convenç, agafem el millor per vots
    print("Cap història ha estat validada per Gemini. Agafant la més votada com a reserva.")
    best = max(posts, key=lambda x: x["ups"])
    return best, f"{best['title']}. {best['body'][:600]}"

# -------------------------------------------------------------
# 3. GENERACIÓ VISUAL DE LA TARGETA DE REDDIT (PANTALLA SUPERIOR)
# -------------------------------------------------------------
def create_reddit_card_image(post, output_image="reddit_card.png"):
    """
    Crea una imatge de 1080x960 estilitzada com la interfície oficial de Reddit en mode fosc.
    """
    width, height = 1080, 960
    img = Image.new("RGB", (width, height), color="#0e1113")
    draw = ImageDraw.Draw(img)
    
    # Marc de la targeta
    card_margin_x, card_margin_y = 50, 60
    card_w, card_h = width - (card_margin_x * 2), height - (card_margin_y * 2)
    card_bg = "#1a1a1b"
    draw.rounded_rectangle([card_margin_x, card_margin_y, card_margin_x + card_w, card_margin_y + card_h], radius=25, fill=card_bg, outline="#343536", width=2)
    
    # Fonts
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    meta_font = ImageFont.truetype(font_reg, 32)
    title_font = ImageFont.truetype(font_bold, 44)
    body_font = ImageFont.truetype(font_reg, 34)
    
    # Capçalera (Icona + Nom Subreddit + Autor)
    draw.ellipse([card_margin_x + 40, card_margin_y + 40, card_margin_x + 95, card_margin_y + 95], fill="#ff4500")
    draw.text((card_margin_x + 115, card_margin_y + 48), f"r/{post['subreddit']}", font=meta_font, fill="#d7dadc")
    draw.text((card_margin_x + 360, card_margin_y + 48), f"• Posted by u/{post['author']}", font=meta_font, fill="#818384")
    
    # Títol
    wrapped_title = textwrap.wrap(post["title"], width=35)
    cur_y = card_margin_y + 130
    for line in wrapped_title[:3]: # Màxim 3 línies de títol
        draw.text((card_margin_x + 40, cur_y), line, font=title_font, fill="#ffffff")
        cur_y += 55
        
    cur_y += 20
    
    # Cos del text (Fragment estilitzat)
    wrapped_body = textwrap.wrap(post["body"][:400], width=45)
    for line in wrapped_body[:7]: # Màxim 7 línies
        draw.text((card_margin_x + 40, cur_y), line, font=body_font, fill="#d7dadc")
        cur_y += 44
        
    # Peu amb vots i comentaris
    ups_k = f"{post['ups'] / 1000:.1f}k" if post['ups'] > 1000 else str(post['ups'])
    footer_y = card_margin_y + card_h - 75
    draw.rounded_rectangle([card_margin_x + 40, footer_y, card_margin_x + 220, footer_y + 50], radius=15, fill="#272729")
    draw.text((card_margin_x + 60, footer_y + 10), f"▲  {ups_k}  ▼", font=meta_font, fill="#d7dadc")
    
    img.save(output_image)
    print("Targeta gràfica de Reddit generada correctament.")

# -------------------------------------------------------------
# 4. GENERACIÓ D'ÀUDIO I SUBTÍTOLS (EDGE-TTS)
# -------------------------------------------------------------
async def generate_audio_and_timestamps(text, output_audio="audio.mp3"):
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    words_data = []

    print("Generant àudio i timestamps amb Edge-TTS...")
    with open(output_audio, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 10_000_000
                duration = chunk["duration"] / 10_000_000
                word = chunk["text"].strip().upper()
                if word:
                    words_data.append({
                        "word": word,
                        "start": start,
                        "end": start + duration
                    })

    if not words_data:
        raw_words = text.replace(".", " ").replace(",", " ").split()
        audio = AudioFileClip(output_audio)
        step = audio.duration / max(len(raw_words), 1)
        for i, w in enumerate(raw_words):
            words_data.append({
                "word": w.upper(),
                "start": i * step,
                "end": (i + 1) * step
            })

    print(f"Àudio enllestit. S'han detectat {len(words_data)} paraules.")
    return words_data

# -------------------------------------------------------------
# 5. MUNTATGE FINAL (SPLIT-SCREEN 9:16)
# -------------------------------------------------------------
def ensure_background_video(gameplay_path="gameplay.mp4"):
    if not (os.path.exists(gameplay_path) and os.path.getsize(gameplay_path) > 1024 * 1024):
        print("Descarregant vídeo de fons per defecte...")
        url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        r = requests.get(url, stream=True)
        with open(gameplay_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def build_split_screen_video(words, card_img="reddit_card.png", gameplay_path="gameplay.mp4", audio_path="audio.mp3", output_path="final_video.mp4"):
    ensure_background_video(gameplay_path)
    audio = AudioFileClip(audio_path)
    audio_duration = audio.duration

    # 1. PANTALLA SUPERIOR: Targeta de Reddit (1080x960 a y=0)
    top_card = (
        ImageClip(card_img)
        .with_duration(audio_duration)
        .resized(new_size=(1080, 960))
        .with_position((0, 0))
    )

    # 2. PANTALLA INFERIOR: Gameplay (1080x960 a y=960)
    gameplay_full = VideoFileClip(gameplay_path)
    if gameplay_full.duration > audio_duration:
        start_time = random.uniform(0, gameplay_full.duration - audio_duration - 1)
        gameplay_clip = gameplay_full.subclipped(start_time, start_time + audio_duration)
    else:
        gameplay_clip = gameplay_full.subclipped(0, min(gameplay_full.duration, audio_duration))

    bottom_gameplay = (
        gameplay_clip
        .resized(new_size=(1080, 960))
        .with_position((0, 960))
    )

    # 3. SUBTÍTOLS DINÀMICS: Sobre el gameplay (y=1400 aproximadament)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    subtitle_clips = []
    
    for item in words:
        txt = (
            TextClip(
                text=item["word"],
                font=font_path,
                font_size=75,
                color="yellow",
                stroke_color="black",
                stroke_width=4
            )
            .with_position(("center", 1400))
            .with_start(item["start"])
            .with_end(item["end"])
        )
        subtitle_clips.append(txt)

    # Muntem el vídeo 1080x1920
    final_video = CompositeVideoClip(
        clips=[top_card, bottom_gameplay] + subtitle_clips,
        size=(1080, 1920)
    ).with_duration(audio_duration).with_audio(audio)

    print("Renderitzant el vídeo complet split-screen (1080x1920)...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )
    print("Vídeo generat amb èxit!")

# -------------------------------------------------------------
# EXECUCIÓ PRINCIPAL
# -------------------------------------------------------------
if __name__ == "__main__":
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    print("Recollint publicacions candidates de Reddit...")
    posts = fetch_candidate_posts(total_needed=15)
    
    chosen_post, narration_text = select_story_with_gemini(posts, gemini_key)
    print(f"\nHistòria seleccionada:\n{narration_text[:120]}...\n")
    
    create_reddit_card_image(chosen_post, "reddit_card.png")
    words = asyncio.run(generate_audio_and_timestamps(narration_text, "audio.mp3"))
    build_split_screen_video(words)
