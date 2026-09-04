import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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

URLS_ROLETAS = {
    "XXXtreme Lightning": "https://api.core.public.tipminer.com/v1/roulette/rounds/e640b7c7-aaba-4ffa-a678-6b6872898162/history?limit=200",
    "Roleta Brasileira": "https://api.core.public.tipminer.com/v1/roulette/rounds/45d12dd3-8f85-4ab2-8c86-4eaea7967e10/history?limit=200",
    "Immersive Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4452-4723-a97d-f3703302d5cc/history?limit=200",
    "Swedish Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-40d2-b479-a28a01c6ee13/history?limit=200"
}

VIZINHOS_ZERO = [1, 5, 8, 11, 14, 23, 26, 32]

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def obter_vizinhos_mesa(num):
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
    camu.update([viz["esq_1"], viz["dir_1"]])
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
            "rodadas_restantes": 4  # ⬅️ Duração recomendada
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
# INTEGRAÇÃO API
# ==========================================
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
        resp = session.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            dados = resp.json()
            if isinstance(dados, dict):
                dados = dados.get("result", dados.get("data", dados.get("results", [])))
            numeros = []
            if isinstance(dados, list):
                for item in dados:
                    if isinstance(item, dict):
                        val = item.get("result", item.get("number", item.get("value")))
                        if val is not None and isinstance(val, (int, float)):
                            numeros.append(int(val))
                    elif isinstance(item, (int, float)):
                        numeros.append(int(item))
            return numeros[:200]
        else:
            st.sidebar.warning(f"API retornou status: {resp.status_code}")
            return []
    except Exception as e:
        st.sidebar.warning(f"Erro na API: {str(e)[:60]}...")
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
        f"🚨 *ALERTA DE SINAL DETECTADO* 🚨\n\n"
        f"🎰 *Roleta:* `{roleta_nome}`\n"
        f"🎲 *Último Número:* `{ultimo}`\n"
        f"🔥 *Score do Sinal:* `{score}/5`\n"
        f"🏆 *Tier:* `{tier_nome}` (Rank: {pos_str} | Assertividade: {taxa_str})\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"📋 *Padrões Identificados:* {', '.join(padroes)}"
    )
    return enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa="", roleta_nome="Desconhecida"):
    emoji = "✅" if tipo == "GREEN" else "❌"
    msg = f"{emoji} *RESULTADO: {tipo}* {f'({etapa})' if etapa else ''}\n🎰 Roleta: `{roleta_nome}`\n🎲 Número Sorteado: `{numero}`"
    return enviar_mensagem_telegram(msg)

# ==========================================
# MOTOR DE IMPACTO
# ==========================================
def processar_tiro_certo_e_headshot(esteira_14, historico_200, dados_brk_in, puxadores_dict, inversoes_dict, vizinhos_fisi_dict, quentes_100):
    ativacoes = {num: set() for num in esteira_14}
    detalhes_pesos = {num: 0.0 for num in esteira_14}
    for num in esteira_14:
        peso = 0.0
        if any(v in esteira_14 for v in vizinhos_fisi_dict.get(num, [])):
            ativacoes[num].add("Vizinho")
            peso += 1.0
        if num in quentes_100:
            ativacoes[num].add("+Quente 100R")
            peso += 1.0
        if esteira_14.count(num) >= 2:
            ativacoes[num].add("+2F")
            peso += 2.0
        pxs = puxadores_dict.get(num, [])
        if pxs and pxs[0] in esteira_14:
            ativacoes[num].add("Px top1")
            peso += 2.5
        if num in dados_brk_in.get("ausentes", []):
            ativacoes[num].add("Ausente")
            peso += 3.0
        if num in esteira_14[1:14]:
            ativacoes[num].add("Ult 13")
            peso += 1.0
        detalhes_pesos[num] = peso
    alvos_tiro_certo = [int(num) for num, p in detalhes_pesos.items() if p >= 4.0]
    alvos_headshot = [int(num) for num, p in detalhes_pesos.items() if p >= 6.5]
    status_nome = "AGUARDAR"
    if alvos_headshot:
        status_nome = "🎯 HEAD-SHOT"
    elif alvos_tiro_certo:
        status_nome = "🔥 TIRO CERTO"
    return {
        "ativacoes": ativacoes,
        "detalhes_pesos": detalhes_pesos,
        "alvos_tiro_certo": alvos_tiro_certo,
        "alvos_headshot": alvos_headshot,
        "status_nome": status_nome
    }

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
        res = analisar_rodada_especifica(sub_hist)
        if res.get("score_num", 0) >= 4:
            futuro = amostra_200[idx:idx+3]
            alvos_zero = set(res.get("alvos", []) + [0])
            hit = any(n in alvos_zero for n in futuro)
            registros.append({
                "Padrão": res.get("padrao_nome", "Desconhecido"),
                "Total de Sinais": 1,
                "Acertos": 1 if hit else 0
            })
    if not registros:
        return {}, pd.DataFrame()
    df_reg = pd.DataFrame(registros)
    estudo = df_reg.groupby("Padrão").agg(
        Total=("Total de Sinais", "sum"),
        Acertos=("Acertos", "sum")
    ).reset_index()
    estudo["Taxa de Acerto (%)"] = round((estudo["Acertos"] / estudo["Total"]) * 100, 1)
    estudo_filtrado = estudo[estudo["Taxa de Acerto (%)"] >= 50.0]
    estudo_ordenado = estudo_filtrado.sort_values(
        by=["Taxa de Acerto (%)", "Total"], ascending=[False, False]
    ).reset_index(drop=True)
    lista_ordenada = estudo_ordenado["Padrão"].tolist()
    tiers = {
        "ELITE_TOP_3": lista_ordenada[:3],
        "SELECAO_OURO_TOP_5": lista_ordenada[:5],
        "SELECAO_TOP_10": lista_ordenada[:10],
        "RADAR_TOP_30": lista_ordenada[:30]
    }
    return tiers, estudo_ordenado

def obter_tiers_cache():
    hist_atual = len(st.session_state.get("historico", []))
    if ("tier_cache" not in st.session_state or
        st.session_state.get("tier_cache_tamanho", -1) != hist_atual):
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = \
            classificar_padroes_200_rodadas(st.session_state.get("historico", []))
        st.session_state["tier_cache_tamanho"] = hist_atual
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

# ==========================================
# MOTOR DE SCORING
# ==========================================
def analisar_rodada_especifica(sub_historico, houve_troca=False):
    if not sub_historico:
        return {}
    ultimo = sub_historico[-1]
    score = 0
    alvos = set()
    filtros_ativos = []

    res_brk = validar_gatilho_sequencial_brk(sub_historico)
    if res_brk["sinal_ativo"]:
        score += 1
        filtros_ativos.append(f"OcultosBRK(G{res_brk['grupo_confirmado']})")
        alvos.update(res_brk["grupo_completo"])

    puxadores = obter_puxadores_otimizados(ultimo, sub_historico)
    if puxadores:
        score += 1
        filtros_ativos.append("Puxadores")
        alvos.update(puxadores[:2])

    vizinhos = obter_vizinhos_mesa(ultimo)
    score += 1
    filtros_ativos.append("Vizinhos")
    alvos.update([vizinhos["esq_1"], vizinhos["dir_1"]])

    invertido = obter_dezena_invertida(ultimo)
    str_inversao = f"{ultimo}➔{invertido}" if invertido is not None else "-"
    if invertido is not None:
        score += 1
        filtros_ativos.append("Inversão")
        alvos.add(invertido)

    fantasma = checar_estrategia_fantasma(sub_historico)
    if fantasma["status"] == "ATIVADO":
        score += 1
        filtros_ativos.append("Fantasma")
        alvos.update(fantasma["principais"])

    if houve_troca and ultimo in VIZINHOS_ZERO:
        score += 1
        filtros_ativos.append("VizinhosZero")
        alvos.update([0, 10, 20, 30])

    esteira_14 = sub_historico[-14:]
    reincidencia = [num for num in alvos if num in esteira_14[-3:]]
    if reincidencia:
        score += 1
        filtros_ativos.append("Reincidência")

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
            filtros_ativos.append("Racetrack")

    score_final = min(score, 5)

    if res_brk["sinal_ativo"]:
        alvos_ausentes = [int(n) for n in res_brk["prioridade_maxima"] if n in alvos]
        outros_alvos = [int(n) for n in sorted(list(alvos)) if n not in alvos_ausentes]
        alvos_ordenados = alvos_ausentes + outros_alvos
    else:
        alvos_ordenados = [int(n) for n in sorted(list(alvos))]

    padrao_nome = " + ".join(filtros_ativos) if filtros_ativos else "Geral"
    return {
        "ultimo": int(ultimo),
        "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores": str(puxadores[:2]),
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)),
        "racetrack": setor_dom,
        "inversao": str_inversao,
        "reincidencia": str(reincidencia) if reincidencia else "-",
        "confirmacoes": "🔴 " * len(filtros_ativos),
        "score": f"{score_final}/5",
        "status": "AGUARDAR" if score_final < 4 else f"SINAL: {alvos_ordenados}",
        "alvos": alvos_ordenados,
        "score_num": score_final,
        "padrao_nome": padrao_nome,
        "dados_brk": res_brk
    }

# ==========================================
# INICIALIZAÇÃO DE ESTADO
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

for chave, padrao in [
    ("historico", []),
    ("sinal_ativo", False),
    ("alvos_sinal", []),
    ("tentativa_atual", 0),
    ("ultimo_resultado", None),
    ("ultima_busca_api", 0),
    ("erros_consecutivos_api", 0),
    ("brk_rodadas_contagem", 0),   # ⬅️ NOVO: Contador BRK
    ("brk_grupo_ativo", None)       # ⬅️ NOVO: Grupo ativo BRK
]:
    if chave not in st.session_state:
        st.session_state[chave] = padrao

# ==========================================
# PROCESSAMENTO DE NOVO NÚMERO
# ==========================================
def processar_novo_numero(num_novo, roleta_nome, filtro_opcao, modo_gale):
    # Contador BRK — decrementa rodadas restantes se houver grupo ativo
    if st.session_state.brk_grupo_ativo:
        st.session_state.brk_rodadas_contagem -= 1
        if st.session_state.brk_rodadas_contagem <= 0:
            st.session_state.brk_grupo_ativo = None  # Expirou

    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")

        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome, roleta_nome=roleta_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            enviar_resultado_telegram("LOSS", num_novo, roleta_nome=roleta_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return

    if len(st.session_state.historico) >= 20:
        historico_analise = list(reversed(st.session_state.historico))
        res_ultimo = analisar_rodada_especifica(historico_analise)

        # ✅ ATUALIZA ESTADO DO BRK_OURO quando gatilho dispara
        brk_dados = res_ultimo.get("dados_brk", {})
        if brk_dados.get("sinal_ativo"):
            st.session_state.brk_grupo_ativo = brk_dados["grupo_confirmado"]
            st.session_state.brk_rodadas_contagem = brk_dados["rodadas_restantes"]

        if res_ultimo.get("score_num", 0) >= 4:
            tiers, df_rank = obter_tiers_cache()
            padrao = res_ultimo.get("padrao_nome", "")

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

            if permitido:
                if st.session_state.sinal_ativo:
                    if "Fusão" in modo_gale and tier_do_padrao == "👑 Elite (Top 3)":
                        alvos_novos_brutos = [n for n in res_ultimo["alvos"] if n not in st.session_state.alvos_sinal]
                        if res_ultimo.get("dados_brk", {}).get("sinal_ativo"):
                            prioridades = res_ultimo["dados_brk"].get("prioridade_maxima", [])
                            alvos_novos_filtrados = [n for n in alvos_novos_brutos if n in prioridades]
                            if not alvos_novos_filtrados:
                                alvos_novos_filtrados = alvos_novos_brutos[:2]
                        else:
                            alvos_novos_filtrados = alvos_novos_brutos[:3]
                        limite_maximo_alvos = 8
                        vagas_disponiveis = limite_maximo_alvos - len(st.session_state.alvos_sinal)
                        if vagas_disponiveis > 0 and alvos_novos_filtrados:
                            alvos_para_adicionar = alvos_novos_filtrados[:vagas_disponiveis]
                            st.session_state.alvos_sinal.extend(alvos_para_adicionar)
                            enviar_mensagem_telegram(
                                f"🔄 *FUSÃO AFUNILADA (GALE)*\n"
                                f"🎰 Roleta: `{roleta_nome}`\n"
                                f"Dezenas adicionadas: `{alvos_para_adicionar}`\n"
                                f"🎯 Alvos Totais (Máx {limite_maximo_alvos}): `{st.session_state.alvos_sinal}`"
                            )
                else:
                    st.session_state.sinal_ativo = True
                    st.session_state.alvos_sinal = res_ultimo["alvos"][:8]
                    st.session_state.tentativa_atual = 0
                    enviar_alerta_telegram(
                        res_ultimo["ultimo"],
                        res_ultimo["score_num"],
                        st.session_state.alvos_sinal,
                        [res_ultimo["status"]],
                        roleta_nome=roleta_selecionada,
                        tier_nome=tier_do_padrao,
                        posicao_rank=posicao_rank,
                        taxa_acerto=taxa_acerto
                    )

    st.session_state.historico.insert(0, num_novo)

# ==========================================
# PAINEL LATERAL
# ==========================================
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
# EXECUÇÃO DO MODO DE OPERAÇÃO
# ==========================================
if modo_operacao == "On-line (Captura Automática)":
    agora = time.time()
    intervalo_busca = 15
    if agora - st.session_state.ultima_busca_api > intervalo_busca:
        novos_dados = buscar_dados_roleta_url(roleta_selecionada)
        st.session_state.ultima_busca_api = agora
        if novos_dados:
            st.session_state.erros_consecutivos_api = 0
            st.sidebar.success(f"🟢 Conectado: **{roleta_selecionada}**")
            if novos_dados != st.session_state.historico:
                num_novo = novos_dados[0]
                processar_novo_numero(num_novo, roleta_selecionada, filtro_hibrido_opcao, modo_gale_opcao)
                st.session_state.historico = novos_dados
        else:
            st.session_state.erros_consecutivos_api += 1
            st.sidebar.warning(f"🟡 Tentando reconectar... (Erros: {st.session_state.erros_consecutivos_api})")
            if st.session_state.erros_consecutivos_api >= 5:
                st.sidebar.error("🔌 Muitas falhas — trocando para Modo Manual...")
                modo_operacao = "Off-line (Digitação Manual)"
else:
    st.sidebar.warning(f"🟠 Modo Manual ativo: **{roleta_selecionada}**")
    with st.sidebar.form(key="form_entrada_manual", clear_on_submit=True):
        novo_numero_input = st.number_input(
            "Número Sorteado (Manual):", min_value=0, max_value=36, step=1,
            value=None, placeholder="Digite de 0 a 36 e tecle Enter"
        )
        submetido = st.form_submit_button("➕ Adicionar Número (Enter)")
        if submetido and novo_numero_input is not None:
            num = int(novo_numero_input)
            processar_novo_numero(num, roleta_selecionada, filtro_hibrido_opcao, modo_gale_opcao)
            st.rerun()
    if st.sidebar.button("🧹 Limpar Histórico"):
        st.session_state.historico = []
        st.session_state.sinal_ativo = False
        st.session_state.alvos_sinal = []
        st.session_state.tentativa_atual = 0
        st.session_state.ultimo_resultado = None
        st.session_state.brk_grupo_ativo = None
        st.session_state.brk_rodadas_contagem = 0
        for chave in ["tier_cache", "df_rank_cache", "tier_cache_tamanho"]:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()

# ==========================================
# 🎯 PAINEL EXCLUSIVO BRK_OURO — NOVO!
# ==========================================
st.markdown("---")
st.header("🏆 PAINEL BRK_OURO — Sinais de Grupo Oculto")

if len(st.session_state.historico) >= 2:
    historico_cron = list(reversed(st.session_state.historico))
    res_brk = validar_gatilho_sequencial_brk(historico_cron)
else:
    res_brk = {"sinal_ativo": False}

# Definir cores e rótulos dos grupos
cores_grupos = {
    "GRUPO_A": "#FFD700",   # Ouro
    "GRUPO_B": "#00C853",   # Verde
    "GRUPO_C": "#2196F3"    # Azul
}
nomes_grupos = {
    "GRUPO_A": "🟡 GRUPO A — Terminação 1, 2, 3",
    "GRUPO_B": "🟢 GRUPO B — Terminação 4, 5, 6",
    "GRUPO_C": "🔵 GRUPO C — Terminação 7, 8, 9, 0"
}

col_status, col_contagem = st.columns([3, 1])

with col_status:
    if res_brk["sinal_ativo"] or st.session_state.brk_grupo_ativo:
        grupo_ativo = res_brk["grupo_confirmado"] if res_brk["sinal_ativo"] else st.session_state.brk_grupo_ativo
        rodadas_restantes = res_brk.get("rodadas_restantes", st.session_state.brk_rodadas_contagem)
        
        st.markdown(f"""
        <div style="padding: 16px; border-radius: 10px; background-color: {cores_grupos[grupo_ativo]}20; 
                    border: 3px solid {cores_grupos[grupo_ativo]};">
            <h3 style="margin:0; color:{cores_grupos[grupo_ativo]};">✅ {nomes_grupos[grupo_ativo]} — ATIVO!</h3>
            <p style="font-size:16px; margin:8px 0 0 0;">
                ✅ Gatilho confirmado: mesma dezena em rodadas consecutivas
            </p>
        </div>
        """, unsafe_allow_html=True)

        c_prio, c_cob = st.columns(2)
        with c_prio:
            st.subheader("🔥 PRIORIDADE MÁXIMA")
            st.caption("Números que NÃO saíram nas últimas 200 rodadas — apostar PRIMEIRO")
            prio = res_brk.get("prioridade_maxima", []) if res_brk["sinal_ativo"] else []
            if prio:
                st.code(f"🎯 {prio}", language=None)
            else:
                st.info("Todos os números já saíram — cobrir o grupo completo")

        with c_cob:
            st.subheader("🛡️ COBERTURA")
            st.caption("Números que JÁ saíram no histórico do grupo")
            cob = res_brk.get("cobertura", []) if res_brk["sinal_ativo"] else []
            if cob:
                st.code(f"✅ {cob}", language=None)
            else:
                st.info("Nenhum número do grupo apareceu ainda")

        st.subheader("📋 GRUPO COMPLETO")
        st.caption("Números totais do grupo — manter cobertura nas próximas rodadas")
        st.code(f"🎰 {res_brk.get('grupo_completo', GRUPO_OCULTO_BRK.get(grupo_ativo, []))}", language=None)

        with col_contagem:
            st.metric(label="⏱️ Rodadas Restantes", value=f"{rodadas_restantes}")
            st.progress(rodadas_restantes / 4)
            st.caption("Recomendado: 3–4 rodadas de cobertura")

    else:
        st.info("⏳ Aguardando gatilho BRK_OURO...\n\n> 💡 Condição: **dois números seguidos da mesma dezena** (ex: 12 → 13 = dezena 1 repetida → Grupo A ativado)")
        
        # Mostrar os 3 grupos para referência
        ga, gb, gc = st.columns(3)
        with ga:
            st.markdown("🟡 **GRUPO A**")
            st.caption("1, 2, 3, 11, 12, 13, 21, 22, 23, 31, 32, 33")
        with gb:
            st.markdown("🟢 **GRUPO B**")
            st.caption("4, 5, 6, 14, 15, 16, 24, 25, 26, 34, 35, 36")
        with gc:
            st.markdown("🔵 **GRUPO C**")
            st.caption("7, 8, 9, 10, 17, 18, 19, 20, 27, 28, 29, 30")

st.markdown("---")

# ==========================================
# VISUALIZAÇÃO DA ESTEIRA TEMPORAL
# ==========================================
st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)
else:
    st.info("Aguardando captura do primeiro sorteio na mesa...")

# ==========================================
# ALERTA BRK (compatível com código original)
# ==========================================
if len(st.session_state.historico) >= 2:
    historico_cron = list(reversed(st.session_state.historico))
    res_brk_painel = validar_gatilho_sequencial_brk(historico_cron)
    if res_brk_painel["sinal_ativo"]:
        st.success(f"🎯 **GATILHO OCULTO BRK CONFIRMADO PARA O GRUPO {res_brk_painel['grupo_confirmado']}!**")
        st.markdown(f"**Validação:** A dezena recente `{res_brk_painel['dezena_gatilho']}` confirmou a dezena anterior `{res_brk_painel['dezena_confirmada']}`.")

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
    else:
        st.error(f"⚠️ Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")

# ==========================================
# MAPEAMENTO ANALÍTICO
# ==========================================
if st.session_state.historico:
    st.markdown("---")
    esteira_14 = st.session_state.historico[:14]
    historico_200 = list(reversed(st.session_state.historico[:200]))
    res_brk = validar_gatilho_sequencial_brk(historico_200)
    dados_brk_in = {
        "ausentes": res_brk.get("prioridade_maxima", []) if res_brk.get("sinal_ativo") else [],
        "cobertura": res_brk.get("cobertura", []) if res_brk.get("sinal_ativo") else []
    }
    puxadores_dict = {n: TABELA_PUXADORES_FIXA.get(n, []) for n in range(37)}
    vizinhos_fisi_dict = {
        n: [obter_vizinhos_mesa(n)["esq_1"], obter_vizinhos_mesa(n)["dir_1"]]
        for n in range(37)
    }
    contagem_100 = pd.Series(historico_200[-100:]).value_counts()
    quentes_100 = set(contagem_100.head(10).index.tolist()) if not contagem_100.empty else set()
    res_tiro_certo = processar_tiro_certo_e_headshot(
        esteira_14, historico_200, dados_brk_in,
        puxadores_dict, {}, vizinhos_fisi_dict, quentes_100
    )
    dados_tabela = []
    for idx, num in enumerate(esteira_14):
        sub_hist = list(reversed(st.session_state.historico[idx:]))
        res = analisar_rodada_especifica(sub_hist)
        ativacoes_num = res_tiro_certo["ativacoes"].get(num, set())
        dezenas_vizinhos = vizinhos_fisi_dict.get(num, [])
        puxs_lista = puxadores_dict.get(num, [])
        px_top1 = [puxs_lista[0]] if len(puxs_lista) > 0 else []
        sugestao = res_tiro_certo["status_nome"] if idx == 0 else res.get("status", "AGUARDAR")
        if res_tiro_certo["alvos_headshot"] and idx == 0:
            sugestao += f": {[int(x) for x in res_tiro_certo['alvos_headshot']]}"
        elif res_t
