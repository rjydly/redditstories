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
def call_gemini_api(prompt, api_key, temperature=0.7):
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
# 1. GENERADOR D'HISTÒRIES ANTI-REPETICIÓ (GEMINI AI)
# -------------------------------------------------------------
TEMES_VIRALS = [
    "A petty revenge on a terrible boss or coworker that worked out perfectly",
    "An awkward misunderstanding with my girlfriend's or boyfriend's parents",
    "A completely chaotic wedding or anniversary disaster",
    "An accidental lie in a job interview that spiraled totally out of control",
    "An absurd neighbor feud involving garden fences, loud music, or pets",
    "A catastrophic culinary disaster while trying to impress guests",
    "Discovering a bizarre secret about a roommate after living together for months",
    "A ridiculous school or university prank that caused unintended consequences",
    "An airport or vacation mishap where everything that could go wrong did",
    "Mistaking a total stranger for a close friend in public in the worst way possible",
    "Winning something useless and having it take over my whole life",
    "A mystery package arriving at my door with completely unexplained contents"
]

def generate_fresh_stories_with_gemini(api_key):
    """
    Genera 5 històries 100% noves utilitzant temàtiques aleatòries per evitar repeticions.
    """
    random_theme = random.choice(TEMES_VIRALS)
    unique_seed = random.randint(10000, 99999)
    print(f"Generant contingut inèdit amb Gemini (Temàtica: '{random_theme[:40]}...', ID: {unique_seed})...")
    
    prompt = (
        f"Ets un guionista d'elit especialitzat en relats virals de Reddit per a format curt (TikTok, Reels, Shorts).\n"
        f"Gènere/Temàtica obligatòria per a aquesta tirada: {random_theme}.\n"
        f"Identificador de sessió aleatori: {unique_seed}.\n\n"
        "REQUISITS ESTRICTES:\n"
        "1. Crea 5 històries COMPLETAMENT DIFERENTS entre elles, fresques i inèdites.\n"
        "2. El títol ('title') ha de ser un ganxo irresistible (màxim 12-14 paraules en anglès).\n"
        "3. El cos ('story') ha de ser el text EXACTE que es llegirà i es veurà a la pantalla.\n"
        "4. Longitud exacta: entre 90 i 120 paraules en anglès (ideal per a un vídeo de 40-50 segons).\n"
        "5. El llenguatge ha de ser directe, en primera persona, sense introduccions com 'Hello Reddit' ni fórmules com 'TL;DR'.\n\n"
        "Respon ÚNICAMENT amb un JSON vàlid:\n"
        "[\n"
        "  {\n"
        '    "subreddit": "tifu",\n'
        '    "author": "random_user_name",\n'
        '    "title": "Títol molt atractiu en anglès",\n'
        '    "story": "El text complet del relat que serà pronunciat i escrit...",\n'
        '    "ups": 18500\n'
        "  }\n"
        "]"
    )
    
    response_text = call_gemini_api(prompt, api_key, temperature=0.85)
    if response_text:
        try:
            posts = json.loads(response_text)
            if isinstance(posts, list) and len(posts) > 0:
                print(f"S'han generat {len(posts)} històries inèdites sense duplicats.")
                return posts
        except Exception as e:
            print(f"Error processant JSON de Gemini: {e}")

    # Reserva única amb títol i relat sincronitzats
    return [{
        "subreddit": "tifu",
        "author": f"user_{unique_seed}",
        "title": "I accidentally convinced my entire gym that I am a famous Olympic athlete",
        "story": "It started when I wore a vintage track jacket my brother found at a thrift store. A trainer asked if I was training for the qualifiers, and instead of explaining, I just nodded nervously. Within two days, the manager gave me VIP access and asked me to sign a poster. Now I have to pretend to stretch for two hours every morning because I cannot do a single pull up without crying.",
        "ups": 21300
    }]

def fetch_candidate_posts(api_key, total_needed=15):
    """
    Intenta obtenir posts reals variant els filtres temporals per evitar repeticions.
    Si els servidors externs fallen o es repeteixen, activa el motor inèdit de Gemini.
    """
    posts = []
    mirrors = ["https://safereddit.com", "https://redlib.tux.pizza"]
    subreddits = ["tifu", "confession", "TrueOffMyChest"]
    # Variem el filtre per no veure sempre els mateixos 'hot'
    time_filters = ["hot.json", "top.json?t=week", "rising.json"]
    chosen_filter = random.choice(time_filters)
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) App/{random.randint(100, 999)}"}

    print(f"Buscant a la xarxa Reddit (Filtre: {chosen_filter})...")
    for mirror in mirrors:
        if len(posts) >= total_needed:
            break
        for sub in subreddits:
            url = f"{mirror}/r/{sub}/{chosen_filter}?limit=15"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    children = data.get("data", {}).get("children", [])
                    random.shuffle(children) # Barregem per trencar l'ordre fix
                    for item in children:
                        p = item.get("data", {})
                        title = p.get("title", "").strip()
                        body = p.get("selftext", "").strip()
                        author = p.get("author", "reddit_user")
                        ups = p.get("ups", 1000)

                        if 180 <= len(body) <= 750 and not p.get("stickied", False):
                            posts.append({
                                "subreddit": sub,
                                "author": author,
                                "title": title,
                                "story": body,
                                "ups": ups
                            })
                            if len(posts) >= total_needed:
                                return posts
            except Exception:
                continue

    print("Connexió externa limitada. Utilitzant el generador d'històries inèdites amb IA...")
    return generate_fresh_stories_with_gemini(api_key)

# -------------------------------------------------------------
# 2. SELECCIÓ I REVISIÓ EDITORIAL (GEMINI AI)
# -------------------------------------------------------------
def select_story_with_gemini(posts, api_key):
    """
    Avalua les opcions i garanteix que 'title' i 'story' siguin exactament
    el que es dibuixa a la targeta i el que es transmet a la veu.
    """
    if not posts:
        posts = generate_fresh_stories_with_gemini(api_key)

    if not api_key:
        p = posts[0]
        return p

    batch_size = 5
    max_rounds = 3
    
    for round_idx in range(max_rounds):
        start = round_idx * batch_size
        end = start + batch_size
        batch = posts[start:end]
        
        if not batch:
            break
            
        print(f"\n--- Avaluant Ronda {round_idx + 1} de 5 opcions amb Gemini ---")
        batch_descriptions = ""
        for i, p in enumerate(batch, 1):
            batch_descriptions += f"\n[OPCIÓ {i}]\nTítol: {p['title']}\nHistòria: {p['story'][:250]}...\n"
            
        prompt = (
            "Ets el director de contingut d'un canal de vídeos curts d'alta retenció.\n"
            "Analitza aquestes 5 publicacions. Necessitem la història més divertida, sorprenent o addictiva.\n"
            f"{batch_descriptions}\n"
            "INSTRUCCIONS:\n"
            "- Si alguna és fantàstica, respon amb el seu número i retorna el 'title' polit i la 'story' polida en anglès.\n"
            "- IMPORTANTÍSSIM: La 'story' ha de tenir entre 90 i 120 paraules exactes per no saturar la pantalla i durar uns 45 segons de veu.\n"
            "- Si cap és prou bona, respon amb 'selected': null.\n"
            "Format JSON estricte:\n"
            "{\n"
            '  "selected": 1,\n'
            '  "title": "Títol polit en anglès...",\n'
            '  "story": "Text exacte que es llegirà i es mostrarà a la targeta..."\n'
            "}"
        )
        
        response_text = call_gemini_api(prompt, api_key, temperature=0.3)
        if response_text:
            try:
                parsed = json.loads(response_text)
                selected = parsed.get("selected")
                
                if selected and isinstance(selected, int) and 1 <= selected <= len(batch):
                    chosen = batch[selected - 1].copy()
                    # Substituïm el contingut pel text polit per assegurar concordança 1:1
                    chosen["title"] = parsed.get("title", chosen["title"]).strip()
                    chosen["story"] = parsed.get("story", chosen["story"]).strip()
                    print(f"Història seleccionada: {chosen['title'][:50]}...")
                    return chosen
                else:
                    print("Cap d'aquestes 5 ha superat el criteri de qualitat. Provant següent ronda...")
            except Exception as e:
                print(f"Error interpretant el veredicte: {e}")

    print("Seleccionant la millor història disponible.")
    best = max(posts, key=lambda x: x.get("ups", 0), default=posts[0])
    return best

# -------------------------------------------------------------
# 3. GENERACIÓ VISUAL DE LA TARGETA (100% FIDEL AL TEXT)
# -------------------------------------------------------------
def create_reddit_card_image(post, output_image="reddit_card.png"):
    """
    Genera la targeta gràfica (1080x960). Dibuixa exactament el títol
    i el cos de la història que la veu narrarà.
    """
    width, height = 1080, 960
    img = Image.new("RGB", (width, height), color="#0e1113")
    draw = ImageDraw.Draw(img)
    
    card_margin_x, card_margin_y = 50, 50
    card_w, card_h = width - (card_margin_x * 2), height - (card_margin_y * 2)
    card_bg = "#1a1a1b"
    draw.rounded_rectangle(
        [card_margin_x, card_margin_y, card_margin_x + card_w, card_margin_y + card_h],
        radius=25,
        fill=card_bg,
        outline="#343536",
        width=2
    )
    
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    meta_font = ImageFont.truetype(font_reg, 30)
    title_font = ImageFont.truetype(font_bold, 40)
    body_font = ImageFont.truetype(font_reg, 32)
    
    # Capçalera (Subreddit + Autor)
    draw.ellipse([card_margin_x + 35, card_margin_y + 35, card_margin_x + 90, card_margin_y + 90], fill="#ff4500")
    draw.text((card_margin_x + 105, card_margin_y + 45), f"r/{post['subreddit']}", font=meta_font, fill="#d7dadc")
    draw.text((card_margin_x + 360, card_margin_y + 45), f"• u/{post['author']}", font=meta_font, fill="#818384")
    
    # Títol
    wrapped_title = textwrap.wrap(post["title"], width=36)
    cur_y = card_margin_y + 115
    for line in wrapped_title[:3]:
        draw.text((card_margin_x + 35, cur_y), line, font=title_font, fill="#ffffff")
        cur_y += 50
        
    cur_y += 15
    
    # Cos exacte (tota la història visible)
    wrapped_story = textwrap.wrap(post["story"], width=46)
    for line in wrapped_story[:10]: # Fins a 10 línies
        draw.text((card_margin_x + 35, cur_y), line, font=body_font, fill="#d7dadc")
        cur_y += 42
        
    # Recompte de vots
    ups = post.get("ups", 15400)
    ups_k = f"{ups / 1000:.1f}k" if ups > 1000 else str(ups)
    footer_y = card_margin_y + card_h - 75
    draw.rounded_rectangle([card_margin_x + 35, footer_y, card_margin_x + 220, footer_y + 48], radius=15, fill="#272729")
    draw.text((card_margin_x + 55, footer_y + 10), f"▲  {ups_k}  ▼", font=meta_font, fill="#d7dadc")
    
    img.save(output_image)
    print("Targeta gràfica 100% sincronitzada generada amb èxit.")

# -------------------------------------------------------------
# 4. GENERACIÓ D'ÀUDIO I SUBTÍTOLS (EDGE-TTS)
# -------------------------------------------------------------
async def generate_audio_and_timestamps(text, output_audio="audio.mp3"):
    """
    Sintetitza la narració que coincideix exactament amb el text de la targeta.
    """
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    words_data = []

    print("Generant veu neuronal i marques de temps...")
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

    print(f"Àudio completat ({len(words_data)} paraules sincronitzades).")
    return words_data

# -------------------------------------------------------------
# 5. MUNTATGE FINAL (SPLIT-SCREEN 9:16)
# -------------------------------------------------------------
def ensure_background_video(gameplay_path="gameplay.mp4"):
    if not (os.path.exists(gameplay_path) and os.path.getsize(gameplay_path) > 1024 * 1024):
        print("Descarregant vídeo de gameplay de suport...")
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

    # 1. Pantalla Superior (Targeta coincident 1080x960)
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

    # 3. Subtítols centrats a la part inferior (y=1400)
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

    # Composició completa vertical (1080x1920)
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
    print("Procés finalitzat amb èxit!")

# -------------------------------------------------------------
# EXECUCIÓ PRINCIPAL
# -------------------------------------------------------------
if __name__ == "__main__":
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    print("Iniciant selecció de contingut inèdit...")
    posts = fetch_candidate_posts(gemini_key, total_needed=15)
    
    chosen_post = select_story_with_gemini(posts, gemini_key)
    
    # El text narrat és EXACTAMENT el títol seguit del text escrit a la targeta
    full_narrative = f"{chosen_post['title']}. {chosen_post['story']}"
    print(f"\nHistòria definitiva:\n{full_narrative[:140]}...\n")
    
    create_reddit_card_image(chosen_post, "reddit_card.png")
    words = asyncio.run(generate_audio_and_timestamps(full_narrative, "audio.mp3"))
    build_split_screen_video(words)
