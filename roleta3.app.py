import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 0. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Sniper", page_icon="🎲", layout="wide")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# 1. MATRIZ DE POSICIONAMENTO E CONSTANTES
# ==========================================
ROULETTE_CYLINDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

NUMEROS_VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

SETORES_ROLETA = {
    "VOISINS_DU_ZERO": [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    "TIERS_DU_CYLINDRE": [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    "ORPHELINS": [1, 20, 14, 31, 9, 17, 34, 6],
    "ZERO_SPIEL": [12, 35, 3, 26, 0, 32, 15]
}

CAMUFLADOS_BASE = {
    1: [10, 19, 28], 2: [11, 20, 29], 3: [12, 21, 30], 4: [13, 22, 31],
    5: [14, 23, 32], 6: [15, 24, 33], 7: [16, 25, 34], 8: [17, 26, 35],
    9: [18, 27, 36], 10: [1, 19, 28]
}

GRUPO_FANTASMA = {0, 2, 4, 6, 7, 11, 13, 14, 15, 17, 18, 19, 20, 21, 22, 25, 27, 28, 29, 31, 32, 34, 36}

GRUPO_OCULTO_BRK = {
    1: [1, 10, 19, 28, 34],
    2: [2, 11, 20, 29, 24, 35],
    3: [3, 12, 21, 30, 36, 14, 25],
    4: [4, 13, 22, 31, 26, 15],
    5: [5, 14, 23, 32, 16, 27],
    6: [6, 15, 24, 33, 17],
    7: [7, 16, 25, 34, 14, 29],
    8: [8, 17, 26, 35, 19],
    9: [9, 18, 27, 36],
    10: [0, 5, 20, 30, 19, 28]
}

TABELA_PUXADORES_FIXA = {
    0:  [33, 11, 21, 34], 1:  [20, 22, 32, 12], 2:  [36, 5, 7, 33],
    3:  [0, 7, 20, 10],   4:  [5, 10, 7, 3],    5:  [3, 6, 9, 27],
    6:  [7, 4, 17, 27],   7:  [8, 4, 18, 28],   8:  [3, 6, 19, 29],
    9:  [4, 0, 10, 20],   10: [1, 2, 18, 28],   11: [3, 6, 24, 31],
    12: [31, 4, 33, 35],  13: [5, 3, 7, 34],    14: [30, 6, 4, 0],
    15: [21, 7, 8, 19],   16: [20, 8, 6, 7],    17: [11, 7, 9, 28],
    18: [10, 8, 20, 29],  19: [4, 2, 17, 30],   20: [16, 3, 12, 27],
    21: [24, 4, 26, 2],   22: [5, 26, 32, 21],  23: [6, 2, 22, 26],
    24: [5, 7, 21, 29],   25: [8, 4, 13, 24],   26: [9, 5, 29, 17],
    27: [10, 6, 14, 7],   28: [11, 7, 14, 30],  29: [0, 15, 3, 29],
    30: [13, 33, 35, 0],  31: [34, 31, 3, 0],   32: [6, 30, 1, 0],
    33: [7, 32, 1, 14],   34: [5, 2, 31, 33],   35: [6, 9, 3, 0],
    36: [0, 0, 0, 0]
}

URLS_ROLETAS = {
    "XXXtreme Lightning": "https://api.core.public.tipminer.com/v1/roulette/rounds/e640b7c7-aaba-4ffa-a678-6b6872898162/history?limit=200",
    "Roleta Brasileira": "https://api.core.public.tipminer.com/v1/roulette/rounds/45d12dd3-8f85-4ab2-8c86-4eaea7967e10/history?limit=200",
    "Immersive Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4452-4723-a97d-f3703302d5cc/history?limit=200",
    "Swedish Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-40d2-b479-a28a01c6ee13/history?limit=200"
}

# ==========================================
# 2. FUNÇÕES AUXILIARES E API
# ==========================================
def obter_grupo_brk(numero):
    for grupo, numeros in GRUPO_OCULTO_BRK.items():
        if numero in numeros:
            return str(sorted(numeros))
    return "-"

def obter_vizinhos_mesa(num):
    idx = ROULETTE_CYLINDER.index(num)
    n = len(ROULETTE_CYLINDER)
    return {
        "esq_2": ROULETTE_CYLINDER[(idx - 2) % n],
        "esq_1": ROULETTE_CYLINDER[(idx - 1) % n],
        "dir_1": ROULETTE_CYLINDER[(idx + 1) % n],
        "dir_2": ROULETTE_CYLINDER[(idx + 2) % n],
    }

def obter_dezena_invertida(numero):
    if numero < 10:
        inv = numero * 10
        return inv if inv <= 36 else None
    inv = int(str(numero)[::-1])
    return inv if inv <= 36 else None

def soma_digitos_reduzida(numero):
    if numero == 0:
        return 0
    soma = sum(int(d) for d in str(numero))
    while soma >= 10:
        soma = sum(int(d) for d in str(soma))
    return soma

def obter_camuflados(numero):
    soma = soma_digitos_reduzida(numero)
    camu = CAMUFLADOS_BASE.get(soma, [])
    return [n for n in camu if n != numero]

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

def validar_gatilho_sequencial_brk(sub_historico, atraso_minimo=25):
    if len(sub_historico) < 2:
        return {"sinal_ativo": False}
    d1, d2 = sub_historico[-2] // 10, sub_historico[-1] // 10
    grupo_detectado = next((g for g, nums in GRUPO_OCULTO_BRK.items() if sub_historico[-1] in nums), None)
    if d1 == d2 and grupo_detectado:
        todos_grupo = GRUPO_OCULTO_BRK[grupo_detectado]
        ausentes = [n for n in todos_grupo if n not in sub_historico[-atraso_minimo:]]
        cobertura = [n for n in todos_grupo if n in sub_historico[-atraso_minimo:]]
        return {
            "sinal_ativo": True, "grupo_confirmado": grupo_detectado,
            "dezena_gatilho": d2, "dezena_confirmada": d1,
            "grupo_completo": todos_grupo, "prioridade_maxima": ausentes, "cobertura": cobertura
        }
    return {"sinal_ativo": False}

def checar_estrategia_fantasma(historico):
    if len(historico) >= 3 and all(n in GRUPO_FANTASMA for n in historico[-3:]):
        return {"status": "ATIVADO", "principais": [9, 19, 27]}
    return {"status": "INATIVO"}

def buscar_dados_roleta_url(roleta_nome):
    url = URLS_ROLETAS.get(roleta_nome)
    if not url:
        return []
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.tipminer.com",
            "Referer": "https://www.tipminer.com/"
        }
        resp = session.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            dados = resp.json()
            if isinstance(dados, dict):
                dados = dados.get("result", dados.get("data", dados.get("results", [])))
            if isinstance(dados, list):
                numeros = []
                for i in dados:
                    if isinstance(i, dict):
                        val = i.get("result", i.get("number", i.get("value", i.get("outcome"))))
                        if val is not None and str(val).isdigit():
                            numeros.append(int(val))
                    elif isinstance(i, (int, str)) and str(i).isdigit():
                        numeros.append(int(i))
                return numeros[:200]
        st.sidebar.warning(f"⚠️ Resposta API Status: {resp.status_code}")
    except Exception as e:
        st.sidebar.warning(f"❌ Erro de conexão API: {str(e)[:60]}")
    return []

# ==========================================
# 3. NOTIFICAÇÕES TELEGRAM
# ==========================================
def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Token ou Chat ID não configurados nos Secrets."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, data=payload, timeout=8)
        if res.status_code == 200:
            return True, "✅ Mensagem enviada com sucesso!"
        return False, f"❌ Erro {res.status_code}: {res.text[:100]}"
    except Exception as e:
        return False, f"❌ Falha na conexão: {str(e)}"

def enviar_alerta_telegram(ultimo, score_100, alvos, padroes, roleta_nome="Desconhecida", tier_nome="Indefinido", posicao_rank=None, taxa_acerto=None, aposta_total=35.0):
    pos_str = f"#{posicao_rank}" if posicao_rank else "N/A"
    taxa_str = f"{taxa_acerto}%" if taxa_acerto is not None else "N/A"
    prot_zero = round(aposta_total / 35.0, 2)
    
    msg = (f"🎯 *RADAR DE ROLETA PRO - ALERTA CONFIRMADO*\n\n"
           f"🎰 *MESA:* {roleta_nome}\n"
           f"🎲 *Último Número:* {ultimo}\n"
           f"🏆 *TIER:* {tier_nome} (Rank: {pos_str} | Acerto: {taxa_str})\n"
           f"📊 *SCORE DE ASSERTIVIDADE:* {score_100}/100 pts\n"
           f"📋 *Estratégia:* {', '.join(padroes)}\n"
           f"-----------------------------------\n"
           f"🎯 *ALVOS PRINCIPAIS (Tiro Seco):*\n"
           f"➡️ {alvos}\n\n"
           f"🛡️ *PROTEÇÃO NO ZERO (0):*\n"
           f"➡️ Apostar: R$ {prot_zero:.2f} (Base Aposta: R$ {aposta_total:.2f})\n"
           f"-----------------------------------\n"
           f"⏱ *Validade:* Próximas 2 rodadas (Máx. GALE 1)")
    return enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa="", roleta_nome="Desconhecida"):
    emoji = "✅" if tipo == "GREEN" else "❌"
    msg = f"{emoji} *RESULTADO:* {tipo} {f'({etapa})' if etapa else ''}\n🎰 *Mesa:* {roleta_nome}\n🎲 *Número Sorteado:* {numero}"
    return enviar_mensagem_telegram(msg)

# ==========================================
# 4. MOTOR SNIPER & PONTUAÇÃO (0-100)
# ==========================================
def calcular_score_avancado(puxador_ativo, oculto_brk, racetrack, reincidencia, tiro_seco_pct=80, gale1_pct=70, inercia_positiva=True):
    # Camada de Filtros (Max 60 pts)
    pts_pux = 20.0 if puxador_ativo else 0.0
    pts_ocu = 25.0 if oculto_brk else 0.0
    pts_race = 10.0 if racetrack else 0.0
    pts_reinc = 5.0 if reincidencia else 0.0
    total_filtros = pts_pux + pts_ocu + pts_race + pts_reinc

    # Camada de Performance (Max 40 pts)
    pts_seco = (tiro_seco_pct / 100.0) * 25.0
    pts_gale = (gale1_pct / 100.0) * 10.0
    pts_inercia = 5.0 if inercia_positiva else 0.0
    total_performance = pts_seco + pts_gale + pts_inercia

    score_total = min(100.0, total_filtros + total_performance)
    return round(score_total, 1), round(total_filtros, 1), round(total_performance, 1)

def obter_posicoes_estrategicas(historico_completo):
    if len(historico_completo) < 13:
        return []
    return [historico_completo[0], historico_completo[1], historico_completo[2], historico_completo[12]]

def processar_tiro_certo_e_headshot(historico_completo, dados_brk_in, puxadores_dict, vizinhos_fisi_dict, quentes_100):
    pos_estrategicas = obter_posicoes_estrategicas(historico_completo)
    if not pos_estrategicas:
        return {"tiro_certo": [], "headshot": [], "pesos": {}, "candidatos": [], "ativacoes": {}}
    
    historico_30 = historico_completo[:30]
    ultimo_numero = pos_estrategicas[0]
    candidatos = set(pos_estrategicas)
    for p in pos_estrategicas:
        candidatos.update(puxadores_dict.get(p, [])[:2])
        candidatos.update(vizinhos_fisi_dict.get(p, []))
        candidatos.update(dados_brk_in.get("ausentes", []))

    candidatos_lista = list(candidatos)
    pesos_detalhados = {num: 0.0 for num in candidatos_lista}
    ativacoes_detalhadas = {num: set() for num in candidatos_lista}

    for num in candidatos_lista:
        peso = 0.0
        if num in puxadores_dict.get(ultimo_numero, [])[:2]:
            peso += 3.5
            ativacoes_detalhadas[num].add("Px Top 1/2")
        if num in dados_brk_in.get("ausentes", []):
            peso += 3.0
            ativacoes_detalhadas[num].add("Ausente BRK")
        if any(num in vizinhos_fisi_dict.get(p, []) for p in pos_estrategicas):
            peso += 1.5
            ativacoes_detalhadas[num].add("Vizinho Estratégico")
        if num in quentes_100:
            peso += 1.0
            ativacoes_detalhadas[num].add("Quente 100R")
        if num in pos_estrategicas:
            peso += 2.0
            ativacoes_detalhadas[num].add("Na Esteira 1,2,3,13")
        pesos_detalhados[num] = peso

    candidatos_ordenados = sorted(candidatos_lista, key=lambda x: pesos_detalhados[x], reverse=True)
    alvos_tiro_certo = [n for n in candidatos_ordenados if pesos_detalhados[n] >= 4.0]
    alvos_headshot = [n for n in alvos_tiro_certo if historico_30.count(n) >= 2 and pesos_detalhados[n] >= 5.5]

    return {
        "tiro_certo": alvos_tiro_certo,
        "headshot": alvos_headshot,
        "pesos": pesos_detalhados,
        "candidatos": candidatos_ordenados,
        "ativacoes": ativacoes_detalhadas
    }

def aplicar_afunilamento_estrategico(alvos_brutos, padrao_nome, df_rank, res_tiro_certo):
    if df_rank.empty or padrao_nome not in df_rank["Padrão"].values:
        return {"status": "INVALIDO", "alvos": []}
    
    idx = df_rank[df_rank["Padrão"] == padrao_nome].index[0]
    taxa_acerto = df_rank.loc[idx, "Taxa de Acerto (%)"]
    pos_rank = idx + 1

    if taxa_acerto < 50.0:
        return {"status": "BAIXA_ASSERTIVIDADE", "alvos": []}

    pool_tc = res_tiro_certo["tiro_certo"]
    pool_hs = res_tiro_certo["headshot"]
    
    intersecao_hs = [n for n in pool_hs if n in alvos_brutos]
    if intersecao_hs:
        return {"status": "VALIDADO", "tipo": "🎯 HEAD-SHOT", "alvos": intersecao_hs[:3], "taxa": taxa_acerto, "rank": pos_rank}

    intersecao_tc = [n for n in pool_tc if n in alvos_brutos]
    if intersecao_tc:
        alvos_finais = intersecao_tc.copy()
        if len(alvos_finais) < 4:
            complemento = [n for n in pool_tc if n not in alvos_finais]
            alvos_finais.extend(complemento[:(4 - len(alvos_finais))])
        alvos_finais = alvos_finais[:6]
        if len(alvos_finais) >= 4:
            return {"status": "VALIDADO", "tipo": "🔥 TIRO CERTO", "alvos": alvos_finais, "taxa": taxa_acerto, "rank": pos_rank}

    intersecao_base = [n for n in alvos_brutos if n in res_tiro_certo["candidatos"]]
    if intersecao_base:
        return {"status": "VALIDADO", "tipo": "🚨 SINAL CONFIRMADO", "alvos": intersecao_base[:8], "taxa": taxa_acerto, "rank": pos_rank}

    return {"status": "SEM_CONFLUENCIA", "alvos": []}

# ==========================================
# 5. CLASSIFICADOR DE TIERS + CACHE
# ==========================================
def classificar_padroes_200_rodadas(historico_completo):
    amostra_200 = list(reversed(historico_completo[:200]))
    if len(amostra_200) < 20:
        return {}, pd.DataFrame()
    registros = []
    for idx in range(10, len(amostra_200) - 2):
        res = analisar_rodada_especifica(amostra_200[:idx])
        if res.get("score_num", 0) >= 4:
            futuro = amostra_200[idx:idx+3]
            hit = any(n in set(res["alvos"] + [0]) for n in futuro)
            registros.append({"Padrão": res["padrao_nome"], "Total de Sinais": 1, "Acertos": 1 if hit else 0})

    if not registros:
        return {}, pd.DataFrame()

    estudo = pd.DataFrame(registros).groupby("Padrão").sum().reset_index()
    estudo["Taxa de Acerto (%)"] = round((estudo["Acertos"] / estudo["Total de Sinais"]) * 100, 1)
    estudo_ordenado = estudo[estudo["Taxa de Acerto (%)"] >= 50.0].sort_values(
        by=["Taxa de Acerto (%)", "Total de Sinais"], ascending=[False, False]
    ).reset_index(drop=True)

    l = estudo_ordenado["Padrão"].tolist()
    return {
        "ELITE_TOP_3": l[:3],
        "SELECAO_OURO_TOP_5": l[:5],
        "SELECAO_TOP_10": l[:10],
        "RADAR_TOP_30": l[:30]
    }, estudo_ordenado

def obter_tiers_cache():
    h = len(st.session_state.historico)
    if st.session_state.get("tier_cache_tamanho", -1) != h:
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = classificar_padroes_200_rodadas(st.session_state.historico)
        st.session_state["tier_cache_tamanho"] = h
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

# ==========================================
# 6. MOTOR DE SCORAGE
# ==========================================
def analisar_rodada_especifica(sub_historico, atraso_brk=25):
    if not sub_historico:
        return {}
    ultimo = sub_historico[-1]
    score, alvos, filtros = 0, set(), []

    res_brk = validar_gatilho_sequencial_brk(sub_historico, atraso_minimo=atraso_brk)
    if res_brk["sinal_ativo"]:
        score += 1
        filtros.append(f"OcultosBRK(G{res_brk['grupo_confirmado']})")
        alvos.update(res_brk["grupo_completo"])

    pux = obter_puxadores_otimizados(ultimo, sub_historico)
    if pux:
        score += 1
        filtros.append("Puxadores")
        alvos.update(pux[:2])

    viz = obter_vizinhos_mesa(ultimo)
    score += 1
    filtros.append("Vizinhos")
    alvos.update([viz["esq_1"], viz["dir_1"]])

    inv = obter_dezena_invertida(ultimo)
    if inv is not None:
        score += 1
        filtros.append("Inversão")
        alvos.add(inv)

    fantasma = checar_estrategia_fantasma(sub_historico)
    if fantasma["status"] == "ATIVADO":
        score += 1
        filtros.append("Fantasma")
        alvos.update(fantasma["principais"])

    camu = obter_camuflados(ultimo)
    if camu:
        score += 1
        filtros.append("Camuflados")
        alvos.update(camu[:2])

    reincidencia = [n for n in alvos if n in sub_historico[-14:][-3:]]
    if reincidencia:
        score += 1
        filtros.append("Reincidência")

    racetrack_ativo = False
    if len(sub_historico) >= 10:
        contagem_setores = {s: sum(1 for n in sub_historico[-10:] if n in nums) for s, nums in SETORES_ROLETA.items()}
        setor_dom = max(contagem_setores, key=contagem_setores.get)
        if any(n in SETORES_ROLETA[setor_dom] for n in alvos):
            score += 1
            filtros.append("Racetrack")
            racetrack_ativo = True

    score_final = min(score, 5)
    return {
        "ultimo": int(ultimo),
        "padrao_nome": " + ".join(filtros) if filtros else "Geral",
        "score_num": score_final,
        "alvos": sorted(list(alvos)),
        "dados_brk": res_brk,
        "puxador_ativo": bool(pux),
        "racetrack_ativo": racetrack_ativo,
        "reincidencia_ativa": bool(reincidencia)
    }

# ==========================================
# 7. ESTADO INICIAL E PAINEL LATERAL
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel SNIPER")

if "historico" not in st.session_state:
    st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
if "alvos_sinal" not in st.session_state:
    st.session_state.alvos_sinal = []
if "tentativa_atual" not in st.session_state:
    st.session_state.tentativa_atual = 0
if "ultimo_resultado" not in st.session_state:
    st.session_state.ultimo_resultado = None
if "ultimo_alerta" not in st.session_state:
    st.session_state.ultimo_alerta = {"ultimo": None, "score": None, "alvos": [], "padroes": [], "roleta": "", "tier": None, "rank": None, "taxa": None}

# Trava de Quarentena
if "reds_consecutivos" not in st.session_state:
    st.session_state.reds_consecutivos = 0
if "rodadas_quarentena_restantes" not in st.session_state:
    st.session_state.rodadas_quarentena_restantes = 0

st.sidebar.header("🕹️ Painel de Operação")
modo_operacao = st.sidebar.selectbox("🌐 Modo:", ["On-line (Captura Automática)", "Off-line (Digitação Manual)"])
roleta_selecionada = st.sidebar.selectbox("🎰 Selecionar Roleta:", list(URLS_ROLETAS.keys()))
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Parâmetros do Motor Sniper")
atraso_minimo_oculto = st.sidebar.slider("Atraso Mínimo Oculto (BRK)", 20, 35, 25)
valor_aposta_alvos = st.sidebar.number_input("Aposta Total nos Alvos (R$)", value=35.0, step=5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Filtro Híbrido de Assertividade")
filtro_hibrido_opcao = st.sidebar.selectbox(
    "Nível de Filtragem dos Sinais:",
    ["👑 Elite (Top 3 - Máxima Precisão)", "🥇 Seleção Ouro (Top 5)",
     "🥈 Seleção (Top 10 - Equilibrado)", "🥉 Radar (Top 30 - Permissivo)"],
    index=2
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Travas de Quarentena & Risco")
max_reds_consecutivos = st.sidebar.number_input("Max REDs Consecutivos", value=2)
tempo_quarentena = st.sidebar.number_input("Rodadas em Quarentena", value=15)

def processar_novo_numero(num_novo):
    # Decrementa quarentena se ativa
    if st.session_state.rodadas_quarentena_restantes > 0:
        st.session_state.rodadas_quarentena_restantes -= 1

    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapa_nome = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")
        
        if num_novo in set(st.session_state.alvos_sinal + [0]):
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome, roleta_nome=roleta_selecionada)
            st.session_state.sinal_ativo = False
            st.session_state.alvos_sinal = []
            st.session_state.tentativa_atual = 0
            st.session_state.reds_consecutivos = 0
            return
        elif st.session_state.tentativa_atual >= 2:  # Limite máximo até GALE 1
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            enviar_resultado_telegram("LOSS", num_novo, roleta_nome=roleta_selecionada)
            st.session_state.sinal_ativo = False
            st.session_state.alvos_sinal = []
            st.session_state.tentativa_atual = 0
            st.session_state.reds_consecutivos += 1
            
            # Aciona Quarentena se atingir limite de REDs
            if st.session_state.reds_consecutivos >= max_reds_consecutivos:
                st.session_state.rodadas_quarentena_restantes = tempo_quarentena
            return

    # Se estiver em quarentena, bloqueia novas entradas
    if st.session_state.rodadas_quarentena_restantes > 0:
        return

    if len(st.session_state.historico) >= 30:
        res_ultimo = analisar_rodada_especifica(list(reversed(st.session_state.historico)), atraso_brk=atraso_minimo_oculto)
        if res_ultimo.get("score_num", 0) >= 4:
            hist_completo = st.session_state.historico
            hist_200 = list(reversed(st.session_state.historico[:200]))
            dados_brk_in = {"ausentes": res_ultimo.get("dados_brk", {}).get("prioridade_maxima", [])}
            px_dict = {n: TABELA_PUXADORES_FIXA.get(n, []) for n in range(37)}
            viz_dict = {n: [obter_vizinhos_mesa(n)["esq_1"], obter_vizinhos_mesa(n)["dir_1"]] for n in range(37)}
            q_100 = set(pd.Series(hist_200[-100:]).value_counts().head(10).index.tolist())
            
            res_motor = processar_tiro_certo_e_headshot(hist_completo, dados_brk_in, px_dict, viz_dict, q_100)
            tiers, df_rank = obter_tiers_cache()
            sinal = aplicar_afunilamento_estrategico(res_ultimo["alvos"], res_ultimo["padrao_nome"], df_rank, res_motor)

            if sinal["status"] == "VALIDADO":
                # Cálculo do Score Ponderado (0-100 pts)
                score_100, pts_filtros, pts_perf = calcular_score_avancado(
                    puxador_ativo=res_ultimo["puxador_ativo"],
                    oculto_brk=res_ultimo["dados_brk"].get("sinal_ativo", False),
                    racetrack=res_ultimo["racetrack_ativo"],
                    reincidencia=res_ultimo["reincidencia_ativa"],
                    inercia_positiva=(st.session_state.reds_consecutivos == 0)
                )

                # Classificação de Tiers com base no Score 0-100
                if score_100 >= 88:
                    tier_padrao = "👑 Elite"
                elif score_100 >= 78:
                    tier_padrao = "🥇 Ouro"
                elif score_100 >= 65:
                    tier_padrao = "🥈 Seleção"
                elif score_100 >= 50:
                    tier_padrao = "🥉 Radar"
                else:
                    tier_padrao = "Fora"

                permitido = False
                if "Radar" in filtro_hibrido_opcao and tier_padrao != "Fora":
                    permitido = True
                elif "Seleção (" in filtro_hibrido_opcao and tier_padrao in ["👑 Elite", "🥇 Ouro", "🥈 Seleção"]:
                    permitido = True
                elif "Ouro" in filtro_hibrido_opcao and tier_padrao in ["👑 Elite", "🥇 Ouro"]:
                    permitido = True
                elif "Elite" in filtro_hibrido_opcao and tier_padrao == "👑 Elite":
                    permitido = True

                if permitido and score_100 >= 50:
                    st.session_state.sinal_ativo = True
                    st.session_state.alvos_sinal = sinal["alvos"]
                    st.session_state.tentativa_atual = 0
                    st.session_state.ultimo_alerta = {
                        "ultimo": res_ultimo["ultimo"],
                        "score": score_100,
                        "alvos": sinal["alvos"],
                        "padroes": [sinal["tipo"]],
                        "roleta": roleta_selecionada,
                        "tier": tier_padrao,
                        "rank": sinal["rank"],
                        "taxa": sinal["taxa"]
                    }
                    enviar_alerta_telegram(
                        res_ultimo["ultimo"], score_100, sinal["alvos"],
                        [sinal["tipo"]], roleta_nome=roleta_selecionada, tier_nome=tier_padrao,
                        posicao_rank=sinal["rank"], taxa_acerto=sinal["taxa"], aposta_total=valor_aposta_alvos
                    )

# ATUALIZAÇÃO AUTOMÁTICA
if modo_operacao == "On-line (Captura Automática)":
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    if novos_dados:
        st.sidebar.success(f"🟢 Conectado: {roleta_selecionada}")
        if novos_dados != st.session_state.historico:
            num_novo = novos_dados[0]
            processar_novo_numero(num_novo)
            st.session_state.historico = novos_dados
            st.sidebar.success(f"🔄 Novo número: {num_novo}")
        else:
            st.sidebar.info("✅ Monitorando sem alterações...")
    else:
        st.sidebar.warning("🟡 Sem comunicação com a API Tipminer.")
else:
    st.sidebar.warning(f"🟠 Modo Manual ativo: {roleta_selecionada}")
    with st.sidebar.form(key="form_entrada", clear_on_submit=True):
        novo_numero_input = st.number_input("Número (0-36):", min_value=0, max_value=36, step=1, value=None)
        if st.form_submit_button("➕ Adicionar") and novo_numero_input is not None:
            num = int(novo_numero_input)
            processar_novo_numero(num)
            st.session_state.historico.insert(0, num)
            st.rerun()

if st.sidebar.button("🧹 Limpar Histórico"):
    st.session_state.clear()
    st.rerun()

# ==========================================
# INTERFACE PRINCIPAL - METRICAS & STATUS
# ==========================================
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Status da Mesa", "🔴 QUARENTENA" if st.session_state.rodadas_quarentena_restantes > 0 else "🟢 ATIVA", 
              delta=f"{st.session_state.rodadas_quarentena_restantes} rodadas restantes" if st.session_state.rodadas_quarentena_restantes > 0 else "Operação Livre")

with col_m2:
    st.metric("Amostra Analisada", f"{len(st.session_state.historico)} Rodadas", f"Filtro: {filtro_hibrido_opcao.split()[1]}")

with col_m3:
    st.metric("REDs Consecutivos", f"{st.session_state.reds_consecutivos} / {max_reds_consecutivos}")

with col_m4:
    ult_num = st.session_state.historico[0] if st.session_state.historico else "-"
    st.metric("Último Número", ult_num)

st.subheader("Esteira Temporal (Últimas 13 Rodadas)")
if st.session_state.historico:
    cols = st.columns(min(len(st.session_state.historico[:13]), 13))
    for i, num in enumerate(st.session_state.historico[:13]):
        with cols[i]:
            st.metric(label=f"Pos {i+1}", value=num)
else:
    st.info("Aguardando capturas...")

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 {st.session_state.ultimo_resultado}")
    else:
        st.error(f"⚠️ {st.session_state.ultimo_resultado}")

# ==========================================
# 8. PROTEÇÃO DO ZERO & MENSAGEM TELEGRAM
# ==========================================
st.markdown("---")
c_z1, c_z2 = st.columns(2)

with c_z1:
    st.subheader("🛡️ Proteção no Zero (0)")
    prot_zero_val = round(valor_aposta_alvos / 35.0, 2)
    st.info(f"Aposta Recomendada no Zero: **R$ {prot_zero_val:.2f}** (Base Total Alvos: R$ {valor_aposta_alvos:.2f})")

with c_z2:
    st.subheader("📲 Alerta Ativo (Telegram)")
    if st.session_state.ultimo_alerta["alvos"]:
        st.json(st.session_state.ultimo_alerta)
    else:
        st.write("Aguardando confirmação de sinal...")

# ==========================================
# 9. MAPEAMENTO ANALÍTICO
# ==========================================
sinal_identificado_texto = None
if st.session_state.historico and len(st.session_state.historico) >= 30:
    st.markdown("---")
    historico_completo = st.session_state.historico
    historico_200 = list(reversed(st.session_state.historico[:200]))
    
    res_brk = validar_gatilho_sequencial_brk(historico_200, atraso_minimo=atraso_minimo_oculto)
    dados_brk_in = {"ausentes": res_brk.get("prioridade_maxima", []) if res_brk.get("sinal_ativo") else []}
    puxadores_dict = {n: TABELA_PUXADORES_FIXA.get(n, []) for n in range(37)}
    vizinhos_fisi_dict = {n: [obter_vizinhos_mesa(n)["esq_1"], obter_vizinhos_mesa(n)["dir_1"]] for n in range(37)}
    quentes_100 = set(pd.Series(historico_200[-100:]).value_counts().head(10).index.tolist())
    
    res_motores = processar_tiro_certo_e_headshot(historico_completo, dados_brk_in, puxadores_dict, vizinhos_fisi_dict, quentes_100)
    res_ultimo = analisar_rodada_especifica(list(reversed(st.session_state.historico)), atraso_brk=atraso_minimo_oculto)
    tiers_atuais, df_rank = obter_tiers_cache()

    st.subheader(f"📊 Mapeamento Analítico Sniper - {roleta_selecionada}")
    posicoes_idx = [0, 1, 2, 12]
    nomes_pos = {0: "Pos 1", 1: "Pos 2", 2: "Pos 3", 12: "Pos 13"}
    dados_tabela = []
    
    alvos_sugeridos = sorted(res_motores["headshot"] + res_motores["tiro_certo"])
    for idx in posicoes_idx:
        if idx >= len(historico_completo):
            continue
        num = historico_completo[idx]
        ativacoes = res_motores["ativacoes"].get(num, set())
        peso = res_motores["pesos"].get(num, 0.0)

        if num in res_motores["headshot"]:
            status_dezena = f"🎯 HEAD-SHOT → {alvos_sugeridos}"
        elif num in res_motores["tiro_certo"]:
            status_dezena = f"🔥 TIRO CERTO → {alvos_sugeridos}"
        else:
            status_dezena = "⚪ Aguardar"

        dados_tabela.append({
            "Posição": nomes_pos[idx],
            "Dezena": num,
            "Vizinho (+1.5)": f"🟢 {vizinhos_fisi_dict.get(num, [])}" if "Vizinho Estratégico" in ativacoes else "⚪",
            "+Quente 100R (+1.0)": "🟢 Sim" if "Quente 100R" in ativacoes else "⚪",
            "Px Top 1/2 (+3.5)": f"🟢 {puxadores_dict.get(num, [])[:2]}" if "Px Top 1/2" in ativacoes else "⚪",
            "Ausente BRK (+3.0)": "🟢 Sim" if "Ausente BRK" in ativacoes else "⚪",
            "Score Final 🔥": f"{peso:.1f}",
            "Status": status_dezena
        })
    st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True)

    if res_ultimo.get("score_num", 0) >= 4:
        sinal_afunilado = aplicar_afunilamento_estrategico(res_ultimo["alvos"], res_ultimo["padrao_nome"], df_rank, res_motores)
        if sinal_afunilado["status"] == "VALIDADO":
            sinal_identificado_texto = f"🚨 SINAL IDENTIFICADO: {sinal_afunilado['alvos']}"
            cor = "success" if "HEAD-SHOT" in sinal_afunilado['tipo'] else "warning" if "TIRO CERTO" in sinal_afunilado['tipo'] else "info"
            getattr(st, cor)(f"✅ {sinal_afunilado['tipo']} | Entrar nestas Dezenas:")
            c1, c2, c3 = st.columns(3)
            c1.metric("🎯 Dezenas Sugeridas", str(sinal_afunilado['alvos']))
            c2.metric("🏆 Ranking do Padrão", f"#{sinal_afunilado['rank']}")
            c3.metric("📈 Assertividade", f"{sinal_afunilado['taxa']}%")
            st.caption(f"Origem: Padrão {res_ultimo['padrao_nome']} alinhado com dezenas derivadas das posições (1, 2, 3 e 13).")
        else:
            st.warning("⚠️ Padrão detectado, mas não alcançou critérios de confluência Sniper.")
            st.write(f"- Padrão Base: {res_ultimo['padrao_nome']}")
            st.write("- Motivo: Padrão com assertividade < 50% ou dezenas não confluentes com as posições 1, 2, 3 ou 13.")
    else:
        st.info("⚪ AGUARDANDO CONFLUÊNCIA... Radar sniper monitorando exclusivamente posições 1, 2, 3 e 13.")

    st.markdown("---")
    st.subheader(f"📊 Mapeamento Analítico Completo - {roleta_selecionada}")
    posicoes_mapeamento = list(range(min(10, len(historico_completo))))
    dados_tabela_mapeamento = []
    
    for idx in posicoes_mapeamento:
        num = historico_completo[idx]
        viz = obter_vizinhos_mesa(num)
        pux = TABELA_PUXADORES_FIXA.get(num, [])
        camu = obter_camuflados(num)
        inv = obter_dezena_invertida(num)
        setor_pertencente = next((s for s, nums in SETORES_ROLETA.items() if num in nums), "-")
        grupo_brk = obter_grupo_brk(num)

        score_item = sum([
            bool(pux),
            bool([viz["esq_1"], viz["dir_1"]]),
            bool(camu),
            setor_pertencente != "-",
            inv is not None
        ])
        score_item = min(score_item, 5)
        confirmacoes = "🔴" * score_item + "⚪" * (5 - score_item)
        sugestao = f"SINAL: {sorted(list(set([num] + pux[:2] + [viz['esq_1'], viz['dir_1']] + camu + ([inv] if inv else []))))}" if score_item >= 4 else "AGUARDAR"

        dados_tabela_mapeamento.append({
            "Posição": f"Pos {idx+1}",
            "Último": num,
            "Esquerda": f"{viz['esq_2']} | {viz['esq_1']}",
            "Direita": f"{viz['dir_1']} | {viz['dir_2']}",
            "Puxadores Híbridos": str(pux[:4]),
            "Vizinhos Físicos": f"Esq({viz['esq_1']}), Dir({viz['dir_1']})",
            "Camuflados": str(camu),
            "🏷️ Grupo BRK": grupo_brk,
            "Racetrack": setor_pertencente,
            "Inversão": f"{num}→{inv}" if inv else "-",
            "Reincidência": f"[{inv}]" if inv else "-",
            "Confirmações": confirmacoes,
            "Score": f"{score_item}/5",
            "Status / Sugestão": sugestao
        })
    st.dataframe(pd.DataFrame(dados_tabela_mapeamento), use_container_width=True, hide_index=True)

    st.markdown("---")
    if sinal_identificado_texto:
        st.error(sinal_identificado_texto)
    
    ultimo_alerta = st.session_state.ultimo_alerta
    if st.button("🔁 Reenviar Alerta para Telegram"):
        if ultimo_alerta["alvos"]:
            ok, mensagem = enviar_alerta_telegram(
                ultimo_alerta["ultimo"], ultimo_alerta["score"], ultimo_alerta["alvos"],
                ultimo_alerta["padroes"], roleta_nome=ultimo_alerta["roleta"],
                tier_nome=ultimo_alerta["tier"], posicao_rank=ultimo_alerta["rank"],
                taxa_acerto=ultimo_alerta["taxa"], aposta_total=valor_aposta_alvos
            )
            if ok:
                st.success("✅ Alerta reenviado com sucesso!")
            else:
                st.error(f"❌ Falha: {mensagem}")
        else:
            st.warning("⚠️ Nenhum alerta armazenado para reenviar.")

    with st.expander("🏆 Ranking dos Padrões (Assertividade ≥ 50% - Últimas 200 Rodadas)"):
        if not df_rank.empty:
            df_rank_exib = df_rank.copy()
            df_rank_exib.index = range(1, len(df_rank_exib) + 1)
            st.dataframe(df_rank_exib, use_container_width=True)
        else:
            st.info("Nenhum padrão consolidou no mínimo 50% de acerto até o momento.")
