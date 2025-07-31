from flask import Flask, request
import telebot
import json
import random
import os
import datetime
import pytz

TOKEN = os.getenv("BOT_TOKEN") or "7091777737:AAFP5a7WRPumgzN8z7bhuQLZH3g05z53xsQ"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÃO DE HORÁRIO
fuso_brasilia = pytz.timezone("America/Sao_Paulo")

# LISTAS DE JOGO
jogadores = []
cartas_jogadores = {}
jogo_ativo = False
chat_id_partida = None

# CARREGAR CARTAS
def carregar_cartas():
    with open("numeros.json", "r", encoding="utf-8") as f1:
        numeros = json.load(f1)
    with open("acoes.json", "r", encoding="utf-8") as f2:
        acoes = json.load(f2)
    with open("especiais.json", "r", encoding="utf-8") as f3:
        especiais = json.load(f3)
    return numeros + acoes + especiais

# EMBARALHAR E DISTRIBUIR
def distribuir_cartas(jogadores):
    baralho = carregar_cartas()
    random.shuffle(baralho)
    mao = {}
    for jogador in jogadores:
        mao[jogador] = [baralho.pop() for _ in range(7)]
    return mao, baralho

# VERIFICAR HORÁRIO PERMITIDO
def horario_valido():
    agora = datetime.datetime.now(fuso_brasilia).time()
    return agora >= datetime.time(6, 0) and agora <= datetime.time(23, 59)

# COMANDOS DO BOT
@bot.message_handler(commands=["startuno"])
def startuno(message):
    global jogadores, cartas_jogadores, jogo_ativo, chat_id_partida

    if not horario_valido():
        bot.reply_to(message, "⏰ O jogo só pode ser iniciado entre 6h e 00h (horário de Brasília).")
        return

    if jogo_ativo:
        bot.reply_to(message, "🚨 Uma partida já está em andamento!")
        return

    jogadores = []
    cartas_jogadores = {}
    jogo_ativo = True
    chat_id_partida = message.chat.id
    bot.reply_to(message, "🎮 Partida de UNO criada!\nJogadores, enviem /entrar para participar.")

@bot.message_handler(commands=["entrar"])
def entrar(message):
    global jogadores
    user_id = message.from_user.id
    nome = message.from_user.first_name

    if not jogo_ativo:
        bot.reply_to(message, "⚠️ Nenhuma partida ativa. Use /startuno para iniciar.")
        return

    if user_id in jogadores:
        bot.reply_to(message, "❗ Você já entrou na partida.")
        return

    jogadores.append(user_id)
    bot.send_message(chat_id_partida, f"✅ {nome} entrou na partida.")

@bot.message_handler(commands=["iniciar"])
def iniciar(message):
    global cartas_jogadores, baralho

    if message.chat.id != chat_id_partida:
        return

    if not jogadores:
        bot.reply_to(message, "⚠️ Nenhum jogador entrou ainda.")
        return

    cartas_jogadores, baralho = distribuir_cartas(jogadores)

    for jogador_id in jogadores:
        cartas = cartas_jogadores[jogador_id]
        texto = "🃏 Suas cartas:\n" + "\n".join([f"- {carta}" for carta in cartas])
        try:
            bot.send_message(jogador_id, texto)
        except:
            bot.send_message(chat_id_partida, f"⚠️ Não consegui enviar as cartas para <a href='tg://user?id={jogador_id}'>esse jogador</a>. Verifique se ele iniciou o bot no privado.", parse_mode="HTML")

    bot.send_message(chat_id_partida, "🎲 Cartas distribuídas! Em breve a lógica de turnos será ativada.")

# WEBHOOK
@app.route('/', methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK"

@app.route('/')
def home():
    return "UNO bot rodando."

# INICIAR
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
