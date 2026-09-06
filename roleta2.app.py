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
        f"⚠️ *Entrada recomendada: Manter aposta por até 3 a 4 rodadas.*"
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
# GARANTIA DE VARIÁVEIS E ESTADOS GLOBAIS
# ==========================================
if 'roleta_selecionada' not in globals() and 'roleta_selecionada' not in locals():
    roleta_selecionada = st.session_state.get('roleta_selecionada', 'Roleta Principal')

if 'historico' not in st.session_state:
    st.session_state.historico = []

# ==========================================
# 8. TABELA ANALÍTICA
# ==========================================
if st.session_state.historico:
    st.markdown("---")
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    
    dados_tabela = []
    janela_exibicao = st.session_state.historico[:14]
    
    for idx in range(len(janela_exibicao)):
        sub_hist = st.session_state.historico[idx:]
        res = analisar_rodada_especifica(sub_hist) if 'analisar_rodada_especifica' in globals() else {}
        
        dados_tabela.append({
            "Posição": "Atual" if idx == 0 else f"-{idx}r",
            "Último": res.get("ultimo", "-"),
            "Esquerda": res.get("esquerda", "-"),
            "Direita": res.get("direita", "-"),
            "Puxadores BRK": res.get("puxadores_brk", "-"),
            "Puxadores Dinâmico": res.get("puxadores_dinamico", "-"),
            "Vizinhos Físicos": res.get("vizinhos_str", "-"),
            "Camuflados": res.get("camuflados", "-"),
            "Racetrack": res.get("racetrack", "-"),
            "Inversão": res.get("inversao", "-"),
            "Reincidência": res.get("reincidencia", "-"),
            "Confirmações": res.get("confirmacoes", "-"),
            "Score": res.get("score", 0),
            "Status / Sugestão": res.get("status", "-")
        })
    
    df_exibicao = pd.DataFrame(dados_tabela)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

# ==========================================
# 9. ESTATÍSTICAS E MAPA DE CALOR
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
        st.markdown("### 🧭 Setores da Roleta — Últimas 200 rodadas")
        if qtd >= 10 and 'SETORES_ROLETA' in globals():
            amostra_setores = st.session_state.historico[:200]
            contagem_setores = {}
            for nome, nums in SETORES_ROLETA.items():
                contagem_setores[nome] = sum(1 for n in amostra_setores if n in nums)
            
            nomes_exibicao = {
                "VOISINS_DU_ZERO": "Vizinhos do Zero",
                "TIERS_DU_CYLINDRE": "Terços do Cilindro",
                "ORPHELINS": "Órfãos",
                "ZERO_SPIEL": "Zero Spiel"
            }
            
            dados_setores = []
            for chave, valor in contagem_setores.items():
                nome_legivel = nomes_exibicao.get(chave, chave)
                pct = round(valor / len(amostra_setores) * 100, 1)
                dados_setores.append({"Setor": nome_legivel, "Quantidade": valor, "%": pct})
            
            df_setores = pd.DataFrame(dados_setores)
            st.dataframe(df_setores, use_container_width=True, hide_index=True)
            
            st.markdown("##### 🎯 Divisão dos Setores")
            st.markdown("""
            <div style='background-color:#1a1a1a; padding:10px; border-radius:8px; text-align:center;'>
                <span style='background-color:#cc4444; padding:6px 12px; border-radius:4px; margin:3px;'>TERÇOS</span>
                <span style='background-color:#4488cc; padding:6px 12px; border-radius:4px; margin:3px;'>ÓRFÃOS</span>
                <span style='background-color:#cc8844; padding:6px 12px; border-radius:4px; margin:3px;'>VIZINHOS DO ZERO</span>
                <span style='background-color:#44aa66; padding:6px 12px; border-radius:4px; margin:3px;'>ZERO SPIEL</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"Dados insuficientes ({qtd}/10)")

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

        def get_cor_calor(num):
            freq = int(cont.get(num, 0))
            intensidade = freq / max_freq
            if intensidade > 0.75:
                return f"rgba(220, 40, 40, {0.65 + intensidade*0.35:.2f})"
            elif intensidade > 0.50:
                return f"rgba(230, 120, 20, {0.55 + intensidade*0.35:.2f})"
            elif intensidade > 0.25:
                return f"rgba(210, 160, 30, {0.45 + intensidade*0.35:.2f})"
            else:
                return f"rgba(80, 60, 20, {0.35 + intensidade*0.30:.2f})"

        topo_nums = [5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35]
        base_nums = [30, 11, 36, 13, 27, 6, 34, 17, 25, 2, 21, 4, 19, 15, 32]
        esq_nums = [10, 23, 8]
        dir_nums = [3, 26, 0]

        html_topo = "".join([f'<div class="cell" style="background:{get_cor_calor(n)};">{n}<span class="cell-sub">({int(cont.get(n,0))})</span></div>' for n in topo_nums])
        html_base = "".join([f'<div class="cell" style="background:{get_cor_calor(n)};">{n}<span class="cell-sub">({int(cont.get(n,0))})</span></div>' for n in base_nums])

        c_esq_0, c_esq_1, c_esq_2 = esq_nums[0], esq_nums[1], esq_nums[2]
        c_dir_0, c_dir_1, c_dir_2 = dir_nums[0], dir_nums[1], dir_nums[2]

        html_racetrack = f"""
        <style>
            .racetrack-container {{
                width: 100%;
                max-width: 1100px;
                margin: 0 auto;
                background: #0d0e12;
                padding: 15px;
                border-radius: 40px;
                border: 2px solid #333;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                font-family: Arial, sans-serif;
            }}
            .racetrack-grid {{
                display: grid;
                grid-template-columns: 80px repeat(16, 1fr) 80px;
                grid-template-rows: auto auto auto;
                gap: 2px;
                text-align: center;
            }}
            .cell {{
                padding: 6px 2px;
                border: 1px solid #222;
                border-radius: 4px;
                color: #fff;
                font-weight: bold;
                font-size: 13px;
                min-height: 42px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }}
            .cell-sub {{
                font-size: 9px;
                opacity: 0.8;
                font-weight: normal;
            }}
            .center-area {{
                grid-column: 2 / 18;
                grid-row: 2;
                display: flex;
                align-items: center;
                justify-content: space-around;
                background: rgba(25, 28, 36, 0.9);
                border: 1px solid #444;
                border-radius: 8px;
                color: #aaa;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
                padding: 10px 0;
                margin: 2px 0;
            }}
            .sector-title {{
                flex: 1;
                text-align: center;
                border-right: 1px solid #333;
            }}
            .sector-title:last-child {{
                border-right: none;
            }}
            .curva-col {{
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                gap: 2px;
            }}
        </style>

        <div class="racetrack-container">
            <div class="racetrack-grid">
                <div class="curva-col" style="grid-column: 1; grid-row: 1 / span 3;">
                    <div class="cell" style="background:{get_cor_calor(c_esq_0)}; border-top-left-radius: 20px;">
                        {c_esq_0}<span class="cell-sub">({int(cont.get(c_esq_0,0))})</span>
                    </div>
                    <div class="cell" style="background:{get_cor_calor(c_esq_1)};">
                        {c_esq_1}<span class="cell-sub">({int(cont.get(c_esq_1,0))})</span>
                    </div>
                    <div class="cell" style="background:{get_cor_calor(c_esq_2)}; border-bottom-left-radius: 20px;">
                        {c_esq_2}<span class="cell-sub">({int(cont.get(c_esq_2,0))})</span>
                    </div>
                </div>

                {html_topo}

                <div class="center-area">
                    <div class="sector-title">TIER</div>
                    <div class="sector-title">ORPHELINS</div>
                    <div class="sector-title">VOISINS</div>
                    <div class="sector-title">ZERO</div>
                </div>

                {html_base}

                <div class="curva-col" style="grid-column: 18; grid-row: 1 / span 3;">
                    <div class="cell" style="background:{get_cor_calor(c_dir_0)}; border-top-right-radius: 20px;">
                        {c_dir_0}<span class="cell-sub">({int(cont.get(c_dir_0,0))})</span>
                    </div>
                    <div class="cell" style="background:{get_cor_calor(c_dir_1)};">
                        {c_dir_1}<span class="cell-sub">({int(cont.get(c_dir_1,0))})</span>
                    </div>
                    <div class="cell" style="background:{get_cor_calor(c_dir_2)}; border-bottom-right-radius: 20px;">
                        {c_dir_2}<span class="cell-sub">({int(cont.get(c_dir_2,0))})</span>
                    </div>
                </div>
            </div>
        </div>
        """

        # CORREÇÃO AQUI: unsafe_allow_html=True
        st.markdown(html_racetrack, unsafe_allow_html=True)
        st.caption("🌡️ Distribuição Racetrack | As cores esquentam dinamicamente conforme a frequência das últimas 200 rodadas.")
    except Exception as e:
        st.error(f"Erro ao renderizar o Racetrack: {e}")
else:
    st.info(f"Dados insuficientes para mapa de calor no Racetrack ({qtd}/20)")
    
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
