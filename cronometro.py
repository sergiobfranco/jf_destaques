from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def obter_timestamp_brasilia():
    """
    Retorna o timestamp atual no fuso horário de Brasília como string.
    Formato: 'YYYY-MM-DD HH:MM:SS'
    """
    tz_brasilia = ZoneInfo("America/Sao_Paulo")
    agora = datetime.now(tz_brasilia)
    return agora.strftime("%Y-%m-%d %H:%M:%S")

def calcular_tempo_decorrido(timestamp_str):
    """
    Recebe um timestamp como string no formato 'YYYY-MM-DD HH:MM:SS',
    considera que ele esteja no fuso horário de Brasília,
    e retorna a diferença com o momento atual (também em Brasília).
    """
    tz_brasilia = ZoneInfo("America/Sao_Paulo")

    # Converte a string para datetime, assumindo fuso de Brasília
    dt_entrada = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_brasilia)

    # Data/hora atual no mesmo fuso
    dt_atual = datetime.now(tz_brasilia)

    # Calcula a diferença
    delta = dt_atual - dt_entrada

    segundos = delta.total_seconds()
    minutos = segundos / 60
    horas = minutos / 60

    return {
        "segundos": segundos,
        "minutos": minutos,
        "horas": horas
    }
