from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import threading
import time
import json
import random
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ARQ_PARTIDAS = "partidas_ativas.json"
ARQ_JOGADORES = "jogadores.json"
ARQ_CONFIG = "config.json"

TEMPO_POR_JOGADA = 60
MAX_JOGADORES = 10

# === Lê config.json ===
if os.path.exists(ARQ_CONFIG):
    with open(ARQ_CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        TEMPO_POR_JOGADA = cfg.get("tempo_por_jogada", 60)
        MAX_JOGADORES = cfg.get("max_jogadores", 10)

jogos = {}

with open("cartas.json", "r", encoding="utf-8") as f:
    TODAS_AS_CARTAS = json.load(f)

def salvar_partidas():
    with open(ARQ_PARTIDAS, "w", encoding="utf-8") as f:
        json.dump(jogos, f, ensure_ascii=False, indent=2)

def salvar_jogadores(dados):
    with open(ARQ_JOGADORES, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_ranking():
    hoje = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(ARQ_JOGADORES):
        with open(ARQ_JOGADORES, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # Limpa dados antigos
        for jogador in dados.values():
            jogador["jogos_hoje"] = {k: v for k, v in jogador["jogos_hoje"].items() if k == hoje}
        salvar_jogadores(dados)
        return dados
    return {}

def atualizar_ranking(nome):
    hoje = datetime.now().strftime("%Y-%m-%d")
    ranking = carregar_ranking()
    if nome not in ranking:
        ranking[nome] = {"vitorias": 0, "jogos_hoje": {}}
    ranking[nome]["vitorias"] += 1
    ranking[nome]["jogos_hoje"][hoje] = ranking[nome]["jogos_hoje"].get(hoje, 0) + 1
    salvar_jogadores(ranking)

@bot.message_handler(commands=["ranking"])
def cmd_ranking(msg):
    ranking = carregar_ranking()
    top = sorted(ranking.items(), key=lambda x: x[1]["vitorias"], reverse=True)[:3]
    if not top:
        bot.send_message(msg.chat.id, "📊 Ainda não há vitórias registradas.")
        return
    texto = "🏆 Ranking dos melhores jogadores:\\n"
    for i, (nome, dados) in enumerate(top, 1):
        texto += f"{i}º {nome} – {dados['vitorias']} vitórias\\n"
    bot.send_message(msg.chat.id, texto)
def embaralhar_cartas():
    baralho = TODAS_AS_CARTAS * 2
    random.shuffle(baralho)
    return baralho

def distribuir_mao(baralho):
    return [baralho.pop() for _ in range(7)]

def legenda_acao(carta):
    if not carta:
        return ""
    partes = carta.split(" ")
    if len(partes) < 2:
        return ""
    simbolo = partes[1]
    acoes = {
        "+2": "comprar 2",
        "+4": "comprar 4",
        "↩️": "inverter",
        "⏭️": "pular",
        "🎨": "escolher cor"
    }
    return acoes.get(simbolo, simbolo)  # Se for número, só repete

def legenda_cartao(carta):
    if not carta:
        return "Nenhuma carta na mesa."
    
    cor_emoji, valor = carta.split(" ", 1)

    cores = {
        "🟥": "vermelha",
        "🟦": "azul",
        "🟨": "amarela",
        "🟩": "verde",
        "⬛": "preta"
    }
    cor_nome = cores.get(cor_emoji, "desconhecida")

    if cor_emoji == "⬛":
        if "+4" in valor:
            return "🤹 curinga +4 — escolha a nova cor e o próximo jogador comprará 4 cartas."
        elif "🎨" in valor:
            return "🤹 curinga de cor — escolha a nova cor para continuar o jogo."

    if valor == "+2":
        return f"Carta {cor_nome} +2 — o próximo jogador comprará 2 cartas ou empilhar outro +2."
    elif valor == "↩️":
        return f"Carta {cor_nome} de inverter — a ordem do jogo será invertida."
    elif valor == "⏭️":
        return f"Carta {cor_nome} de pular — o próximo jogador perderá a vez."

    return f"Carta {cor_nome} {valor} — jogue uma carta {cor_nome} ou outro {valor} de qualquer cor."

def iniciar_jogo(chat_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Entrar no Jogo", callback_data="entrar_jogo"))
    bot.send_message(chat_id, "JOGO DO UNO 🎴", reply_markup=keyboard)
    jogos[str(chat_id)] = {
        "jogadores": [],
        "vez": 0,
        "direcao": 1,
        "jogo_iniciado": False,
        "baralho": embaralhar_cartas(),
        "carta_mesa": None,
        "esperando_cor": None,
        "ultima_acao": time.time()
    }
    salvar_partidas()

def proxima_vez(chat_id):
    jogo = jogos.get(str(chat_id))
    if not jogo or not jogo["jogadores"]:
        return
    jogo["vez"] = (jogo["vez"] + jogo["direcao"]) % len(jogo["jogadores"])
    jogador = jogo["jogadores"][jogo["vez"]]
    jogo["ultima_acao"] = time.time()
    salvar_partidas()
    carta = jogo["carta_mesa"]
    bot.send_message(
        chat_id,
        f"🃏 Carta atual: {carta}\n\n{legenda_cartao(carta)}\n\n🎮 Sua vez: {jogador['nome']}"
    )

    enviar_mao(jogador, chat_id)
    threading.Thread(target=aguardar_jogada, args=(chat_id, jogador["nome"], jogo["vez"])).start()

def aguardar_jogada(chat_id, nome, vez):
    time.sleep(TEMPO_POR_JOGADA)
    jogo = jogos.get(str(chat_id))
    if jogo and jogo["vez"] == vez and not jogo.get("esperando_cor"):
        bot.send_message(chat_id, "⏰ Tempo esgotado! Próximo jogador...")
        proxima_vez(chat_id)

def enviar_mao(jogador, chat_id):
    jogo = jogos[str(chat_id)]
    keyboard = InlineKeyboardMarkup(row_width=3)
    jogadas_validas = 0
    for carta in jogador["mao"]:
        if carta_valida(carta, jogo["carta_mesa"], jogador["mao"]):
            jogadas_validas += 1
            keyboard.add(InlineKeyboardButton(carta, callback_data=f"jogar|{chat_id}|{carta}"))
    if jogadas_validas == 0:
        keyboard.add(InlineKeyboardButton("🛒 Comprar Carta", callback_data=f"comprar|{chat_id}"))
    msg = bot.send_message(jogador["id"], "🎴 Suas cartas:", reply_markup=keyboard)
    jogador.setdefault("mensagens_para_apagar", []).append(msg.message_id)
    jogador["ultima_msg_id"] = msg.message_id  # para limpar após jogar

def carta_valida(carta, mesa, mao):
    if not mesa:
        return True
    cor_mesa, val_mesa = mesa.split(" ", 1)
    cor_carta, val_carta = carta.split(" ", 1)
    if carta.startswith("⬛ +4"):
        for c in mao:
            if c != carta and carta_valida(c, mesa, [x for x in mao if x != carta]):
                return False
        return True
    return cor_carta == cor_mesa or val_carta == val_mesa or "⬛" in carta

@bot.message_handler(commands=["stop"])
def cmd_stop(msg):
    chat_id = str(msg.chat.id)
    if chat_id in jogos:
        del jogos[chat_id]
        salvar_partidas()
        bot.send_message(msg.chat.id, "🚫 A partida foi encerrada manualmente.")
    else:
        bot.send_message(msg.chat.id, "❌ Nenhuma partida ativa para encerrar.")

@bot.message_handler(commands=["uno"])
def cmd_uno(msg):
    iniciar_jogo(msg.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "entrar_jogo")
def entrar_jogo(call):
    chat_id = str(call.message.chat.id)
    user = call.from_user
    jogo = jogos.get(chat_id)
    if any(j["id"] == user.id for j in jogo["jogadores"]):
        bot.answer_callback_query(call.id, "Você já entrou.")
        return
    if len(jogo["jogadores"]) >= MAX_JOGADORES:
        bot.answer_callback_query(call.id, "Jogo cheio!")
        return
    jogador = {"id": user.id, "nome": user.first_name}
    jogo["jogadores"].append(jogador)
    bot.answer_callback_query(call.id, "Entrou no jogo!")
    bot.send_message(
    chat_id,
    "Jogadores: " + ", ".join(j["nome"] for j in jogo["jogadores"])
    )
    if len(jogo["jogadores"]) >= 1 and not jogo["jogo_iniciado"]: #TROCAR PARA (2) APÓS TESTES
        jogo["jogo_iniciado"] = True
        for j in jogo["jogadores"]:
            j["mao"] = distribuir_mao(jogo["baralho"])

        jogo["carta_mesa"] = jogo["baralho"].pop()
        salvar_partidas()

        bot.send_message(chat_id, "🎲 Jogo iniciado!")

        # ⬇️ Enviar as mãos para todos os jogadores que clicaram em "Entrar no jogo"
        for j in jogo["jogadores"]:
            enviar_mao(j, chat_id)

        # Agora sim inicia a rodada
        proxima_vez(chat_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("jogar|"))
def jogar_carta(call):
    _, chat_id, carta = call.data.split("|")
    chat_id = str(chat_id)
    jogo = jogos.get(chat_id)
    jogador = jogo["jogadores"][jogo["vez"]]
    if call.from_user.id != jogador["id"]:
        bot.answer_callback_query(call.id, "❌ Não é sua vez!")
        return
    if carta not in jogador["mao"] or not carta_valida(carta, jogo["carta_mesa"], jogador["mao"]):
        bot.answer_callback_query(call.id, "❌ Carta inválida!")
        return
    jogador["mao"].remove(carta)
    try:
        bot.delete_message(jogador["id"], jogador.get("ultima_msg_id"))
    except:
        pass
    jogo["carta_mesa"] = carta
    bot.answer_callback_query(call.id, f"✅ Jogou {carta}")
    bot.send_message(chat_id, f"{jogador['nome']} jogou {carta}")
    if not jogador["mao"]:
        bot.send_message(chat_id, f"🏆 {jogador['nome']} venceu o jogo!")
        atualizar_ranking(jogador["nome"])
        fim_de_jogo(chat_id)
        return
    salvar_partidas()
    proxima_vez(chat_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("comprar|"))
def comprar_carta(call):
    _, chat_id = call.data.split("|")
    chat_id = str(chat_id)
    jogo = jogos[chat_id]
    jogador = jogo["jogadores"][jogo["vez"]]
    nova = jogo["baralho"].pop()
    jogador["mao"].append(nova)
    bot.answer_callback_query(call.id, f"Você comprou: {nova}")
    if carta_valida(nova, jogo["carta_mesa"], jogador["mao"]):
        enviar_mao(jogador, int(chat_id))
    else:
        bot.send_message(jogador["id"], "⛔ Não pode jogar. Sua vez acabou.")
        salvar_partidas()
        proxima_vez(int(chat_id))

def fim_de_jogo(chat_id):
    chat_id = str(chat_id)
    if chat_id in jogos:
        # Limpa todas as mensagens privadas dos jogadores
        for jogador in jogos[chat_id]["jogadores"]:
            for mid in jogador.get("mensagens_para_apagar", []):
                try:
                    bot.delete_message(jogador["id"], mid)
                except:
                    pass

        jogos.pop(chat_id)
        # Opcional: limpar variável se quiser
    for jogador in jogos[chat_id]["jogadores"]:
        jogador["mensagens_para_apagar"] = []
        salvar_partidas()
        bot.send_message(int(chat_id), "Partida encerrada.")
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🎮 Novo jogo", callback_data="novo_jogo"))
        bot.send_message(int(chat_id), "Clique para começar uma nova partida:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "novo_jogo")
def novo_jogo(call):
    iniciar_jogo(call.message.chat.id)

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = telebot.types.Update.de_json(request.data.decode("utf-8"))
        bot.process_new_updates([update])
        return "", 200
    return "invalid", 400

@app.route("/ping")
def ping():
    return "UNO com ranking, config e limpeza diária ✅", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
