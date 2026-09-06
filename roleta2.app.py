import streamlit as st
import pandas as pd
import requests
import random
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# ==========================================
# 1. CONFIGURAÇÃO E CREDENCIAIS SEGURAS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Motor Avançado", layout="wide")
st_autorefresh(interval=15000, key="autoupdate_roleta")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# ⬡ MATRIZ PRINCIPAL — EXATAMENTE DO CÓDIGO 1 ⬡
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
# 2. FUNÇÕES AUXILIARES E CÁLCULO ESTATÍSTICO
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

# ✅ FUNÇÃO ATUALIZADA: busca nas ÚLTIMAS 100 rodadas e retorna as 4 mais frequentes (0 a 36)
def buscar_puxadores_dinamicos(numero_alvo, historico, limite_amostra=100):
    """
    Analisa as últimas 100 rodadas do histórico e retorna as 4 dezenas
    que mais aparecem em seguida ao numero_alvo, de 0 a 36.
    """
    amostra = historico[:limite_amostra]  # Usa apenas as últimas 100 rodadas
    if len(amostra) < 2:
        return []
    
    # amostra[0] = mais recente; quando aparece o numero_alvo, o próximo sorteado é a posição anterior (i-1)
    subsequentes = [amostra[i-1] for i in range(1, len(amostra)) if amostra[i] == numero_alvo]
    
    if not subsequentes:
        return []
    
    # Conta frequência e retorna os 4 mais comuns
    contagem = pd.Series(subsequentes).value_counts()
    return contagem.head(4).index.tolist()

def calcular_scores_reais(historico, limite=30):
    """Calcula taxa de acerto real das duas estratégias nas últimas 'limite' rodadas"""
    if len(historico) < limite:
        return 50.0, 50.0, 0.0, 0.0
    amostra = historico[:limite]
    acertos_din = acertos_brk = tiros_din = tiros_brk = 0
    for i in range(len(amostra) - 1):
        ultimo = amostra[i+1]
        proximo = amostra[i]
        pux_din = buscar_puxadores_dinamicos(ultimo, amostra[i+1:], limite_amostra=100)
        if pux_din:
            tiros_din += 1
            if proximo in pux_din[:4]:
                acertos_din += 1
        pux_brk = TABELA_PUXADORES_FIXA_BRK.get(ultimo, [])
        if pux_brk:
            tiros_brk += 1
            if proximo in pux_brk[:4]:
                acertos_brk += 1
    score_din = round(100 * acertos_din / tiros_din, 1) if tiros_din else 50.0
    score_brk = round(100 * acertos_brk / tiros_brk, 1) if tiros_brk else 50.0
    seco_din = round(score_din * 0.45, 1)
    seco_brk = round(score_brk * 0.40, 1)
    return score_din, score_brk, seco_din, seco_brk

# ==========================================
# 3. LÓGICA DE GERENCIAMENTO DE MODOS
# ==========================================
def determinar_modo_operacional(
    score_dinamico, score_brk, seco_dinamico, seco_brk,
    modo_atual, rodadas_no_modo_atual, trava_cooldown=15
):
    diferenca = score_dinamico - score_brk
    if rodadas_no_modo_atual < trava_cooldown:
        return modo_atual, f"🔒 Cooldown ativo ({rodadas_no_modo_atual}/{trava_cooldown} rodadas)"
    if diferenca > 5.0:
        return "DINAMICO", f"Vantagem Dinâmica > 5% ({diferenca:+.1f}%)"
    elif diferenca < -5.0:
        return "BRK", f"Vantagem BRK > 5% ({abs(diferenca):.1f}%)"
    else:
        if seco_dinamico > seco_brk:
            return "DINAMICO", f"Desempate por Tiro Seco ({seco_dinamico}% vs {seco_brk}%)"
        elif seco_brk > seco_dinamico:
            return "BRK", f"Desempate por Tiro Seco ({seco_brk}% vs {seco_dinamico}%)"
        return (modo_atual if modo_atual else "DINAMICO"), "Inércia / Padrão Mantido"

# ==========================================
# 4. BUSCA DA API & TELEGRAM
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
        res = requests.get(url_completo, headers=headers, timeout=10)
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
                return numeros
            st.sidebar.warning("⚠️ API respondeu, sem números extraídos")
        else:
            st.sidebar.error(f"⚠️ Erro HTTP: {res.status_code}")
    except Exception as e:
        st.sidebar.error(f"⚠️ Erro de Conexão: {type(e).__name__}")
    return st.session_state.get("historico", [])

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

def enviar_alerta_telegram(ultimo_num, score, alvos, detalhes, tier_nome="", posicao_rank=None, taxa_acerto=None, modo_estrategia=""):
    texto_detalhes = "\n".join([f"• {d}" for d in detalhes])
    prefixo_tier = f"🏆 *Classificação:* `{tier_nome}`\n" if tier_nome else ""
    str_rank = f"📊 *Posição no Ranking:* `#{posicao_rank}º lugar` ({taxa_acerto}% de assertividade)\n" if posicao_rank else ""
    str_estrategia = f"⚙️ *Estratégia:* `{modo_estrategia}`\n" if modo_estrategia else ""
    mensagem = (
        f"🚨 *SINAL CONFIRMADO - RADAR DE ROLETA*\n\n"
        f"{prefixo_tier}{str_rank}{str_estrategia}"
        f"📌 *Último Número:* `{ultimo_num}`\n"
        f"📊 *Score de Assertividade:* `{score}/5`\n"
        f"🎯 *Alvos Sugeridos:* `{alvos}`\n"
        f"🛡️ *Proteção:* `0 (Zero)`\n\n"
        f"🔍 *Filtros Convergentes:*\n{texto_detalhes}\n\n"
        f"⚠️ *Entrada recomendada: Manter aposta por até 2 rodadas.*"
    )
    return enviar_mensagem_telegram(mensagem)

def enviar_resultado_telegram(tipo, numero, etapa=""):
    if tipo == "GREEN":
        msg = f"✅ *GREEN CONFIRMADO!* 🎉\n\n🎯 Número Bateu: `{numero}`\n📍 Momento: `{etapa}`"
    else:
        msg = f"❌ *RED / LOSS* 😔\n\n📌 Último Sorteado: `{numero}`\n⚠️ Limite de Gales atingido."
    return enviar_mensagem_telegram(msg)

# ==========================================
# 5. MOTOR ESTATÍSTICO & REGRAS DE NEGÓCIO
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

# ✅ FUNÇÃO ATUALIZADA: analisa ausências considerando apenas as ÚLTIMAS 30 RODADAS
def validar_gatilho_sequencial_brk(historico):
    if not historico or len(historico) < 2:
        return {"sinal_ativo": False, "motivo": "Aguardando mais rodadas."}
    
    dezena_atual = historico[0]  # Mais recente
    dezena_anterior = historico[1]
    
    if dezena_atual == 0:
        soma, diferenca = 10, 10
    else:
        d1, d2 = dezena_atual // 10, dezena_atual % 10
        soma = d1 + d2
        diferenca = abs(d2 - d1)
        soma = (soma // 10) + (soma % 10) if soma > 10 else soma
    
    grupo_confirmado = soma if soma == dezena_anterior else (diferenca if diferenca == dezena_anterior else None)
    if grupo_confirmado is None or grupo_confirmado not in TABELA_OCULTOS_BRK:
        return {"sinal_ativo": False, "motivo": f"Dígitos de {dezena_atual} não confirmam {dezena_anterior}."}
    
    grupo_completo = TABELA_OCULTOS_BRK[grupo_confirmado]
    amostra_30 = set(historico[:30])  # Janela de 30 rodadas para verificação de ausência
    
    dezenas_prioritarias = [num for num in grupo_completo if num not in amostra_30]
    dezenas_cobertura = [num for num in grupo_completo if num in amostra_30]
    
    return {
        "sinal_ativo": True, "grupo_confirmado": grupo_confirmado,
        "dezena_gatilho": dezena_atual, "dezena_confirmada": dezena_anterior,
        "prioridade_maxima": dezenas_prioritarias, "cobertura": dezenas_cobertura,
        "grupo_completo": grupo_completo
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
            alvos_zero = set(res["alvos"] + [0])
            hit = any(n in alvos_zero for n in futuro)
            registros.append({"Padrão": res["padrao_nome"], "Total de Sinais": 1, "Acertos": 1 if hit else 0})
    if not registros:
        return {}, pd.DataFrame()
    df_reg = pd.DataFrame(registros)
    estudo = df_reg.groupby("Padrão").agg(Total=("Total de Sinais", "sum"), Acertos=("Acertos", "sum")).reset_index()
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
    if "tier_cache" not in st.session_state or st.session_state.get("tier_cache_tamanho", -1) != hist_atual:
        st.session_state["tier_cache"], st.session_state["df_rank_cache"] = classificar_padroes_200_rodadas(st.session_state.historico)
        st.session_state["tier_cache_tamanho"] = hist_atual
    return st.session_state["tier_cache"], st.session_state["df_rank_cache"]

def analisar_rodada_especifica(sub_historico, houve_troca=False):
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
    if res_brk["sinal_ativo"]:
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
        
    if houve_troca and ultimo in [1, 5, 8, 11, 14, 23, 26, 32]:
        score += 1
        filtros_ativos.append("VizinhosZero")
        alvos.update([0, 10, 20, 30])
        
    esteira_14 = sub_historico[:14]
    reincidencia = [num for num in alvos if num in esteira_14[:3]]
    if reincidencia:
        score += 1
        filtros_ativos.append("Reincidência")
        
    setor_dom = "-"
    if len(sub_historico) >= 10:
        foco_10 = sub_historico[:10]
        contagem = {s: 0 for s in SETORES_ROLETA}
        for num in foco_10:
            for s, nums in SETORES_ROLETA.items():
                if num in nums:
                    contagem[s] += 1
        setor_dom = max(contagem, key=contagem.get)
        if any(num in SETORES_ROLETA[setor_dom] for num in alvos):
            score += 1
            filtros_ativos.append("Racetrack")
            
    score_final = min(score, 5)
    
    if res_brk["sinal_ativo"]:
        prio = res_brk["prioridade_maxima"]
        resto = [n for n in sorted(alvos) if n not in prio]
        alvos_ordenados = prio + resto
    else:
        alvos_ordenados = sorted(list(alvos))
        
    padrao_nome = " + ".join(filtros_ativos) if filtros_ativos else "Geral"
    return {
        "ultimo": ultimo, "esquerda": f"{vizinhos['esq_2']} | {vizinhos['esq_1']}",
        "direita": f"{vizinhos['dir_1']} | {vizinhos['dir_2']}",
        "puxadores_brk": str(puxadores_brk) if puxadores_brk else "-",
        "puxadores_dinamico": str(puxadores_dinamico) if puxadores_dinamico else "-",
        "vizinhos_str": f"Esq({vizinhos['esq_1']}), Dir({vizinhos['dir_1']})",
        "camuflados": str(obter_camuflados(ultimo)), "racetrack": setor_dom,
        "inversao": str_inversao, "reincidencia": str(reincidencia) if reincidencia else "-",
        "confirmacoes": "🔴 " * len(filtros_ativos), "score": f"{score_final}/5",
        "status": "AGUARDAR" if score_final < 4 else f"SINAL: {alvos_ordenados}",
        "alvos": alvos_ordenados, "score_num": score_final,
        "padrao_nome": padrao_nome, "dados_brk": res_brk
    }

# ==========================================
# 6. INICIALIZAÇÃO DO ESTADO DE SESSÃO
# ==========================================
if "historico" not in st.session_state:
    st.session_state.historico = []
if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False
    st.session_state.alvos_sinal = []
    st.session_state.tentativa_atual = 0
    st.session_state.ultimo_resultado = None
if "modo_operacional_atual" not in st.session_state:
    st.session_state.modo_operacional_atual = "DINAMICO"
if "rodadas_no_modo_atual" not in st.session_state:
    st.session_state.rodadas_no_modo_atual = 15

# ==========================================
# 7. MÁQUINA DE ESTADOS & MODO ATIVO
# ==========================================
score_dinamico, score_brk, seco_dinamico, seco_brk = calcular_scores_reais(st.session_state.historico, limite=30)
modo_ativo, status_motivo = determinar_modo_operacional(
    score_dinamico=score_dinamico, score_brk=score_brk,
    seco_dinamico=seco_dinamico, seco_brk=seco_brk,
    modo_atual=st.session_state.modo_operacional_atual,
    rodadas_no_modo_atual=st.session_state.rodadas_no_modo_atual,
    trava_cooldown=15
)
if modo_ativo != st.session_state.modo_operacional_atual:
    st.session_state.modo_operacional_atual = modo_ativo
    st.session_state.rodadas_no_modo_atual = 0
else:
    st.session_state.rodadas_no_modo_atual += 1
if modo_ativo == "DINAMICO":
    st.markdown(
        f"🟢 **MODO ATIVO:** `MODO OCULTOS DINÂMICO` &nbsp;|&nbsp; "
        f"**Status:** {status_motivo} &nbsp;|&nbsp; *Analisando vetor completo (0 a 36)*"
    )
    estrategia_telegram = f"Matriz Dinâmica + Frequência (Score: {score_dinamico}%)"
else:
    st.markdown(
        f"🔵 **MODO ATIVO:** `MODO OCULTOS BRK` &nbsp;|&nbsp; "
        f"**Status:** {status_motivo} &nbsp;|&nbsp; *Tabela Fixa Estática*"
    )
    estrategia_telegram = f"Puxadores Estáticos + Oculto BRK (Score: {score_brk}%)"
st.markdown("---")

# ==========================================
# 8. INTERFACE STREAMLIT
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")
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
        
        alvos_com_zero = set(st.session_state.alvos_sinal).union({0})
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
        res_ultimo = analisar_rodada_especifica(st.session_state.historico)
        
        if res_ultimo.get("score_num", 0) >= 4:
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

            # Processamento de Sinal Ativo (Gale / Fusão) vs Novo Sinal
            if st.session_state.sinal_ativo:
                if "Fusão" in modo_gale_opcao and tier_do_padrao == "👑 Elite (Top 3)":
                    alvos_atuais = set(st.session_state.alvos_sinal)
                    novos_alvos_unicos = set(res_ultimo.get("alvos", [])) - alvos_atuais

                    # Trava para manter o limite máximo em 8 alvos acumulados no Gale
                    if novos_alvos_unicos and len(alvos_atuais) < 8:
                        vagas = 8 - len(alvos_atuais)
                        novos_adicionados = list(novos_alvos_unicos)[:vagas]

                        alvos_finais = list(alvos_atuais) + novos_adicionados
                        st.session_state.alvos_sinal = alvos_finais

                        enviar_mensagem_telegram(
                            f"🔄 *FUSÃO DE ALVOS (GALE)*\n"
                            f"Novos alvos adicionados: `{novos_adicionados}`\n"
                            f"Alvos Totais ({len(alvos_finais)}): `{alvos_finais}`"
                        )
            elif permitido:
                st.session_state.sinal_ativo = True

                # Garante no máximo 8 alvos no sinal de entrada primário
                alvos_originais = list(dict.fromkeys(res_ultimo["alvos"]))
                st.session_state.alvos_sinal = alvos_originais[:8]
                st.session_state.tentativa_atual = 0

                enviar_alerta_telegram(
                    res_ultimo["ultimo"],
                    res_ultimo["score_num"],
                    st.session_state.alvos_sinal,
                    [f"Padrão: {padrao}", f"Filtro: {filtro_hibrido_opcao}"],
                    tier_nome=tier_do_padrao,
                    posicao_rank=posicao_rank,
                    taxa_acerto=taxa_acerto,
                    modo_estrategia=estrategia_telegram
                )

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
        st.session_state.rodadas_no_modo_atual = 15
        for chave in ["tier_cache", "df_rank_cache", "tier_cache_tamanho"]:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()

st.subheader("Esteira Temporal (Últimas 13 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:13]
    cols = st.columns(min(len(esteira), 13))
    for i, num in enumerate(esteira):
        with cols[i]:
            rotulo = "Atual" if i == 0 else f"-{i}r"
            st.metric(label=rotulo, value=num)

if st.session_state.historico and len(st.session_state.historico) >= 2:
    res_brk_painel = validar_gatilho_sequencial_brk(st.session_state.historico)
    
    if res_brk_painel["sinal_ativo"]:
        st.markdown("---")
        st.success(f"🎯 **GATILHO OCULTO BRK CONFIRMADO PARA O GRUPO {res_brk_painel['grupo_confirmado']}!**")
        st.markdown(f"**Validação:** A dezena recente `{res_brk_painel['dezena_gatilho']}` confirmou a dezena anterior `{res_brk_painel['dezena_confirmada']}`.")
        
        c_prio, c_cob = st.columns(2)
        with c_prio:
            st.error(f"🔥 **PRIORIDADE MÁXIMA (Ainda não saíram nas 30 rodadas):**\n\n`{res_brk_painel['prioridade_maxima']}`")
        with c_cob:
            st.warning(f"🛡️ **COBERTURA (Já saíram no histórico):**\n\n`{res_brk_painel['cobertura']}`")
        st.info("⏱️ **Estratégia Recomendada:** Manter apostas neste grupo pelas próximas **3 rodadas**.")

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
    else:
        st.error(f"⚠️ Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
# ==========================================
# 10. SINAL ATIVO — GALE & ACOMPANHAMENTO
# ==========================================
st.markdown("---")
st.subheader("🚨 Sinal Ativo & Acompanhamento")

if st.session_state.get('sinal_ativo', False):
    tentativa = st.session_state.get('tentativa_atual', 0)
    st.warning(f"⚠️ **SINAL EM ANDAMENTO — Tentativa {tentativa + 1}/3**")
    
    alvos = st.session_state.get('alvos_sinal', [])
    alvos_exibicao = [str(n) for n in alvos]
    
    st.markdown("### 🎯 Alvos Sugeridos:")
    st.markdown(f"## `{' | '.join(alvos_exibicao)}`")
    st.info("🛡️ Proteção recomendada: Apostar também no **0 (Zero)** para cobertura.")

    progresso = (tentativa + 1) / 3
    st.progress(min(progresso, 1.0), text=f"Rodada {tentativa + 1} de 3 (Limite de Gales)")

    dica_etapa = {
        0: "💰 Entrada — Valor Base",
        1: "📈 Gale 1 — Aumentar ~50%",
        2: "📊 Gale 2 — Aumentar ~100%",
        3: "🛑 Parar — Limite Atingido"
    }
    st.info(f"💡 Sugestão de aposta: **{dica_etapa.get(tentativa, 'Parar')}**")

else:
    st.success("✅ Nenhum sinal ativo — Aguardando padrão convergente...")


# Tabela Analítica
if st.session_state.historico:
    st.markdown("---")
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    
    dados_tabela = []
    janela_exibicao = st.session_state.historico[:14]
    
    for idx in range(len(janela_exibicao)):
        sub_hist = st.session_state.historico[idx:]
        res = analisar_rodada_especifica(sub_hist)
        
        dados_tabela.append({
            "Posição": "Atual" if idx == 0 else f"-{idx}r",
            "Último": res["ultimo"],
            "Esquerda": res["esquerda"],
            "Direita": res["direita"],
            "Puxadores BRK": res["puxadores_brk"],
            "Puxadores Dinâmico": res["puxadores_dinamico"],
            "Vizinhos Físicos": res["vizinhos_str"],
            "Camuflados": res["camuflados"],
            "Racetrack": res["racetrack"],
            "Inversão": res["inversao"],
            "Reincidência": res["reincidencia"],
            "Confirmações": res["confirmacoes"],
            "Score": res["score"],
            "Status / Sugestão": res["status"]
        })
    
    df_exibicao = pd.DataFrame(dados_tabela)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    
# ==========================================
# 9. ESTATÍSTICAS E MAPA DE CALOR
# ==========================================
st.markdown("---")
st.subheader("📈 Estatísticas — Últimas 80 Rodadas")

if st.session_state.historico:
    ultimas = st.session_state.historico[:80]
    qtd = len(ultimas)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### 🔥 Quentes / Frias")
        if qtd >= 10:
            cont = pd.Series(ultimas).value_counts().reindex(range(37), fill_value=0)
            
            top_12_quentes = cont.sort_values(ascending=False).head(12)
            top_12_frias = cont.sort_values(ascending=True).head(12)
            
            col_q, col_f = st.columns(2)
            with col_q:
                st.markdown("#### 🔥 Mais Sorteados")
                for num, freq in top_12_quentes.items():
                    st.markdown(f"<span style='font-size:18px; font-weight:bold; color:#ff6666;'>{num:2d}</span> &nbsp; <span style='color:#cccccc;'>({freq}x)</span>", unsafe_allow_html=True)
            
            with col_f:
                st.markdown("#### ❄️ Menos Sorteados")
                for num, freq in top_12_frias.items():
                    st.markdown(f"<span style='font-size:18px; font-weight:bold; color:#6699ff;'>{num:2d}</span> &nbsp; <span style='color:#cccccc;'>({freq}x)</span>", unsafe_allow_html=True)
        else:
            st.info(f"Dados insuficientes ({qtd}/10)")

    with c2:
        st.markdown("### 📐 Dúzias / Colunas / Paridade")
        if qtd >= 12 and 'calcular_estatisticas' in globals():
            est = calcular_estatisticas(ultimas)
            categorias = ['D1\n1-12', 'D2\n13-24', 'D3\n25-36', 'C1', 'C2', 'C3', 'Pares', 'Ímpares', 'Baixas\n1-18', 'Altas\n19-36']
            valores = [
                est.get('d1', 0), est.get('d2', 0), est.get('d3', 0),
                est.get('c1', 0), est.get('c2', 0), est.get('c3', 0),
                est.get('par', 0), est.get('impar', 0),
                est.get('baixas', 0), est.get('altas', 0)
            ]
            cores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#2ECC71', '#E74C3C', '#3498DB', '#E67E22']
            
            fig_meta = go.Figure(go.Bar(
                x=categorias, y=valores,
                marker_color=cores, text=valores, textposition='auto'
            ))
            fig_meta.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=30, b=60), showlegend=False)
            st.plotly_chart(fig_meta, use_container_width=True)
        else:
            st.info(f"Dados insuficientes ({qtd}/12)")

    with c3:
        st.markdown("### 🎨 Mapa de Cores — Últimas 80")
        if qtd > 0:
            amostra_mapa = ultimas[:80]
            
            # Opções de formato para os seletores (Bolinha, Quadrado, Arredondado)
            formato = st.selectbox(
                "Formato dos ícones",
                options=["Círculo", "Quadrado", "Arredondado"],
                index=0,
                key="fmt_mapa_cores"
            )
            
            if formato == "Círculo":
                border_radius = "50%"
            elif formato == "Arredondado":
                border_radius = "6px"
            else:
                border_radius = "0px"

            linhas_html = []
            for i in range(0, len(amostra_mapa), 10):
                bloco = amostra_mapa[i:i+10]
                spans_bloco = []
                
                for n in bloco:
                    if n == 0:
                        bg_cor = "#00AA00"
                    elif 'NUMEROS_VERMELHOS' in globals() and n in NUMEROS_VERMELHOS:
                        bg_cor = "#FF2222"
                    elif n in {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}:
                        bg_cor = "#FF2222"
                    else:
                        bg_cor = "#111111"
                    
                    spans_bloco.append(
                        f'<span style="background-color:{bg_cor};color:#FFF;border-radius:{border_radius};'
                        f'width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;'
                        f'font-size:11px;font-weight:bold;margin:2px;box-sizing:border-box;">{n}</span>'
                    )
                
                linha = f'<div style="display:flex;flex-wrap:nowrap;margin-bottom:2px;">{"".join(spans_bloco)}</div>'
                linhas_html.append(linha)

            mapa_completo_html = f'<div style="background:#0d0e12;padding:10px;border-radius:8px;border:1px solid #333;">{"".join(linhas_html)}</div>'
            st.markdown(mapa_completo_html, unsafe_allow_html=True)
        else:
            st.info("Aguardando dados...")

# ==========================================
# MAPA DE CALOR (LAYOUT RACETRACK / PISTA)
# ==========================================
st.markdown("---")
st.subheader("🌡️ Mapa de Calor — Distribuição no Cilindro (Racetrack)")

ultimas_200 = st.session_state.historico[:200]
qtd = len(ultimas_200)

if qtd >= 20:
    try:
        cont = pd.Series(ultimas_200).value_counts().reindex(range(37), fill_value=0)
        max_freq = int(max(cont.values)) if max(cont.values) > 0 else 1

        VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

        def get_estilo_celula(num):
            freq = int(cont.get(num, 0))
            intensidade = freq / max_freq

            if num == 0:
                base_color = "#1b6d43"
            elif num in VERMELHOS:
                base_color = "#8b181b"
            else:
                base_color = "#111111"

            if intensidade > 0.70:
                glow = "border: 2px solid #ff4444; box-shadow: inset 0 0 8px #ff4444;"
            elif intensidade > 0.40:
                glow = "border: 2px solid #ffbb33; box-shadow: inset 0 0 5px #ffbb33;"
            else:
                glow = "border: 1px solid #444;"

            return f"background: {base_color}; {glow}"

        topo_nums = [5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35]
        base_nums = [30, 11, 36, 13, 27, 6, 34, 17, 25, 2, 21, 4, 19, 15, 32]
        curva_esq = [10, 23, 8]
        curva_dir = [3, 26, 0]

        def render_cells(nums):
            cells = []
            for n in nums:
                f = int(cont.get(n, 0))
                cells.append(f'<div class="rt-cell" style="{get_estilo_celula(n)}"><span>{n}</span><small>({f})</small></div>')
            return "".join(cells)

        topo_html = render_cells(topo_nums)
        base_html = render_cells(base_nums)

        esq_0, esq_1, esq_2 = [f'<div class="rt-cell" style="{get_estilo_celula(n)}"><span>{n}</span><small>({int(cont.get(n,0))})</small></div>' for n in curva_esq]
        dir_0, dir_1, dir_2 = [f'<div class="rt-cell" style="{get_estilo_celula(n)}"><span>{n}</span><small>({int(cont.get(n,0))})</small></div>' for n in curva_dir]

        # HTML e CSS totalmente colapsados em linha única para impedir interpretação Markdown
        raw_html = f"""<style>body {{ background-color: transparent; color: white; margin: 0; font-family: Arial, sans-serif; }} .rt-wrapper {{ width: 100%; max-width: 950px; margin: 0 auto; background: #08080a; padding: 12px; border-radius: 80px; border: 2px solid #d4af37; box-sizing: border-box; }} .rt-outer {{ display: flex; flex-direction: column; width: 100%; }} .rt-row {{ display: flex; width: 100%; justify-content: center; }} .rt-spacer {{ width: 45px; flex-shrink: 0; }} .rt-cell {{ flex: 1; height: 46px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #fff; font-weight: bold; font-size: 12px; margin: 1px; border-radius: 3px; box-sizing: border-box; }} .rt-cell small {{ font-size: 8px; color: #bbb; font-weight: normal; }} .rt-middle {{ display: flex; height: 75px; width: 100%; margin: 1px 0; }} .rt-curva-esq, .rt-curva-dir {{ width: 45px; display: flex; flex-direction: column; flex-shrink: 0; }} .rt-center-area {{ flex: 1; display: flex; background: #050505; border: 1px solid #333; margin: 0 2px; border-radius: 4px; align-items: center; }} .rt-sector {{ display: flex; align-items: center; justify-content: center; color: #d4af37; font-weight: bold; font-size: 11px; letter-spacing: 1px; height: 100%; }} .sec-tier {{ flex: 3; border-right: 1px solid #333; }} .sec-orphelins {{ flex: 2.5; border-right: 1px solid #333; }} .sec-voisins {{ flex: 3.5; border-right: 1px solid #333; }} .sec-zero {{ flex: 2; border: 1px solid #555; border-radius: 30px; margin: 4px; background: #0d0d10; height: 80%; }}</style><div class="rt-wrapper"><div class="rt-outer"><div class="rt-row"><div class="rt-spacer"></div>{topo_html}<div class="rt-spacer"></div></div><div class="rt-middle"><div class="rt-curva-esq">{esq_0}{esq_1}{esq_2}</div><div class="rt-center-area"><div class="rt-sector sec-tier">TIER</div><div class="rt-sector sec-orphelins">ORPHELINS</div><div class="rt-sector sec-voisins">VOISINS</div><div class="rt-sector sec-zero">ZERO</div></div><div class="rt-curva-dir">{dir_0}{dir_1}{dir_2}</div></div><div class="rt-row"><div class="rt-spacer"></div>{base_html}<div class="rt-spacer"></div></div></div></div>"""

        # Renderização isolada sem passar pelo parser de Markdown do Streamlit
        components.html(raw_html, height=210)
        st.caption("Dica: As casas destacam dinamicamente conforme a frequência das últimas 200 rodadas.")
    except Exception as e:
        st.error(f"Erro ao renderizar o Racetrack: {e}")
else:
    st.info(f"Dados insuficientes para mapa de calor no Racetrack ({qtd}/20)")

# Verifica se existe histórico antes de renderizar as estatísticas
if st.session_state.get("historico", []):

    # === RANKING DE PADRÕES ===
    st.markdown("---")
    st.subheader("🏆 Ranking de Padrões — Taxa de Acerto Histórica")
    tiers, df_rank = obter_tiers_cache()
    
    if not df_rank.empty:
        # Ajusta os valores da coluna de porcentagem para garantir compatibilidade com o ProgressColumn
        df_display = df_rank.copy()
        
        st.dataframe(
            df_display,
            column_config={
                "Padrão": st.column_config.TextColumn("Padrão Detectado"),
                "Total": st.column_config.NumberColumn("Sinais Gerados"),
                "Acertos": st.column_config.NumberColumn("Acertos Confirmados"),
                "Taxa de Acerto (%)": st.column_config.ProgressColumn(
                    "Taxa de Acerto", 
                    format="%.1f%%", 
                    min_value=0, 
                    max_value=100
                )
            },
            use_container_width=True, 
            hide_index=True
        )
        
        c_tier1, c_tier2, c_tier3, c_tier4 = st.columns(4)
        c_tier1.info(f"👑 **Elite Top 3:** {', '.join(tiers.get('ELITE_TOP_3', [])) or '—'}")
        c_tier2.success(f"🥇 **Ouro Top 5:** {', '.join(tiers.get('SELECAO_OURO_TOP_5', [])) or '—'}")
        c_tier3.warning(f"🥈 **Seleção Top 10:** {', '.join(tiers.get('SELECAO_TOP_10', [])) or '—'}")
        c_tier4.info(f"🥉 **Radar Top 30:** {', '.join(tiers.get('RADAR_TOP_30', [])) or '—'}")
    else:
        st.info("Aguardando histórico mínimo para gerar ranking de padrões...")

    # === DESEMPENHO DAS ESTRATÉGIAS ===
    st.markdown("---")
    st.subheader("📊 Desempenho das Estratégias (Últimas 30 rodadas)")
    
    # Obtém métricas com tratamento padrão caso ainda não tenham sido calculadas
    score_dinamico = globals().get("score_dinamico", 0)
    score_brk = globals().get("score_brk", 0)
    seco_dinamico = globals().get("seco_dinamico", 0)
    seco_brk = globals().get("seco_brk", 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🎯 Dinâmico", f"{score_dinamico}%")
    col2.metric("🔷 BRK Fixo", f"{score_brk}%")
    col3.metric("⚡ Tiro Seco Din", f"{seco_dinamico}%")
    col4.metric("⚡ Tiro Seco BRK", f"{seco_brk}%")

    st.markdown("""
    > **Método de cálculo:** Taxa de acerto real das sugestões de puxadores nas últimas 30 rodadas.  
    > *Dinâmico* = baseado nas últimas 100 rodadas | *BRK* = tabela fixa
    """)

else:
    st.info("ℹ️ Inicie a captura ou digite números manualmente para visualizar as estatísticas.")


# ==========================================
# RODAPÉ
# ==========================================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.85em;'>
⚠️ <strong>Aviso:</strong> Esta ferramenta é para fins de análise e estudo estatístico. 
Não garante resultados — a roleta é um jogo de probabilidade independente por rodada. 
Jogue com responsabilidade e dentro de seus limites.
</div>
""", unsafe_allow_html=True)
