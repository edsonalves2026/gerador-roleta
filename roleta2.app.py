import streamlit as st
import pandas as pd
import requests
import random
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURAÇÃO E CREDENCIAIS SEGURAS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Painel Completo", layout="wide")
st_autorefresh(interval=5000, key="autoupdate_roleta")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# MATRIZES E TABELAS BASE
# ==========================================
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

TABELA_OCULTOS_BRK = {
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

NUMEROS_VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
]

URLS_ROLETAS = {
    "Cassino ao Vivo Immersive Roulette": {
        "api_endpoint": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4452-4723-a97d-f3703302d5cc/history?timezone=America%2FSao_Paulo&subject=filter&limit=1000"
    },
    "Cassino ao Vivo Swedish Roulette": {
        "api_endpoint": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-40d2-b479-a28a01c6ee13/history?timezone=America%2FSao_Paulo&subject=filter&limit=1000"
    }
}

# ==========================================
# 2. FUNÇÃO DE BUSCA DA API (ROBUSTA)
# ==========================================
def buscar_dados_roleta_url(roleta_nome):
    config = URLS_ROLETAS.get(roleta_nome, {})
    endpoint = config.get("api_endpoint", "")
    
    if not endpoint:
        st.sidebar.warning("⚠️ Nenhum endpoint configurado.")
        return st.session_state.get("historico", [])
    
    try:
        t_param = f"&t={int(time.time() * 1000)}"
        url_completo = endpoint + t_param
        
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.tipminer.com",
            "Referer": "https://www.tipminer.com/",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        st.sidebar.info(f"🔄 Consultando: {roleta_nome}")
        res = requests.get(url_completo, headers=headers, timeout=10)
        st.sidebar.text(f"Status HTTP: {res.status_code}")
        
        if res.status_code == 200:
            dados = res.json()
            numeros = []
            
            if isinstance(dados, list):
                for item in dados:
                    if isinstance(item, dict) and "result" in item:
                        val = item["result"]
                        if val is not None:
                            try:
                                numeros.append(int(val))
                            except (ValueError, TypeError):
                                pass
            
            if numeros:
                st.sidebar.success(f"✅ {len(numeros)} rodadas recebidas")
                return numeros
            else:
                st.sidebar.warning("⚠️ API respondeu, sem números extraídos")
        else:
            st.sidebar.error(f"⚠️ Erro HTTP: {res.status_code} — API inacessível no momento")
    
    except requests.exceptions.Timeout:
        st.sidebar.error("⏱️ Tempo esgotado na consulta à API")
    except Exception as e:
        st.sidebar.error(f"⚠️ Falha na conexão: {type(e).__name__}")
    
    st.sidebar.info("📌 Usando histórico existente ou Modo Manual")
    return st.session_state.get("historico", [])

# ==========================================
# 3. TELEGRAM (TRATAMENTO SILENCIOSO)
# ==========================================
def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Token/Chat ID não configurados nos Secrets."
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            return True, "✅ Mensagem enviada ao Telegram!"
        else:
            return False, f"Telegram: HTTP {res.status_code}"
    except Exception as e:
        return False, f"Falha na rede: {str(e)[:60]}"

def enviar_alerta_telegram(numero, score, alvos, observacoes, tier_nome="", posicao_rank=None, taxa_acerto=None):
    detalhes = observacoes.copy()
    if tier_nome:
        detalhes.append(f"Tier: {tier_nome}")
    if posicao_rank and taxa_acerto:
        detalhes.append(f"Rank: {posicao_rank}º | Taxa: {taxa_acerto}%")
    
    mensagem = (
        f"🚨 *SINAL DETECTADO* 🚨\n\n"
        f"📌 Último Número: `{numero}`\n"
        f"🔥 Score: `{score}`\n"
        f"🎯 Alvos: `{alvos}`\n"
        f"ℹ️ {'; '.join(detalhes)}\n\n"
        f"🛡️ Proteção: `0 (Zero)`\n"
        f"⏱️ Manter por 3 a 4 rodadas."
    )
    return enviar_mensagem_telegram(mensagem)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    if tipo == "GREEN":
        msg = f"✅ *GREEN CONFIRMADO!* 🎉\n\n🎯 Número Bateu: `{numero}`\n📍 Momento: `{etapa}`"
    else:
        msg = f"❌ *RED / LOSS* 😔\n\n📌 Último Sorteado: `{numero}`\n⚠️ Limite de Gales atingido."
    return enviar_mensagem_telegram(msg)

# ==========================================
# 4. FUNÇÕES AUXILIARES DE CÁLCULO
# ==========================================
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
    return pd.Series(subsequentes).value_counts().head(4).index.tolist() if subsequentes else []

def obter_puxadores_otimizados(numero_sorteado, historico_recentes):
    if len(historico_recentes) < 100:
        return TABELA_PUXADORES_FIXA.get(numero_sorteado, [])
    puxadores_dinamicos = calcular_matriz_transicao(historico_recentes)
    puxadores_fixos = TABELA_PUXADORES_FIXA.get(numero_sorteado, [])
    intersecao = [num for num in puxadores_dinamicos if num in puxadores_fixos]
    return intersecao if intersecao else (puxadores_dinamicos[:4] if puxadores_dinamicos else puxadores_fixos)

def validar_gatilho_sequencial_brk(historico_200):
    if not historico_200 or len(historico_200) < 2:
        return {"sinal_ativo": False}
    dezena_atual = historico_200[-1]
    dezena_anterior = historico_200[-2]
    
    if dezena_atual == 0:
        soma, diferenca = 10, 10
    else:
        d1, d2 = dezena_atual // 10, dezena_atual % 10
        soma = d1 + d2
        if soma > 10:
            soma = (soma // 10) + (soma % 10)
        diferenca = abs(d2 - d1)
    
    grupo_confirmado = None
    if soma == dezena_anterior:
        grupo_confirmado = soma
    elif diferenca == dezena_anterior:
        grupo_confirmado = diferenca
    
    if grupo_confirmado is None or grupo_confirmado not in TABELA_OCULTOS_BRK:
        return {"sinal_ativo": False}
    
    grupo_completo = TABELA_OCULTOS_BRK[grupo_confirmado]
    amostra_200 = historico_200[-200:]
    dezenas_prioritarias = [num for num in grupo_completo if num not in amostra_200]
    dezenas_cobertura = [num for num in grupo_completo if num in amostra_200]
    
    return {
        "sinal_ativo": True,
        "grupo_confirmado": grupo_confirmado,
        "dezena_gatilho": dezena_atual,
        "dezena_confirmada": dezena_anterior,
        "prioridade_maxima": dezenas_prioritarias,
        "cobertura": dezenas_cobertura,
        "grupo_completo": grupo_completo
    }

# ==========================================
# 5. RANKING DE PADRÕES E TIERS
# ==========================================
def nomear_padrao(brk, puxadores, vizinhos, invertido, fantasma, racetrack, reincidencia):
    componentes = []
    if brk: componentes.append("OcultosBRK")
    if puxadores: componentes.append("Puxadores")
    if vizinhos: componentes.append("Vizinhos")
    if invertido: componentes.append("Inversão")
    if fantasma: componentes.append("Fantasma")
    if racetrack: componentes.append("Racetrack")
    if reincidencia: componentes.append("Reincidência")
    return " + ".join(componentes) if componentes else "Básico"

def obter_tiers_cache():
    if ("tier_cache" in st.session_state and 
        "df_rank_cache" in st.session_state and
        "tier_cache_tamanho" in st.session_state and
        st.session_state.tier_cache_tamanho == len(st.session_state.historico)):
        return st.session_state.tier_cache, st.session_state.df_rank_cache
    
    historico = st.session_state.historico
    if len(historico) < 20:
        return {}, pd.DataFrame()
    
    amostra = historico[:200]
    padroes_contagem = {}
    
    for idx in range(4, len(amostra)):
        sub_hist = list(reversed(amostra[idx:]))
        if len(sub_hist) < 4:
            continue
        
        ultimo = sub_hist[-1]
        res_brk = validar_gatilho_sequencial_brk(sub_hist)
        puxadores = bool(obter_puxadores_otimizados(ultimo, sub_hist))
        vizinhos = True
        invertido = obter_dezena_invertida(ultimo) is not None
        fantasma = ultimo in GRUPO_FANTASMA
        racetrack = len(sub_hist) >= 10
        reincidencia = any(n in sub_hist[-3:] for n in (obter_puxadores_otimizados(ultimo, sub_hist) or []))
        
        nome = nomear_padrao(res_brk["sinal_ativo"], puxadores, vizinhos, invertido, fantasma, racetrack, reincidencia)
        score = sum([res_brk["sinal_ativo"], puxadores, vizinhos, invertido, fantasma, racetrack, reincidencia])
        
        if nome not in padroes_contagem:
            padroes_contagem[nome] = {"Total": 0, "Acertos": 0}
        padroes_contagem[nome]["Total"] += 1
        if score >= 4:
            padroes_contagem[nome]["Acertos"] += 1
    
    linhas = []
    for padrao, vals in padroes_contagem.items():
        taxa = round((vals["Acertos"] / vals["Total"] * 100), 1) if vals["Total"] > 0 else 0
        linhas.append({
            "Padrão": padrao,
            "Total": vals["Total"],
            "Acertos": vals["Acertos"],
            "Taxa de Acerto (%)": taxa
        })
    
    df_rank = pd.DataFrame(linhas).sort_values("Taxa de Acerto (%)", ascending=False).reset_index(drop=True)
    
    tiers = {}
    if not df_rank.empty:
        tiers["ELITE_TOP_3"] = df_rank.head(3)["Padrão"].tolist()
        tiers["SELECAO_OURO_TOP_5"] = df_rank.head(5)["Padrão"].tolist()
        tiers["SELECAO_TOP_10"] = df_rank.head(10)["Padrão"].tolist()
        tiers["RADAR_TOP_30"] = df_rank.head(30)["Padrão"].tolist()
    
    st.session_state.tier_cache = tiers
    st.session_state.df_rank_cache = df_rank
    st.session_state.tier_cache_tamanho = len(historico)
    
    return tiers, df_rank

# ==========================================
# 6. CÁLCULO DE SCORE PONDERADO
# ==========================================
def calcular_score_ponderado_num(num, sub_historico, res_brk, puxadores, vizinhos):
    score = 0.0
    pontos = {"vizinho": 0.0, "quente_100r": 0.0, "dois_filtros": 0.0, "px_top1": 0.0, "ausente": 0.0}
    detalhes = []
    
    if res_brk.get("sinal_ativo") and num in res_brk.get("prioridade_maxima", []):
        score += 3.0
        pontos["ausente"] = 3.0
        detalhes.append("Ausente(+3.0)")
    
    if puxadores and num == puxadores[0]:
        score += 2.5
        pontos["px_top1"] = 2.5
        detalhes.append("PxTop1(+2.5)")
    
    qtd_filtros = sum([
        1 if num in puxadores else 0,
        1 if num in [vizinhos["esq_1"], vizinhos["dir_1"]] else 0,
        1 if res_brk.get("sinal_ativo") and num in res_brk.get("grupo_completo", []) else 0,
        1 if num == obter_dezena_invertida(sub_historico[-1]) else 0
    ])
    
    if qtd_filtros >= 2:
        score += 2.0
        pontos["dois_filtros"] = 2.0
        detalhes.append("+2Filtros(+2.0)")
    
    if len(sub_historico) >= 50:
        amostra = sub_historico[-200:]
        if amostra.count(num) > (len(amostra) / 37):
            score += 1.0
            pontos["quente_100r"] = 1.0
            detalhes.append("Quente100R(+1.0)")
    
    if num in [vizinhos["esq_1"], vizinhos["dir_1"]]:
        score += 1.0
        pontos["vizinho"] = 1.0
        detalhes.append("Vizinho(+1.0)")
    
    return round(score, 1), pontos, detalhes

def analisar_rodada_especifica(sub_historico):
    if not sub_historico:
        return {}
    
    ultimo = sub_historico[-1]
    res_brk = validar_gatilho_sequencial_brk(sub_historico)
    puxadores = obter_puxadores_otimizados(ultimo, sub_historico)
    vizinhos = obter_vizinhos_mesa(ultimo)
    invertido = obter_dezena_invertida(ultimo)
    fantasma = ultimo in GRUPO_FANTASMA
    racetrack = len(sub_historico) >= 10
    reincidencia = any(n in sub_historico[-3:] for n in (puxadores or []))
    
    filtros_ativos_contagem = sum([
        1 if res_brk["sinal_ativo"] else 0,
        1 if puxadores else 0,
        1,
        1 if invertido is not None else 0
    ])
    
    padrao_nome = nomear_padrao(
        res_brk["sinal_ativo"], bool(puxadores), True,
        invertido is not None, fantasma, racetrack, reincidencia
    )
    
    alvos_brutos = set()
    if res_brk["sinal_ativo"]:
        alvos_brutos.update(res_brk["grupo_completo"])
    if puxadores:
        alvos_brutos.update(puxadores[:2])
    alvos_brutos.update([vizinhos["esq_1"], vizinhos["dir_1"]])
    if invertido is not None:
        alvos_brutos.add(invertido)
    
    scores_alvos, pontos_alvos, detalhes_alvos = {}, {}, {}
    for num in alvos_brutos:
        sc, pts, det = calcular_score_ponderado_num(num, sub_historico, res_brk, puxadores, vizinhos)
        scores_alvos[num] = sc
        pontos_alvos[num] = pts
        detalhes_alvos[num] = det
    
    alvos_ordenados = sorted(scores_alvos.keys(), key=lambda x: scores_alvos[x], reverse=True)
    score_maximo = max(scores_alvos.values()) if scores_alvos else 0.0
    
    return {
        "ultimo": ultimo,
        "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores": str(puxadores[:2]) if puxadores else "-",
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)),
        "racetrack": max(SETORES_ROLETA, key=lambda s: sum(1 for n in sub_historico[-10:] if n in SETORES_ROLETA[s])) if len(sub_historico)>=10 else "-",
        "inversao": f"{ultimo}➔{invertido}" if invertido is not None else "-",
        "reincidencia": str([n for n in alvos_brutos if n in sub_historico[-3:]]) if any(n in sub_historico[-3:] for n in alvos_brutos) else "-",
        "confirmacoes": "🔴 " * min(filtros_ativos_contagem, 5),
        "score": f"{min(filtros_ativos_contagem, 5)}/5",
        "score_num": filtros_ativos_contagem,
        "padrao_nome": padrao_nome,
        "alvos": alvos_ordenados,
        "scores_alvos": scores_alvos,
        "detalhes_alvos": detalhes_alvos,
        "score_maximo": score_maximo,
        "status": f"SINAL: {alvos_ordenados}" if score_maximo >= 7.5 else "AGUARDAR"
    }

# ==========================================
# 7. EXECUÇÃO PRINCIPAL & ENGINE
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

if "historico" not in st.session_state:
    st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0
    st.session_state.ultimo_resultado = None

# ================= PAINEL LATERAL RESTAURADO ====================
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

st.sidebar.subheader("🎛️ Filtro Híbrido de Assertividade (200 Rodadas)")
filtro_hibrido_opcao = st.sidebar.selectbox(
    "Nível de Filtragem dos Sinais:",
    [
        "Desativado (Usar apenas regras fixas)",
        "🥉 Radar (Top 30 - Permissivo)",
        "🥈 Seleção (Top 10 - Equilibrado)",
        "🥇 Seleção Ouro (Top 5 - Conservador)",
        "👑 Elite (Top 3 - Máxima Precisão)"
    ],
    index=2
)
modo_gale_opcao = st.sidebar.radio(
    "Estratégia no Gale ao detectar novo Sinal Elite:",
    ["Opção A: Mantém Sinal A (Aposta Fixa)", "Opção B: Fusão de Alvos Únicos (A + B)"],
    index=1
)
st.sidebar.markdown("---")

# ==========================================
# PROCESSAMENTO DE NOVO NÚMERO COM FILTROS
# ==========================================
def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")
        
        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome)
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            enviar_resultado_telegram("LOSS", num_novo)
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
    
    if len(st.session_state.historico) >= 20:
        historico_analise = list(reversed(st.session_state.historico))
        res_ultimo = analisar_rodada_especifica(historico_analise)
        
        if res_ultimo["score_num"] >= 4:
            tiers, df_rank = obter_tiers_cache()
            padrao = res_ultimo["padrao_nome"]
            
            posicao_rank = None
            taxa_acerto = None
            if not df_rank.empty and padrao in df_rank["Padrão"].values:
                idx = df_rank[df_rank["Padrão"] == padrao].index[0]
                posicao_rank = idx + 1
                taxa_acerto = df_rank.loc[idx, "Taxa de Acerto (%)"]
            
            tier_do_padrao = "Fora dos Tiers"
            if padrao in tiers.get("ELITE_TOP_3", []):
                tier_do_padrao = "👑 Elite (Top 3)"
            elif padrao in tiers.get("SELECAO_OURO_TOP_5", []):
                tier_do_padrao = "🥇 Seleção Ouro (Top 5)"
            elif padrao in tiers.get("SELECAO_TOP_10", []):
                tier_do_padrao = "🥈 Seleção (Top 10)"
            elif padrao in tiers.get("RADAR_TOP_30", []):
                tier_do_padrao = "🥉 Radar (Top 30)"
            
            permitido = False
            if filtro_hibrido_opcao == "Desativado (Usar apenas regras fixas)":
                permitido = True
            elif filtro_hibrido_opcao == "🥉 Radar (Top 30 - Permissivo)" and tier_do_padrao != "Fora dos Tiers":
                permitido = True
            elif filtro_hibrido_opcao == "🥈 Seleção (Top 10 - Equilibrado)" and tier_do_padrao in ["👑 Elite (Top 3)", "🥇 Seleção Ouro (Top 5)", "🥈 Seleção (Top 10)"]:
                permitido = True
            elif filtro_hibrido_opcao == "🥇 Seleção Ouro (Top 5 - Conservador)" and tier_do_padrao in ["👑 Elite (Top 3)", "🥇 Seleção Ouro (Top 5)"]:
                permitido = True
            elif filtro_hibrido_opcao == "👑 Elite (Top 3 - Máxima Precisão)" and tier_do_padrao == "👑 Elite (Top 3)":
                permitido = True
            
            if st.session_state.sinal_ativo:
                if "Fusão" in modo_gale_opcao and tier_do_padrao == "👑 Elite (Top 3)":
                    alvos_novos = [n for n in res_ultimo["alvos"] if n not in st.session_state.alvos_sinal]
                    if alvos_novos and len(st.session_state.alvos_sinal) < 10:
                        st.session_state.alvos_sinal.extend(alvos_novos)
                        enviar_mensagem_telegram(
                            f"🔄 *FUSÃO DE ALVOS (GALE)*\n"
                            f"Novos alvos: `{alvos_novos}`\n"
                            f"Total: `{st.session_state.alvos_sinal}`"
                        )
            elif permitido:
                st.session_state.sinal_ativo = True
                st.session_state.alvos_sinal = res_ultimo["alvos"]
                st.session_state.tentativa_atual = 0
                enviar_alerta_telegram(
                    res_ultimo["ultimo"],
                    res_ultimo["score_num"],
                    res_ultimo["alvos"],
                    [f"Padrão: {padrao}", f"Filtro: {filtro_hibrido_opcao}"],
                    tier_nome=tier_do_padrao,
                    posicao_rank=posicao_rank,
                    taxa_acerto=taxa_acerto
                )

# ==========================================
# CAPTURA DE DADOS
# ==========================================
if modo_operacao == "On-line (Captura Automática)":
    st.sidebar.info(f"🟢 Conectado: **{roleta_selecionada}**")
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    
    if novos_dados and novos_dados != st.session_state.historico:
        num_novo = novos_dados[0]
        processar_novo_numero(num_novo)
        st.session_state.historico = novos_dados
else:
    st.sidebar.warning(f"🟠 Modo Manual: **{roleta_selecionada}**")
    with st.sidebar.form(key="form_manual", clear_on_submit=True):
        input_num = st.number_input("Número Sorteado:", min_value=0, max_value=36, step=1, value=None)
        if st.form_submit_button("➕ Adicionar (Enter)") and input_num is not None:
            n = int(input_num)
            processar_novo_numero(n)
            st.session_state.historico.insert(0, n)
            st.rerun()
    
    if st.sidebar.button("🧹 Limpar Histórico"):
        st.session_state.historico = []
        st.session_state.sinal_ativo = False
        st.session_state.alvos_sinal = []
        st.session_state.tentativa_atual = 0
        st.session_state.ultimo_resultado = None
        for chave in ["tier_cache", "df_rank_cache", "tier_cache_tamanho"]:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()

# ==========================================
# EXIBIÇÃO VISUAL COMPLETA
# ==========================================
st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    janela_14 = st.session_state.historico[:14]
    cols = st.columns(min(len(janela_14), 14))
    for i, num in enumerate(janela_14):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)

if st.session_state.historico and len(st.session_state.historico) >= 2:
    historico_cron = list(reversed(st.session_state.historico))
    res_brk = validar_gatilho_sequencial_brk(historico_cron)
    
    if res_brk["sinal_ativo"]:
        st.markdown("---")
        st.success(f"🎯 **GATILHO OCULTO BRK CONFIRMADO PARA O GRUPO {res_brk['grupo_confirmado']}!**")
        st.markdown(f"**Validação:** A dezena recente `{res_brk['dezena_gatilho']}` confirmou a dezena anterior `{res_brk['dezena_confirmada']}`.")
        
        c_prio, c_cob = st.columns(2)
        with c_prio:
            st.error(f"🔥 **PRIORIDADE MÁXIMA:**\n\n`{res_brk['prioridade_maxima']}`")
        with c_cob:
            st.warning(f"🛡️ **COBERTURA:**\n\n`{res_brk['cobertura']}`")
        st.info("⏱️ Manter apostas neste grupo por 3 a 4 rodadas.")

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
    else:
        st.error(f"⚠️ Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")

st.markdown("---")
if st.session_state.historico:
    tiers_atuais, df_rank = obter_tiers_cache()
    
    with st.expander("🏆 Ranking dos Padrões (Últimas 200 Rodadas)", expanded=True):
        if not df_rank.empty:
            st.dataframe(df_rank, use_container_width=True, hide_index=True)
        else:
            st.info("Aguardando histórico suficiente (mínimo ~20 rodadas) para consolidação do ranking.")
    
    historico_analise = list(reversed(st.session_state.historico))
    res_ultimo = analisar_rodada_especifica(historico_analise)
    
    if res_ultimo["score_num"] >= 4:
        st.error(f"🚨 SINAL IDENTIFICADO: {res_ultimo['alvos']}")
        
        if st.button("📤 Reenviar Alerta para Telegram"):
            posicao_rank = None
            taxa_acerto = None
            if not df_rank.empty and res_ultimo["padrao_nome"] in df_rank["Padrão"].values:
                idx = df_rank[df_rank["Padrão"] == res_ultimo["padrao_nome"]].index[0]
                posicao_rank = idx + 1
                taxa_acerto = df_rank.loc[idx, "Taxa de Acerto (%)"]
            
            sucesso, msg = enviar_alerta_telegram(
                res_ultimo["ultimo"],
                res_ultimo["score_num"],
                res_ultimo["alvos"],
                [res_ultimo["status"]],
                posicao_rank=posicao_rank,
                taxa_acerto=taxa_acerto
            )
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

st.markdown("---")
st.subheader("📊 Estatísticas das Rodadas (Quentes/Frios, Avançada, Últimas 1000)")

if st.session_state.historico:
    total_disponivel = len(st.session_state.historico)
    max_amostra = min(1000, total_disponivel)
    qtd_rodadas = st.slider(
        "Tamanho da amostra (Últimas X rodadas):",
        min_value=min(10, total_disponivel),
        max_value=max_amostra,
        value=max_amostra,
        step=5
    )
    
    amostra = list(reversed(st.session_state.historico[:qtd_rodadas]))
    total_amostra = len(amostra) or 1
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.markdown("### 📊 QUENTES/FRIOS")
        contagem = pd.Series(amostra).value_counts()
        quentes = contagem.head(5).index.tolist()
        frios = contagem.tail(5).index.tolist()
        
        st.write(f"🔥 **Mais Frequentes:** `{quentes}`")
        st.write(f"🧊 **Menos Frequentes:** `{frios}`")
        
        freq_df = pd.DataFrame({'Número': contagem.index.astype(str), 'Frequência': contagem.values})
        fig_freq = px.bar(freq_df.head(10), x='Número', y='Frequência', title="Top 10 Números")
        fig_freq.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_freq, use_container_width=True)
    
    with col_g2:
        st.markdown("### 📊 AVANÇADA")
        d1 = sum(1 for n in amostra if 1 <= n <= 12) / total_amostra * 100
        d2 = sum(1 for n in amostra if 13 <= n <= 24) / total_amostra * 100
        d3 = sum(1 for n in amostra if 25 <= n <= 36) / total_amostra * 100
        
        c1 = sum(1 for n in amostra if n > 0 and n % 3 == 1) / total_amostra * 100
        c2 = sum(1 for n in amostra if n > 0 and n % 3 == 2) / total_amostra * 100
        c3 = sum(1 for n in amostra if n > 0 and n % 3 == 0) / total_amostra * 100
        
        df_duzias = pd.DataFrame({
            'Grupo': ['1ª Dúzia', '2ª Dúzia', '3ª Dúzia', '1ª Coluna', '2ª Coluna', '3ª Coluna'],
            'Porcentagem': [round(d1,1), round(d2,1), round(d3,1), round(c1,1), round(c2,1), round(c3,1)]
        })
        
        fig_adv = px.bar(df_duzias, x='Grupo', y='Porcentagem', text='Porcentagem', title="Distribuição (%)")
        fig_adv.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_adv.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=5))
        st.plotly_chart(fig_adv, use_container_width=True)
    
    with col_g3:
        st.markdown(f"### 📊 ÚLTIMAS {qtd_rodadas}")
        matriz_freq = {n: amostra.count(n) for n in range(0, 37)}
        st.write("🔥 **Mapa de Calor da Mesa (0 a 36):**")
        
        grid_rows = [
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
            [0, 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
            [0, 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]
        ]
        
        z_vals = [[matriz_freq[n] for n in row] for row in grid_rows]
        text_vals = [[f"{n}<br>({matriz_freq[n]})" for n in row] for row in grid_rows]
        
        fig_grid = go.Figure(data=go.Heatmap(
            z=z_vals,
            text=text_vals,
            texttemplate='%{text}',
            colorscale='RdYlGn',
            showscale=True
        ))
        
        fig_grid.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_showticklabels=False,
            yaxis_showticklabels=False,
            template="plotly_dark"
        )
        st.plotly_chart(fig_grid, use_container_width=True)

st.markdown("---")
st.subheader("📋 Últimos 14 Números Recebidos")
if st.session_state.historico:
    st.write(" | ".join(str(n) for n in st.session_state.historico[:14]))
else:
    st.info("Aguardando recebimento de números...")
