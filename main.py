from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time
import json
import random

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
jogos = {}
TEMPO_POR_JOGADA = 60

with open("cartas.json", "r", encoding="utf-8") as f:
    TODAS_AS_CARTAS = json.load(f)

with open("frases_uno.json", "r", encoding="utf-8") as f:
    FRASES = json.load(f)

def escolher_frase(tipo, nome=None):
    frases = FRASES.get(tipo, [])
    if frases:
        frase = random.choice(frases)
        return frase.replace("{nome}", nome) if nome else frase
    return ""

def embaralhar_cartas():
    baralho = TODAS_AS_CARTAS * 2
    random.shuffle(baralho)
    return baralho

def distribuir_mao(baralho):
    return [baralho.pop() for _ in range(7)]

def iniciar_jogo(chat_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Entrar no jogo", callback_data="entrar_jogo"))
    bot.send_message(chat_id, "UNO 🎴! Quem quiser jogar, clique no botão abaixo para entrar:", reply_markup=keyboard)
    jogos[chat_id] = {
        "jogadores": [],
        "vez": 0,
        "jogo_iniciado": False,
        "baralho": embaralhar_cartas(),
        "carta_mesa": None,
        "ultima_acao": time.time()
    }

def proxima_vez(chat_id):
    jogo = jogos.get(chat_id)
    if not jogo or not jogo["jogadores"]:
        return

    jogo["vez"] = (jogo["vez"] + 1) % len(jogo["jogadores"])
    jogador = jogo["jogadores"][jogo["vez"]]
    jogo["ultima_acao"] = time.time()

    carta_mesa = jogo["carta_mesa"]
    bot.send_message(chat_id, f"🃏 Carta atual na mesa: {carta_mesa}\n🎯 É a vez de {jogador['nome']} jogar!")

    enviar_mao_para_jogador(jogador, chat_id)

    threading.Thread(target=aguardar_jogada, args=(chat_id, jogador['id'], jogo["vez"])).start()

def aguardar_jogada(chat_id, jogador_id, vez):
    time.sleep(TEMPO_POR_JOGADA)
    jogo = jogos.get(chat_id)
    if jogo and jogo["vez"] == vez:
        bot.send_message(chat_id, "⏰ Tempo esgotado! Próximo jogador...")
        proxima_vez(chat_id)

def enviar_mao_para_jogador(jogador, chat_id):
    keyboard = InlineKeyboardMarkup(row_width=3)
    for carta in jogador["mao"]:
        keyboard.add(InlineKeyboardButton(carta, callback_data=f"jogar|{chat_id}|{carta}"))
    bot.send_message(jogador["id"], "🎴 Suas cartas:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("jogar|"))
def jogar_carta(call):
    _, chat_id, carta = call.data.split("|")
    chat_id = int(chat_id)
    jogo = jogos.get(chat_id)
    if not jogo:
        return

    jogador = jogo["jogadores"][jogo["vez"]]
    if call.from_user.id != jogador["id"]:
        bot.answer_callback_query(call.id, "❌ Não é sua vez!")
        return

    if carta not in jogador["mao"]:
        bot.answer_callback_query(call.id, "❌ Você não tem essa carta!")
        return

    carta_mesa = jogo["carta_mesa"]
    cor_mesa, valor_mesa = carta_mesa.split(" ", 1)
    cor_jogada, valor_jogada = carta.split(" ", 1)

    if cor_mesa != cor_jogada and valor_mesa != valor_jogada and "⬛" not in carta:
        bot.answer_callback_query(call.id, "❌ Carta inválida! Jogue uma da mesma cor ou valor.")
        return

    jogador["mao"].remove(carta)
    jogo["carta_mesa"] = carta
    bot.answer_callback_query(call.id, f"✅ Você jogou {carta}!")
    bot.send_message(chat_id, f"{jogador['nome']} jogou {carta}!")

    if not jogador["mao"]:
        bot.send_message(chat_id, f"🏆 {jogador['nome']} venceu o jogo!")
        return

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

    novo_jogador = {"id": user.id, "nome": user.first_name}
    jogo["jogadores"].append(novo_jogador)
    bot.answer_callback_query(call.id, "Você entrou no jogo!")
    jogadores_nomes = ', '.join([j['nome'] for j in jogo["jogadores"]])
    bot.edit_message_text(f"Jogadores na partida: {jogadores_nomes}", chat_id, call.message.message_id)
    bot.send_message(chat_id, escolher_frase("entrada_jogador", novo_jogador["nome"]))

    if len(jogo["jogadores"]) >= 2 and not jogo["jogo_iniciado"]:
        jogo["jogo_iniciado"] = True
        for jogador in jogo["jogadores"]:
            jogador["mao"] = distribuir_mao(jogo["baralho"])
        jogo["carta_mesa"] = jogo["baralho"].pop()
        bot.send_message(chat_id, "🎲 O jogo começou!")
        proxima_vez(chat_id)

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    return "invalid", 405

@app.route("/ping", methods=["GET"])
def ping():
    return "UNO rodando com distribuição de cartas ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
