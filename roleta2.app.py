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
st.set_page_config(page_title="Radar de Roleta Pro - Motor Avançado", layout="wide")
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
# 2. FUNÇÕES AUXILIARES DE CÁLCULO E API
# ==========================================
def buscar_dados_roleta_url(roleta_nome):
    config = URLS_ROLETAS.get(roleta_nome, {})
    endpoint = config.get("api_endpoint", "")
    if not endpoint:
        return st.session_state.get("historico", [])
    try:
        t_param = f"&t={int(time.time() * 1000)}"
        res = requests.get(endpoint + t_param, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=15)
        if res.status_code == 200:
            dados = res.json()
            numeros = [int(item["result"]) for item in dados if isinstance(item, dict) and item.get("result") is not None]
            if numeros:
                return numeros
    except Exception:
        pass
    return st.session_state.get("historico", [])

def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Token/Chat ID não configurados."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=5)
        return (True, "Enviado com sucesso!") if res.status_code == 200 else (False, res.text)
    except Exception as e:
        return False, str(e)

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

def checar_estrategia_fantasma(historico):
    if len(historico) >= 3 and all(n in GRUPO_FANTASMA for n in historico[-3:]):
        return {"status": "ATIVADO", "principais": [9, 19, 27]}
    return {"status": "INATIVO"}

def validar_gatilho_sequencial_brk(historico_200):
    if not historico_200 or len(historico_200) < 2:
        return {"sinal_ativo": False}
    dezena_atual = historico_200[-1]
    dezena_anterior = historico_200[-2]

    if dezena_atual == 0:
        soma, diferenca = 10, 10
    else:
        d1, d2 = dezena_atual // 10, dezena_atual % 10
        soma = (d1 + d2) if (d1 + d2) <= 10 else ((d1 + d2) // 10 + (d1 + d2) % 10)
        diferenca = abs(d2 - d1)

    grupo_confirmado = soma if soma == dezena_anterior else (diferenca if diferenca == dezena_anterior else None)
    if grupo_confirmado is None or grupo_confirmado not in TABELA_OCULTOS_BRK:
        return {"sinal_ativo": False}

    grupo_completo = TABELA_OCULTOS_BRK[grupo_confirmado]
    amostra_200 = historico_200[-200:]
    dezenas_prioritarias = [num for num in grupo_completo if num not in amostra_200]
    dezenas_cobertura = [num for num in grupo_completo if num in amostra_200]

    return {
        "sinal_ativo": True,
        "grupo_confirmado": grupo_confirmado,
        "prioridade_maxima": dezenas_prioritarias,
        "cobertura": dezenas_cobertura,
        "grupo_completo": grupo_completo
    }

# ==========================================
# 3. NOVO CÁLCULO DE SCORE PONDERADO 🔥
# ==========================================
def calcular_score_ponderado_num(num, sub_historico, res_brk, puxadores, vizinhos):
    score = 0.0
    pontos = {
        "vizinho": 0.0,
        "quente_100r": 0.0,
        "dois_filtros": 0.0,
        "px_top1": 0.0,
        "ausente": 0.0
    }
    detalhes = []

    # 1. Ausente no BRK (+3.0)
    if res_brk.get("sinal_ativo") and num in res_brk.get("prioridade_maxima", []):
        score += 3.0
        pontos["ausente"] = 3.0
        detalhes.append("Ausente(+3.0)")

    # 2. É Puxador Top 1 (+2.5)
    if puxadores and num == puxadores[0]:
        score += 2.5
        pontos["px_top1"] = 2.5
        detalhes.append("PxTop1(+2.5)")

    # 3. Apareceu em 2 ou mais filtros (+2.0)
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

    # 4. Quente nas 200 rodadas (+1.0)
    if len(sub_historico) >= 50:
        amostra = sub_historico[-200:]
        frequencia = amostra.count(num)
        if frequencia > (len(amostra) / 37):
            score += 1.0
            pontos["quente_100r"] = 1.0
            detalhes.append("Quente100R(+1.0)")

    # 5. É Vizinho Físico (+1.0)
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

    filtros_ativos_contagem = 0
    if res_brk["sinal_ativo"]: filtros_ativos_contagem += 1
    if puxadores: filtros_ativos_contagem += 1
    filtros_ativos_contagem += 1 # Vizinhos sempre ativos
    if invertido is not None: filtros_ativos_contagem += 1

    alvos_brutos = set()
    if res_brk["sinal_ativo"]: alvos_brutos.update(res_brk["grupo_completo"])
    if puxadores: alvos_brutos.update(puxadores[:2])
    alvos_brutos.update([vizinhos["esq_1"], vizinhos["dir_1"]])
    if invertido is not None: alvos_brutos.add(invertido)

    # Avalia Score Ponderado 🔥 de cada alvo
    scores_alvos = {}
    pontos_alvos = {}
    detalhes_alvos = {}
    for num in alvos_brutos:
        sc, pts, det = calcular_score_ponderado_num(num, sub_historico, res_brk, puxadores, vizinhos)
        scores_alvos[num] = sc
        pontos_alvos[num] = pts
        detalhes_alvos[num] = det

    alvos_ordenados = sorted(scores_alvos.keys(), key=lambda x: scores_alvos[x], reverse=True)
    score_maximo = max(scores_alvos.values()) if scores_alvos else 0.0

    # Ponderação média do Top Alvo para preencher a linha da tabela
    top_num = alvos_ordenados[0] if alvos_ordenados else None
    top_pontos = pontos_alvos.get(top_num, {"vizinho": 0.0, "quente_100r": 0.0, "dois_filtros": 0.0, "px_top1": 0.0, "ausente": 0.0})

    return {
        "ultimo": ultimo,
        "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores": str(puxadores[:2]),
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)),
        "racetrack": max(SETORES_ROLETA, key=lambda s: sum(1 for n in sub_historico[-10:] if n in SETORES_ROLETA[s])) if len(sub_historico)>=10 else "-",
        "inversao": f"{ultimo}➔{invertido}" if invertido is not None else "-",
        "reincidencia": str([n for n in alvos_brutos if n in sub_historico[-14:][-3:]]) if any(n in sub_historico[-14:][-3:] for n in alvos_brutos) else "-",
        "confirmacoes": "🔴 " * min(filtros_ativos_contagem, 5),
        "score_base": f"{min(filtros_ativos_contagem, 5)}/5",
        "alvos": alvos_ordenados,
        "scores_alvos": scores_alvos,
        "detalhes_alvos": detalhes_alvos,
        "top_pontos": top_pontos,
        "score_maximo": score_maximo,
        "dados_brk": res_brk
    }

# ==========================================
# 4. DISPARO DE ALERTA TELEGRAM (RIGOROSO ≥ 7.5)
# ==========================================
def enviar_alerta_telegram_score75(ultimo_num, alvos_filtrados, scores_alvos, detalhes_alvos):
    linhas_alvos = []
    for num in alvos_filtrados:
        sc = scores_alvos.get(num, 0.0)
        det = ", ".join(detalhes_alvos.get(num, []))
        linhas_alvos.append(f"• *{num:02d}* ➔ Score 🔥 `{sc}` _({det})_")

    texto_alvos = "\n".join(linhas_alvos)

    mensagem = (
        f"🚨 *SINAL DE ALTA CONFIRMAÇÃO (SCORE ≥ 7.5)* 🚨\n\n"
        f"📌 *Último Número:* `{ultimo_num}`\n"
        f"🛡️ *Proteção OBRIGATÓRIA:* `0 (Zero)`\n\n"
        f"🎯 *ALVOS SELECIONADOS:*\n{texto_alvos}\n\n"
        f"⚠️ *Entrada Recomendada: Manter aposta de 3 a 4 rodadas.*"
    )
    return enviar_mensagem_telegram(mensagem)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    if tipo == "GREEN":
        msg = f"✅ *GREEN CONFIRMADO!* 🎉\n\n🎯 Número Bateu: `{numero}`\n📍 Momento: `{etapa}`"
    else:
        msg = f"❌ *RED / LOSS* 😔\n\n📌 Último Sorteado: `{numero}`\n⚠️ Limite de Gales atingido."
    return enviar_mensagem_telegram(msg)

# ==========================================
# 5. EXECUÇÃO DO STREAMLIT & ENGINE
# ==========================================
st.title("🎯 Radar de Roleta Pro - Tabela com Score 🔥 Ponderado")

if "historico" not in st.session_state:
    st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0

st.sidebar.header("🕹️ Painel de Operação")
modo_operacao = st.sidebar.selectbox("🌐 Modo de Operação:", ["On-line (Captura Automática)", "Off-line (Digitação Manual)"])
roleta_selecionada = st.sidebar.selectbox("🎰 Selecionar Roleta:", list(URLS_ROLETAS.keys()))

def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")

        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            enviar_resultado_telegram("LOSS", num_novo)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return

    if len(st.session_state.historico) >= 10:
        historico_analise = list(reversed(st.session_state.historico))
        res = analisar_rodada_especifica(historico_analise)

        alvos_qualificados = [num for num in res["alvos"] if res["scores_alvos"].get(num, 0.0) >= 7.5]

        if alvos_qualificados and not st.session_state.sinal_ativo:
            st.session_state.sinal_ativo = True
            st.session_state.alvos_sinal = alvos_qualificados
            st.session_state.tentativa_atual = 0

            enviar_alerta_telegram_score75(
                res["ultimo"],
                alvos_qualificados,
                res["scores_alvos"],
                res["detalhes_alvos"]
            )

# Controle de Dados (Online x Manual)
if modo_operacao == "On-line (Captura Automática)":
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    if novos_dados and novos_dados != st.session_state.historico:
        num_novo = novos_dados[0]
        processar_novo_numero(num_novo)
        st.session_state.historico = novos_dados
else:
    with st.sidebar.form(key="form_manual", clear_on_submit=True):
        input_num = st.number_input("Número Sorteado:", min_value=0, max_value=36, step=1, value=None)
        if st.form_submit_button("➕ Adicionar (Enter)") and input_num is not None:
            n = int(input_num)
            processar_novo_numero(n)
            st.session_state.historico.insert(0, n)
            st.rerun()

# ==========================================
# 6. TABELA ANALÍTICA COM COLUNAS DE SCORE 🔥
# ==========================================
if st.session_state.historico:
    st.markdown("---")
    st.subheader(f"📊 Mapeamento Analítico com Níveis de Pontuação - {roleta_selecionada}")

    dados_tabela = []
    janela_exibicao = st.session_state.historico[:10]

    for idx, num in enumerate(janela_exibicao):
        sub_hist = list(reversed(st.session_state.historico[idx:]))
        res = analisar_rodada_especifica(sub_hist)

        pts = res.get("top_pontos", {})
        sc_max = res.get("score_maximo", 0.0)
        alvos_top = [n for n in res["alvos"] if res["scores_alvos"].get(n, 0.0) >= 7.5]
        status_txt = f"SINAL: {alvos_top}" if alvos_top else "AGUARDAR"

        dados_tabela.append({
            "Posição": f"Pos {idx+1:02d}",
            "Último": res["ultimo"],
            "Esquerda": res["esquerda"],
            "Direita": res["direita"],
            "Puxadores Híbridos": res["puxadores"],
            "Vizinhos Físicos": res["vizinhos_str"],
            "Camuflados": res["camuflados"],
            "Racetrack": res["racetrack"],
            "Inversão": res["inversao"],
            "Reincidência": res["reincidencia"],
            
            # NOVAS COLUNAS DA SUA IMAGEM:
            "Vizinho (+1,0)": f"+{pts.get('vizinho', 0.0)}" if pts.get('vizinho', 0.0) > 0 else "-",
            "+Quent 100R (+1,0)": f"+{pts.get('quente_100r', 0.0)}" if pts.get('quente_100r', 0.0) > 0 else "-",
            "+2F (+2,0)": f"+{pts.get('dois_filtros', 0.0)}" if pts.get('dois_filtros', 0.0) > 0 else "-",
            "Px top1 (+2,5)": f"+{pts.get('px_top1', 0.0)}" if pts.get('px_top1', 0.0) > 0 else "-",
            "Ausente (+3,0)": f"+{pts.get('ausente', 0.0)}" if pts.get('ausente', 0.0) > 0 else "-",
            "SCORE 🔥": sc_max,
            
            "Confirmações": res["confirmacoes"],
            "Score Base": res["score_base"],
            "Status / Sugestão": status_txt
        })

    df_exibicao = pd.DataFrame(dados_tabela)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
else:
    st.info("Aguardando inserção de dados para gerar a tabela analítica...")
