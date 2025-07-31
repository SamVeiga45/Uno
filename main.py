from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time

API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# Armazena dados dos jogos ativos
jogos = {}

# Tempo máximo por jogador (em segundos)
TEMPO_POR_JOGADA = 60

def iniciar_jogo(chat_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Entrar no jogo", callback_data="entrar_jogo"))
    bot.send_message(chat_id, "UNO 🎴! Quem quiser jogar, clique no botão abaixo para entrar:", reply_markup=keyboard)
    jogos[chat_id] = {
        "jogadores": [],
        "vez": 0,
        "jogo_iniciado": False,
        "ultima_acao": time.time()
    }

def proxima_vez(chat_id):
    jogo = jogos.get(chat_id)
    if not jogo or not jogo["jogadores"]:
        return

    jogo["vez"] = (jogo["vez"] + 1) % len(jogo["jogadores"])
    jogador = jogo["jogadores"][jogo["vez"]]
    bot.send_message(chat_id, f"É a vez de {jogador['nome']} jogar! Você tem {TEMPO_POR_JOGADA} segundos.")

    # Inicia o temporizador da jogada
    threading.Thread(target=aguardar_jogada, args=(chat_id, jogador['id'], jogo["vez"])).start()

def aguardar_jogada(chat_id, jogador_id, vez):
    time.sleep(TEMPO_POR_JOGADA)
    jogo = jogos.get(chat_id)
    if jogo and jogo["vez"] == vez:
        bot.send_message(chat_id, "⏰ Tempo esgotado! Próximo jogador...")
        proxima_vez(chat_id)

@bot.message_handler(commands=["uno"])
def handle_uno(msg):
    chat_id = msg.chat.id
    iniciar_jogo(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == "entrar_jogo")
def callback_entrar_jogo(call):
    chat_id = call.message.chat.id
    user = call.from_user
    jogo = jogos.get(chat_id)

    if any(j['id'] == user.id for j in jogo["jogadores"]):
        bot.answer_callback_query(call.id, "Você já entrou no jogo.")
        return

    jogo["jogadores"].append({"id": user.id, "nome": user.first_name})
    bot.answer_callback_query(call.id, "Você entrou no jogo!")

    jogadores_nomes = ', '.join([j['nome'] for j in jogo["jogadores"]])
    bot.edit_message_text(f"Jogadores na partida: {jogadores_nomes}", chat_id, call.message.message_id)

    # Iniciar o jogo automaticamente com 2+ jogadores
    if len(jogo["jogadores"]) >= 2 and not jogo["jogo_iniciado"]:
        jogo["jogo_iniciado"] = True
        bot.send_message(chat_id, "Jogo iniciado! 🎮")
        proxima_vez(chat_id)

# Webhook
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'invalid', 405

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
