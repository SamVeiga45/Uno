from flask import Flask, request
import telebot
import os
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Token do bot
TOKEN = os.getenv("BOT_TOKEN") or "7091777737:AAFP5a7WRPumgzN8z7bhuQLZH3g05z53xsQ"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Variáveis de controle
PARTIDA_ATIVA = False
JOGADORES = []
MAX_JOGADORES = 10
ID_GRUPO = -1001234567890  # ⬅️ Troque para o ID real do grupo

# Cria teclado para entrar
def teclado_entrada():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ Entrar no jogo", callback_data="entrar"))
    return markup

# Cria teclado para iniciar
def teclado_iniciar():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎲 Iniciar Partida", callback_data="comecar"))
    return markup

# Comando para iniciar o UNO
@bot.message_handler(commands=["uno"])
def iniciar_uno(m):
    global PARTIDA_ATIVA, JOGADORES
    if m.chat.id != ID_GRUPO:
        bot.reply_to(m, "❌ Este comando só pode ser usado no grupo principal.")
        return

    if PARTIDA_ATIVA:
        bot.send_message(m.chat.id, "⚠️ Uma partida já está ativa.")
        return

    PARTIDA_ATIVA = True
    JOGADORES = []
    bot.send_message(m.chat.id, "🎮 Partida de UNO iniciada!\nClique para entrar:", reply_markup=teclado_entrada())

# Callback dos botões
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global JOGADORES, PARTIDA_ATIVA

    if call.data == "entrar":
        jogador = call.from_user
        if jogador.id in [j["id"] for j in JOGADORES]:
            bot.answer_callback_query(call.id, "❗️Você já está na partida.")
            return

        if len(JOGADORES) >= MAX_JOGADORES:
            bot.answer_callback_query(call.id, "🚫 Limite de jogadores atingido.")
            return

        JOGADORES.append({
            "id": jogador.id,
            "nome": jogador.first_name,
            "username": jogador.username or ""
        })

        texto = "🧑‍🤝‍🧑 Jogadores até agora:\n"
        for j in JOGADORES:
            nome = f"@{j['username']}" if j["username"] else j["nome"]
            texto += f"• {nome}\n"

        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text=texto + "\nClique para entrar:",
                              reply_markup=teclado_entrada())

        if len(JOGADORES) >= 2:
            bot.send_message(call.message.chat.id, "✅ Pronto para começar?", reply_markup=teclado_iniciar())

    elif call.data == "comecar":
        if len(JOGADORES) < 2:
            bot.answer_callback_query(call.id, "⚠️ Precisa de pelo menos 2 jogadores.")
            return

        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text="🚨 Partida começando... Embaralhando cartas!")

        iniciar_partida(call.message.chat.id)

# Lógica inicial da partida (temporário)
def iniciar_partida(chat_id):
    bot.send_message(chat_id, "🃏 Ainda vamos implementar as cartas e rodadas...")

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@app.route("/")
def index():
    return "UNO Bot rodando!"

# Iniciar servidor Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
