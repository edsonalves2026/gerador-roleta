import streamlit as st
import pandas as pd
import requests
import random
import time
import uuid
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURAÇÃO E CREDENCIAIS SEGURAS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Motor Avançado", layout="wide")

# Recarrega a cada 5 segundos
st_autorefresh(interval=5000, key="autoupdate_roleta")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

CILINDRO_EUROPEU = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

SETORES_ROLETA = {
    "VOISINS_DU_ZERO": [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    "TIERS_DU_CYLINDRE": [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    "ORPHELINS": [1, 20, 14, 31, 9, 17, 34, 6],
    "ZERO_SPIEL": [12, 35, 3, 26, 0, 32, 15]
}

CAMUFLADOS_BASE = {
    2: [11, 20, 29], 3: [12, 21, 30], 4: [13, 22, 31],
    5: [14, 23, 32], 6: [15, 24, 33], 7: [16, 25, 34],
    8: [17, 26, 35], 9: [18, 27, 36], 10: [1, 19, 28]
}

GRUPO_FANTASMA = {0, 2, 4, 6, 7, 11, 13, 14, 15, 17, 18, 19, 20, 21, 22, 25, 27, 28, 29, 31, 32, 34, 36}

TABELA_PUXADORES_FIXA = {
    0: [34, 14, 26, 10], 1: [36, 1, 21, 29], 2: [20, 11, 22, 25],
    3: [35, 4, 33, 6],   4: [12, 22, 2, 19],  5: [18, 6, 24, 2],
    6: [12, 20, 5, 27],  7: [16, 14, 28, 4],  8: [11, 35, 28, 4],
    9: [9, 36, 3, 19],   10: [24, 20, 28, 19],11: [2, 29, 13, 22],
    12: [32, 21, 3, 30], 13: [31, 11, 33, 15],14: [34, 30, 14, 7],
    15: [35, 32, 13, 17],16: [36, 33, 19, 7], 17: [22, 25, 16, 8],
    18: [5, 22, 6, 21],  19: [28, 21, 16, 20],20: [2, 29, 20, 10],
    21: [12, 19, 18, 30],22: [2, 17, 18, 11], 23: [32, 23, 12, 14],
    24: [22, 27, 10, 7], 25: [27, 22, 2, 7],  26: [0, 17, 29, 23],
    27: [25, 24, 13, 22],28: [19, 8, 7, 14],  29: [20, 11, 26, 2],
    30: [8, 14, 12, 36], 31: [13, 28, 11, 4], 32: [12, 23, 15, 22],
    33: [36, 13, 1, 3],  34: [0, 14, 34, 7],  35: [15, 12, 8, 9],
    36: [16, 36, 1, 9]
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
]

# ==========================================
# 2. CONFIGURAÇÃO DAS ROLETAS E ENDPOINTS
# ==========================================
URLS_ROLETAS = {
    "Cassino ao Vivo Immersive Roulette": {
        "api_endpoint": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4457-4723-a97d-f3703302d5cc/history?timezone=America%2FSao_Paulo&subject=filter&limit=200"
    },
    "Cassino ao Vivo Swedish Roulette": {
        "api_endpoint": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-10d2-b479-a28a01c6ee13/history?timezone=America%2FSao_Paulo&subject=filter&limit=200"
    }
}

def buscar_dados_roleta_url(roleta_nome):
    config = URLS_ROLETAS.get(roleta_nome, {})
    endpoint = config.get("api_endpoint", "")
    
    if not endpoint:
        return st.session_state.get("historico", [])
        
    try:
        # Token anti-cache dinâmico exigido pela API
        cb_token = f"{int(time.time() * 1000)}-{str(uuid.uuid4())[:18]}"
        url_base = endpoint.split("&_cb=")[0]
        url_com_cb = f"{url_base}&_cb={cb_token}"
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://www.tipminer.com",
            "Referer": "https://www.tipminer.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        
        res = requests.get(url_com_cb, headers=headers, timeout=8)
        
        if res.status_code == 200:
            dados = res.json()
            numeros = []
            
            # Trata respostas do tipo Array direto ou Objeto com chave 'data'
            itens = dados if isinstance(dados, list) else dados.get("data", [])
            
            for item in itens:
                if isinstance(item, dict) and "result" in item:
                    val = item.get("result")
                    if val is not None and str(val).strip().isdigit():
                        numeros.append(int(val))
            
            if numeros:
                # Inverte a lista para manter a ordem cronológica (Antigo -> Recente)
                return numeros[::-1]
            else:
                st.sidebar.warning("⚠️ Conectado, aguardando novos dados...")
        else:
            st.sidebar.error(f"⚠️ Status API: {res.status_code}")
    except Exception as e:
        st.sidebar.error(f"⚠️ Erro ao conectar na API: {e}")
        
    return st.session_state.get("historico", [])

# ==========================================
# 3. FUNÇÕES AUXILIARES & TELEGRAM
# ==========================================
def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Token ou Chat ID não configurados nos Secrets."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=5)
        return (True, "Enviado com sucesso!") if res.status_code == 200 else (False, res.text)
    except Exception as e:
        return False, str(e)

def enviar_alerta_telegram(ultimo_num, score, alvos, detalhes):
    texto_detalhes = "\n".join([f"• {d}" for d in detalhes])
    mensagem = (
        f"🚨 *SINAL CONFIRMADO - RADAR DE ROLETA*\n\n"
        f"📌 *Último Número:* `{ultimo_num}`\n"
        f"📊 *Score de Assertividade:* `{score}/5`\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"🛡️ *Proteção:* `0 (Zero)`\n\n"
        f"🔍 *Filtros Convergentes:*\n{texto_detalhes}\n\n"
        f"⚠️ *Entrada recomendada: Até 2 Gales (G1/G2)*"
    )
    return enviar_mensagem_telegram(mensagem)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    if tipo == "GREEN":
        msg = f"✅ *GREEN CONFIRMADO!* 🎉\n\n🎯 Número Bateu: `{numero}`\n📍 Momento: `{etapa}`"
    else:
        msg = f"❌ *RED / LOSS* 😔\n\n📌 Último Sorteado: `{numero}`\n⚠️ Limite de Gales atingido."
    return enviar_mensagem_telegram(msg)

def obter_vizinhos_mesa(numero):
    idx = CILINDRO_EUROPEU.index(numero)
    tamanho = len(CILINDRO_EUROPEU)
    return {
        "esq_2": CILINDRO_EUROPEU[(idx - 2) % tamanho],
        "esq_1": CILINDRO_EUROPEU[(idx - 1) % tamanho],
        "dir_1": CILINDRO_EUROPEU[(idx + 1) % tamanho],
        "dir_2": CILINDRO_EUROPEU[(idx + 2) % tamanho]
    }

def obter_dezena_invertida(numero):
    if numero < 10:
        return numero * 10 if numero * 10 <= 36 else None
    inv = int(str(numero)[::-1])
    return inv if inv <= 36 else None

def obter_camuflados(numero):
    soma = sum(int(digit) for digit in str(numero))
    if soma > 10:
        soma = sum(int(digit) for digit in str(soma))
    return CAMUFLADOS_BASE.get(soma, [])

def calcular_matriz_transicao(historico):
    if len(historico) < 2:
        return []
    ultimo = historico[-1]
    subsequentes = [historico[i+1] for i in range(len(historico) - 1) if historico[i] == ultimo]
    if not subsequentes:
        return []
    return pd.Series(subsequentes).value_counts().head(4).index.tolist()

def obter_puxadores_otimizados(numero_sorteado, historico_recentes):
    if len(historico_recentes) < 100:
        return TABELA_PUXADORES_FIXA.get(numero_sorteado, [])
    puxadores_dinamicos = calcular_matriz_transicao(historico_recentes)
    puxadores_fixos = TABELA_PUXADORES_FIXA.get(numero_sorteado, [])
    intersecao = [num for num in puxadores_dinamicos if num in puxadores_fixos]
    return intersecao if intersecao else (puxadores_dinamicos[:4] if puxadores_dinamicos else puxadores_fixos)

def checar_estrategia_fantasma(historico):
    if len(historico) >= 3 and all(n in GRUPO_FANTASMA for n in historico[-3:]):
        return {"status": "ATIVADO", "principais": [9, 19, 27]}
    return {"status": "INATIVO"}

# ==========================================
# 4. MOTOR DE SCORAGE & PROCESSAMENTO
# ==========================================
def analisar_rodada_especifica(sub_historico, houve_troca=False):
    if not sub_historico:
        return {}
    
    ultimo = sub_historico[-1]
    score = 0
    alvos = set()
    filtros_ativos_cnt = 0

    puxadores = obter_puxadores_otimizados(ultimo, sub_historico)
    if puxadores:
        score += 1
        filtros_ativos_cnt += 1
        alvos.update(puxadores[:2])

    vizinhos = obter_vizinhos_mesa(ultimo)
    score += 1
    filtros_ativos_cnt += 1
    alvos.update([vizinhos["esq_1"], vizinhos["dir_1"]])

    invertido = obter_dezena_invertida(ultimo)
    str_inversao = f"{ultimo}➔{invertido}" if invertido is not None else "-"
    if invertido is not None:
        score += 1
        filtros_ativos_cnt += 1
        alvos.add(invertido)

    fantasma = checar_estrategia_fantasma(sub_historico)
    if fantasma["status"] == "ATIVADO":
        score += 1
        filtros_ativos_cnt += 1
        alvos.update(fantasma["principais"])

    vizinhos_zero = [1, 5, 8, 11, 14, 23, 26, 32]
    if houve_troca and ultimo in vizinhos_zero:
        score += 1
        filtros_ativos_cnt += 1
        alvos.update([0, 10, 20, 30])

    esteira_14 = sub_historico[-14:]
    reincidencia = [num for num in alvos if num in esteira_14[-3:]]
    if reincidencia:
        score += 1
        filtros_ativos_cnt += 1

    setor_dom = "-"
    if len(sub_historico) >= 10:
        foco_10 = sub_historico[-10:]
        contagem = {setor: 0 for setor in SETORES_ROLETA}
        for num in foco_10:
            for setor, numeros in SETORES_ROLETA.items():
                if num in numeros:
                    contagem[setor] += 1
        setor_dom = max(contagem, key=contagem.get)
        if any(num in SETORES_ROLETA[setor_dom] for num in alvos):
            score += 1
            filtros_ativos_cnt += 1

    score_final = min(score, 5)
    alvos_ordenados = sorted(list(alvos))
    
    status_str = "AGUARDAR"
    if score_final == 3:
        status_str = "PRÉ-ALERTA"
    elif score_final >= 4:
        status_str = f"SINAL CONFIRMADO: {alvos_ordenados}"

    return {
        "ultimo": ultimo,
        "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores": str(puxadores[:2]),
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)),
        "racetrack": setor_dom,
        "inversao": str_inversao,
        "reincidencia": str(reincidencia) if reincidencia else "-",
        "confirmacoes": "🔴 " * filtros_ativos_cnt,
        "score": f"{score_final}/5",
        "status": status_str,
        "alvos": alvos_ordenados,
        "score_num": score_final
    }

# ==========================================
# 5. INTERFACE STREAMLIT
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

if "historico" not in st.session_state:
    st.session_state.historico = []

if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0
    st.session_state.ultimo_resultado = None

st.sidebar.header("🕹️ Painel de Operação")

modo_operacao = st.sidebar.selectbox(
    "🌐 Modo de Operação:",
    ["On-line (Captura Automática)", "Off-line (Digitação Manual)"]
)

roleta_selecionada = st.sidebar.selectbox(
    "🎰 Selecionar Roleta:",
    list(URLS_ROLETAS.keys())
)

st.sidebar.markdown("---")

def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual
