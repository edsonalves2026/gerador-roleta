import time
import uuid
import urllib.parse
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# ==========================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro", layout="wide")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# CONSTANTES
# ==========================================
ROULETTE_CYLINDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

NUMEROS_VERMELHOS = {
    1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36
}

SETORES_ROLETA = {
    "Voisins du Zéro": [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    "Tiers du Cylindre": [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    "Orphelins": [1, 20, 14, 31, 9, 17, 34, 6]
}

TABELA_PUXADORES_FIXA = {
    0: [26, 32], 1: [20, 14], 2: [21, 25], 3: [35, 26], 4: [19, 21],
    5: [24, 10], 6: [27, 34], 7: [29, 28], 8: [30, 23], 9: [31, 22],
    10: [5, 23], 11: [36, 30], 12: [28, 35], 13: [27, 36], 14: [20, 31],
    15: [32, 19], 16: [24, 33], 17: [34, 6], 18: [22, 29], 19: [15, 4],
    20: [1, 14], 21: [4, 2], 22: [9, 18], 23: [8, 10], 24: [5, 16],
    25: [2, 17], 26: [0, 3], 27: [6, 13], 28: [7, 12], 29: [18, 7],
    30: [11, 8], 31: [14, 9], 32: [0, 15], 33: [16, 1], 34: [17, 6],
    35: [3, 12], 36: [13, 11]
}

GRUPO_OCULTO_BRK = {
    "GRUPO_A": [1, 2, 3, 11, 12, 13, 21, 22, 23, 31, 32, 33],
    "GRUPO_B": [4, 5, 6, 14, 15, 16, 24, 25, 26, 34, 35, 36],
    "GRUPO_C": [7, 8, 9, 10, 17, 18, 19, 20, 27, 28, 29, 30]
}

# Endpoints base higienizados sem query strings hardcoded
URLS_ROLETAS = {
    "XXXtreme Lightning": "https://api.core.public.tipminer.com/v1/roulette/rounds/e640b7c7-aaba-4ffa-a678-6b6872898162/history",
    "Roleta Brasileira": "https://api.core.public.tipminer.com/v1/roulette/rounds/45d12dd3-8f85-4ab2-8c86-4eaea7967e10/history",
    "Immersive Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4452-4723-a97d-f3703302d5cc/history",
    "Swedish Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-40d2-b479-a28a01c6ee13/history"
}

VIZINHOS_ZERO = [1, 5, 8, 11, 14, 23, 26, 32]

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def obter_vizinhos_mesa(num):
    if num not in ROULETTE_CYLINDER:
        return {"esq_2": None, "esq_1": None, "dir_1": None, "dir_2": None}
    idx = ROULETTE_CYLINDER.index(num)
    n = len(ROULETTE_CYLINDER)
    return {
        "esq_2": ROULETTE_CYLINDER[(idx - 2) % n],
        "esq_1": ROULETTE_CYLINDER[(idx - 1) % n],
        "dir_1": ROULETTE_CYLINDER[(idx + 1) % n],
        "dir_2": ROULETTE_CYLINDER[(idx + 2) % n],
    }

def obter_dezena_invertida(num):
    if num < 10 or num > 36:
        return None
    inv = int(str(num)[::-1])
    return inv if inv <= 36 else None

def obter_camuflados(num):
    inv = obter_dezena_invertida(num)
    viz = obter_vizinhos_mesa(num)
    camu = set()
    if inv is not None:
        camu.add(inv)
    if viz["esq_1"] is not None:
        camu.add(viz["esq_1"])
    if viz["dir_1"] is not None:
        camu.add(viz["dir_1"])
    return sorted(list(camu))

def obter_puxadores_otimizados(ultimo, sub_historico):
    base_puxadores = TABELA_PUXADORES_FIXA.get(ultimo, [])
    if len(sub_historico) >= 30:
        ocorrencias = [
            sub_historico[i+1] for i in range(len(sub_historico)-1)
            if sub_historico[i] == ultimo
        ]
        if ocorrencias:
            mais_frequente = pd.Series(ocorrencias).mode()
            if not mais_frequente.empty:
                num_freq = int(mais_frequente.iloc[0])
                if num_freq not in base_puxadores:
                    return [num_freq] + base_puxadores[:1]
    return base_puxadores

def validar_gatilho_sequencial_brk(sub_historico):
    if len(sub_historico) < 2:
        return {"sinal_ativo": False}
    d1 = sub_historico[-2] // 10
    d2 = sub_historico[-1] // 10
    grupo_detectado = None
    for grupo, nums in GRUPO_OCULTO_BRK.items():
        if sub_historico[-1] in nums:
            grupo_detectado = grupo
            break
    if d1 == d2 and grupo_detectado:
        todos_grupo = GRUPO_OCULTO_BRK[grupo_detectado]
        ausentes = [n for n in todos_grupo if n not in sub_historico[-200:]]
        cobertura = [n for n in todos_grupo if n in sub_historico[-200:]]
        return {
            "sinal_ativo": True,
            "grupo_confirmado": grupo_detectado,
            "dezena_gatilho": d2,
            "dezena_confirmada": d1,
            "grupo_completo": todos_grupo,
            "prioridade_maxima": ausentes,
            "cobertura": cobertura,
            "rodadas_restantes": 4
        }
    return {"sinal_ativo": False}

def checar_estrategia_fantasma(sub_historico):
    if len(sub_historico) < 5:
        return {"status": "INATIVO"}
    ultimos_5 = sub_historico[-5:]
    seis_duzias = [n for n in ultimos_5 if n != 0]
    if len(seis_duzias) == 5:
        duzias = [(n-1)//12 for n in seis_duzias]
        if len(set(duzias)) == 1:
            return {"status": "ATIVADO", "principais": ultimos_5[-2:]}
    return {"status": "INATIVO"}

def calcular_estatisticas(amostra):
    total = len(amostra)
    if total == 0:
        return {}
    return {
        "d1": sum(1 for n in amostra if 1 <= n <= 12),
        "d2": sum(1 for n in amostra if 13 <= n <= 24),
        "d3": sum(1 for n in amostra if 25 <= n <= 36),
        "c1": sum(1 for n in amostra if n > 0 and n % 3 == 1),
        "c2": sum(1 for n in amostra if n > 0 and n % 3 == 2),
        "c3": sum(1 for n in amostra if n > 0 and n % 3 == 0),
        "par": sum(1 for n in amostra if n > 0 and n % 2 == 0),
        "impar": sum(1 for n in amostra if n % 2 != 0),
        "baixas": sum(1 for n in amostra if 1 <= n <= 18),
        "altas": sum(1 for n in amostra if 19 <= n <= 36),
        "total": total
    }

# ==========================================
# 🎯 FILTRO TIRO CERTO + HEAD-SHOT
# ==========================================
def aplicar_filtro_tiro_certo_e_headshot(sub_historico, res_brk, puxadores, invertido, vizinhos, quentes_100):
    pontuacao_numeros = {n: 0.0 for n in range(0, 37)}
    detalhe_pesos = {n: {} for n in range(0, 37)}
    origem_filtros = []

    brk_ausentes = res_brk.get("prioridade_maxima", [])
    brk_cobertura = res_brk.get("cobertura", [])
    for n in brk_ausentes:
        pontuacao_numeros[n] += 3.0
        detalhe_pesos[n]["Ausente"] = 3.0
    for n in brk_cobertura:
        pontuacao_numeros[n] += 1.5
        detalhe_pesos[n]["BRK-Cob"] = 1.5
    if brk_ausentes or brk_cobertura:
        origem_filtros.append("BRK")

    if puxadores:
        pontuacao_numeros[puxadores[0]] += 2.5
        detalhe_pesos[puxadores[0]]["Px top 1"] = 2.5
        if len(puxadores) > 1:
            pontuacao_numeros[puxadores[1]] += 1.5
            detalhe_pesos[puxadores[1]]["Px top 2"] = 1.5
        origem_filtros.append("Puxador")

    if invertido is not None:
        pontuacao_numeros[invertido] += 1.5
        detalhe_pesos[invertido]["Inversão"] = 1.5
        origem_filtros.append("Inversão")

    viz_list = [vizinhos.get("esq_1"), vizinhos.get("dir_1")]
    for n in viz_list:
        if n is not None:
            pontuacao_numeros[n] += 1.0
            detalhe_pesos[n]["Vizinhos"] = 1.0

    for n in range(0, 37):
        if pontuacao_numeros[n] > 0 and n in quentes_100:
            pontuacao_numeros[n] += 1.0
            detalhe_pesos[n]["+Quente 100R"] = 1.0

    if len(sub_historico) >= 13:
        pos13 = sub_historico[-13]
        pontuacao_numeros[pos13] += 1.0
        detalhe_pesos[pos13]["Ult 13"] = 1.0

    todos_candidatos = brk_ausentes + brk_cobertura + (puxadores[:2] if puxadores else []) + ([invertido] if invertido else []) + [n for n in viz_list if n is not None]
    frequencia = Counter(todos_candidatos)
    for n, qtd in frequencia.items():
        if qtd > 1:
            bonus = (qtd - 1) * 2.0
            pontuacao_numeros[n] += bonus
            detalhe_pesos[n][f"2F×{qtd}"] = bonus

    numeros_ordenados = sorted(pontuacao_numeros.items(), key=lambda x: x[1], reverse=True)
    alvos_tiro_certo = [num for num, score in numeros_ordenados if score >= 3.0][:7]

    amostra_30 = sub_historico[-30:] if len(sub_historico) >= 30 else sub_historico
    amostra_5 = sub_historico[-5:] if len(sub_historico) >= 5 else sub_historico
    dezenas_ouro = []
    for num in alvos_tiro_certo:
        score_num = pontuacao_numeros[num]
        estava_ativa_30 = num in amostra_30
        nao_saiu_ultimas_5 = num not in amostra_5
        eh_brk_ausente = num in brk_ausentes
        eh_brk_cobertura_quente = (num in brk_cobertura) and estava_ativa_30
        passou_maturacao = eh_brk_ausente or eh_brk_cobertura_quente
        if score_num >= 7.5 and passou_maturacao and nao_saiu_ultimas_5:
            dezenas_ouro.append(num)

    alvos_headshot = sorted(dezenas_ouro[:4])
    tem_headshot = len(alvos_headshot) >= 2

    assinatura = "+".join(sorted(set(origem_filtros))) if origem_filtros else "Convergência"
    if tem_headshot:
        status_nome = f"💥 HEAD-SHOT [{assinatura}] Score≥7.5"
    elif len(alvos_tiro_certo) >= 4:
        status_nome = f"🎯 TIRO CERTO [{assinatura}] Score≥3.0"
    else:
        status_nome = "⏳ AGUARDAR — Pontuação insuficiente"

    top_score_val = numeros_ordenados[0][1] if numeros_ordenados else 0.0

    return {
        "sinal_ativo": len(alvos_tiro_certo) >= 4,
        "tem_headshot": tem_headshot,
        "alvos_tiro_certo": sorted(alvos_tiro_certo),
        "alvos_headshot": alvos_headshot if tem_headshot else [],
        "nome_padrao": status_nome,
        "top_score": top_score_val,
        "pontuacao": pontuacao_numeros,
        "detalhe_pesos": detalhe_pesos
    }

# ==========================================
# INTEGRAÇÃO API — OTIMIZADA E ESTRUTURADA
# ==========================================
def buscar_dados_roleta_url(roleta_nome):
    url_base = URLS_ROLETAS.get(roleta_nome)
    if not url_base:
        return []

    params = {
        "limit": "200",
        "timezone": "America/Sao_Paulo",
        "_cb": str(uuid.uuid4())
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.tipminer.com/",
        "Origin": "https://www.tipminer.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }

    try:
        session = requests.Session()
        resp = session.get(url_base, params=params, headers=headers, timeout=10)

        if resp.status_code == 200:
            dados = resp.json()
            numeros = []
            
            # Tratamento adaptativo caso o retorno seja dict {'data': [...]} ou list direto
            itens = dados.get("data", dados) if isinstance(dados, dict) else dados
            
            if isinstance(itens, list):
                for item in itens:
                    if isinstance(item, dict):
                        val = item.get("result")
                        if val is not None and isinstance(val, (int, float)):
                            numeros.append(int(val))
            return numeros[:200]
        else:
            st.sidebar.warning(f"API Status: {resp.status_code}")
            return []
    except Exception as e:
        st.sidebar.warning(f"Erro ao buscar API: {str(e)[:80]}")
        return []

# ==========================================
# TELEGRAM
# ==========================================
def enviar_mensagem_telegram(texto):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Credenciais do Telegram não configuradas."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code == 200, "Mensagem enviada com sucesso!"
    except Exception as e:
        return False, str(e)

def enviar_alerta_telegram(ultimo, score, alvos, padroes, roleta_nome="Desconhecida", tier_nome="Indefinido", posicao_rank=None, taxa_acerto=None):
    pos_str = f"#{posicao_rank}" if posicao_rank else "N/A"
    taxa_str = f"{taxa_acerto}%" if taxa_acerto is not None else "N/A"
    msg = (
        f"🚨 *SINAL DISPARADO* 🚨\n\n"
        f"🎰 *Roleta:* `{roleta_nome}`\n"
        f"🎲 *Último Número:* `{ultimo}`\n"
        f"🔥 *Score do Sinal:* `{score}`\n"
        f"🏆 *Tier:* `{tier_nome}` (Rank: {pos_str} | Assertividade: {taxa_str})\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"📋 *Padrão:* {padroes}"
    )
    return enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa="", roleta_nome="Desconhecida"):
    emoji = "✅" if tipo == "GREEN" else "❌"
    msg = f"{emoji} *RESULTADO: {tipo}* {f'({etapa})' if etapa else ''}\n🎰 Roleta: `{roleta_nome}`\n🎲 Número Sorteado: `{numero}`"
    return enviar_mensagem_telegram(msg)

# ==========================================
# CLASSIFICADOR DE TIERS
# ==========================================
def classificar_padroes_200_rodadas(historico_completo):
    amostra_200 = list(reversed(historico_completo[:200]))
    if len(amostra_200) < 20:
        return {}, pd.DataFrame()
    registros = []
    for idx in range(10, len(amostra_200) - 2):
        sub_hist = amostra_200[:idx]
        res_brk = validar_gatilho_sequencial_brk(sub_hist)
        ultimo = sub_hist[-1]
        puxadores = obter_puxadores_otimizados(ultimo, sub_hist)
        inv = obter_dezena_invertida(ultimo)
        viz = obter_vizinhos_mesa(ultimo)
        contagem_100 = pd.Series(sub_hist[-100:] if len(sub_hist)>=100 else sub_hist).value_counts()
        quentes_100 = set(contagem_100.head(10).index.tolist()) if not contagem_100.empty else set()
        res_tiro = aplicar_filtro_tiro_certo_e_headshot(sub_hist, res_brk, puxadores, inv, viz, quentes_100)
        if res_tiro.get("tem_headshot"):
            futuro = amostra_200[idx:idx+3]
            hit = any(n in res_tiro["alvos_headshot"] for n in futuro)
            registros.append({"Padrão": res_tiro["nome_padrao"], "Total": 1, "Acertos": 1 if hit else 0})
    if not registros:
        return {}, pd.DataFrame()
    df_reg = pd.DataFrame(registros)
    estudo = df_reg.groupby("Padrão").agg(Total=("Total", "sum"), Acertos=("Acertos", "sum")).reset_index()
    estudo["Taxa de Acerto (%)"] = round((estudo["Acertos"] / estudo["Total"]) * 100, 1)
    estudo = estudo.sort_values(by=["Taxa de Acerto (%)", "Total"], ascending=[False, False]).reset_index(drop=True)
    lista = estudo["Padrão"].tolist()
    tiers = {
        "ELITE_TOP_3": lista[:3],
        "SELECAO_OURO_TOP_5": lista[:5],
        "SELECAO_TOP_10": lista[:10],
        "RADAR_TOP_30": lista[:30]
    }
    return tiers, estudo

def obter_tiers_cache():
    hist_atual = len(st.session_state.get("historico", []))
    if ("tier_cache" not in st.session_state or st.session_state.get("tier_cache_tamanho", -1) != hist_atual):
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = classificar_padroes_200_rodadas(st.session_state.get("historico", []))
        st.session_state["tier_cache_tamanho"] = hist_atual
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

# ==========================================
# INICIALIZAÇÃO DE ESTADO
# ==========================================
st.title("🎯 Radar de Roleta Pro — TIRO CERTO + HEAD-SHOT")

for chave, padrao in [
    ("historico", []), ("sinal_ativo", False), ("alvos_sinal", []),
    ("tentativa_atual", 0), ("ultimo_resultado", None), ("ultima_busca_api", 0),
    ("erros_consecutivos_api", 0), ("brk_rodadas_contagem", 0), ("brk_grupo_ativo", None)
]:
    if chave not in st.session_state:
        st.session_state[chave] = padrao

# ==========================================
# PROCESSAMENTO DE NOVO NÚMERO
# ==========================================
def processar_novo_numero(num_novo, roleta_nome, filtro_opcao, modo_gale):
    if st.session_state.brk_grupo_ativo:
        st.session_state.brk_rodadas_contagem -= 1
        if st.session_state.brk_rodadas_contagem <= 0:
            st.session_state.brk_grupo_ativo = None

    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")
        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            st.session_state.ultimo_resultado = f"✅ GREEN ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome, roleta_nome=roleta_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            st.session_state.ultimo_resultado = "❌ LOSS"
            enviar_resultado_telegram("LOSS", num_novo, roleta_nome=roleta_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return

    if len(st.session_state.historico) >= 10:
        historico_cron = list(reversed(st.session_state.historico))
        janela_validacao = historico_cron[-3:] if len(historico_cron)>=3 else historico_cron
        if len(historico_cron)>=13:
            janela_validacao.append(historico_cron[-13])

        res_brk = validar_gatilho_sequencial_brk(historico_cron)
        if res_brk["sinal_ativo"]:
            st.session_state.brk_grupo_ativo = res_brk["grupo_confirmado"]
            st.session_state.brk_rodadas_contagem = res_brk["rodadas_restantes"]

        ultimo = historico_cron[-1]
        puxadores = obter_puxadores_otimizados(ultimo, historico_cron)
        inv = obter_dezena_invertida(ultimo)
        viz = obter_vizinhos_mesa(ultimo)
        amostra_100 = historico_cron[-100:] if len(historico_cron)>=100 else historico_cron
        contagem_100 = pd.Series(amostra_100).value_counts()
        quentes_100 = set(contagem_100.head(10).index.tolist()) if not contagem_100.empty else set()

        res_tiro = aplicar_filtro_tiro_certo_e_headshot(historico_cron, res_brk, puxadores, inv, viz, quentes_100)

        if res_tiro["sinal_ativo"]:
            tiers, df_rank = obter_tiers_cache()
            padrao = res_tiro["nome_padrao"]
            score_val = res_tiro["top_score"]

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
            if filtro_opcao == "Desativado (Usar apenas regras fixas)":
                permitido = True
            elif filtro_opcao == "🥉 Radar (Top 30 - Permissivo)" and tier_do_padrao != "Fora dos Tiers":
                permitido = True
            elif filtro_opcao == "🥈 Seleção (Top 10 - Equilibrado)" and tier_do_padrao in ["👑 Elite (Top 3)", "🥇 Seleção Ouro (Top 5)", "🥈 Seleção (Top 10)"]:
                permitido = True
            elif filtro_opcao == "🥇 Seleção Ouro (Top 5 - Conservador)" and tier_do_padrao in ["👑 Elite (Top 3)", "🥇 Seleção Ouro (Top 5)"]:
                permitido = True
            elif filtro_opcao == "👑 Elite (Top 3 - Máxima Precisão)" and tier_do_padrao == "👑 Elite (Top 3)":
                permitido = True

            alvos_para_usar = res_tiro["alvos_headshot"] if res_tiro["tem_headshot"] else res_tiro["alvos_tiro_certo"]

            if permitido and not st.session_state.sinal_ativo:
                st.session_state.sinal_ativo = True
                st.session_state.alvos_sinal = alvos_para_usar
                st.session_state.tentativa_atual = 0

                if res_tiro["tem_headshot"]:
                    enviar_alerta_telegram(ultimo, f"{score_val:.1f}/7.5", alvos_para_usar, padrao, roleta_nome=roleta_nome, tier_nome=tier_do_padrao, posicao_rank=posicao_rank, taxa_acerto=taxa_acerto)
                elif score_val >= 5.0:
                    enviar_alerta_telegram(ultimo, f"{score_val:.1f}/7.5", alvos_para_usar, padrao, roleta_nome=roleta_nome, tier_nome=tier_do_padrao, posicao_rank=posicao_rank, taxa_acerto=taxa_acerto)

    st.session_state.historico.insert(0, num_novo)

# ==========================================
# PAINEL LATERAL
# ==========================================
st.sidebar.header("🕹️ Painel de Operação")
modo_operacao = st.sidebar.selectbox("🌐 Modo de Operação:", ["On-line (Captura Automática)", "Off-line (Digitação Manual)"])
roleta_selecionada = st.sidebar.selectbox("🎰 Selecionar Roleta:", list(URLS_ROLETAS.keys()))
st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Filtro Híbrido de Assertividade")
filtro_hibrido_opcao = st.sidebar.selectbox(
    "Nível de Filtragem dos Sinais:",
    [
        "Desativado (Usar apenas regras fixas)",
        "🥉 Radar (Top 30 - Permissivo)",
        "🥈 Seleção (Top 10 - Equilibrado)",
        "🥇 Seleção Ouro (Top 5 - Conservador)",
        "👑 Elite (Top 3 - Máxima Precisão)"
    ], index=2
)
st.sidebar.markdown("---")

# ==========================================
# MODO AUTOMÁTICO - CORRIGIDO SEM TRAVAMENTO
# ==========================================
if modo_operacao == "On-line (Captura Automática)":
    st.markdown("🔄 **Modo Automático Ativo — Verificando a cada 15s...**")

    agora = time.time()
    if agora - st.session_state.ultima_busca_api > 15:
        st.session_state.ultima_busca_api = agora
        novos_dados = buscar_dados_roleta_url(roleta_selecionada)

        if novos_dados and len(novos_dados) > 0:
            st.session_state.erros_consecutivos_api = 0
            st.sidebar.success(f"🟢 Conectado: **{roleta_selecionada}** — {len(novos_dados)} rodadas")

            ultimo_novo = novos_dados[0]
            ultimo_atual = st.session_state.historico[0] if st.session_state.historico else None

            if ultimo_atual is not None and ultimo_novo != ultimo_atual:
                st.success(f"🆕 NOVO NÚMERO → **{ultimo_novo}**")
                processar_novo_numero(ultimo_novo, roleta_selecionada, filtro_hibrido_opcao, None)
                st.session_state.historico = novos_dados
                st.rerun()

            if ultimo_atual is None:
                st.session_state.historico = novos_dados
                st.rerun()
        else:
            st.session_state.erros_consecutivos_api += 1
            st.sidebar.warning(f"🟡 Falha na busca ({st.session_state.erros_consecutivos_api}/5)")
            if st.session_state.erros_consecutivos_api >= 5:
                st.error("🔌 Muitas falhas — verifique a conexão ou os parâmetros da API.")

    tempo_passado = int(time.time() - st.session_state.ultima_busca_api)
    proxima = max(0, 15 - tempo_passado)
    st.info(f"⏳ Próxima verificação em **{proxima}s**")
    
    time.sleep(1)
    st.rerun()

else:
    st.sidebar.warning(f"🟠 Modo Manual: **{roleta_selecionada}**")
    with st.sidebar.form(key="form_manual", clear_on_submit=True):
        num_input = st.number_input("Número Sorteado:", 0, 36, step=1)
        if st.form_submit_button("➕ Adicionar"):
            processar_novo_numero(num_input, roleta_selecionada, filtro_hibrido_opcao, None)
            st.rerun()
    if st.sidebar.button("🧹 Limpar Histórico"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ==========================================
# 🏆 PAINEL BRK_OURO
# ==========================================
st.markdown("---")
st.header("🏆 PAINEL BRK_OURO")

if len(st.session_state.historico) >= 2:
    h_cron = list(reversed(st.session_state.historico))
    res_brk_painel = validar_gatilho_sequencial_brk(h_cron)
else:
    res_brk_painel = {"sinal_ativo": False}

cores_grupos = {"GRUPO_A": "#FFD700", "GRUPO_B": "#00C853", "GRUPO_C": "#2196F3"}
nomes_grupos = {
    "GRUPO_A": "🟡 GRUPO A — Termina em 1,2,3",
    "GRUPO_B": "🟢 GRUPO B — Termina em 4,5,6",
    "GRUPO_C": "🔵 GRUPO C — Termina em 7,8,9,0"
}

if res_brk_painel["sinal_ativo"] or st.session_state.brk_grupo_ativo:
    grupo_ativo = res_brk_painel["grupo_confirmado"] if res_brk_painel["sinal_ativo"] else st.session_state.brk_grupo_ativo
    rest = res_brk_painel.get("rodadas_restantes", st.session_state.brk_rodadas_contagem)
    st.markdown(f"""
    <div style="padding:16px; border-radius:10px; background:{cores_grupos.get(grupo_ativo, '#FFF')}20; border:3px solid {cores_grupos.get(grupo_ativo, '#000')};">
        <h3 style="margin:0; color:{cores_grupos.get(grupo_ativo, '#000')};">✅ {nomes_grupos.get(grupo_ativo, 'GRUPO')} — ATIVO!</h3>
        <p>Gatilho: mesma dezena em rodadas consecutivas</p>
    </div>""", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🔥 PRIORIDADE MÁXIMA (Ausentes)")
        prio = res_brk_painel.get("prioridade_maxima", [])
        st.code(f"{prio}" if prio else "Todos já saíram")
    with c2:
        st.subheader("🛡️ COBERTURA (Já saíram)")
        cob = res_brk_painel.get("cobertura", [])
        st.code(f"{cob}" if cob else "Nenhum apareceu ainda")
    st.metric("⏱️ Rodadas Restantes", rest)
    st.progress(min(max(rest / 4.0, 0.0), 1.0))
else:
    st.info("⏳ Aguardando gatilho: mesma dezena em 2 rodadas seguidas.")
    ga, gb, gc = st.columns(3)
    ga.markdown("🟡 **A:** 1,2,3,11,12,13,21,22,23,31,32,33")
    gb.markdown("🟢 **B:** 4,5,6,14,15,16,24,25,26,34,35,36")
    gc.markdown("🔵 **C:** 7,8,9,10,17,18,19,20,27,28,29,30")

# ==========================================
# ESTEIRA TEMPORAL
# ==========================================
st.markdown("---")
st.subheader("📋 Esteira Temporal (Últimas 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(len(esteira))
    for i, n in enumerate(esteira):
        with cols[i]:
            st.metric(f"Pos {i+1}", n)
else:
    st.info("Aguardando dados...")

# ==========================================
# 📊 MAPEAMENTO ANALÍTICO COM SCORE PONDERADO
# ==========================================
st.markdown("---")
st.header("📊 MAPEAMENTO ANALÍTICO — Score Ponderado 🔥")

if len(st.session_state.historico) >= 10:
    h_cron = list(reversed(st.session_state.historico))
    res_brk_map = validar_gatilho_sequencial_brk(h_cron)
    ultimo = h_cron[-1]
    puxadores_map = obter_puxadores_otimizados(ultimo, h_cron)
    inv_map = obter_dezena_invertida(ultimo)
    viz_map = obter_vizinhos_mesa(ultimo)
    amostra_100_map = h_cron[-100:] if len(h_cron)>=100 else h_cron
    quentes_100_map = set(pd.Series(amostra_100_map).value_counts().head(10).index.tolist())
    res_tiro_map = aplicar_filtro_tiro_certo_e_headshot(h_cron, res_brk_map, puxadores_map, inv_map, viz_map, quentes_100_map)

    st.subheader("🎯 Resultado TIRO CERTO / HEAD-SHOT")
    if res_tiro_map["tem_headshot"]:
        st.success(f"💥 **HEAD-SHOT ATIVO!** {res_tiro_map['nome_padrao']}")
        st.code(f"Alvos: {res_tiro_map['alvos_headshot']}  |  Score: {res_tiro_map['top_score']:.1f}/7.5")
    elif res_tiro_map["sinal_ativo"]:
        st.info(f"🎯 TIRO CERTO — {res_tiro_map['nome_padrao']}")
        st.code(f"Alvos: {res_tiro_map['alvos_tiro_certo']}  |  Score: {res_tiro_map['top_score']:.1f}/7.5")
    else:
        st.warning("⏳ Aguardando convergência mínima (Score ≥ 3.0, mínimo 4 alvos)")

    st.subheader("📋 Detalhamento dos Pesos por Número Candidato")
    linhas = []
    for num in res_tiro_map["alvos_tiro_certo"]:
        pesos = res_tiro_map["detalhe_pesos"].get(num, {})
        score_final = res_tiro_map["pontuacao"][num]
        linhas.append({
            "Número": num,
            "Ausente (+3.0)": pesos.get("Ausente", "-"),
            "Px top 1 (+2.5)": pesos.get("Px top 1", "-"),
            "2F Convergência": next((v for k,v in pesos.items() if k.startswith("2F")), "-"),
            "+Quente 100R (+1.0)": pesos.get("+Quente 100R", "-"),
            "Vizinhos (+1.0)": pesos.get("Vizinhos", "-"),
            "Ult 13 (+1.0)": pesos.get("Ult 13", "-"),
            "Score Final 🔥": f"{score_final:.1f}"
        })
    if linhas:
        st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

# ==========================================
# ESTATÍSTICAS
# ==========================================
st.markdown("---")
st.subheader("📈 Estatísticas — Últimas 200 Rodadas")
if st.session_state.historico:
    ultimas = st.session_state.historico[:200]
    qtd = len(ultimas)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 🔥 Quentes / Frias")
        if qtd >= 10:
            cont = pd.Series(ultimas).value_counts().reindex(range(37), fill_value=0)
            quentes = cont.sort_values(ascending=False).head(12)
            frias = cont.sort_values(ascending=True).head(12)
            fig = go.Figure([
                go.Bar(name='Mais Sorteados', x=quentes.index, y=quentes.values, marker_color='#FF4444'),
                go.Bar(name='Menos Sorteados', x=frias.index, y=frias.values, marker_color='#4488FF')
            ])
            fig.update_layout(barmode='group', height=300, margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Dados insuficientes ({qtd}/10)")

    with c2:
        st.markdown("### 📐 Dúzias / Colunas / Paridade")
        if qtd >= 12:
            est = calcular_estatisticas(ultimas)
            categorias = ['D1\n1-12', 'D2\n13-24', 'D3\n25-36', 'C1', 'C2', 'C3', 'Pares', 'Ímpares', 'Baixas\n1-18', 'Altas\n19-36']
            valores = [
                est.get('d1', 0), est.get('d2', 0), est.get('d3', 0),
                est.get('c1', 0), est.get('c2', 0), est.get('c3', 0),
                est.get('par', 0), est.get('impar', 0),
                est.get('baixas', 0), est.get('altas', 0)
            ]
            cores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#2ECC71', '#E74C3C', '#3498DB', '#E67E22']
            fig2 = go.Figure(data=[go.Bar(x=categorias, y=valores, marker_color=cores)])
            fig2.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=60), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info(f"Dados insuficientes ({qtd}/12)")

    with c3:
        st.markdown("### 🎨 Mapa de Cores — Últimas 200")
        if qtd > 0:
            linhas_html = []
            for i in range(0, qtd, 10):
                bloco = ultimas[i:i+10]
                html_bloco = "<div style='display:flex;gap:4px;margin:3px 0;'>"
                for n in bloco:
                    if n == 0:
                        bg_cor = "#00AA00"
                    elif n in NUMEROS_VERMELHOS:
                        bg_cor = "#FF2222"
                    else:
                        bg_cor = "#000000"
                    html_bloco += f"<span style='background-color:{bg_cor};color:#FFF;border-radius:4px;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;'>{n}</span>"
                html_bloco += "</div>"
                linhas_html.append(html_bloco)
            st.markdown("".join(linhas_html), unsafe_allow_html=True)
        else:
            st.info("Aguardando dados...")

# ==========================================
# 🚨 SINAL ATIVO — ÁREA DE APOSTA
# ==========================================
st.markdown("---")
st.subheader("🚨 SINAL ATIVO — Área de Aposta")

if st.session_state.sinal_ativo:
    alvos_exibidos = st.session_state.alvos_sinal
    tentativa = st.session_state.tentativa_atual
    etapa_nome = {
        0: "🎯 Entrada Direta",
        1: "📈 Gale 1 (G1)",
        2: "📊 Gale 2 (G2)"
    }.get(tentativa, f"🔄 Tentativa {tentativa}")

    st.warning(f"""
    ⚠️ **SINAL DISPARADO — {etapa_nome}**
    🎰 Roleta: **{roleta_selecionada}**
    🎲 Números Alvo: **{alvos_exibidos}**
    🔢 Total de alvos: **{len(alvos_exibidos)}**
    """)

    cols_alvos = st.columns(len(alvos_exibidos)) if alvos_exibidos else []
    for idx, num in enumerate(alvos_exibidos):
        with cols_alvos[idx]:
            if num == 0:
                cor_fundo = "#00AA00"
            elif num in NUMEROS_VERMELHOS:
                cor_fundo = "#FF2222"
            else:
                cor_fundo = "#000000"
            st.markdown(f"""
            <div style="background-color:{cor_fundo}; color:#FFF; border-radius:8px; 
                        padding:15px; text-align:center; font-size:22px; font-weight:bold;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                {num}
            </div>
            """, unsafe_allow_html=True)

    st.info("""
    💡 **Regras de Aposta:**
    - ✅ Se sair **qualquer número alvo ou o 0** → **GREEN** (Sinal encerrado)
    - ❌ Se errar → avança para a próxima etapa (Gale)
    - 🔄 Após 3 tentativas sem acerto → **LOSS** (Sinal encerrado)
    """)

else:
    st.success("✅ Nenhum sinal ativo no momento — Aguardando padrões...")

# ==========================================
# 📊 HISTÓRICO DE RESULTADOS
# ==========================================
st.markdown("---")
st.subheader("📊 Histórico de Resultados")

if st.session_state.ultimo_resultado:
    st.markdown(f"**Último Resultado:** {st.session_state.ultimo_resultado}")
else:
    st.info("Nenhum resultado registrado ainda.")

if len(st.session_state.historico) > 0:
    total_rodadas = len(st.session_state.historico)
    ultimo_numero = st.session_state.historico[0]
    st.markdown(f"""
    📋 **Resumo:**
    - Total de rodadas registradas: **{total_rodadas}**
    - Último número sorteado: **{ultimo_numero}**
    - Status do sinal: **{'🔴 ATIVO' if st.session_state.sinal_ativo else '🟢 Inativo'}**
    """)

# ==========================================
# 🏆 RANKING DE PADRÕES
# ==========================================
st.markdown("---")
st.subheader("🏆 Ranking de Padrões — Taxa de Acerto")

tiers, df_rank = obter_tiers_cache()
if not df_rank.empty:
    st.dataframe(df_rank, use_container_width=True, hide_index=True)
else:
    st.info("Dados insuficientes para gerar ranking de padrões (mínimo 20 rodadas necessárias)")

# ==========================================
# 📋 MANUAL DO SISTEMA
# ==========================================
st.markdown("---")
with st.expander("📖 Manual Completo do Sistema — Regras e Funcionamento", expanded=False):
    st.markdown("""
    ### 🎯 Sistema TIRO CERTO + HEAD-SHOT

    **Objetivo:** Identificar padrões estatísticos e sugerir números com maior probabilidade de sair.

    ---
    ### 📐 Critérios de Pontuação
    | Critério | Pontuação |
    |---|---|
    | Número ausente no grupo BRK | +3.0 |
    | Primeiro número mais frequente | +2.5 |
    | Segundo número mais frequente | +1.5 |
    | Número invertido | +1.5 |
    | Vizinhos imediatos | +1.0 cada |
    | Número quente (últimos 100) | +1.0 |
    | Número da posição 13 | +1.0 |
    | Convergência de múltiplos critérios | +2.0 por critério extra |

    **Limiares:**
    - Score ≥ 3.0 → TIRO CERTO (mínimo 4 alvos)
    - Score ≥ 7.5 + maturação → HEAD-SHOT

    ---
    ### 🟢 Regras de Acerto
    - Acertou → **GREEN** ✅ (sinal encerrado)
    - Errou → avança para **G1**, depois **G2**
    - 3 erros seguidos → **LOSS** ❌

    ---
    ### 🎛️ Níveis de Filtro
    - **Desativado:** emite todos os sinais detectados
    - **🥉 Radar:** apenas padrões do Top 30
    - **🥈 Seleção:** apenas padrões do Top 10
    - **🥇 Ouro:** apenas padrões do Top 5
    - **👑 Elite:** apenas padrões do Top 3 (maior precisão)
    """)

# ==========================================
# RODAPÉ
# ==========================================
st.markdown("---")
st.caption("""
⚡ Radar de Roleta Pro — Sistema TIRO CERTO + HEAD-SHOT com Score Ponderado
✅ Validação BRK + Padrões Históricos + Ranking de Assertividade
🔄 Atualização automática a cada 15 segundos | 🔔 Alertas via Telegram
""")
