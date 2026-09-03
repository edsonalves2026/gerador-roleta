import streamlit as st
import pandas as pd
import requests
import random
import time
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURAÇÃO E CREDENCIAIS SEGURAS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Motor Avançado", layout="wide")
st_autorefresh(interval=5000, key="autoupdate_roleta")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# ⬡ MATRIZ PRINCIPAL — TABELA ATUALIZADA ⬡
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
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
# 2. MOTORES TIRO CERTO & HEAD-SHOT
# ==========================================
def processar_tiro_certo_e_headshot(
    esteira_14,
    historico_200,
    dados_brk,
    puxadores_dict,
    inversoes_dict,
    vizinhos_fisi_dict,
    quentes_100
):
    if len(esteira_14) < 13:
        return {
            "alvos_tiro_certo": [],
            "alvos_headshot": [],
            "score_maximo": 0.0,
            "status_nome": "AGUARDAR",
            "detalhes_pesos": {}
        }

    pos_01 = esteira_14[0]
    pos_02 = esteira_14[1]
    pos_03 = esteira_14[2]
    pos_13 = esteira_14[12]
    
    tres_ultimos = [pos_01, pos_02, pos_03]
    
    pontuacao = {n: 0.0 for n in range(0, 37)}
    ativacoes = {n: set() for n in range(0, 37)}

    brk_ausentes = dados_brk.get("ausentes", [])
    for n in brk_ausentes:
        pontuacao[n] += 3.0
        ativacoes[n].add("Ausente")

    puxadores_candidatos = []
    for ult in tres_ultimos:
        puxs = puxadores_dict.get(ult, [])
        if len(puxs) > 0:
            pontuacao[puxs[0]] += 2.5
            ativacoes[puxs[0]].add("Px top1")
            puxadores_candidatos.append(puxs[0])
        if len(puxs) > 1:
            pontuacao[puxs[1]] += 1.5
            puxadores_candidatos.append(puxs[1])

    inversoes_candidatas = []
    for ult in tres_ultimos:
        inv = inversoes_dict.get(ult)
        if inv is not None:
            pontuacao[inv] += 1.5
            ativacoes[inv].add("Inversão")
            inversoes_candidatas.append(inv)

    vizinhos_candidatos = []
    for ult in tres_ultimos:
        vizs = vizinhos_fisi_dict.get(ult, [])
        for v in vizs:
            pontuacao[v] += 1.0
            ativacoes[v].add("Vizinho")
            vizinhos_candidatos.append(v)

    pontuacao[pos_13] += 1.0
    ativacoes[pos_13].add("Ult 13")

    for n in range(0, 37):
        if pontuacao[n] > 0 and n in quentes_100:
            pontuacao[n] += 1.0
            ativacoes[n].add("+Quente 100R")

    todos_indicados = brk_ausentes + puxadores_candidatos + inversoes_candidatas + vizinhos_candidatos + [pos_13]
    frequencia = Counter(todos_indicados)
    
    for n, qtd in frequencia.items():
        if qtd > 1:
            pontuacao[n] += (qtd - 1) * 2.0
            ativacoes[n].add("+2F")

    ordenados = sorted(pontuacao.items(), key=lambda x: x[1], reverse=True)
    qualificados = [num for num, score in ordenados if score >= 3.0]
    alvos_tiro_certo = sorted(qualificados[:7])

    amostra_30 = historico_200[-30:] if len(historico_200) >= 30 else historico_200
    ultimo_sorteado = tres_ultimos[0]
    
    alvos_headshot = []
    for num in alvos_tiro_certo:
        score_num = pontuacao[num]
        estava_ativa_30 = num in amostra_30
        nao_foi_o_ultimo = (num != ultimo_sorteado)
        
        if score_num >= 5.0 and estava_ativa_30 and nao_foi_o_ultimo:
            alvos_headshot.append(num)

    alvos_headshot = sorted(alvos_headshot[:4])
    
    tem_headshot = len(alvos_headshot) >= 2
    tem_tiro_certo = len(alvos_tiro_certo) >= 4

    fontes_ativas = set()
    for n in (alvos_headshot if tem_headshot else alvos_tiro_certo):
        fontes_ativas.update(ativacoes[n])

    tag_fontes = "+".join(list(fontes_ativas)[:3]) if fontes_ativas else "Sinal"

    if tem_headshot:
        status_nome = f"💥 HEAD-SHOT [{tag_fontes}]"
    elif tem_tiro_certo:
        status_nome = f"🎯 TIRO CERTO [{tag_fontes}]"
    else:
        status_nome = "AGUARDAR"

    top_score = ordenados[0][1] if ordenados else 0.0

    return {
        "alvos_tiro_certo": alvos_tiro_certo,
        "alvos_headshot": alvos_headshot if tem_headshot else [],
        "score_maximo": top_score,
        "status_nome": status_nome,
        "detalhes_pesos": pontuacao,
        "ativacoes": ativacoes
    }

# ==========================================
# 3. FUNÇÃO DE BUSCA DA API
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
        res = requests.get(url_completo, headers=headers, timeout=15)
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
                with st.sidebar.expander("Ver resposta API"):
                    st.code(str(dados[:3]))
        else:
            st.sidebar.error(f"⚠️ Erro HTTP: {res.status_code}")
            with st.sidebar.expander("Resposta do erro"):
                st.code(res.text[:500])
    except Exception as e:
        st.sidebar.error(f"⚠️ Erro: {type(e).__name__}: {e}")
        
    return st.session_state.get("historico", [])

# ==========================================
# 4. FUNÇÕES AUXILIARES & TELEGRAM
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

def enviar_alerta_telegram(ultimo_num, score, alvos, detalhes, tier_nome="", posicao_rank=None, taxa_acerto=None):
    texto_detalhes = "\n".join([f"• {d}" for d in detalhes])
    prefixo_tier = f"🏆 *Classificação:* `{tier_nome}`\n" if tier_nome else ""
    str_rank = f"📊 *Posição no Ranking:* `#{posicao_rank}º lugar` ({taxa_acerto}% de assertividade)\n" if posicao_rank else ""
    
    mensagem = (
        f"🚨 *SINAL CONFIRMADO - RADAR DE ROLETA*\n\n"
        f"{prefixo_tier}"
        f"{str_rank}"
        f"📌 *Último Número:* `{ultimo_num}`\n"
        f"📊 *Score de Assertividade:* `{score}/5`\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"🛡️ *Proteção:* `0 (Zero)`\n\n"
        f"🔍 *Filtros Convergentes:*\n{texto_detalhes}\n\n"
        f"⚠️ *Entrada recomendada: Manter aposta por até 3 a 4 rodadas.*"
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

def validar_gatilho_sequencial_brk(historico_200):
    if not historico_200 or len(historico_200) < 2:
        return {"sinal_ativo": False, "motivo": "Aguardando mais rodadas."}

    dezena_atual = historico_200[-1]
    dezena_anterior = historico_200[-2]

    if dezena_atual == 0:
        soma, diferenca = 10, 10
    else:
        d1 = dezena_atual // 10
        d2 = dezena_atual % 10
        soma = d1 + d2
        diferenca = abs(d2 - d1)
        if soma > 10:
            soma = (soma // 10) + (soma % 10)

    grupo_confirmado = None
    if soma == dezena_anterior:
        grupo_confirmado = soma
    elif diferenca == dezena_anterior:
        grupo_confirmado = diferenca

    if grupo_confirmado is None or grupo_confirmado not in TABELA_OCULTOS_BRK:
        return {
            "sinal_ativo": False,
            "motivo": f"Dígitos de {dezena_atual} não confirmam {dezena_anterior}."
        }

    grupo_completo = TABELA_OCULTOS_BRK[grupo_confirmado]
    amostra_200 = historico_200[-200:]
    
    dezenas_prioritarias = [num for num in grupo_completo if num not in amostra_200]
    dezenas_cobertura = [num for num in grupo_completo if num in amostra_200]
    dezenas_cobertura.sort(key=lambda x: amostra_200.index(x) if x in amostra_200 else -1)

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
    estudo_ordenado = estudo.sort_values(by=["Taxa de Acerto (%)", "Total"], ascending=[False, False]).reset_index(drop=True)
    
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
    
    # Processa os dados da esteira de 14 com o novo motor
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
        
        sugestao = res_tiro_certo["status_nome"]
        if res_tiro_certo["alvos_headshot"]:
            sugestao += f": {res_tiro_certo['alvos_headshot']}"
        elif res_tiro_certo["alvos_tiro_certo"]:
            sugestao += f": {res_tiro_certo['alvos_tiro_certo']}"

        dados_tabela.append({
            "Posição": f"Pos {idx+1:02d}",
            "Último": res["ultimo"],
            "Vizinho (+1.0)": "🟢" if "Vizinho" in ativacoes_num else "⚪",
            "+Quente 100R (+1.0)": "🟢" if "+Quente 100R" in ativacoes_num else "⚪",
            "2F (+2.0)": "🟢" if "+2F" in ativacoes_num else "⚪",
            "Px top 1 (+2.5)": "🟢" if "Px top1" in ativacoes_num else "⚪",
            "Ausente (+3.0)": "🟢" if "Ausente" in ativacoes_num else "⚪",
            "Ult 13 (+1.0)": "🟢" if "Ult 13" in ativacoes_num else "⚪",
            "Score 🔥": f"{res_tiro_certo['detalhes_pesos'].get(num, 0.0):.1f}",
            "Status / Sugestão": sugestao if idx == 0 else res["status"]
        })
    
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    df_exibicao = pd.DataFrame(dados_tabela)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

    # Ranking dos Tiers
    tiers_atuais, df_rank = obter_tiers_cache()
    with st.expander("🏆 Ranking dos Padrões (Últimas 200 Rodadas)", expanded=False):
        if not df_rank.empty:
            st.dataframe(df_rank, use_container_width=True, hide_index=True)
        else:
            st.info("Aguardando histórico suficiente (mínimo ~20 sinais) para consolidação do ranking.")

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
