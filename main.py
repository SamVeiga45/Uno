import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import threading
import time

API_TOKEN = '7091777737:AAFP5a7WRPumgzN8z7bhuQLZH3g05z53xsQ'
bot = telebot.TeleBot(API_TOKEN)

partidas = {}  # {chat_id: {'jogadores': [id1, id2...], 'baralho': [], 'mesa': [], 'turno': 0, 'ultimo_movimento': timestamp}}
TEMPO_MAXIMO_POR_JOGADA = 60  # segundos

CORES = ['🔴', '🟡', '🟢', '🔵']
VALORES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '⏩', '🔄', '+2']
ESPECIAIS = ['+4', '🎨']


def criar_baralho():
    baralho = []
    for cor in CORES:
        for valor in VALORES:
            baralho.append(f'{cor} {valor}')
            baralho.append(f'{cor} {valor}')
    for especial in ESPECIAIS:
        baralho += [especial] * 4
    random.shuffle(baralho)
    return baralho


def distribuir_cartas(baralho):
    return [baralho.pop() for _ in range(7)]


def jogador_atual(partida):
    return partida['jogadores'][partida['turno'] % len(partida['jogadores'])]


def avancar_turno(chat_id):
    partida = partidas[chat_id]
    partida['turno'] += 1
    partida['ultimo_movimento'] = time.time()
    checar_tempo(chat_id)
    enviar_mesa(chat_id)


def carta_valida(carta, carta_mesa):
    if carta in ['+4', '🎨']:
        return True
    if not carta_mesa:
        return True
    cor1, val1 = carta.split()
    cor2, val2 = carta_mesa.split()
    return cor1 == cor2 or val1 == val2


def enviar_mesa(chat_id):
    partida = partidas[chat_id]
    mesa = partida['mesa'][-1] if partida['mesa'] else '❓'
    jogador = jogador_atual(partida)
    mao = partida[f'mao_{jogador}']
    markup = InlineKeyboardMarkup()
    for carta in mao:
        if carta_valida(carta, mesa):
            markup.add(InlineKeyboardButton(carta, callback_data=f'jogar:{carta}'))
    markup.add(InlineKeyboardButton('Comprar carta', callback_data='comprar'))
    bot.send_message(chat_id, f'🃏 Carta na mesa: {mesa}\n🎯 Vez de <a href="tg://user?id={jogador}">{jogador}</a>', parse_mode="HTML", reply_markup=markup)


def checar_tempo(chat_id):
    def loop():
        while True:
            if chat_id in partidas:
                partida = partidas[chat_id]
                tempo = time.time() - partida['ultimo_movimento']
                if tempo > TEMPO_MAXIMO_POR_JOGADA:
                    jogador = jogador_atual(partida)
                    bot.send_message(chat_id, f"⏰ <a href='tg://user?id={jogador}'>Perdeu a vez!</a>", parse_mode="HTML")
                    avancar_turno(chat_id)
            time.sleep(5)

    threading.Thread(target=loop, daemon=True).start()


@bot.message_handler(commands=['uno'])
def iniciar_jogo(m):
    chat_id = m.chat.id
    partidas[chat_id] = {
        'jogadores': [m.from_user.id],
        'baralho': criar_baralho(),
        'mesa': [],
        'turno': 0,
        'ultimo_movimento': time.time()
    }
    partidas[chat_id][f'mao_{m.from_user.id}'] = distribuir_cartas(partidas[chat_id]['baralho'])

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton('Entrar no jogo', callback_data='entrar'))
    markup.add(InlineKeyboardButton('Começar', callback_data='comecar'))
    bot.send_message(chat_id, '🎮 Novo jogo de UNO iniciado! Clique para entrar.', reply_markup=markup)
    checar_tempo(chat_id)


@bot.callback_query_handler(func=lambda call: True)
def responder_botoes(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    partida = partidas.get(chat_id)
    if not partida:
        return

    if call.data == 'entrar':
        if user_id not in partida['jogadores']:
            partida['jogadores'].append(user_id)
            partida[f'mao_{user_id}'] = distribuir_cartas(partida['baralho'])
            bot.answer_callback_query(call.id, 'Você entrou no jogo!')

    elif call.data == 'comecar':
        if len(partida['jogadores']) < 2:
            bot.answer_callback_query(call.id, 'Mínimo 2 jogadores.')
        else:
            partida['mesa'].append(partida['baralho'].pop())
            enviar_mesa(chat_id)

    elif call.data.startswith('jogar:'):
        if jogador_atual(partida) != user_id:
            bot.answer_callback_query(call.id, 'Não é sua vez.')
            return
        carta = call.data.split(':')[1]
        mao = partida[f'mao_{user_id}']
        if carta in mao and carta_valida(carta, partida['mesa'][-1]):
            mao.remove(carta)
            partida['mesa'].append(carta)
            if not mao:
                bot.send_message(chat_id, f'🏆 <a href="tg://user?id={user_id}">VENCEU!</a>', parse_mode="HTML")
                del partidas[chat_id]
                return
            avancar_turno(chat_id)
        else:
            bot.answer_callback_query(call.id, 'Carta inválida.')

    elif call.data == 'comprar':
        if jogador_atual(partida) != user_id:
            bot.answer_callback_query(call.id, 'Não é sua vez.')
            return
        carta = partida['baralho'].pop()
        partida[f'mao_{user_id}'].append(carta)
        bot.answer_callback_query(call.id, f'Você comprou: {carta}')
        avancar_turno(chat_id)


bot.infinity_polling()
