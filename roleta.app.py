import streamlit as st
import pandas as pd
import requests
import random
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURAÇÃO E CREDENCIAIS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Painel Avançado", layout="wide")
st_autorefresh(interval=15000, key="autoupdate_roleta")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# MATRIZES FIXAS E CONFIGURAÇÕES DA MESA
# ==========================================
CILINDRO_EUROPEU = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

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
    1: [1, 10, 19, 28, 34], 2: [2, 11, 20, 29, 24, 35],
    3: [3, 12, 21, 30, 36, 14, 25], 4: [4, 13, 22, 31, 26, 15],
    5: [5, 14, 23, 32, 16, 27], 6: [6, 15, 24, 33, 17],
    7: [7, 16, 25, 34, 14, 29], 8: [8, 17, 26, 35, 19],
    9: [9, 18, 27, 36], 10: [0, 5, 20, 30, 19, 28]
}

TABELA_PUXADORES_FIXA_BRK = {
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
    36: [11, 13, 27, 30]
}

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
# 2. FUNÇÕES AUXILIARES & MOTOR ESTATÍSTICO
# ==========================================
def calcular_estatisticas(amostra):
    if not amostra:
        return {}
    return {
        'd1': sum(1 for n in amostra if 1 <= n <= 12),
        'd2': sum(1 for n in amostra if 13 <= n <= 24),
        'd3': sum(1 for n in amostra if 25 <= n <= 36),
        'c1': sum(1 for n in amostra if n > 0 and n % 3 == 1),
        'c2': sum(1 for n in amostra if n > 0 and n % 3 == 2),
        'c3': sum(1 for n in amostra if n > 0 and n % 3 == 0),
        'par': sum(1 for n in amostra if n > 0 and n % 2 == 0),
        'impar': sum(1 for n in amostra if n % 2 != 0),
        'baixas': sum(1 for n in amostra if 1 <= n <= 18),
        'altas': sum(1 for n in amostra if 19 <= n <= 36)
    }

def buscar_puxadores_dinamicos(numero_alvo, historico, limite_amostra=100):
    amostra = historico[:limite_amostra]
    if len(amostra) < 2:
        return []
    subsequentes = [amostra[i-1] for i in range(1, len(amostra)) if amostra[i] == numero_alvo]
    if not subsequentes:
        return []
    return pd.Series(subsequentes).value_counts().head(4).index.tolist()

def calcular_scores_reais(historico, limite=30):
    if len(historico) < limite:
        return 50.0, 50.0, 0.0, 0.0
    amostra = historico[:limite]
    acertos_din = acertos_brk = tiros_din = tiros_brk = 0
    for i in range(len(amostra) - 1):
        ultimo, proximo = amostra[i+1], amostra[i]
        pux_din = buscar_puxadores_dinamicos(ultimo, amostra[i+1:], limite_amostra=100)
        if pux_din:
            tiros_din += 1
            if proximo in pux_din[:4]: acertos_din += 1
        pux_brk = TABELA_PUXADORES_FIXA_BRK.get(ultimo, [])
        if pux_brk:
            tiros_brk += 1
            if proximo in pux_brk[:4]: acertos_brk += 1
    score_din = round(100 * acertos_din / tiros_din, 1) if tiros_din else 50.0
    score_brk = round(100 * acertos_brk / tiros_brk, 1) if tiros_brk else 50.0
    return score_din, score_brk, round(score_din * 0.45, 1), round(score_brk * 0.40, 1)

def determinar_modo_operacional(score_dinamico, score_brk, seco_dinamico, seco_brk, modo_atual, rodadas_no_modo_atual, trava_cooldown=15):
    diferenca = score_dinamico - score_brk
    if rodadas_no_modo_atual < trava_cooldown:
        return modo_atual, f"🔒 Cooldown ativo ({rodadas_no_modo_atual}/{trava_cooldown} rodadas)"
    if diferenca > 5.0: return "DINAMICO", f"Vantagem Dinâmica > 5% ({diferenca:+.1f}%)"
    elif diferenca < -5.0: return "BRK", f"Vantagem BRK > 5% ({abs(diferenca):.1f}%)"
    else:
        if seco_dinamico > seco_brk: return "DINAMICO", f"Desempate por Tiro Seco ({seco_dinamico}% vs {seco_brk}%)"
        elif seco_brk > seco_dinamico: return "BRK", f"Desempate por Tiro Seco ({seco_brk}% vs {seco_dinamico}%)"
        return (modo_atual if modo_atual else "DINAMICO"), "Inércia / Padrão Mantido"

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
        inv = numero * 10
        return inv if inv <= 36 else None
    inv = int(str(numero)[::-1])
    return inv if inv <= 36 else None

def obter_camuflados(numero):
    soma = sum(int(d) for d in str(numero))
    soma = sum(int(d) for d in str(soma)) if soma > 10 else soma
    return CAMUFLADOS_BASE.get(soma, [])

def checar_estrategia_fantasma(historico):
    if len(historico) >= 3 and all(n in GRUPO_FANTASMA for n in historico[:3]):
        return {"status": "ATIVADO", "principais": [9, 19, 27]}
    return {"status": "INATIVO"}

def validar_gatilho_sequencial_brk(historico):
    if not historico or len(historico) < 2:
        return {"sinal_ativo": False}
    dezena_atual, dezena_anterior = historico[0], historico[1]
    if dezena_atual == 0:
        soma, diferenca = 10, 10
    else:
        d1, d2 = dezena_atual // 10, dezena_atual % 10
        soma, diferenca = d1 + d2, abs(d2 - d1)
        soma = (soma // 10) + (soma % 10) if soma > 10 else soma
    
    grupo_confirmado = soma if soma == dezena_anterior else (diferenca if diferenca == dezena_anterior else None)
    if grupo_confirmado is None or grupo_confirmado not in TABELA_OCULTOS_BRK:
        return {"sinal_ativo": False}
    
    grupo_completo = TABELA_OCULTOS_BRK[grupo_confirmado]
    amostra_30 = set(historico[:30])
    return {
        "sinal_ativo": True, "grupo_confirmado": grupo_confirmado,
        "prioridade_maxima": [num for num in grupo_completo if num not in amostra_30],
        "cobertura": [num for num in grupo_completo if num in amostra_30],
        "grupo_completo": grupo_completo
    }

def analisar_rodada_especifica(sub_historico):
    if not sub_historico:
        return {}
    ultimo = sub_historico[0]
    score = 0
    alvos = set()
    filtros_ativos = []
    
    puxadores_brk = TABELA_PUXADORES_FIXA_BRK.get(ultimo, [])
    puxadores_dinamico = buscar_puxadores_dinamicos(ultimo, sub_historico, limite_amostra=100)
    modo_atual = st.session_state.get("modo_operacional_atual", "DINAMICO")
    puxadores_ativos = puxadores_dinamico if modo_atual == "DINAMICO" and puxadores_dinamico else puxadores_brk
    
    res_brk = validar_gatilho_sequencial_brk(sub_historico)
    if res_brk.get("sinal_ativo"):
        score += 1
        filtros_ativos.append(f"OcultosBRK(G{res_brk['grupo_confirmado']})")
        alvos.update(res_brk["grupo_completo"])
    if puxadores_ativos:
        score += 1
        filtros_ativos.append("Puxadores")
        alvos.update(puxadores_ativos)
    
    vizinhos = obter_vizinhos_mesa(ultimo)
    score += 1
    filtros_ativos.append("Vizinhos")
    alvos.update([vizinhos["esq_1"], vizinhos["dir_1"]])
    
    invertido = obter_dezena_invertida(ultimo)
    if invertido is not None:
        score += 1
        filtros_ativos.append("Inversão")
        alvos.add(invertido)
        
    fantasma = checar_estrategia_fantasma(sub_historico)
    if fantasma["status"] == "ATIVADO":
        score += 1
        filtros_ativos.append("Fantasma")
        alvos.update(fantasma["principais"])
        
    esteira_14 = sub_historico[:14]
    reincidencia = [num for num in alvos if num in esteira_14[:3]]
    if reincidencia:
        score += 1
        filtros_ativos.append("Reincidência")
        
    setor_dom = "-"
    if len(sub_historico) >= 10:
        foco_10 = sub_historico[:10]
        contagem = {s: sum(1 for num in foco_10 if num in nums) for s, nums in SETORES_ROLETA.items()}
        setor_dom = max(contagem, key=contagem.get)
        if any(num in SETORES_ROLETA[setor_dom] for num in alvos):
            score += 1
            filtros_ativos.append("Racetrack")
            
    score_final = min(score, 5)
    alvos_ordenados = sorted(list(alvos))
    
    return {
        "ultimo": ultimo,
        "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores_brk": str(puxadores_brk) if puxadores_brk else "-",
        "puxadores_dinamico": str(puxadores_dinamico) if puxadores_dinamico else "-",
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)),
        "racetrack": setor_dom,
        "inversao": f"{ultimo}➔{invertido}" if invertido is not None else "-",
        "reincidencia": str(reincidencia) if reincidencia else "-",
        "confirmacoes": "🔴 " * len(filtros_ativos),
        "score": f"{score_final}/5",
        "score_num": score_final,
        "status": "AGUARDAR" if score_final < 4 else f"SINAL: {alvos_ordenados}",
        "alvos": alvos_ordenados,
        "padrao_nome": " + ".join(filtros_ativos) if filtros_ativos else "Geral"
    }

def classificar_padroes_200_rodadas(historico_completo):
    amostra_200 = historico_completo[:200]
    if len(amostra_200) < 20:
        return {}, pd.DataFrame()
    registros = []
    for idx in range(len(amostra_200) - 10, 2, -1):
        sub_hist = amostra_200[idx:]
        res = analisar_rodada_especifica(sub_hist)
        if res.get("score_num", 0) >= 4:
            futuro = amostra_200[max(0, idx-3):idx]
            hit = any(n in set(res["alvos"] + [0]) for n in futuro)
            registros.append({"Padrão": res["padrao_nome"], "Total": 1, "Acertos": 1 if hit else 0})
    if not registros:
        return {}, pd.DataFrame()
    df_reg = pd.DataFrame(registros)
    estudo = df_reg.groupby("Padrão").agg(Total=("Total", "sum"), Acertos=("Acertos", "sum")).reset_index()
    estudo["Taxa de Acerto (%)"] = round((estudo["Acertos"] / estudo["Total"]) * 100, 1)
    estudo_ordenado = estudo.sort_values(by=["Taxa de Acerto (%)", "Total"], ascending=[False, False]).reset_index(drop=True)
    lista_ordenada = estudo_ordenado["Padrão"].tolist()
    return {
        "ELITE_TOP_3": lista_ordenada[:3],
        "SELECAO_OURO_TOP_5": lista_ordenada[:5],
        "SELECAO_TOP_10": lista_ordenada[:10],
        "RADAR_TOP_30": lista_ordenada[:30]
    }, estudo_ordenado

def obter_tiers_cache():
    hist_atual = len(st.session_state.historico)
    if "tier_cache" not in st.session_state or st.session_state.get("tier_cache_tamanho", -1) != hist_atual:
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = classificar_padroes_200_rodadas(st.session_state.historico)
        st.session_state["tier_cache_tamanho"] = hist_atual
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

# ==========================================
# 3. BUSCA API E TELEGRAM
# ==========================================
def buscar_dados_roleta_url(roleta_nome):
    config = URLS_ROLETAS.get(roleta_nome, {})
    endpoint = config.get("api_endpoint", "")
    if not endpoint: return st.session_state.get("historico", [])
    try:
        url_completo = f"{endpoint}&t={int(time.time() * 1000)}"
        headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": "https://www.tipminer.com/"}
        res = requests.get(url_completo, headers=headers, timeout=10)
        if res.status_code == 200:
            dados = res.json()
            numeros = [int(item["result"]) for item in dados if isinstance(item, dict) and item.get("result") is not None]
            if numeros: return numeros
    except Exception:
        pass
    return st.session_state.get("historico", [])

def enviar_mensagem_telegram(mensagem):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        return requests.post(url, json=payload, timeout=5).status_code == 200
    except Exception:
        return False

def enviar_alerta_telegram(ultimo_num, score, alvos, detalhes, tier_nome="", posicao_rank=None, taxa_acerto=None, modo_estrategia=""):
    texto_detalhes = "\n".join([f"• {d}" for d in detalhes])
    cabecalho = "💥💥 *ALERTA HEAD-SHOT DISPARADO* 💥💥\n🔥 *Confluência Máxima Nível 5/5*" if "HEAD-SHOT" in tier_nome else "🎯 *SINAL CONFIRMADO - TIRO CERTO*"
    msg = (
        f"{cabecalho}\n\n"
        f"🏆 *Classificação:* `{tier_nome}`\n"
        f"📌 *Último Número:* `{ultimo_num}`\n"
        f"📊 *Score:* `{score}/5` | 🎯 *Alvos:* `{alvos}`\n\n"
        f"🔍 *Filtros Convergentes:*\n{texto_detalhes}"
    )
    enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    msg = f"✅ *GREEN!* (`{numero}`) na etapa `{etapa}`" if tipo == "GREEN" else f"❌ *RED!* (`{numero}`)"
    enviar_mensagem_telegram(msg)

# ==========================================
# 4. INICIALIZAÇÃO DE ESTADOS
# ==========================================
if "historico" not in st.session_state: st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0
    st.session_state.ultimo_resultado = None
if "modo_operacional_atual" not in st.session_state: st.session_state.modo_operacional_atual = "DINAMICO"
if "rodadas_no_modo_atual" not in st.session_state: st.session_state.rodadas_no_modo_atual = 15

score_din, score_brk, seco_din, seco_brk = calcular_scores_reais(st.session_state.historico, limite=30)
modo_ativo, status_motivo = determinar_modo_operacional(
    score_din, score_brk, seco_din, seco_brk,
    st.session_state.modo_operacional_atual, st.session_state.rodadas_no_modo_atual
)
st.session_state.modo_operacional_atual = modo_ativo

# ==========================================
# 5. BARRA LATERAL (OPERAÇÃO)
# ==========================================
st.sidebar.header("🕹️ Painel de Operação")
modo_operacao = st.sidebar.selectbox("🌐 Modo de Operação:", ["On-line (Captura Automática)", "Off-line (Digitação Manual)"])
roleta_selecionada = st.sidebar.selectbox("🎰 Selecionar Roleta:", list(URLS_ROLETAS.keys()))
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Filtro Híbrido de Assertividade (200 Rodadas)")
filtro_hibrido_opcao = st.sidebar.selectbox(
    "Nível de Filtragem dos Sinais:",
    ["Desativado (Usar apenas regras fixas)", "🥉 Radar (Top 30 - Permissivo)", "🥈 Seleção (Top 10 - Equilibrado)", "🥇 Seleção Ouro (Top 5 - Conservador)", "👑 Elite (Top 3 - Máxima Precisão)"],
    index=2
)
st.sidebar.radio("Estratégia no Gale ao detectar novo Sinal Elite:", ["Opção A: Mantém Sinal A (Aposta Fixa)", "Opção B: Fusão de Alvos Únicos (A + B)"], index=1)

def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapa_nome = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual-1}")
        if num_novo in set(st.session_state.alvos_sinal).union({0}):
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome)
            st.session_state.sinal_ativo = False
            return
        elif st.session_state.tentativa_atual >= 3:
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            enviar_resultado_telegram("LOSS", num_novo)
            st.session_state.sinal_ativo = False
            return

    if len(st.session_state.historico) >= 20:
        res_ultimo = analisar_rodada_especifica(st.session_state.historico)
        score_obtido = res_ultimo.get("score_num", 0)
        if score_obtido >= 4:
            tiers, df_rank = obter_tiers_cache()
            padrao = res_ultimo["padrao_nome"]
            tier_do_padrao = "👑 Elite (Top 3)" if padrao in tiers.get("ELITE_TOP_3", []) else ("🥇 Seleção Ouro (Top 5)" if padrao in tiers.get("SELECAO_OURO_TOP_5", []) else ("🥈 Seleção (Top 10)" if padrao in tiers.get("SELECAO_TOP_10", []) else "Fora dos Tiers"))
            
            tipo_operacao = "💥 HEAD-SHOT (MÁXIMA CONFLUÊNCIA)" if score_obtido == 5 and tier_do_padrao == "👑 Elite (Top 3)" else ("🎯 TIRO CERTO" if score_obtido >= 4 else None)
            
            if tipo_operacao:
                st.session_state.sinal_ativo = True
                st.session_state.alvos_sinal = res_ultimo["alvos"]
                st.session_state.tentativa_atual = 1
                enviar_alerta_telegram(res_ultimo["ultimo"], score_obtido, res_ultimo["alvos"], res_ultimo["padrao_nome"].split(" + "), f"{tier_do_padrao} | {tipo_operacao}")

if modo_operacao == "On-line (Captura Automática)":
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    if novos_dados and novos_dados != st.session_state.historico:
        st.session_state.historico = novos_dados
        processar_novo_numero(novos_dados[0])
else:
    num_manual = st.sidebar.number_input("Digitar Número Sorteado (0-36):", min_value=0, max_value=36, step=1)
    if st.sidebar.button("Adicionar Número"):
        st.session_state.historico.insert(0, num_manual)
        processar_novo_numero(num_manual)

# ==========================================
# 6. DASHBOARD VISUAL COMPLETO
# ==========================================

# STATUS DO MODO NO TOPO
cor_modo = "#00E676" if modo_ativo == "DINAMICO" else "#29B6F6"
st.markdown(f"<div style='background-color:#1E1E1E; padding:8px 15px; border-radius:5px; margin-bottom:15px; border-left: 5px solid {cor_modo}'>"
            f"🔵 <b>MODO ATIVO:</b> <span style='color:{cor_modo}'>MODO OCULTOS {modo_ativo}</span> | "
            f"<b>Status:</b> {status_motivo}</div>", unsafe_text_mode=True)

st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

hist = st.session_state.historico

# --- A. ESTEIRA TEMPORAL (ÚLTIMAS 13 RODADAS) ---
st.subheader("Esteira Temporal (Últimas 13 Rodadas)")
if hist:
    cols_esteira = st.columns(min(13, len(hist)))
    for idx, num in enumerate(hist[:13]):
        cor_fundo = "#2E7D32" if num == 0 else ("#D32F2F" if num in VERMELHOS else "#212121")
        with cols_esteira[idx]:
            st.markdown(
                f"<div style='background-color:{cor_fundo}; color:white; font-weight:bold; "
                f"text-align:center; padding:10px; border-radius:5px; font-size:18px;'>{num}</div>",
                unsafe_text_mode=True
            )
else:
    st.info("Aguardando histórico para montagem da esteira...")

# BANNER DE RESULTADO E SINAL ATIVO
if st.session_state.ultimo_resultado:
    bg_res = "#1B5E20" if "GREEN" in st.session_state.ultimo_resultado else "#B71C1C"
    st.markdown(f"<div style='background-color:{bg_res}; padding:8px; border-radius:5px; color:white; font-weight:bold; text-align:center; margin-top:10px;'>"
                f"Resultado do Último Sinal: {st.session_state.ultimo_resultado}</div>", unsafe_text_mode=True)

st.subheader("🚨 Sinal Ativo & Acompanhamento")
if st.session_state.sinal_ativo:
    st.warning(f"🎯 **SINAL IDENTIFICADO:** `{st.session_state.alvos_sinal}` | Tentativa ({st.session_state.tentativa_atual}/3)")
else:
    st.success("✅ Nenhum sinal ativo no momento — Aguardando padrão convergente...")

st.markdown("---")

# --- B. MAPEAMENTO ANALÍTICO (TABELA DETALHADA) ---
st.subheader(f"📊 Mapeamento Analítico — {roleta_selecionada}")
if len(hist) >= 10:
    linhas_tabela = []
    for i in range(min(10, len(hist))):
        sub = hist[i:]
        res = analisar_rodada_especifica(sub)
        linhas_tabela.append({
            "Posição": f"#{i+1}",
            "Último": res["ultimo"],
            "Esq. Mesa": res["esquerda"],
            "Dir. Mesa": res["direita"],
            "Puxadores Dinâmico": res["puxadores_dinamico"],
            "Puxadores Estático": res["puxadores_brk"],
            "Camuflados": res["camuflados"],
            "Racetrack": res["racetrack"],
            "Inversão": res["inversao"],
            "Reincidência": res["reincidencia"],
            "Confirmações": res["confirmacoes"],
            "Score": res["score"],
            "Sinais Sugeridos": str(res["alvos"])
        })
    df_mapa = pd.DataFrame(linhas_tabela)
    st.dataframe(df_mapa, use_container_width=True)
else:
    st.info("Mapeamento analítico aguardando pelo menos 10 rodadas de histórico...")

st.markdown("---")

# --- C. ESTATÍSTICAS E MAPA DE CORES ---
st.subheader("📊 Estatísticas — Últimas 80 Rodadas")
col_e1, col_e2, col_e3 = st.columns([1, 2, 1.5])

amostra_80 = hist[:80]
estats = calcular_estatisticas(amostra_80)

with col_e1:
    st.markdown("**🔥 Quentes / Frias**")
    if amostra_80:
        freq = pd.Series(amostra_80).value_counts()
        st.write("Mais Sorteados:", dict(freq.head(5)))
        st.write("Menos Sorteados:", dict(freq.tail(5)))

with col_e2:
    st.markdown("**📊 Dúzias / Colunas / Paridade**")
    if estats:
        df_chart = pd.DataFrame({
            'Categoria': ['D1', 'D2', 'D3', 'C1', 'C2', 'C3', 'Pares', 'Ímpares', 'Baixas', 'Altas'],
            'Quantidade': [estats['d1'], estats['d2'], estats['d3'], estats['c1'], estats['c2'], estats['c3'], estats['par'], estats['impar'], estats['baixas'], estats['altas']]
        })
        fig = px.bar(df_chart, x='Categoria', y='Quantidade', color='Categoria', text_auto=True)
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with col_e3:
    st.markdown("**🎨 Mapa de Cores — Últimas 80**")
    if amostra_80:
        html_mapa = "<div style='display:flex; flex-wrap:wrap; gap:4px; max-width:280px;'>"
        for num in amostra_80:
            cor = "#00E676" if num == 0 else ("#FF1744" if num in VERMELHOS else "#212121")
            html_mapa += f"<div style='background-color:{cor}; width:22px; height:22px; border-radius:50%; text-align:center; color:white; font-size:11px; font-weight:bold; line-height:22px;'>{num}</div>"
        html_mapa += "</div>"
        st.markdown(html_mapa, unsafe_text_mode=True)

st.markdown("---")

# --- D. RACETRACK / CILINDRO ---
st.subheader("🎯 Mapa de Calor — Distribuição no Cilindro (Racetrack)")
if amostra_80:
    freq_cilindro = pd.Series(amostra_80).value_counts()
    html_race = "<div style='display:flex; gap:2px; overflow-x:auto; padding:10px; background:#121212; border-radius:8px;'>"
    for n in CILINDRO_EUROPEU:
        qtd = freq_cilindro.get(n, 0)
        bg = f"rgba(255, 23, 68, {min(1.0, qtd/5 + 0.1)})" if n in VERMELHOS else (f"rgba(0, 230, 118, {min(1.0, qtd/5 + 0.2)})" if n == 0 else f"rgba(255, 255, 255, {min(1.0, qtd/5 + 0.05)})")
        html_race += f"<div style='background:{bg}; border:1px solid #333; min-width:32px; padding:5px 0; text-align:center; border-radius:4px; font-size:12px;'><b style='color:white;'>{n}</b><br><span style='font-size:10px; color:#aaa;'>{qtd}x</span></div>"
    html_race += "</div>"
    st.markdown(html_race, unsafe_text_mode=True)

st.markdown("---")

# --- E. RANKING DE PADRÕES & PERFORMANCE DAS ESTRATÉGIAS ---
st.subheader("🏆 Ranking de Padrões — Taxa de Acerto Histórica (200 Rodadas)")
tiers_rank, df_rank = obter_tiers_cache()
if not df_rank.empty:
    fig_rank = px.bar(df_rank.head(10), x='Taxa de Acerto (%)', y='Padrão', orientation='h', text_auto=True, color='Taxa de Acerto (%)', color_continuous_scale='Reds')
    fig_rank.update_layout(height=300, yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_rank, use_container_width=True)

    c_t1, c_t2, c_t3, c_t4 = st.columns(4)
    with c_t1: st.info(f"**👑 Elite Top 3:**\n" + "\n".join([f"• {p}" for p in tiers_rank.get("ELITE_TOP_3", [])]))
    with c_t2: st.success(f"**🥇 Ouro Top 5:**\n" + "\n".join([f"• {p}" for p in tiers_rank.get("SELECAO_OURO_TOP_5", [])]))
    with c_t3: st.warning(f"**🥈 Seleção Top 10:**\n" + "\n".join([f"• {p}" for p in tiers_rank.get("SELECAO_TOP_10", [])]))
    with c_t4: st.error(f"**🥉 Radar Top 30:**\n" + "\n".join([f"• {p}" for p in tiers_rank.get("RADAR_TOP_30", [])[:3]]))

st.markdown("---")

st.subheader("📊 Desempenho das Estratégias (Últimas 30 Rodadas)")
cp1, cp2, cp3, cp4 = st.columns(4)
cp1.metric("📌 Dinâmico", f"{score_din}%")
cp2.metric("📌 BRK Fixa", f"{score_brk}%")
cp3.metric("🎯 Tiro Seco Din.", f"{seco_din}%")
cp4.metric("🎯 Tiro Seco BRK", f"{seco_brk}%")
