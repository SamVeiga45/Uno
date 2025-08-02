import telebot

TOKEN = "7091777737:AAFP5a7WRPumgzN8z7bhuQLZH3g05z53xsQ"
bot = telebot.TeleBot(TOKEN)

CARTAS = [
    "🟥 0", "🟥 1", "🟥 2", "🟥 3", "🟥 4", "🟥 5", "🟥 6", "🟥 7", "🟥 8", "🟥 9",
    "🟥 +2", "🟥 ↩️", "🟥 ⏭️",
    "🟦 0", "🟦 1", "🟦 2", "🟦 3", "🟦 4", "🟦 5", "🟦 6", "🟦 7", "🟦 8", "🟦 9",
    "🟦 +2", "🟦 ↩️", "🟦 ⏭️",
    "🟨 0", "🟨 1", "🟨 2", "🟨 3", "🟨 4", "🟨 5", "🟨 6", "🟨 7", "🟨 8", "🟨 9",
    "🟨 +2", "🟨 ↩️", "🟨 ⏭️",
    "🟩 0", "🟩 1", "🟩 2", "🟩 3", "🟩 4", "🟩 5", "🟩 6", "🟩 7", "🟩 8", "🟩 9",
    "🟩 +2", "🟩 ↩️", "🟩 ⏭️",
    "⬛ +4", "⬛ 🎨"
]

@bot.message_handler(commands=["start"])
def start(msg):
    for i, carta in enumerate(CARTAS):
        bot.send_message(msg.chat.id, f"Envie o sticker da carta: {carta}")
        break  # espera o usuário enviar o primeiro antes de continuar

index = 0
STICKER_IDS = {}

@bot.message_handler(content_types=["sticker"])
def receber_sticker(msg):
    global index
    carta = CARTAS[index]
    file_id = msg.sticker.file_id
    STICKER_IDS[carta] = file_id
    print(f'"{carta}": "{file_id}",')
    index += 1

    if index < len(CARTAS):
        bot.send_message(msg.chat.id, f"Agora envie o sticker da carta: {CARTAS[index]}")
    else:
        bot.send_message(msg.chat.id, "✅ Pronto! Todos os stickers foram coletados.")

bot.polling()
