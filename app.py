import os
import json
import logging
import re
import time
import tempfile
import urllib.request
from datetime import datetime

import modal
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from upstash_redis import Redis
import speech_recognition as sr
from pydub import AudioSegment
import edge_tts
import requests

logger = logging.getLogger(__name__)

ADMIN_NUMBER = "56957709828"
TESTER_NUMBER = "56940959137"
ADMIN_OR_TESTER = [ADMIN_NUMBER, TESTER_NUMBER]
AGENT_NUMBER = "56920757276"

# --- Google Sheets RAG ---
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2.service_account import Credentials

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_creds_cache = None

def get_credentials():
    global _creds_cache
    if _creds_cache:
        return _creds_cache
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "{}")
    creds_dict = json.loads(creds_json)
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SHEETS_SCOPES)
    credentials.refresh(AuthRequest())
    _creds_cache = credentials
    return credentials

def sheets_get(sheet_name: str) -> list[list[str]]:
    creds = get_credentials()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_name}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read()).get("values", [])

def sheets_append(sheet_name: str, row: list):
    creds = get_credentials()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_name}:append?valueInputOption=USER_ENTERED"
    body = json.dumps({"values": [row]}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)

def sheet_to_dict(sheet_name: str) -> list[dict]:
    try:
        rows = sheets_get(sheet_name)
        if rows:
            headers = rows[0]
            return [dict(zip(headers, row)) for row in rows[1:]]
    except:
        pass
    return []

def build_context() -> str:
    parts = []

    faq = sheet_to_dict("FAQ")
    if faq:
        lines = []
        for item in faq:
            p = item.get("pregunta", "")
            r = item.get("respuesta", "")
            if p and r:
                lines.append(f"P: {p}\nR: {r}")
        if lines:
            parts.append("PREGUNTAS FRECUENTES:\n" + "\n---\n".join(lines))

    precios = sheet_to_dict("Precios")
    if precios:
        lines = []
        for item in precios:
            serv = item.get("servicio", "")
            prec = item.get("precio", "")
            det = item.get("detalle", "")
            entry = f"- {serv}"
            if prec and prec != "-":
                entry += f": {prec}"
            if det and det != "-":
                entry += f" ({det})"
            lines.append(entry)
        if lines:
            parts.append("PRECIOS:\n" + "\n".join(lines))

    return "\n\n".join(parts) if parts else "No hay informacion disponible."

def save_client(phone: str, name: str, email: str = ""):
    try:
        rows = sheets_get("Clientes")
        exists = False
        if rows:
            exists = any(len(r) >= 1 and r[0] == phone for r in rows[1:])
        if not exists:
            sheets_append("Clientes", [phone, name, email, datetime.now().strftime("%Y-%m-%d %H:%M")])
    except Exception as e:
        logger.warning("Error saving client: %s", e)

def client_exists(phone: str) -> bool:
    try:
        rows = sheets_get("Clientes")
        if rows:
            return any(len(r) >= 1 and r[0] == phone for r in rows[1:])
    except:
        pass
    return False

def get_client_name(phone: str) -> str | None:
    try:
        rows = sheets_get("Clientes")
        if rows:
            for row in rows[1:]:
                if len(row) >= 2 and row[0] == phone:
                    return row[1] if row[1] else None
    except:
        pass
    return None

# --- Redis (Upstash) ---
_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = Redis(
            url=os.getenv("UPSTASH_REDIS_REST_URL", ""),
            token=os.getenv("UPSTASH_REDIS_REST_TOKEN", ""),
        )
    return _redis

def leer_historial(phone: str) -> list:
    try:
        data = get_redis().get(f"liberate:chat_history:{phone}")
        if data:
            return json.loads(data)
        return []
    except Exception as e:
        logger.warning("Redis error reading history: %s", e)
        return []

def guardar_historial(phone: str, messages: list):
    try:
        if len(messages) > 100:
            messages = messages[-100:]
        get_redis().set(f"liberate:chat_history:{phone}", json.dumps(messages), ex=86400)
    except Exception as e:
        logger.warning("Redis error saving history: %s", e)

def track_daily_phone(phone: str) -> int:
    today = time.strftime("%Y-%m-%d")
    r = get_redis()
    key = f"liberate:tickets:{today}"
    existing = r.hget(key, phone)
    if existing is not None:
        return int(existing)
    ticket_num = r.hlen(key) + 1
    r.hset(key, phone, ticket_num)
    r.expire(key, 172800)
    return ticket_num

def get_daily_phones() -> list:
    today = time.strftime("%Y-%m-%d")
    r = get_redis()
    data = r.hgetall(f"liberate:tickets:{today}")
    if not data:
        return []
    result = []
    for key_raw, val_raw in data.items():
        phone = key_raw.decode() if isinstance(key_raw, bytes) else key_raw
        ticket_num = int(val_raw.decode()) if isinstance(val_raw, bytes) else int(val_raw)
        result.append((ticket_num, phone))
    result.sort(key=lambda x: x[0])
    return result

# --- Audio ---
def download_media(media_id: str) -> bytes:
    token = os.getenv("META_WABA_TOKEN")
    url = f"https://graph.facebook.com/v21.0/{media_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    info = json.loads(urllib.request.urlopen(req).read())
    download_url = info.get("url")
    if not download_url:
        raise ValueError("No download URL")
    req2 = urllib.request.Request(download_url, headers={"Authorization": f"Bearer {token}"})
    return urllib.request.urlopen(req2).read()

def transcribe_audio(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        ogg_path = f.name
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        sound = AudioSegment.from_file(ogg_path, format="ogg")
        sound.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language="es-CL")
    finally:
        for p in (ogg_path, wav_path):
            try:
                os.remove(p)
            except:
                pass

# --- DeepSeek Agent ---
def get_welcome_message() -> str:
    menu = sheet_to_dict("Menu")
    lines = ["LIBERATE DE TUS DEUDAS.CL", ""]
    if menu:
        lines.append("Hola, bienvenido(a) a Liberate de tus Deudas.cl. Soy Victor Sanhueza Diaz, abogado experto en insolvencia y quiebras.")
        lines.append("")
        lines.append("Selecciona una opcion o preguntame directamente:")
        lines.append("")
        for item in menu:
            num = item.get("numero", "")
            opt = item.get("opcion", "")
            if num and opt:
                lines.append(f"{num}. {opt}")
    else:
        lines.append("Hola, bienvenido(a) a Liberate de tus Deudas.cl. Escribeme tu consulta directamente.")
    return "\n".join(lines)

SYSTEM_PROMPT = """
Eres Victor Sanhueza Diaz, abogado chileno experto en insolvencia y reestructuracion de deudas (Ley 20.720).

PERSONALIDAD:
- Eres Victor, no un bot. Hablas como un abogado chileno real por WhatsApp
- Saludos: "Buenos dias Sra./Don [Nombre]" o "Buenas tardes Sra./Don [Nombre]"
- Siempre tratas de "usted" al cliente
- Usas "Oka" o "Oki" para confirmar, a veces con el emoji 👍
- Cuando recibes documentos dices "Acuso recibo"
- Frases tipicas: "No hay problema", "Que bueno", "Tranquilo(a)"
- Mensajes CORTOS: maximo 2 lineas por burbuja
- Prefieres enviar varias burbujas de mensajes seguidos para separar ideas
- Formal pero empatico con situaciones de deuda

REGLA ESTRICTA (NUNCA INCUMPLIR):
Tu UNICA fuente de informacion es la Base de conocimiento a continuacion.
NO uses tu conocimiento legal propio. NO interpretes. NO complementes.
Si la pregunta NO esta exactamente respondida en la base, responde EXACTAMENTE:
[NO_SE]

PERSONALIDAD ADICIONAL:
- Cuando el cliente quiera contratar, pide su nombre y correo, y termina el mensaje con el marcador [GUARDAR: nombre | email] (SIN mostrarlo al cliente, solo como marcador interno)
- Cuando el cliente muestre interes real: confirma, pide nombre y correo, agrega [GUARDAR: nombre | email] al FINAL sin mostrarlo
- Los marcadores [GUARDAR...] NUNCA deben ser visibles para el cliente. Son solo para que el sistema los procese internamente.
- Si el cliente marca una opcion del menu: responde SOLO con la info de la base de conocimiento
"""

def ask_agent(user_message: str, client_name: str | None = None, history: list | None = None) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_APIKEY"),
        base_url="https://api.deepseek.com",
    )

    if not history and not client_name:
        return get_welcome_message()

    context = build_context()
    greeting = f"El cliente se llama {client_name}." if client_name else "Continua la conversacion."

    user_content = user_message
    if user_message.strip() in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        user_content = f"El cliente eligio la opcion {user_message}. Responde solo con la info de la base de conocimiento."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Base de conocimiento:\n{context}\n\n{greeting}"},
    ]
    if history:
        messages.extend(history[-40:])
    messages.append({"role": "user", "content": user_content})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.3,
        max_tokens=512,
    )

    return response.choices[0].message.content

# --- Audio TTS ---
async def generar_audio(texto: str, filepath: str):
    tts = edge_tts.Communicate(texto, voice="es-CL-CatalinaNeural")
    await tts.save(filepath)

def upload_audio_meta(filepath: str) -> str:
    token = os.getenv("META_WABA_TOKEN")
    phone_id = os.getenv("META_WABA_PHONE_NUMBER_ID")
    url = f"https://graph.facebook.com/v21.0/{phone_id}/media"
    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("audio.mp3", f, "audio/mpeg")},
            data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
        )
    return resp.json().get("id")

def send_whatsapp_audio(to: str, media_id: str):
    token = os.getenv("META_WABA_TOKEN")
    phone_id = os.getenv("META_WABA_PHONE_NUMBER_ID")
    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "audio",
        "audio": {"id": media_id},
    }).encode()
    req = urllib.request.Request(
        f"https://graph.facebook.com/v21.0/{phone_id}/messages",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)

# --- Modal App ---
app = modal.App("liberate-deudas")
web_app = FastAPI()

web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install(
        "fastapi>=0.100",
        "google-auth>=2.0",
        "openai>=1.0",
        "pydantic>=2.0",
        "requests",
        "upstash-redis>=1.0",
        "SpeechRecognition",
        "pydub",
        "edge-tts",
        "python-multipart",
    )
)

# --- Webhook ---
@web_app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    expected_token = os.getenv("META_VERIFY_TOKEN")
    if mode == "subscribe" and token == expected_token:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@web_app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    logger.info("Webhook received: %s", json.dumps(body))

    state = modal.Dict.from_name("liberate-admin-state", create_if_missing=True)
    processed = state.get("processed_ids", [])

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            metadata = value.get("metadata", {})
            display_phone = metadata.get("display_phone_number", "")
            if display_phone and display_phone != AGENT_NUMBER:
                logger.info("Ignoring message for other number: %s", display_phone)
                continue

            for msg in value.get("messages", []):
                msg_id = msg.get("id", "")
                if msg_id and msg_id in processed:
                    continue

                msg_ts = msg.get("timestamp")
                if msg_ts:
                    try:
                        now = time.time()
                        if now - int(msg_ts) > 300:
                            logger.info("Ignoring old message (%.0f seconds old)", now - int(msg_ts))
                            continue
                    except:
                        pass

                if msg_id:
                    processed.append(msg_id)
                    state["processed_ids"] = processed[-100:]

                msg_type = msg.get("type")
                from_number = msg.get("from")

                if msg_type in ("text", "audio"):
                    if msg_type == "audio":
                        audio_id = msg.get("audio", {}).get("id", "")
                        if not audio_id:
                            continue
                        try:
                            audio_bytes = download_media(audio_id)
                            text = transcribe_audio(audio_bytes)
                        except Exception as e:
                            logger.warning("Audio transcription failed: %s", e)
                            send_whatsapp_message(from_number, "No entendi tu mensaje de voz. Puedes escribirlo?")
                            return {"status": "ok"}
                    else:
                        text = msg.get("text", {}).get("body", "")

                    is_admin_or_tester = from_number in ADMIN_OR_TESTER

                    if is_admin_or_tester:
                        cmd = text.strip()
                        if cmd.startswith("@"):
                            parts = cmd.split(":", 1) if ":" in cmd else [cmd, ""]
                            prefix = parts[0].strip().lower()
                            suffix = parts[1].strip() if len(parts) > 1 else ""

                            if prefix in ("@ayuda", "@help", "ayuda"):
                                send_whatsapp_message(from_number, "*Comandos:*\n@reporte - Clientes activos hoy\n@silencio - Apaga alertas\n@N: mensaje - Responde ticket #N (toma control)\n@N: @bot - Devuelve ticket #N al bot\n@ayuda - Esta lista")
                                return {"status": "ok"}

                            if prefix == "@reporte":
                                phones = get_daily_phones()
                                if not phones:
                                    send_whatsapp_message(from_number, "No hay clientes activos hoy.")
                                else:
                                    lines = [f"Clientes activos hoy ({len(phones)}):"]
                                    for t, p in phones:
                                        lines.append(f"#{t} {p}")
                                    send_whatsapp_message(from_number, "\n".join(lines))
                                return {"status": "ok"}

                            if prefix == "@silencio":
                                state["modo"] = "off"
                                send_whatsapp_message(from_number, "Oki 👍 Alertas desactivadas.")
                                return {"status": "ok"}

                            match = re.match(r'^@(\d+):?\s*(.*)', cmd, re.DOTALL)
                            if match:
                                cid = match.group(1)
                                msg_text = match.group(2).strip()
                                human_mode = state.get("human_mode", {})
                                client_map = state.get("client_map", {})
                                target = client_map.get(cid)

                                if not target:
                                    send_whatsapp_message(from_number, f"No hay cliente con el #{cid}")
                                    return {"status": "ok"}

                                if msg_text.lower() == "@bot":
                                    human_mode.pop(target, None)
                                    state["human_mode"] = human_mode
                                    send_whatsapp_message(from_number, f"Oki 👍 Cliente #{cid} devuelto al bot.")
                                else:
                                    human_mode[target] = True
                                    state["human_mode"] = human_mode
                                    send_whatsapp_message(target, msg_text)
                                    send_whatsapp_message(from_number, f"Respondido a #{cid} + modo humano activado.")
                                return {"status": "ok"}

                    human_mode = state.get("human_mode", {})
                    if from_number in human_mode:
                        client_map = state.get("client_map", {})
                        cid = next((k for k, v in client_map.items() if v == from_number), None)
                        tag = f"[🤖 Modo humano] Cliente #{cid}: " if cid else "[🤖 Modo humano] Cliente: "
                        forward = f"{tag}{from_number}\nMensaje: {text}\n\nResponde con: @{cid}: mensaje (o @{cid}: @bot para devolver)"
                        send_whatsapp_message(ADMIN_NUMBER, forward)
                        if from_number == TESTER_NUMBER:
                            send_whatsapp_message(from_number, "[Modo humano activo - mensaje reenviado al admin]")
                        continue

                    phone_history = leer_historial(from_number)
                    client_name = get_client_name(from_number)
                    is_new = not phone_history and not client_name

                    reply = ask_agent(text, client_name, phone_history if phone_history else None)

                    if is_new:
                        send_whatsapp_message(from_number, reply)
                        phone_history.append({"role": "assistant", "content": reply})
                        guardar_historial(from_number, phone_history)
                        continue

                    guardar = re.search(r'\[GUARDAR:\s*(.+?)\s*\|\s*(.+?)\]', reply)
                    if guardar:
                        name = guardar.group(1).strip().title()
                        email = guardar.group(2).strip()
                        save_client(from_number, name, email)
                        client_name = name
                    else:
                        guardar_simple = re.search(r'\[GUARDAR:\s*(.+?)\]', reply)
                        if guardar_simple:
                            name = guardar_simple.group(1).strip().title()
                            save_client(from_number, name)
                            client_name = name
                    reply = re.sub(r'\[GUARDAR:[^\]]*\]', '', reply).strip()

                    phone_history.append({"role": "user", "content": text})
                    phone_history.append({"role": "assistant", "content": reply})
                    guardar_historial(from_number, phone_history)

                    if from_number not in ADMIN_OR_TESTER:
                        track_daily_phone(from_number)

                    is_unknown = reply.strip().startswith("[NO_SE]")

                    if is_unknown:
                        client_map = state.get("client_map", {})
                        next_id = state.get("next_id", 1)
                        existing = next((k for k, v in client_map.items() if v == from_number), None)
                        if existing:
                            cid = existing
                        else:
                            cid = str(next_id)
                            client_map[cid] = from_number
                            state["next_id"] = next_id + 1
                        state["client_map"] = client_map

                        modo = state.get("modo", "monitor")
                        if from_number not in ADMIN_OR_TESTER and modo == "monitor":
                            forward = f"⚠️ #{cid} Cliente: {from_number}\nMensaje: {text}\n\nResponde con: @{cid}: mensaje"
                            send_whatsapp_message(ADMIN_NUMBER, forward)

                        if from_number == TESTER_NUMBER:
                            send_whatsapp_message(from_number, f"[TEST] Bot no supo responder. Reenviado al admin como #{cid}.")
                    else:
                        clean_reply = reply.replace("[NO_SE]", "", 1).strip() if is_unknown else reply
                        send_whatsapp_message(from_number, clean_reply)

                        modo = state.get("modo", "monitor")
                        debe_reenviar = from_number not in ADMIN_OR_TESTER and modo == "monitor"

                        if debe_reenviar:
                            client_map = state.get("client_map", {})
                            next_id = state.get("next_id", 1)
                            existing = next((k for k, v in client_map.items() if v == from_number), None)
                            if existing:
                                cid = existing
                            else:
                                cid = str(next_id)
                                client_map[cid] = from_number
                                state["next_id"] = next_id + 1
                            state["client_map"] = client_map

                            forward = f"> #{cid} Cliente: {from_number}\nMensaje: {text}\n\nBot: {clean_reply}\n\nResponde con: @{cid}: mensaje"
                            send_whatsapp_message(ADMIN_NUMBER, forward)

    return {"status": "ok"}

@web_app.get("/health")
async def health():
    from openai import OpenAI
    sheets_ok = False
    sheets_error = "not tested"
    env_ok = False
    try:
        raw = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
        env_ok = len(raw) > 100
        raw_preview = raw[:50]
        try:
            d = json.loads(raw)
            if isinstance(d, str):
                sheets_error = f"is_str len={len(d)} first={d[:30]}"
            else:
                r = sheets_get("FAQ")
                sheets_ok = True
        except Exception as e:
            sheets_error = repr(e)[:200]
    except Exception as e:
        sheets_error = repr(e)[:200]

    try:
        client = OpenAI(api_key=os.getenv("DEEPSEEK_APIKEY"), base_url="https://api.deepseek.com")
        test = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "responde solo 'ok'"}],
            temperature=0, max_tokens=10,
        )
        deepseek_ok = bool(test.choices[0].message.content)
    except Exception as e:
        deepseek_ok = str(e)

    return {
        "status": "ok",
        "deepseek": "connected" if deepseek_ok is True else deepseek_ok,
        "sheets": {
            "configured": sheets_ok,
            "env_present": env_ok,
            "error": sheets_error,
        },
    }

_last_send = 0

def send_whatsapp_message(to: str, text: str):
    global _last_send
    elapsed = time.time() - _last_send
    if elapsed < 1.5:
        time.sleep(1.5 - elapsed)
    _last_send = time.time()

    text = text.replace("*", "").replace("_", "").replace("`", "")

    token = os.getenv("META_WABA_TOKEN")
    phone_id = os.getenv("META_WABA_PHONE_NUMBER_ID")
    base_url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }).encode()

    req = urllib.request.Request(base_url, data=body, headers=headers, method="POST")
    urllib.request.urlopen(req)

@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("liberate-deudas-secrets"),
    ],
)
@modal.asgi_app()
def fastapi_app():
    return web_app
