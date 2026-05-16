import telebot
import requests

# TOKEN BOT TELEGRAM
TELEGRAM_TOKEN = "TELEGRAM TOKEN"

# API KEY GROQ
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(func=lambda message: True)
def chat(message):
    user_text = message.text

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Kamu adalah teman chat Telegram yang santai dan natural. "
                    "Balas singkat seperti manusia asli. "
                    "Jangan terlalu formal dan jangan memberi jawaban panjang seperti AI. "
                    "Gunakan bahasa sehari-hari yang nyaman. "
                    "Kadang boleh pakai haha, wkwk, atau emoji seperlunya. "
                    "Kalau ditanya model AI, jawab bahwa kamu memakai llama-3.3-70b-versatile dari Groq API."
                )
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        "temperature": 0.9,
        "max_tokens": 200
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        result = response.json()

        reply = result["choices"][0]["message"]["content"]

        bot.reply_to(message, reply)

    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

print("Bot berjalan...")
bot.infinity_polling()
