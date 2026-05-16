


import logging
import requests
import base64
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# GANTI 2 BARIS INI
TELEGRAM_TOKEN = "7978086768:AAG7atLCiMP4olGkPlgtDlASCKhqawkFKuY"
GEMINI_API_KEY = "AIzaSyCeEf1gO9TERPyIlagq4WKGJFZdmBy0uyU"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
SYSTEM_PROMPT = "Kamu AI assistant santai dan helpful. Bisa analisis gambar, dokumen, dan ngobrol natural. Gaya casual, pakai bahasa gaul. Selalu selesaikan jawaban dengan penuh, jangan potong di tengah."

history = {}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def call_gemini(contents, max_retries=2):
    """Call Gemini dengan retry logic"""
    for attempt in range(max_retries):
        try:
            payload = {
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": 1500,  # Kurangi dari 2048
                    "temperature": 0.85,  # Sedikit lebih rendah biar stabil
                    "topP": 0.9,
                    "topK": 40
                }
            }
            
            r = requests.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=90  # Timeout lebih lama
            )
            
            data = r.json()
            
            if "error" in data:
                error_msg = data['error'].get('message', 'Unknown error')
                return f"❌ Gemini Error: {error_msg}"
            
            if "candidates" not in data:
                return f"❌ Unexpected response: {data}"
            
            candidate = data["candidates"][0]
            
            # Check finish reason
            finish_reason = candidate.get("finishReason", "UNKNOWN")
            text = candidate["content"]["parts"][0]["text"]
            
            # Kalau text kosong, retry
            if not text.strip():
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return "❌ AI tidak ada response. Coba lagi."
            
            # Kalau di-cut off, tambah warning tapi tetap return textnya
            if finish_reason == "MAX_TOKENS":
                text += "\n\n⚠️ *(Jawaban terpotong karena panjang, coba tanya lebih spesifik)*"
            
            return text
        
        except requests.Timeout:
            if attempt < max_retries - 1:
                logging.warning(f"Timeout attempt {attempt+1}, retrying...")
                time.sleep(2)
                continue
            return "❌ Timeout — Gemini lagi slow. Coba lagi dalam 10 detik."
        
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Error attempt {attempt+1}: {str(e)}, retrying...")
                time.sleep(1)
                continue
            return f"❌ Error: {str(e)[:200]}"
    
    return "❌ Gagal setelah beberapa kali coba. Coba lagi nanti."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history[uid] = []
    await update.message.reply_text(
        "Yo! 👋 Gue AI bot santai.\n\n"
        "💬 Chat apa aja — gue balas panjang full\n"
        "📷 Kirim foto buat dianalisis\n"
        "📄 Kirim dokumen (PDF, TXT)\n"
        "/reset — reset chat\n"
        "/help — bantuan\n\n"
        "Powered by Gemini 2.5 Flash ✨"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Bantuan:*\n\n"
        "• Ketik pesan apapun → AI balas santai & lengkap\n"
        "• Kirim foto → langsung dianalisis detail\n"
        "• Kirim dokumen → dibaca & dianalisis\n"
        "• /reset → mulai percakapan baru\n\n"
        "*Pro tips:*\n"
        "• Tanya spesifik → jawab lebih akurat\n"
        "• Kalau terlalu panjang, split jadi 2 tanya",
        parse_mode="Markdown"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    history[uid] = []
    await update.message.reply_text("✅ Chat direset! Fresh start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    
    if uid not in history:
        history[uid] = []
    
    parts = []
    text_for_history = ""
    
    # TEXT
    if msg.text:
        parts.append({"text": msg.text})
        text_for_history = msg.text
    
    # PHOTO
    elif msg.photo:
        await msg.chat.send_action("typing")
        try:
            photo = msg.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            file_bytes = await file.download_as_bytearray()
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": base64.b64encode(bytes(file_bytes)).decode("utf-8")
                }
            })
            caption = msg.caption or "Analisis foto ini detail."
            parts.append({"text": caption})
            text_for_history = f"[FOTO] {caption}"
        except Exception as e:
            await msg.reply_text(f"❌ Gagal baca foto: {str(e)[:100]}")
            return
    
    # DOCUMENT
    elif msg.document:
        await msg.chat.send_action("typing")
        try:
            doc = msg.document
            mime = doc.mime_type or "application/octet-stream"
            file = await context.bot.get_file(doc.file_id)
            file_bytes = await file.download_as_bytearray()
            
            supported = ["application/pdf", "text/plain", "image/jpeg", "image/png", "image/webp"]
            if mime not in supported:
                await msg.reply_text(f"❌ Format `{mime}` belum support.\nCoba: PDF, TXT, atau gambar.", parse_mode="Markdown")
                return
            
            parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(bytes(file_bytes)).decode("utf-8")
                }
            })
            caption = msg.caption or f"Baca dan analisis file ini."
            parts.append({"text": caption})
            text_for_history = f"[DOKUMEN] {caption}"
        except Exception as e:
            await msg.reply_text(f"❌ Gagal baca dokumen: {str(e)[:100]}")
            return
    
    else:
        await msg.reply_text("Kirim teks, foto, atau dokumen ya!")
        return
    
    # Simpan ke history
    history[uid].append({"role": "user", "parts": [{"text": text_for_history}]})
    
    # Batasi history ke 8 pesan terakhir (biar tidak terlalu banyak token)
    if len(history[uid]) > 8:
        history[uid] = history[uid][-8:]
    
    await msg.chat.send_action("typing")
    
    # Build contents: history + current message dengan media
    contents = history[uid][:-1] + [{"role": "user", "parts": parts}]
    
    # Call Gemini dengan retry
    reply = call_gemini(contents)
    
    # Simpan ke history
    history[uid].append({"role": "model", "parts": [{"text": reply}]})
    
    # Send reply — split kalau > 4000 karakter
    if len(reply) > 4000:
        chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for i, chunk in enumerate(chunks):
            if i > 0:
                time.sleep(0.5)  # Delay antar chunk biar ga spam
            await msg.reply_text(chunk)
    else:
        await msg.reply_text(reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.Document.ALL,
        handle_message
    ))
    
    print("✅ Bot jalan! (Fixed version)")
    print(f"Token: {TELEGRAM_TOKEN[:20]}...")
    print(f"API Key: {GEMINI_API_KEY[:20]}...")
    print("📝 Chat response sekarang lebih stabil & lengkap")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
