from datetime import datetime
import pytz
import json
import random

def horario_disponivel():
    from config import HORARIO_INICIO, HORARIO_FIM
    agora = datetime.now(pytz.timezone("America/Sao_Paulo"))
    return HORARIO_INICIO <= agora.hour < HORARIO_FIM

def embaralhar_cartas():
    with open("cartas.json", "r", encoding="utf-8") as f:
        cartas = json.load(f)
    random.shuffle(cartas)
    return cartas
