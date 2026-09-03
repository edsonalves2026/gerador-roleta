# ==========================================
# IMPORTS E CONFIGURAÇÕES INICIAIS
# ==========================================
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# 1. MATRIZ DE POSICIONAMENTO E CONSTANTES
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
    "Brazilian Roulette": "https://api.tipminer.com/v1/roulette/brazilian",
    "VIP Roulette": "https://api.tipminer.com/v1/roulette/vip",
    "Immersive Roulette": "https://api.tipminer.com/v1/roulette/immersive",
    "Auto-Roulette": "https://api.tipminer.com/v1/roulette/auto"
}

TELEGRAM_BOT_TOKEN = "SEU_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "SEU_CHAT_ID_HERE"

# ==========================================
# 2. FUNÇÕES AUXILIARES E INTEGRAÇÃO API
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
    s = str(num)[::-1]
    inv = int(s)
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
                num_freq = mais_frequente.iloc[0]
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
            "cobertura": cobertura
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
    
# SUBSTITUA A FUNÇÃO POR ESTA VERSÃO TRATADA:
def buscar_dados_roleta_url(roleta_nome):
    url = URLS_ROLETAS.get(roleta_nome)
    if not url:
        return []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            dados = resp.json()
            
            # Se for um dicionário, busca a lista dentro de chaves comuns de APIs
            if isinstance(dados, dict):
                dados = dados.get("data", dados.get("results", dados.get("history", [])))
            
            # Se for uma lista direta de inteiros [32, 15, 19, ...]
            if isinstance(dados, list) and len(dados) > 0 and isinstance(dados[0], int):
                return dados[:200]
                
            # Se for uma lista de objetos [{"number": 32}, ...]
            if isinstance(dados, list):
                return [item["number"] for item in dados if isinstance(item, dict) and "number" in item][:200]
                
            st.sidebar.warning("API respondeu, mas o formato dos dados é incompatível.")
            return []
        else:
            st.sidebar.error(f"Servidor Indisponível (HTTP {resp.status_code}). Use o modo manual.")
            return []
    except Exception as e:
        st.sidebar.error("⚠️ Domínio indisponível na nuvem. Alterne para 'Off-line (Digitação Manual)'.")
        return []

# ==========================================
# 3. NOTIFICAÇÕES TELEGRAM
# ==========================================
def enviar_mensagem_telegram(texto):
    if TELEGRAM_BOT_TOKEN == "SEU_BOT_TOKEN_HERE":
        return False, "Token do Bot não configurado."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code == 200, "Mensagem enviada com sucesso!"
    except Exception as e:
        return False, str(e)

def enviar_alerta_telegram(ultimo, score, alvos, padroes, tier_nome="Indefinido", posicao_rank=None, taxa_acerto=None):
    pos_str = f"#{posicao_rank}" if posicao_rank else "N/A"
    taxa_str = f"{taxa_acerto}%" if taxa_acerto is not None else "N/A"
    msg = (
        f"🚨 *ALERTA DE SINAL DETECTADO* 🚨\n\n"
        f"🎰 *Último Número:* `{ultimo}`\n"
        f"🔥 *Score do Sinal:* `{score}/5`\n"
        f"🏆 *Tier:* `{tier_nome}` (Rank: {pos_str} | Assertividade: {taxa_str})\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"📋 *Padrões Identificados:* {', '.join(padroes)}"
    )
    return enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    emoji = "✅" if tipo == "GREEN" else "❌"
    msg = f"{emoji} *RESULTADO: {tipo}* {f'({etapa})' if etapa else ''}\n🎲 Número Sorteado: `{numero}`"
    return enviar_mensagem_telegram(msg)

# ==========================================
# 4. MOTOR DE IMPACTO: TIRO CERTO E HEAD-SHOT
# ==========================================
def processar_tiro_certo_e_headshot(esteira_14, historico_200, dados_brk_in, puxadores_dict, inversoes_dict, vizinhos_fisi_dict, quentes_100):
    ativacoes = {num: set() for num in esteira_14}
    detalhes_pesos = {num: 0.0 for num in esteira_14}
    
    for num in esteira_14:
        peso = 0.0
        # 1. Vizinhos
        if any(v in esteira_14 for v in vizinhos_fisi_dict.get(num, [])):
            ativacoes[num].add("Vizinho")
            peso += 1.0
        # 2. Quentes
        if num in quentes_100:
            ativacoes[num].add("+Quente 100R")
            peso += 1.0
        # 3. Segunda Forma (2F)
        if esteira_14.count(num) >= 2:
            ativacoes[num].add("+2F")
            peso += 2.0
        # 4. Puxador Top 1
        pxs = puxadores_dict.get(num, [])
        if pxs and pxs[0] in esteira_14:
            ativacoes[num].add("Px top1")
            peso += 2.5
        # 5. Ausente BRK
        if num in dados_brk_in.get("ausentes", []):
            ativacoes[num].add("Ausente")
            peso += 3.0
        # 6. Presença nas últimas 13 rodadas
        if num in esteira_14[1:14]:
            ativacoes[num].add("Ult 13")
            peso += 1.0
            
        detalhes_pesos[num] = peso

    alvos_tiro_certo = [num for num, p in detalhes_pesos.items() if p >= 4.0]
    alvos_headshot = [num for num, p in detalhes_pesos.items() if p >= 6.5]

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
# 5. CLASSIFICADOR DE TIERS + CACHE
# ==========================================
def classificar_padroes_200_rodadas(historico_completo):
    amostra_200 = list(reversed(historico_completo[:200]))
    if len(amostra_200) < 20:
        return {}, pd.DataFrame()
    
    registros = []
    for idx in range(10, len(amostra_200) - 2):
        sub_hist = amostra_200[:idx]
        res = analisar_rodada_especifica(sub_hist)
        
        if res["score_num"] >= 4:
            futuro = amostra_200[idx:idx+3]
            alvos_zero = set(res["alvos"] + [0])
            hit = any(n in alvos_zero for n in futuro)
            
            registros.append({
                "Padrão": res["padrao_nome"],
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
    
    # REGRA DE CORREÇÃO: Aplicação estrita do filtro de no mínimo 50% de assertividade
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
    hist_atual = len(st.session_state.historico)
    if ("tier_cache" not in st.session_state or 
        st.session_state.get("tier_cache_tamanho", -1) != hist_atual):
        
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = \
            classificar_padroes_200_rodadas(st.session_state.historico)
        st.session_state["tier_cache_tamanho"] = hist_atual
    
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

# ==========================================
# 6. MOTOR DE SCORAGE (ATUALIZADO COM BRK)
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

    vizinhos_zero = [1, 5, 8, 11, 14, 23, 26, 32]
    if houve_troca and ultimo in vizinhos_zero:
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
        alvos_ausentes = [n for n in res_brk["prioridade_maxima"] if n in alvos]
        outros_alvos = [n for n in sorted(list(alvos)) if n not in alvos_ausentes]
        alvos_ordenados = alvos_ausentes + outros_alvos
    else:
        alvos_ordenados = sorted(list(alvos))

    padrao_nome = " + ".join(filtros_ativos) if filtros_ativos else "Geral"

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
        "confirmacoes": "🔴 " * len(filtros_ativos),
        "score": f"{score_final}/5",
        "status": "AGUARDAR" if score_final < 4 else f"SINAL: {alvos_ordenados}",
        "alvos": alvos_ordenados,
        "score_num": score_final,
        "padrao_nome": padrao_nome,
        "dados_brk": res_brk
    }

# ==========================================
# 7. INTERFACE STREAMLIT
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro", layout="wide")
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

if "historico" not in st.session_state:
    st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0
    st.session_state.ultimo_resultado = None

# Painel Lateral
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

def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")
        
        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            enviar_resultado_telegram("LOSS", num_novo)
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
                            f"Novos alvos adicionados: `{alvos_novos}`\n"
                            f"Alvos Totais: `{st.session_state.alvos_sinal}`"
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

# Modo Online / Manual
if modo_operacao == "On-line (Captura Automática)":
    st.sidebar.info(f"🟢 Conectado: **{roleta_selecionada}**")
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    
    if novos_dados and novos_dados != st.session_state.historico:
        num_novo = novos_dados[0]
        processar_novo_numero(num_novo)
        st.session_state.historico = novos_dados
else:
    st.sidebar.warning(f"🟠 Modo Manual ativo: **{roleta_selecionada}**")
    
    with st.sidebar.form(key="form_entrada_manual", clear_on_submit=True):
        novo_numero_input = st.number_input(
            "Número Sorteado (Manual):", 
            min_value=0, 
            max_value=36, 
            step=1,
            value=None,
            placeholder="Digite de 0 a 36 e tecle Enter"
        )
        submetido = st.form_submit_button("➕ Adicionar Número (Enter)")
        
        if submetido and novo_numero_input is not None:
            num = int(novo_numero_input)
            processar_novo_numero(num)
            st.session_state.historico.insert(0, num)
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

# Visualização Principal
st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)

# ALERTA EXCLUSIVO BRK
if st.session_state.historico and len(st.session_state.historico) >= 2:
    historico_cronologico = list(reversed(st.session_state.historico))
    res_brk_painel = validar_gatilho_sequencial_brk(historico_cronologico)
    
    if res_brk_painel["sinal_ativo"]:
        st.markdown("---")
        st.success(f"🎯 **GATILHO OCULTO BRK CONFIRMADO PARA O GRUPO {res_brk_painel['grupo_confirmado']}!**")
        st.markdown(f"**Validação:** A dezena recente `{res_brk_painel['dezena_gatilho']}` confirmou a dezena anterior `{res_brk_painel['dezena_confirmada']}`.")
        
        c_prio, c_cob = st.columns(2)
        with c_prio:
            st.error(f"🔥 **PRIORIDADE MÁXIMA (Ainda não saíram nas 200 rodadas):**\n\n`{res_brk_painel['prioridade_maxima']}`")
        with c_cob:
            st.warning(f"🛡️ **COBERTURA (Já saíram no histórico):**\n\n`{res_brk_painel['cobertura']}`")
        st.info("⏱️ **Estratégia Recomendada:** Manter apostas neste grupo pelas próximas **3 a 4 rodadas**.")

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
    else:
        st.error(f"⚠️ Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")

# ==========================================
# 8. MAPEAMENTO ANALÍTICO (TIRO CERTO & HEAD-SHOT)
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
    inversoes_dict = {n: obter_dezena_invertida(n) for n in range(37)}
    vizinhos_fisi_dict = {
        n: [obter_vizinhos_mesa(n)["esq_1"], obter_vizinhos_mesa(n)["dir_1"]] 
        for n in range(37)
    }
    
    contagem_100 = pd.Series(historico_200[-100:]).value_counts()
    quentes_100 = set(contagem_100.head(10).index.tolist()) if not contagem_100.empty else set()

    res_tiro_certo = processar_tiro_certo_e_headshot(
        esteira_14,
        historico_200,
        dados_brk_in,
        puxadores_dict,
        inversoes_dict,
        vizinhos_fisi_dict,
        quentes_100
    )

    dados_tabela = []
    for idx, num in enumerate(esteira_14):
        sub_hist = list(reversed(st.session_state.historico[idx:]))
        res = analisar_rodada_especifica(sub_hist)
        
        ativacoes_num = res_tiro_certo["ativacoes"].get(num, set())
        
        dezenas_vizinhos = vizinhos_fisi_dict.get(num, [])
        puxs_lista = puxadores_dict.get(num, [])
        px_top1 = [puxs_lista[0]] if len(puxs_lista) > 0 else []
        dezenas_ausentes = dados_brk_in["ausentes"] if num in dados_brk_in["ausentes"] else []

        sugestao = res_tiro_certo["status_nome"]
        if res_tiro_certo["alvos_headshot"]:
            sugestao += f": {res_tiro_certo['alvos_headshot']}"
        elif res_tiro_certo["alvos_tiro_certo"]:
            sugestao += f": {res_tiro_certo['alvos_tiro_certo']}"

        dados_tabela.append({
            "Último": res["ultimo"],
            "Vizinho (+1.0)": f"🟢 {dezenas_vizinhos}" if "Vizinho" in ativacoes_num else "⚪",
            "+Quente 100R (+1.0)": f"🟢 ({num})" if "+Quente 100R" in ativacoes_num else "⚪",
            "2F (+2.0)": f"🟢 ({num})" if "+2F" in ativacoes_num else "⚪",
            "Px top 1 (+2.5)": f"🟢 {px_top1}" if "Px top1" in ativacoes_num else "⚪",
            "Ausente (+3.0)": f"🟢 ({num})" if "Ausente" in ativacoes_num else "⚪",
            "Ult 13 (+1.0)": f"🟢 ({num})" if "Ult 13" in ativacoes_num else "⚪",
            "Score 🔥": f"{res_tiro_certo['detalhes_pesos'].get(num, 0.0):.1f}",
            "Status / Sugestão": sugestao if idx == 0 else res["status"]
        })
    
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    
    # REGRA DE CORREÇÃO: Índice visual da tabela iniciando estritamente em 1
    df_exibicao = pd.DataFrame(dados_tabela)
    df_exibicao.index = range(1, len(df_exibicao) + 1)
    st.dataframe(df_exibicao, use_container_width=True)

    # Ranking dos Tiers
    tiers_atuais, df_rank = obter_tiers_cache()
    with st.expander("🏆 Ranking dos Padrões (Assertividade ≥ 50% - Últimas 200 Rodadas)", expanded=False):
        if not df_rank.empty:
            df_rank_exib = df_rank.copy()
            # REGRA DE CORREÇÃO: Índice do ranking iniciando em 1
            df_rank_exib.index = range(1, len(df_rank_exib) + 1)
            st.dataframe(df_rank_exib, use_container_width=True)
        else:
            st.info("Nenhum padrão com no mínimo 50% de acerto foi consolidado ainda (mínimo ~20 sinais).")

    # Alerta Manual
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
else:
    st.info("Aguardando dados da API ou inserção manual no painel lateral...")

# ==========================================
# 9. ESTATÍSTICAS E PAINEL VISUAL
# ==========================================
if st.session_state.historico:
    st.markdown("---")
    st.subheader("📊 Estatísticas das Rodadas (Quentes/Frios, Avançada, Últimas 1000)")
    
    total_disponivel = len(st.session_state.historico)
    max_amostra = min(1000, total_disponivel)
    qtd_rodadas = st.slider(
        "Selecione o tamanho da amostra (Últimas X rodadas):",
        min_value=min(10, total_disponivel),
        max_value=max_amostra,
        value=max_amostra,
        step=5
    )
    
    amostra = list(reversed(st.session_state.historico[:qtd_rodadas]))
    total_amostra = len(amostra)
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.markdown("### 📊 QUENTES/FRIOS")
        contagem = pd.Series(amostra).value_counts()
        quentes = contagem.head(5).index.tolist()
        frios = contagem.tail(5).index.tolist()
        
        st.write(f"🔥 **Mais Frequentes (Quentes):** {quentes}")
        st.write(f"🧊 **Menos Frequentes (Frios):** {frios}")
        
        freq_df = pd.DataFrame({'Número': contagem.index.astype(str), 'Frequência': contagem.values})
        fig_freq = px.bar(freq_df.head(10), x='Número', y='Frequência', title="Top 10 Números na Amostra", color='Frequência')
        fig_freq.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_freq, use_container_width=True)
        
    with col_g2:
        st.markdown("### 📊 AVANÇADA")
        
        d1 = sum(1 for n in amostra if 1 <= n <= 12)
        d2 = sum(1 for n in amostra if 13 <= n <= 24)
        d3 = sum(1 for n in amostra if 25 <= n <= 36)
        
        c1 = sum(1 for n in amostra if n > 0 and n % 3 == 1)
        c2 = sum(1 for n in amostra if n > 0 and n % 3 == 2)
        c3 = sum(1 for n in amostra if n > 0 and n % 3 == 0)
        
        par = sum(1 for n in amostra if n > 0 and n % 2 == 0)
        impar = sum(1 for n in amostra if n % 2 != 0)
        
        baixas = sum(1 for n in amostra if 1 <= n <= 18)
        altas = sum(1 for n in amostra if 19 <= n <= 36)
        
        df_duzias = pd.DataFrame({
            'Grupo': ['1ª Dúzia', '2ª Dúzia', '3ª Dúzia', '1ª Coluna', '2ª Coluna', '3ª Coluna'],
            'Porcentagem': [
                round((d1/total_amostra)*100, 1), round((d2/total_amostra)*100, 1), round((d3/total_amostra)*100, 1),
                round((c1/total_amostra)*100, 1), round((c2/total_amostra)*100, 1), round((c3/total_amostra)*100, 1)
            ]
        })
        
        fig_adv = px.bar(df_duzias, x='Grupo', y='Porcentagem', text='Porcentagem', title="Distribuição Dúzias e Colunas (%)")
        fig_adv.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_adv.update_layout(template="plotly_dark", height=280, margin=dict(l=10, r=10, t=30, b=5))
        st.plotly_chart(fig_adv, use_container_width=True)
        
        st.caption(f"**Par:** {round((par/total_amostra)*100)}% | **Ímpar:** {round((impar/total_amostra)*100)}% | **1-18:** {round((baixas/total_amostra)*100)}% | **19-36:** {round((altas/total_amostra)*100)}%")

    with col_g3:
        st.markdown(f"### 📊 ÚLTIMAS {qtd_rodadas}")
        
        matriz_freq = {n: amostra.count(n) for n in range(0, 37)}
        
        st.write("🔥 **Mapa de Calor da Mesa (0 a 36):**")
        
        grid_rows = [
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
            [0, 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
            [0, 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]
        ]
        
        text_vals = [[f"{n}<br>({matriz_freq[n]})" for n in row] for row in grid_rows]
        
        custom_colorscale = [
            [0.0, "#FFFFFF"],   # Branco para o Zero (0)
            [0.5, "#1E1E1E"],   # Preto / Cinza Escuro
            [1.0, "#D32F2F"]    # Vermelho
        ]

        def calcular_valor_cor(n):
            if n == 0:
                return 0.0
            elif n in NUMEROS_VERMELHOS:
                return 1.0
            else:
                return 0.5

        color_vals = [[calcular_valor_cor(n) for n in row] for row in grid_rows]

        fig_grid = go.Figure(data=go.Heatmap(
            z=color_vals,
            text=text_vals,
            texttemplate="%{text}",
            colorscale=custom_colorscale,
            showscale=False,
            zmin=0.0,
            zmax=1.0
        ))
        
        fig_grid.update_layout(
            template="plotly_dark",
            height=280,
            margin=dict(l=5, r=5, t=10, b=5),
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False)
        )
        st.plotly_chart(fig_grid, use_container_width=True)
