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
# MOTOR DE CONNEXIÓ AMB GEMINI AI (MULTI-MODEL RESILIENT)
# -------------------------------------------------------------
def call_gemini_api(prompt, api_key, temperature=0.2):
    """
    Crida a l'API de Gemini provant models actius en cascada.
    """
    models_to_try = ["gemini-3.6-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "response_mime_type": "application/json"}
    }
    
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            elif res.status_code == 404:
                continue
            else:
                print(f"Avís resposta Gemini ({model}): {res.status_code}")
        except Exception as e:
            print(f"Error connectant amb model {model}: {e}")
            
    return None

# -------------------------------------------------------------
# 1. EXTRACCIÓ DE CONTINGUT (MIRALLS REDLIB + MOTOR GENERATIU GEMINI)
# -------------------------------------------------------------
def generate_stories_with_gemini(api_key):
    """
    Genera 5 històries hiperrealistes amb l'estil i format de Reddit.
    Garanteix 0 bloquejos i evita contingut duplicat a xarxes socials.
    """
    print("Activant motor de generació viral amb Gemini AI...")
    
    prompt = (
        "Ets un guionista expert en crear vídeos virals per a TikTok, Shorts i Reels a partir d'històries d'estil Reddit.\n"
        "Genera 5 històries fictícies però totalment creïbles, boges, intrigants o divertides, com si fossin publicacions de "
        "subreddits com r/tifu, r/confession o r/TrueOffMyChest.\n"
        "REQUISITS:\n"
        "- Cada història ha de començar amb una primera frase molt potent (ganxo viral).\n"
        "- Longitud ideal per a 40-50 segons de veu en off (entre 110 i 140 paraules en anglès).\n"
        "- Retorna ÚNICAMENT un array JSON vàlid amb aquest format:\n"
        "[\n"
        "  {\n"
        '    "subreddit": "tifu",\n'
        '    "author": "usuari_inventat",\n'
        '    "title": "Títol molt atractiu",\n'
        '    "body": "El text complet de la història en primera persona...",\n'
        '    "ups": 19400\n'
        "  }\n"
        "]"
    )
    
    response_text = call_gemini_api(prompt, api_key, temperature=0.7)
    if response_text:
        try:
            posts = json.loads(response_text)
            print(f"S'han obtingut {len(posts)} històries inèdites amb èxit.")
            return posts
        except Exception as e:
            print(f"Error processant JSON de Gemini: {e}")

    # Reserva local en cas d'absència de clau o xarxa
    return [{
        "subreddit": "tifu",
        "author": "mystery_student",
        "title": "I accidentally convinced my entire university that our library was haunted",
        "body": "It all started when I left my Bluetooth speaker hidden on top of an old bookshelf during exam week. I started playing faint whisper tracks whenever someone sat nearby, and within forty-eight hours, the local news showed up.",
        "ups": 24500
    }]

def fetch_candidate_posts(api_key, total_needed=15):
    """
    Intenta obtenir publicacions a través d'instàncies mirall de Reddit (sense bloquejos d'IP).
    Si no responen, activa el motor generatiu de Gemini.
    """
    posts = []
    # Instàncies mirall públiques que no bloquegen GitHub Actions
    mirrors = ["https://safereddit.com", "https://redlib.tux.pizza"]
    subreddits = ["tifu", "confession", "TrueOffMyChest"]
    headers = {"User-Agent": "Mozilla/5.0"}

    print("Intentant connexió amb instàncies mirall de Reddit...")
    for mirror in mirrors:
        if len(posts) >= total_needed:
            break
        for sub in subreddits:
            url = f"{mirror}/r/{sub}/hot.json?limit=15"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    for item in data.get("data", {}).get("children", []):
                        p = item.get("data", {})
                        title = p.get("title", "").strip()
                        body = p.get("selftext", "").strip()
                        author = p.get("author", "reddit_user")
                        ups = p.get("ups", 1000)

                        if len(body) >= 200 and not p.get("stickied", False):
                            posts.append({
                                "subreddit": sub,
                                "author": author,
                                "title": title,
                                "body": body,
                                "ups": ups
                            })
                            if len(posts) >= total_needed:
                                return posts
            except Exception:
                continue

    # Si les instàncies mirall no estan disponibles, fem servir Gemini
    print("Servidors externs inaccessibles. Fent servir el generador d'històries amb IA...")
    return generate_stories_with_gemini(api_key)

# -------------------------------------------------------------
# 2. FILTRATGE AMB GEMINI AI (3 RONDES DE 5 POSTS)
# -------------------------------------------------------------
def select_story_with_gemini(posts, api_key):
    """
    Avalua les històries en blocs de 5 fins a un màxim de 3 rondes.
    """
    if not posts:
        posts = generate_stories_with_gemini(api_key)

    if not api_key:
        print("Avís: Sense GEMINI_API_KEY. Seleccionant la primera història.")
        p = posts[0]
        return p, f"{p['title']}. {p['body'][:500]}"

    batch_size = 5
    max_rounds = 3
    
    for round_idx in range(max_rounds):
        start = round_idx * batch_size
        end = start + batch_size
        batch = posts[start:end]
        
        if not batch:
            break
            
        print(f"\n--- Avaluant Ronda {round_idx + 1} de 5 publicacions amb Gemini ---")
        batch_descriptions = ""
        for i, p in enumerate(batch, 1):
            sample = p['body'][:300].replace('\n', ' ')
            batch_descriptions += f"\n[OPCIÓ {i}]\nTítol: {p['title']}\nInici: {sample}...\n"
            
        prompt = (
            "Ets un expert en creació de contingut viral per a format curt (Reels, Shorts, Spotlight).\n"
            "Analitza aquestes 5 publicacions. Necessitem una història amb un GANXO inicial fort, "
            "ritme dinàmic i durada d'uns 40-50 segons (110-140 paraules en anglès).\n"
            f"{batch_descriptions}\n"
            "INSTRUCCIONS:\n"
            "- Si alguna és adequada, respon amb el seu índex (1-5) i el text polit en anglès per a la narració (sense 'TL;DR' ni links).\n"
            "- Si cap és prou bona, respon amb 'selected': null.\n"
            "Format JSON estricte:\n"
            "{\n"
            '  "selected": 1,\n'
            '  "narration": "Text net en anglès per ser narrat..."\n'
            "}"
        )
        
        response_text = call_gemini_api(prompt, api_key, temperature=0.2)
        if response_text:
            try:
                parsed = json.loads(response_text)
                selected = parsed.get("selected")
                narration = parsed.get("narration", "")
                
                if selected and isinstance(selected, int) and 1 <= selected <= len(batch):
                    chosen_post = batch[selected - 1]
                    print(f"Gemini ha seleccionat l'Opció {selected}: {chosen_post['title'][:50]}...")
                    return chosen_post, narration
                else:
                    print("Gemini ha rebutjat el bloc actual per manca de ganxo. Passant al següent...")
            except Exception as e:
                print(f"Error interpretant el veredicte: {e}")

    print("Seleccionant la història més valorada com a solució de seguretat.")
    best = max(posts, key=lambda x: x.get("ups", 0), default=posts[0])
    return best, f"{best['title']}. {best['body'][:500]}"

# -------------------------------------------------------------
# 3. GENERACIÓ VISUAL DE LA TARGETA DE REDDIT (PANTALLA SUPERIOR)
# -------------------------------------------------------------
def create_reddit_card_image(post, output_image="reddit_card.png"):
    """
    Genera la targeta gràfica (1080x960) en mode fosc amb l'estètica oficial de Reddit.
    """
    width, height = 1080, 960
    img = Image.new("RGB", (width, height), color="#0e1113")
    draw = ImageDraw.Draw(img)
    
    card_margin_x, card_margin_y = 50, 60
    card_w, card_h = width - (card_margin_x * 2), height - (card_margin_y * 2)
    card_bg = "#1a1a1b"
    draw.rounded_rectangle([card_margin_x, card_margin_y, card_margin_x + card_w, card_margin_y + card_h], radius=25, fill=card_bg, outline="#343536", width=2)
    
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    meta_font = ImageFont.truetype(font_reg, 32)
    title_font = ImageFont.truetype(font_bold, 44)
    body_font = ImageFont.truetype(font_reg, 34)
    
    # Capçalera
    draw.ellipse([card_margin_x + 40, card_margin_y + 40, card_margin_x + 95, card_margin_y + 95], fill="#ff4500")
    draw.text((card_margin_x + 115, card_margin_y + 48), f"r/{post['subreddit']}", font=meta_font, fill="#d7dadc")
    draw.text((card_margin_x + 380, card_margin_y + 48), f"• u/{post['author']}", font=meta_font, fill="#818384")
    
    # Títol
    wrapped_title = textwrap.wrap(post["title"], width=35)
    cur_y = card_margin_y + 130
    for line in wrapped_title[:3]:
        draw.text((card_margin_x + 40, cur_y), line, font=title_font, fill="#ffffff")
        cur_y += 55
        
    cur_y += 20
    
    # Cos
    wrapped_body = textwrap.wrap(post["body"][:400], width=45)
    for line in wrapped_body[:7]:
        draw.text((card_margin_x + 40, cur_y), line, font=body_font, fill="#d7dadc")
        cur_y += 44
        
    # Recompte de vots
    ups = post.get("ups", 1200)
    ups_k = f"{ups / 1000:.1f}k" if ups > 1000 else str(ups)
    footer_y = card_margin_y + card_h - 75
    draw.rounded_rectangle([card_margin_x + 40, footer_y, card_margin_x + 220, footer_y + 50], radius=15, fill="#272729")
    draw.text((card_margin_x + 60, footer_y + 10), f"▲  {ups_k}  ▼", font=meta_font, fill="#d7dadc")
    
    img.save(output_image)
    print("Targeta gràfica generada amb èxit.")

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

    print(f"Àudio enllestit amb {len(words_data)} paraules sincronitzades.")
    return words_data

# -------------------------------------------------------------
# 5. MUNTATGE FINAL (SPLIT-SCREEN 9:16)
# -------------------------------------------------------------
def ensure_background_video(gameplay_path="gameplay.mp4"):
    if not (os.path.exists(gameplay_path) and os.path.getsize(gameplay_path) > 1024 * 1024):
        print("Descarregant vídeo de gameplay per defecte...")
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

    # 1. Pantalla Superior (Targeta 1080x960)
    top_card = (
        ImageClip(card_img)
        .with_duration(audio_duration)
        .resized(new_size=(1080, 960))
        .with_position((0, 0))
    )

    # 2. Pantalla Inferior (Gameplay 1080x960)
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

    # 3. Subtítols centrats sobre el gameplay (y=1400)
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

    # Composició completa 9:16
    final_video = CompositeVideoClip(
        clips=[top_card, bottom_gameplay] + subtitle_clips,
        size=(1080, 1920)
    ).with_duration(audio_duration).with_audio(audio)

    print("Renderitzant el vídeo final...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )
    print("Vídeo generat correctament!")

# -------------------------------------------------------------
# EXECUCIÓ PRINCIPAL
# -------------------------------------------------------------
if __name__ == "__main__":
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    print("Iniciant extracció de contingut...")
    posts = fetch_candidate_posts(gemini_key, total_needed=15)
    
    chosen_post, narration_text = select_story_with_gemini(posts, gemini_key)
    print(f"\nHistòria seleccionada:\n{narration_text[:120]}...\n")
    
    create_reddit_card_image(chosen_post, "reddit_card.png")
    words = asyncio.run(generate_audio_and_timestamps(narration_text, "audio.mp3"))
    build_split_screen_video(words)
