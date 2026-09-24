import os
import json
import random
import asyncio
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, vfx
import edge_tts

# -------------------------------------------------------------
# MOTOR DE CONNEXIÓ AMB GEMINI AI (MULTI-MODEL RESILIENT)
# -------------------------------------------------------------
def call_gemini_api(prompt, api_key, temperature=0.7):
    """
    Crida a l'API de Gemini provant models en cascada per evitar errors 404.
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
# 1. CONTINGUT EXCLUSIU DE CONFESSIONS I SECRETS
# -------------------------------------------------------------
TEMES_CONFESSIONS = [
    "A dark secret I have kept from my spouse or partner for years",
    "A massive lie I told at my workplace that everyone still believes",
    "Something terrible I did as a teenager that nobody ever found out about",
    "A petty and anonymous revenge on an obnoxious neighbor or ex-friend",
    "The reason I secretly cut off my entire family and vanished without warning",
    "An accidental crime or huge mistake I got away with completely"
]

def generate_confessions_with_gemini(api_key):
    """
    Genera confessions inèdites i dividides en blocs de frases llestes per a l'animació.
    """
    tema = random.choice(TEMES_CONFESSIONS)
    seed = random.randint(10000, 99999)
    print(f"Generant confessions anònimes amb Gemini (Tema: '{tema[:35]}...', Seed: {seed})...")
    
    prompt = (
        f"Ets un guionista d'elit especialitzat en confessions anònimes virals de Reddit (estil r/confession, r/TrueOffMyChest).\n"
        f"Temàtica: {tema}. Codi aleatori: {seed}.\n\n"
        "REQUISITS ESTRICTES:\n"
        "1. Genera 5 confessions COMPLETAMENT DIFERENTS entre elles, fresques i captivadores.\n"
        "2. El títol ('title') ha de ser un ganxo demolidor (màxim 12 paraules en anglès).\n"
        "3. El relat s'ha de dividir en exactament 3 o 4 fragments ('chunks') curts i directes.\n"
        "4. En total, la suma de tots els chunks ha de tenir entre 90 i 115 paraules (ideal per a 40-45 segons).\n"
        "5. Llenguatge en primera persona, sincer, fosc o impactant, sense fórmules com 'TL;DR' ni comiats.\n\n"
        "Respon ÚNICAMENT amb un JSON vàlid amb aquest format:\n"
        "[\n"
        "  {\n"
        '    "subreddit": "confession",\n'
        '    "author": "throwaway_secret99",\n'
        '    "title": "Títol molt cridaner en anglès",\n'
        '    "chunks": [\n'
        '      "Primera frase o introducció del secret...",\n'
        '      "Segona part on s\'explica el nus de la confessió...",\n'
        '      "Desenllaç impactant o situació actual..."\n'
        "    ],\n"
        '    "ups": 28300\n'
        "  }\n"
        "]"
    )
    
    response_text = call_gemini_api(prompt, api_key, temperature=0.85)
    if response_text:
        try:
            posts = json.loads(response_text)
            if isinstance(posts, list) and len(posts) > 0:
                return posts
        except Exception as e:
            print(f"Error parsejant JSON de confessions: {e}")

    # Reserva per defecte en cas d'error
    return [{
        "subreddit": "confession",
        "author": f"anon_{seed}",
        "title": "I have been secretly replacing my roommate expensive coffee with decaf for six months",
        "chunks": [
            "It all started when he accused me of stealing his food and insulted me in front of everyone.",
            "Instead of arguing with him, I bought the cheapest decaf brand and poured it into his luxury jar.",
            "Now he constantly visits the doctor complaining of chronic fatigue, and I just smile while sipping my real espresso."
        ],
        "ups": 32100
    }]

def fetch_confession_posts(api_key):
    """
    Intenta obtenir confessions de miralls de Reddit o activa el motor de Gemini.
    """
    mirrors = ["https://safereddit.com", "https://redlib.tux.pizza"]
    subreddits = ["confession", "TrueOffMyChest"]
    headers = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64) App/{random.randint(100, 999)}"}
    posts = []

    print("Cercant confessions reals a la xarxa...")
    for mirror in mirrors:
        for sub in subreddits:
            url = f"{mirror}/r/{sub}/top.json?t=month&limit=15"
            try:
                r = requests.get(url, headers=headers, timeout=5)
                if r.status_code == 200:
                    children = r.json().get("data", {}).get("children", [])
                    random.shuffle(children)
                    for item in children:
                        p = item.get("data", {})
                        title = p.get("title", "").strip()
                        body = p.get("selftext", "").strip()
                        author = p.get("author", "confession_user")
                        ups = p.get("ups", 1500)
                        
                        if 180 <= len(body) <= 600 and not p.get("stickied", False):
                            # Dividim aproximadament per frases
                            sentences = [s.strip() for s in body.replace("\n", " ").split(". ") if len(s.strip()) > 15]
                            if len(sentences) >= 3:
                                posts.append({
                                    "subreddit": sub,
                                    "author": author,
                                    "title": title,
                                    "chunks": sentences[:4],
                                    "ups": ups
                                })
                                if len(posts) >= 5:
                                    return posts
            except Exception:
                continue

    return generate_confessions_with_gemini(api_key)

# -------------------------------------------------------------
# 2. SELECCIÓ EDITORIAL AMB GEMINI
# -------------------------------------------------------------
def select_confession(posts, api_key):
    if not posts:
        posts = generate_confessions_with_gemini(api_key)

    if not api_key:
        return posts[0]

    print("\nAvaluant la millor confessió amb Gemini AI...")
    batch_descriptions = ""
    for i, p in enumerate(posts[:5], 1):
        preview = " ".join(p['chunks'])[:180]
        batch_descriptions += f"\n[OPCIÓ {i}]\nTítol: {p['title']}\nConfessió: {preview}...\n"

    prompt = (
        "Ets un director de contingut viral. Selecciona la millor confessió d'aquestes opcions "
        "(la que tingui més tensió, intriga o impacte emocional per a l'audiència).\n"
        f"{batch_descriptions}\n"
        "Retorna un JSON amb l'opció triada i el contingut dividit en 3 o 4 'chunks' nets en anglès:\n"
        "{\n"
        '  "selected": 1,\n'
        '  "title": "Títol polit...",\n'
        '  "chunks": ["Frase 1...", "Frase 2...", "Frase 3..."]\n'
        "}"
    )

    response_text = call_gemini_api(prompt, api_key, temperature=0.3)
    if response_text:
        try:
            parsed = json.loads(response_text)
            sel = parsed.get("selected", 1)
            if isinstance(sel, int) and 1 <= sel <= len(posts):
                chosen = posts[sel - 1].copy()
                chosen["title"] = parsed.get("title", chosen["title"]).strip()
                chosen["chunks"] = parsed.get("chunks", chosen["chunks"])
                return chosen
        except Exception as e:
            print(f"Error analitzant selecció: {e}")

    return posts[0]

# -------------------------------------------------------------
# 3. GENERACIÓ D'AVATAR I TARGETES PROGRESSIVES (PILLOW)
# -------------------------------------------------------------
def draw_reddit_avatar(draw, x, y, size=55):
    """
    Dibuixa la silueta oficial del ninot de Reddit (Snoo) amb un fons circular de color aleatori.
    """
    avatar_colors = ["#FF4500", "#0079D3", "#7193FF", "#FFB000", "#46D160", "#FF585B"]
    bg_color = random.choice(avatar_colors)
    
    # Cercle exterior
    draw.ellipse([x, y, x + size, y + size], fill=bg_color)
    
    # Cap blanc de Snoo
    cx, cy = x + size // 2, y + size // 2
    draw.ellipse([cx - 15, cy - 8, cx + 15, cy + 14], fill="#ffffff")
    
    # Orelles
    draw.ellipse([cx - 18, cy - 4, cx - 12, cy + 4], fill="#ffffff")
    draw.ellipse([cx + 12, cy - 4, cx + 18, cy + 4], fill="#ffffff")
    
    # Antena
    draw.line([cx, cy - 8, cx + 7, cy - 18], fill="#ffffff", width=2)
    draw.ellipse([cx + 5, cy - 22, cx + 11, cy - 16], fill="#ffffff")
    
    # Ulls taronges
    draw.ellipse([cx - 7, cy + 1, cx - 3, cy + 5], fill="#FF4500")
    draw.ellipse([cx + 3, cy + 1, cx + 7, cy + 5], fill="#FF4500")

def render_progressive_cards(post, output_prefix="card_stage_"):
    """
    Crea les imatges estàtiques que representen cada fase del text a la pantalla.
    Etapa 0: Només títol
    Etapa 1: Títol + Frase 1
    Etapa 2: Títol + Frase 1 + Frase 2...
    """
    width, height = 1080, 960
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    meta_font = ImageFont.truetype(font_reg, 30)
    title_font = ImageFont.truetype(font_bold, 38)
    body_font = ImageFont.truetype(font_reg, 33)
    
    generated_images = []
    chunks = post["chunks"]
    
    for stage in range(len(chunks) + 1):
        img = Image.new("RGB", (width, height), color="#0e1113")
        draw = ImageDraw.Draw(img)
        
        # Marc de la targeta
        card_x, card_y = 50, 50
        card_w, card_h = width - 100, height - 100
        draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=25, fill="#1a1a1b", outline="#343536", width=2)
        
        # Capçalera amb avatar Snoo oficial
        draw_reddit_avatar(draw, card_x + 35, card_y + 35, size=55)
        draw.text((card_x + 105, card_y + 45), f"r/{post['subreddit']}", font=meta_font, fill="#d7dadc")
        draw.text((card_x + 360, card_y + 45), f"• u/{post['author']}", font=meta_font, fill="#818384")
        
        # Títol (sempre visible des del principi)
        wrapped_title = textwrap.wrap(post["title"], width=38)
        cur_y = card_y + 115
        for line in wrapped_title[:3]:
            draw.text((card_x + 35, cur_y), line, font=title_font, fill="#ffffff")
            cur_y += 48
            
        cur_y += 20
        
        # Dibuixem els chunks acumulats segons l'etapa
        for i in range(stage):
            chunk_text = chunks[i]
            wrapped_chunk = textwrap.wrap(chunk_text, width=44)
            for line in wrapped_chunk:
                draw.text((card_x + 35, cur_y), line, font=body_font, fill="#d7dadc")
                cur_y += 44
            cur_y += 15 # Petit espai entre frases
            
        # Recompte de vots inferior
        ups = post.get("ups", 18200)
        ups_k = f"{ups / 1000:.1f}k" if ups > 1000 else str(ups)
        footer_y = card_y + card_h - 70
        draw.rounded_rectangle([card_x + 35, footer_y, card_x + 220, footer_y + 48], radius=15, fill="#272729")
        draw.text((card_x + 55, footer_y + 10), f"▲  {ups_k}  ▼", font=meta_font, fill="#d7dadc")
        
        filename = f"{output_prefix}{stage}.png"
        img.save(filename)
        generated_images.append(filename)
        
    print(f"Generades {len(generated_images)} etapes de la targeta amb èxit.")
    return generated_images

# -------------------------------------------------------------
# 4. GENERACIÓ D'ÀUDIO I CÀLCUL DE TEMPS PER FRASE
# -------------------------------------------------------------
async def generate_speech_and_timings(title, chunks, output_audio="audio.mp3"):
    """
    Genera l'àudio complet i troba en quin segon comença cada frase.
    """
    full_text = f"{title}. " + " ".join(chunks)
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(full_text, voice, boundary="WordBoundary")
    words_data = []

    print("Generant àudio de la confessió amb Edge-TTS...")
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

    # Càlcul precís dels temps d'inici de cada tram
    title_word_count = len(title.split())
    timings = [0.0] # L'etapa 0 (títol) comença a 0.0s
    
    current_idx = title_word_count
    for c in chunks:
        c_words = len(c.split())
        if current_idx < len(words_data):
            timings.append(words_data[current_idx]["start"])
        else:
            timings.append(timings[-1] + 5.0)
        current_idx += c_words

    print(f"Timestamps calculats per a les frases: {timings}")
    return timings

# -------------------------------------------------------------
# 5. MUNTATGE FINAL AMB ANIMACIÓ DE FADE PROGRESSIU
# -------------------------------------------------------------
def ensure_background_video(gameplay_path="gameplay.mp4"):
    if not (os.path.exists(gameplay_path) and os.path.getsize(gameplay_path) > 1024 * 1024):
        print("Descarregant fons de gameplay de suport...")
        url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
        r = requests.get(url, stream=True)
        with open(gameplay_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

def build_progressive_video(card_images, timings, gameplay_path="gameplay.mp4", audio_path="audio.mp3", output_path="final_video.mp4"):
    ensure_background_video(gameplay_path)
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    # 1. Capes de la targeta superior amb transició de fade
    top_clips = []
    
    # La targeta base (només títol) està present des de l'inici
    base_clip = (
        ImageClip(card_images[0])
        .with_duration(total_duration)
        .resized(new_size=(1080, 960))
        .with_position((0, 0))
    )
    top_clips.append(base_clip)
    
    # Afegim les etapes progressives amb fade in (0.35 segons) a mesura que la veu arriba a la frase
    for i in range(1, len(card_images)):
        start_t = timings[i]
        dur = total_duration - start_t
        if dur > 0:
            stage_clip = (
                ImageClip(card_images[i])
                .with_start(start_t)
                .with_duration(dur)
                .resized(new_size=(1080, 960))
                .with_position((0, 0))
                .with_effects([vfx.CrossFadeIn(0.35)])
            )
            top_clips.append(stage_clip)

    # 2. Gameplay net a la part inferior (y = 960)
    gameplay_full = VideoFileClip(gameplay_path)
    if gameplay_full.duration > total_duration:
        start_time = random.uniform(0, gameplay_full.duration - total_duration - 1)
        gameplay_clip = gameplay_full.subclipped(start_time, start_time + total_duration)
    else:
        gameplay_clip = gameplay_full.subclipped(0, min(gameplay_full.duration, total_duration))

    bottom_gameplay = (
        gameplay_clip
        .resized(new_size=(1080, 960))
        .with_position((0, 960))
    )

    # 3. Composició final vertical (1080x1920) sense subtítols nosa a sota
    final_video = CompositeVideoClip(
        clips=[bottom_gameplay] + top_clips,
        size=(1080, 1920)
    ).with_duration(total_duration).with_audio(audio)

    print("Renderitzant vídeo final amb fade progressiu...")
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=2
    )
    print("Vídeo completat amb èxit!")

# -------------------------------------------------------------
# EXECUCIÓ PRINCIPAL
# -------------------------------------------------------------
if __name__ == "__main__":
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    print("Iniciant extracció de confessions...")
    confessions = fetch_confession_posts(gemini_key)
    chosen_confession = select_confession(confessions, gemini_key)
    
    print(f"\nConfessió escollida:\nTítol: {chosen_confession['title']}")
    for idx, ch in enumerate(chosen_confession['chunks'], 1):
        print(f"Tram {idx}: {ch}")
        
    card_stages = render_progressive_cards(chosen_confession)
    timings = asyncio.run(generate_speech_and_timings(chosen_confession["title"], chosen_confession["chunks"], "audio.mp3"))
    
    build_progressive_video(card_stages, timings)
