import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página Streamlit
st.set_page_config(page_title="Radar de Roleta Pro", layout="wide")

TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

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
    "XXXtreme Lightning": "https://api.core.public.tipminer.com/v1/roulette/rounds/e640b7c7-aaba-4ffa-a678-6b6872898162/history?limit=200",
    "Roleta Brasileira": "https://api.core.public.tipminer.com/v1/roulette/rounds/45d12dd3-8f85-4ab2-8c86-4eaea7967e10/history?limit=200",
    "Immersive Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/dfa678e4-4452-4723-a97d-f3703302d5cc/history?limit=200",
    "Swedish Roulette": "https://api.core.public.tipminer.com/v1/roulette/rounds/9a11309a-4cfa-40d2-b479-a28a01c6ee13/history?limit=200"
}

# ==========================================
# 2. FUNÇÕES AUXILIARES E API
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

def obter_posicoes_estrategicas(historico_completo):
    """
    Retorna apenas as posições estratégicas: 1, 2, 3 e 13
    Ignora o ruído das posições intermediárias (4-12)
    """
    if len(historico_completo) < 13:
        return []
    
    return [
        historico_completo[0],   # pos 1 (última rodada)
        historico_completo[1],   # pos 2
        historico_completo[2],   # pos 3
        historico_completo[12]   # pos 13
    ]

def obter_numeros_unicos_estrategicos(historico_completo):
    """Retorna números únicos das posições estratégicas"""
    pos_estrategicas = obter_posicoes_estrategicas(historico_completo)
    return list(set(pos_estrategicas))

def analisar_ultimos_30_resultados(historico_completo):
    """
    Analisa padrões nos últimos 30 resultados para afunilamento inteligente
    Retorna números com maior probabilidade baseado em:
    - Frequência recente
    - Ciclos de repetição
    - Tendências de vizinhos
    """
    if len(historico_completo) < 30:
        return {
            "quentes_30": [],
            "vizinhos_recorrentes": [],
            "ciclo_detectado": [],
            "score_por_numero": {}
        }
    
    ultimos_30 = historico_completo[:30]
    
    # 1. Números quentes nos últimos 30
    contagem = pd.Series(ultimos_30).value_counts()
    quentes_30 = contagem.head(8).index.tolist()
    
    # 2. Vizinhos que aparecem juntos
    vizinhos_recorrentes = set()
    for i in range(len(ultimos_30) - 1):
        num_atual = ultimos_30[i]
        num_prox = ultimos_30[i + 1]
        viz_atual = obter_vizinhos_mesa(num_atual)
        
        if num_prox in [viz_atual["esq_1"], viz_atual["dir_1"]]:
            vizinhos_recorrentes.add(num_prox)
    
    # 3. Ciclos de repetição (números que voltam após X rodadas)
    ciclos = {}
    for num in set(ultimos_30):
        posicoes = [i for i, x in enumerate(ultimos_30) if x == num]
        if len(posicoes) >= 2:
            intervalos = [posicoes[i+1] - posicoes[i] for i in range(len(posicoes)-1)]
            ciclos[num] = round(np.mean(intervalos)) if intervalos else 0
    
    # Números em zona de ciclo (esperados nas próximas 5 rodadas)
    ciclo_detectado = [num for num, intervalo in ciclos.items() if 3 <= intervalo <= 8]
    
    # 4. Score composto por número
    score_por_numero = {}
    todos_nums = set(quentes_30 + list(vizinhos_recorrentes) + ciclo_detectado)
    
    for num in todos_nums:
        score = 0.0
        if num in quentes_30:
            score += (8 - quentes_30.index(num)) * 1.5
        if num in vizinhos_recorrentes:
            score += 3.0
        if num in ciclo_detectado:
            score += 2.5
        score_por_numero[num] = score
    
    return {
        "quentes_30": quentes_30,
        "vizinhos_recorrentes": list(vizinhos_recorrentes),
        "ciclo_detectado": ciclo_detectado,
        "score_por_numero": score_por_numero
    }

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
            return []
    except Exception:
        return []

# ==========================================
# 3. NOTIFICAÇÕES TELEGRAM
# ==========================================

def enviar_mensagem_telegram(texto):
    if TELEGRAM_BOT_TOKEN == "SEU_BOT_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        return False, "Token do Bot não configurado."
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code == 200, "Mensagem enviada com sucesso!"
    except Exception as e:
        return False, str(e)

def enviar_alerta_telegram(ultimo, score, alvos, padroes, roleta_nome="Desconhecida", 
                           tier_nome="Indefinido", posicao_rank=None, taxa_acerto=None, 
                           tipo_entrada="SINAL"):
    """
    Envia alerta com identificação clara do tipo de entrada:
    - 🎯 HEAD-SHOT: 1-3 dezenas
    - 🔥 TIRO CERTO: 4-6 dezenas
    - 📊 SINAL TIER: 6-8 dezenas
    """
    pos_str = f"#{posicao_rank}" if posicao_rank else "N/A"
    taxa_str = f"{taxa_acerto}%" if taxa_acerto is not None else "N/A"
    
    # Determinar ícone do tipo
    qtd_alvos = len(alvos)
    if "HEAD-SHOT" in tipo_entrada or qtd_alvos <= 3:
        icone_tipo = "🎯"
        nome_tipo = "HEAD-SHOT"
    elif "TIRO CERTO" in tipo_entrada or 4 <= qtd_alvos <= 6:
        icone_tipo = "🔥"
        nome_tipo = "TIRO CERTO"
    else:
        icone_tipo = "📊"
        nome_tipo = "SINAL TIER"
    
    msg = (
        f"{icone_tipo} *{nome_tipo} DETECTADO* {icone_tipo}\n\n"
        f"🎰 *Roleta:* `{roleta_nome}`\n"
        f"🎲 *Último Número:* `{ultimo}`\n"
        f"🔥 *Score:* `{score}/5`\n"
        f"🏆 *Tier:* `{tier_nome}` (#{pos_str} | {taxa_str})\n"
        f"🎯 *Quantidade de Alvos:* `{qtd_alvos} dezenas`\n"
        f"🔢 *APOSTAR EM:* `{alvos}`\n"
        f"📋 *Padrão:* {', '.join(padroes)}"
    )
    return enviar_mensagem_telegram(msg)

def enviar_resultado_telegram(tipo, numero, etapa="", roleta_nome="Desconhecida"):
    emoji = "✅" if tipo == "GREEN" else "❌"
    msg = f"{emoji} *RESULTADO: {tipo}* {f'({etapa})' if etapa else ''}\n🎰 Roleta: `{roleta_nome}`\n🎲 Número Sorteado: `{numero}`"  
    return enviar_mensagem_telegram(msg)

# ==========================================
# 4. MOTOR DE IMPACTO: TIRO CERTO E HEAD-SHOT
# ==========================================

def processar_tiro_certo_e_headshot(historico_completo, historico_200, dados_brk_in, 
                                     puxadores_dict, inversoes_dict, 
                                     vizinhos_fisi_dict, quentes_100):
    """
    Analisa APENAS posições estratégicas (1, 2, 3, 13)
    + Validação com últimos 30 resultados
    
    LIMITES:
    - Head-Shot: 1-3 dezenas (peso ≥ 12.0)
    - Tiro Certo: 4-6 dezenas (peso ≥ 7.0)
    """
    
    posicoes_estrategicas = obter_posicoes_estrategicas(historico_completo)
    numeros_unicos = obter_numeros_unicos_estrategicos(historico_completo)
    
    if not numeros_unicos:
        return {
            "ativacoes": {},
            "detalhes_pesos": {},
            "alvos_tiro_certo": [],
            "alvos_headshot": [],
            "status_nome": "AGUARDAR",
            "posicoes_analisadas": [],
            "analise_30": {}
        }
    
    # ANÁLISE DOS ÚLTIMOS 30 RESULTADOS
    analise_30 = analisar_ultimos_30_resultados(historico_completo)
    
    ativacoes = {num: set() for num in numeros_unicos}
    detalhes_pesos = {num: 0.0 for num in numeros_unicos}
    
    ultimo_numero = historico_completo[0]
    
    for num in numeros_unicos:
        peso = 0.0
        
        # 1. Vizinho físico nas posições estratégicas
        vizinhos = vizinhos_fisi_dict.get(num, [])
        if any(v in numeros_unicos for v in vizinhos):
            ativacoes[num].add("Vizinho_Pos")
            peso += 1.5
        
        # 2. Quente nas últimas 100 rodadas
        if num in quentes_100:
            ativacoes[num].add("Quente_100R")
            peso += 1.0
        
        # 3. Frequência nas posições estratégicas
        freq_estrategica = posicoes_estrategicas.count(num)
        if freq_estrategica >= 2:
            ativacoes[num].add(f"Freq_{freq_estrategica}x")
            peso += freq_estrategica * 2.5
        
        # 4. Puxador direto (Top 2)
        puxs = puxadores_dict.get(ultimo_numero, [])
        if puxs and num in puxs[:2]:
            rank_px = puxs.index(num) + 1
            if rank_px == 1:
                ativacoes[num].add("Puxador_1")
                peso += 4.0
            else:
                ativacoes[num].add("Puxador_2")
                peso += 2.5
        
        # 5. Ausente no grupo BRK (prioridade crítica)
        if num in dados_brk_in.get("ausentes", []):
            ativacoes[num].add("BRK_Ausente")
            peso += 5.0
        
        # 6. Presente nas últimas 3 posições (pos 1, 2, 3)
        if num in historico_completo[:3]:
            ativacoes[num].add("Top3_Recente")
            peso += 3.0
        
        # 7. Inversão do último número
        inv = inversoes_dict.get(ultimo_numero)
        if inv and num == inv:
            ativacoes[num].add("Inversão")
            peso += 2.5
        
        # 8. ⭐ BOOST DOS ÚLTIMOS 30 RESULTADOS
        if num in analise_30["quentes_30"]:
            posicao = analise_30["quentes_30"].index(num) + 1
            boost = (9 - posicao) * 0.6
            ativacoes[num].add(f"Quente30_#{posicao}")
            peso += boost
        
        if num in analise_30["vizinhos_recorrentes"]:
            ativacoes[num].add("Viz_Recorrente")
            peso += 3.5
        
        if num in analise_30["ciclo_detectado"]:
            ativacoes[num].add("Ciclo_Ativo")
            peso += 3.0
        
        # 9. Score composto dos últimos 30
        score_30 = analise_30["score_por_numero"].get(num, 0.0)
        if score_30 > 0:
            peso += min(score_30 * 0.4, 4.0)
        
        detalhes_pesos[num] = round(peso, 2)
    
    # ⭐ CRITÉRIOS AJUSTADOS COM LIMITES PRECISOS
    
    # HEAD-SHOT: 1-3 dezenas (altíssima precisão)
    candidatos_headshot = sorted(
        [(n, p) for n, p in detalhes_pesos.items() if p >= 12.0],
        key=lambda x: x[1],
        reverse=True
    )
    alvos_headshot = [int(n) for n, p in candidatos_headshot[:3]]
    
    # TIRO CERTO: 4-6 dezenas (alta precisão)
    candidatos_tiro_certo = sorted(
        [(n, p) for n, p in detalhes_pesos.items() if p >= 7.0],
        key=lambda x: x[1],
        reverse=True
    )
    alvos_tiro_certo = [int(n) for n, p in candidatos_tiro_certo[:6]]
    
    # Garantir mínimos
    if len(alvos_tiro_certo) < 4 and len(candidatos_tiro_certo) >= 4:
        candidatos_tiro_certo_flex = sorted(
            [(n, p) for n, p in detalhes_pesos.items() if p >= 5.5],
            key=lambda x: x[1],
            reverse=True
        )
        alvos_tiro_certo = [int(n) for n, p in candidatos_tiro_certo_flex[:6]]
    
    # Status
    status_nome = "AGUARDAR"
    if alvos_headshot:
        status_nome = f"🎯 HEAD-SHOT ({len(alvos_headshot)})"
    elif alvos_tiro_certo and len(alvos_tiro_certo) >= 4:
        status_nome = f"🔥 TIRO CERTO ({len(alvos_tiro_certo)})"
    
    return {
        "ativacoes": ativacoes,
        "detalhes_pesos": detalhes_pesos,
        "alvos_tiro_certo": alvos_tiro_certo,
        "alvos_headshot": alvos_headshot,
        "status_nome": status_nome,
        "posicoes_analisadas": posicoes_estrategicas,
        "analise_30": analise_30
    }

def afunilar_alvos_final(alvos_brutos, tier_nivel, res_tiro_certo, analise_30, dados_brk_in=None):
    """
    Afunilamento progressivo com limites rigorosos:
    
    PRIORIDADE 1: Head-Shot (1-3 dezenas) - se disponível
    PRIORIDADE 2: Tiro Certo (4-6 dezenas) - cruzado com tier
    PRIORIDADE 3: Tier + Score 30 (até 8 dezenas)
    
    SAÍDA FINAL: Sempre 6-8 dezenas (nunca mais de 8)
    """
    
    if not alvos_brutos:
        return []
    
    alvos_headshot = set(res_tiro_certo.get("alvos_headshot", []))
    alvos_tiro_certo = set(res_tiro_certo.get("alvos_tiro_certo", []))
    score_30 = analise_30.get("score_por_numero", {})
    detalhes_pesos = res_tiro_certo.get("detalhes_pesos", {})
    
    # ⭐ CASO 1: HEAD-SHOT DISPONÍVEL (1-3 dezenas)
    if alvos_headshot and len(alvos_headshot) in [1, 2, 3]:
        if tier_nivel == "👑 Elite (Top 3)":
            return sorted(list(alvos_headshot), key=lambda x: detalhes_pesos.get(x, 0), reverse=True)
        else:
            base_headshot = sorted(list(alvos_headshot), key=lambda x: detalhes_pesos.get(x, 0), reverse=True)
            
            complemento_tiro = [n for n in alvos_tiro_certo if n not in alvos_headshot]
            complemento_tiro_ordenado = sorted(complemento_tiro, key=lambda x: detalhes_pesos.get(x, 0), reverse=True)
            
            qtd_necessaria = min(8 - len(base_headshot), 5)
            dezenas_finais = base_headshot + complemento_tiro_ordenado[:qtd_necessaria]
            
            return dezenas_finais[:8]
    
    # ⭐ CASO 2: TIRO CERTO (4-6 dezenas) + TIER
    if alvos_tiro_certo and len(alvos_tiro_certo) >= 4:
        if tier_nivel == "👑 Elite (Top 3)":
            alvos_tier = alvos_brutos[:8]
        elif tier_nivel == "🥇 Seleção Ouro (Top 5)":
            alvos_tier = alvos_brutos[:10]
        elif tier_nivel == "🥈 Seleção (Top 10)":
            alvos_tier = alvos_brutos[:12]
        else:
            alvos_tier = alvos_brutos[:15]
        
        compativel_tiro = [n for n in alvos_tier if n in alvos_tiro_certo]
        
        if len(compativel_tiro) >= 4:
            compativel_ordenado = sorted(
                compativel_tiro,
                key=lambda x: detalhes_pesos.get(x, 0),
                reverse=True
            )
            
            if len(compativel_ordenado) >= 6:
                return compativel_ordenado[:8]
            else:
                outros_tier = [n for n in alvos_tier if n not in compativel_ordenado]
                outros_ordenados = sorted(
                    outros_tier,
                    key=lambda x: score_30.get(x, 0),
                    reverse=True
                )
                
                qtd_necessaria = min(8 - len(compativel_ordenado), len(outros_ordenados))
                dezenas_finais = compativel_ordenado + outros_ordenados[:qtd_necessaria]
                
                return dezenas_finais[:8]
    
    # ⭐ CASO 3: SEM TIRO CERTO/HEAD-SHOT - Usar apenas Tier + Score 30
    limite = 8
    
    def calcular_score_final(num):
        base = score_30.get(num, 0.0) * 2
        if dados_brk_in and num in dados_brk_in.get("ausentes", []):
            base += 100.0
        return base
    
    alvos_ordenados = sorted(
        alvos_brutos[:limite],
        key=calcular_score_final,
        reverse=True
    )
    
    return alvos_ordenados[:8]

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
# 6. MOTOR DE SCORAGE
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
# 7. ESTADO INICIAL E PAINEL LATERAL
# ==========================================
st.title("🎯 Radar de Roleta Pro - Painel de Testes & Sinais")

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
# PROCESSAMENTO DE NOVO NÚMERO E SINAIS
# ==========================================
def processar_novo_numero(num_novo):
    if st.session_state.sinal_ativo:
        st.session_state.tentativa_atual += 1
        etapas = {1: "Entrada Direta", 2: "Gale 1 (G1)", 3: "Gale 2 (G2)"}
        etapa_nome = etapas.get(st.session_state.tentativa_atual, f"Gale {st.session_state.tentativa_atual - 1}")
        
        alvos_com_zero = set(st.session_state.alvos_sinal + [0])
        if num_novo in alvos_com_zero:
            st.session_state.ultimo_resultado = f"GREEN ✅ ({etapa_nome})"
            enviar_resultado_telegram("GREEN", num_novo, etapa_nome, roleta_nome=roleta_selecionada)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return
        elif st.session_state.tentativa_atual >= 3:
            st.session_state.ultimo_resultado = "LOSS / RED ❌"
            enviar_resultado_telegram("LOSS", num_novo, roleta_nome=roleta_selecionada)
            st.session_state.sinal_ativo = False
            st.session_state.tentativa_atual = 0
            st.session_state.alvos_sinal = []
            return

    # VALIDAÇÃO DE HISTÓRICO MÍNIMO
    if len(st.session_state.historico) < 30:
        return
    
    historico_analise = list(reversed(st.session_state.historico))
    res_ultimo = analisar_rodada_especifica(historico_analise)
    
    if res_ultimo["score_num"] >= 4:
        tiers, df_rank = obter_tiers_cache()
        padrao = res_ultimo["padrao_nome"]
        
        # Validar se está no ranking
        if df_rank.empty or padrao not in df_rank["Padrão"].values:
            return
        
        idx_rank = df_rank[df_rank["Padrão"] == padrao].index[0]
        posicao_rank = idx_rank + 1
        taxa_acerto = df_rank.loc[idx_rank, "Taxa de Acerto (%)"]
        
        # Determinar tier
        tier_do_padrao = "Fora dos Tiers"
        if padrao in tiers.get("ELITE_TOP_3", []):
            tier_do_padrao = "👑 Elite (Top 3)"
        elif padrao in tiers.get("SELECAO_OURO_TOP_5", []):
            tier_do_padrao = "🥇 Seleção Ouro (Top 5)"
        elif padrao in tiers.get("SELECAO_TOP_10", []):
            tier_do_padrao = "🥈 Seleção (Top 10)"
        elif padrao in tiers.get("RADAR_TOP_30", []):
            tier_do_padrao = "🥉 Radar (Top 30)"
        
        # Validar filtro híbrido
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
        
        if not permitido:
            return
        
        # ⭐ CALCULAR TIRO CERTO COM BASE NOS ÚLTIMOS 30
        historico_200 = list(reversed(st.session_state.historico[:200]))
        dados_brk = validar_gatilho_sequencial_brk(historico_analise)
        dados_brk_in = {
            "ausentes": dados_brk.get("prioridade_maxima", []) if dados_brk.get("sinal_ativo") else [],
            "cobertura": dados_brk.get("cobertura", []) if dados_brk.get("sinal_ativo") else []
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
            st.session_state.historico,
            historico_200,
            dados_brk_in,
            puxadores_dict,
            inversoes_dict,
            vizinhos_fisi_dict,
            quentes_100
        )
        
        # ⭐ AFUNILAMENTO PROGRESSIVO
        analise_30 = res_tiro_certo.get("analise_30", {})
        
        # Determinar limite de dezenas por tier
        if tier_do_padrao == "👑 Elite (Top 3)":
            max_dezenas = 6
        elif tier_do_padrao == "🥇 Seleção Ouro (Top 5)":
            max_dezenas = 7
        else:
            max_dezenas = 8
        
        alvos_afunilados = afunilar_alvos_final(
            alvos_brutos=res_ultimo["alvos"],
            tier_nivel=tier_do_padrao,
            res_tiro_certo=res_tiro_certo,
            analise_30=analise_30,
            dados_brk_in=dados_brk_in
        )
        
        # Garantir limite máximo de 8 dezenas
        alvos_afunilados = alvos_afunilados[:8]
        
        # Validar quantidade mínima
        if len(alvos_afunilados) < 4:
            return
        
        # LÓGICA DE GALE
        if st.session_state.sinal_ativo:
            if "Fusão" in modo_gale_opcao and tier_do_padrao == "👑 Elite (Top 3)":
                alvos_novos = [n for n in alvos_afunilados if n not in st.session_state.alvos_sinal]
                limite_total = 8
                vagas = limite_total - len(st.session_state.alvos_sinal)
                
                if vagas > 0 and alvos_novos:
                    st.session_state.alvos_sinal.extend(alvos_novos[:vagas])
                    enviar_mensagem_telegram(
                        f"🔄 *FUSÃO AFUNILADA (GALE)*\n"
                        f"🎰 Roleta: `{roleta_selecionada}`\n"
                        f"➕ Adicionadas: `{alvos_novos[:vagas]}`\n"
                        f"🎯 Total: `{st.session_state.alvos_sinal}`"
                    )
        else:
            # NOVO SINAL
            st.session_state.sinal_ativo = True
            st.session_state.alvos_sinal = alvos_afunilados
            st.session_state.tentativa_atual = 0
            
            # Determinar tipo de entrada baseado na quantidade
            qtd_final = len(alvos_afunilados)
            if res_tiro_certo["alvos_headshot"] and qtd_final <= 3:
                tipo_entrada = "🎯 HEAD-SHOT"
            elif res_tiro_certo["alvos_tiro_certo"] and 4 <= qtd_final <= 6:
                tipo_entrada = "🔥 TIRO CERTO"
            else:
                tipo_entrada = f"📊 SINAL {tier_do_padrao}"
            
            enviar_alerta_telegram(
                res_ultimo["ultimo"],
                res_ultimo["score_num"],
                alvos_afunilados,
                [f"{padrao}"],
                roleta_nome=roleta_selecionada,
                tier_nome=tier_do_padrao,
                posicao_rank=posicao_rank,
                taxa_acerto=taxa_acerto,
                tipo_entrada=tipo_entrada
            )

# Execução da Entrada de Dados
if modo_operacao == "On-line (Captura Automática)":
    novos_dados = buscar_dados_roleta_url(roleta_selecionada)
    if novos_dados:
        st.sidebar.success(f"🟢 Conectado: **{roleta_selecionada}**")
        if novos_dados != st.session_state.historico:
            num_novo = novos_dados[0]
            processar_novo_numero(num_novo)
            st.session_state.historico = novos_dados
    else:
        st.sidebar.warning(f"🟡 Tentando reconectar à **{roleta_selecionada}**...")
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

# Esteira Visual
st.subheader("🎲 Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)
else:
    st.info("Aguardando captura do primeiro sorteio na mesa...")

# Alerta BRK
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

if st.session_state.ultimo_resultado:
    if "GREEN" in st.session_state.ultimo_resultado:
        st.success(f"🎉 Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")
    else:
        st.error(f"⚠️ Resultado do Último Sinal: **{st.session_state.ultimo_resultado}**")

# ==========================================
# 8. MAPEAMENTO ANALÍTICO (CORRIGIDO E PADRONIZADO)
# ==========================================
if st.session_state.historico and len(st.session_state.historico) >= 30:
    st.markdown("---")
    
    historico_200 = list(reversed(st.session_state.historico[:200]))
    
    # Configurações
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
        st.session_state.historico,
        historico_200,
        dados_brk_in,
        puxadores_dict,
        inversoes_dict,
        vizinhos_fisi_dict,
        quentes_100
    )

    # ANÁLISE DAS POSIÇÕES ESTRATÉGICAS
    posicoes_estrategicas_idx = [0, 1, 2, 12]
    dados_tabela = []
    
    for idx_real in posicoes_estrategicas_idx:
        if idx_real >= len(st.session_state.historico):
            continue
            
        num = st.session_state.historico[idx_real]
        sub_hist = list(reversed(st.session_state.historico[idx_real:]))
        
        if len(sub_hist) < 30:
            continue
            
        res = analisar_rodada_especifica(sub_hist)
        ativacoes_num = res_tiro_certo["ativacoes"].get(num, set())
        
        # Nome da posição
        nomes_posicoes = {0: "🎯 Pos 1", 1: "📍 Pos 2", 2: "📍 Pos 3", 12: "📍 Pos 13"}
        nome_pos = nomes_posicoes.get(idx_real, f"Pos {idx_real+1}")

        # VALIDAÇÃO COM RANKING + AFUNILAMENTO
        tiers_atuais, df_rank = obter_tiers_cache()
        padrao_no_rank = res["padrao_nome"] in df_rank["Padrão"].values if not df_rank.empty else False
        
        if res["score_num"] >= 4 and padrao_no_rank:
            idx_rank = df_rank[df_rank["Padrão"] == res["padrao_nome"]].index[0]
            taxa = df_rank.loc[idx_rank, "Taxa de Acerto (%)"]
            pos_rank = idx_rank + 1
            
            tier = "Fora dos Tiers"
            if res["padrao_nome"] in tiers_atuais.get("ELITE_TOP_3", []):
                tier = "👑 Elite"
            elif res["padrao_nome"] in tiers_atuais.get("SELECAO_OURO_TOP_5", []):
                tier = "🥇 Ouro"
            elif res["padrao_nome"] in tiers_atuais.get("SELECAO_TOP_10", []):
                tier = "🥈 Seleção"
            elif res["padrao_nome"] in tiers_atuais.get("RADAR_TOP_30", []):
                tier = "🥉 Radar"
            
            # APLICAR AFUNILAMENTO
            analise_30 = res_tiro_certo.get("analise_30", {})
            
            # Recalcular dados_brk_in no contexto
            res_brk_atual = validar_gatilho_sequencial_brk(list(reversed(st.session_state.historico[idx_real:])))
            dados_brk_contexto = {
                "ausentes": res_brk_atual.get("prioridade_maxima", []) if res_brk_atual.get("sinal_ativo") else [],
                "cobertura": res_brk_atual.get("cobertura", []) if res_brk_atual.get("sinal_ativo") else []
            }
            
            alvos_afunilados = afunilar_alvos_final(
                alvos_brutos=res["alvos"],
                tier_nivel=tier,
                res_tiro_certo=res_tiro_certo,
                analise_30=analise_30,
                dados_brk_in=dados_brk_contexto
            )
            
            # Limitar exibição
            alvos_afunilados = alvos_afunilados[:8]
            qtd = len(alvos_afunilados)
            
            # Identificar tipo
            if qtd <= 3:
                tipo_icone = "🎯"
            elif 4 <= qtd <= 6:
                tipo_icone = "🔥"
            else:
                tipo_icone = "📊"
            
            sugestao_texto = f"{tipo_icone} {tier} (#{pos_rank}|{taxa}%) → {alvos_afunilados} ({qtd})"
            
        elif idx_real == 0:
            if res_tiro_certo["alvos_headshot"]:
                sugestao_texto = f"🎯 HEAD-SHOT → {res_tiro_certo['alvos_headshot']}"
            elif res_tiro_certo["alvos_tiro_certo"]:
                sugestao_texto = f"🔥 TIRO CERTO → {res_tiro_certo['alvos_tiro_certo']}"
            else:
                sugestao_texto = "⚪ AGUARDAR"
        else:
            sugestao_texto = "⚪ AGUARDAR"

        # Montar linha da tabela
        peso_total = res_tiro_certo['detalhes_pesos'].get(num, 0.0)
        
        dados_tabela.append({
            "Posição": nome_pos,
            "Nº": num,
            "Ativações": " | ".join(sorted(ativacoes_num)) if ativacoes_num else "—",
            "Peso Total": f"⚡ {peso_total:.1f}",
            "Status / Sugestão": sugestao_texto
        })
    
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    
    if dados_tabela:
        df_exibicao = pd.DataFrame(dados_tabela)
        st.dataframe(df_exibicao, use_container_width=True, height=250)
        
        # Informações adicionais
        analise_30 = res_tiro_certo.get("analise_30", {})
        col_info1, col_info2, col_info3 = st.columns(3)
        
        with col_info1:
            st.metric("🔥 Quentes (últimos 30)", len(analise_30.get("quentes_30", [])))
            st.caption(f"Top 8: {analise_30.get('quentes_30', [])[:8]}")
        
        with col_info2:
            st.metric("🎯 Tiro Certo", len(res_tiro_certo.get("alvos_tiro_certo", [])))
            st.caption(f"{res_tiro_certo.get('alvos_tiro_certo', [])}")
        
        with col_info3:
            st.metric("💎 Head-Shot", len(res_tiro_certo.get("alvos_headshot", [])))
            st.caption(f"{res_tiro_certo.get('alvos_headshot', [])}")
    else:
        st.info("⏳ Aguardando histórico mínimo de 30 rodadas...")

    # Ranking de Padrões
    tiers_atuais, df_rank = obter_tiers_cache()
    with st.expander("🏆 Ranking dos Padrões (Assertividade ≥ 50% - Últimas 200 Rodadas)", expanded=False):
        if not df_rank.empty:
            df_rank_exib = df_rank.copy()
            df_rank_exib.index = range(1, len(df_rank_exib) + 1)
            st.dataframe(df_rank_exib, use_container_width=True)
        else:
            st.info("Nenhum padrão com no mínimo 50% de acerto foi consolidado ainda.")

    # Botão Reenviar Alerta
    historico_analise = list(reversed(st.session_state.historico))
    res_ultimo = analisar_rodada_especifica(historico_analise)
    
    if res_ultimo["score_num"] >= 4:
        tiers_atuais, df_rank = obter_tiers_cache()
        
        if not df_rank.empty and res_ultimo["padrao_nome"] in df_rank["Padrão"].values:
            idx_rank = df_rank[df_rank["Padrão"] == res_ultimo["padrao_nome"]].index[0]
            taxa = df_rank.loc[idx_rank, "Taxa de Acerto (%)"]
            pos_rank = idx_rank + 1
            
            st.success(f"✅ **SINAL VALIDADO PELO RANKING**")
            st.info(f"📊 Padrão: `{res_ultimo['padrao_nome']}`  \n🏆 Posição: **#{pos_rank}** | Assertividade: **{taxa}%**")
            
            if st.button("📤 Reenviar Alerta para Telegram"):
                # Determinar tier
                tier_do_padrao = "Fora dos Tiers"
                if res_ultimo["padrao_nome"] in tiers_atuais.get("ELITE_TOP_3", []):
                    tier_do_padrao = "👑 Elite (Top 3)"
                elif res_ultimo["padrao_nome"] in tiers_atuais.get("SELECAO_OURO_TOP_5", []):
                    tier_do_padrao = "🥇 Seleção Ouro (Top 5)"
                elif res_ultimo["padrao_nome"] in tiers_atuais.get("SELECAO_TOP_10", []):
                    tier_do_padrao = "🥈 Seleção (Top 10)"
                elif res_ultimo["padrao_nome"] in tiers_atuais.get("RADAR_TOP_30", []):
                    tier_do_padrao = "🥉 Radar (Top 30)"
                
                sucesso, msg = enviar_alerta_telegram(
                    res_ultimo["ultimo"],
                    res_ultimo["score_num"],
                    st.session_state.alvos_sinal if st.session_state.alvos_sinal else res_ultimo["alvos"][:8],
                    [res_ultimo["padrao_nome"]],
                    roleta_nome=roleta_selecionada,
                    tier_nome=tier_do_padrao,
                    posicao_rank=pos_rank,
                    taxa_acerto=taxa
                )
                if sucesso:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.warning(f"⚠️ **SINAL DETECTADO MAS NÃO VALIDADO PELO RANKING**")
            st.error(f"❌ O padrão `{res_ultimo['padrao_nome']}` não atingiu 50% de assertividade nas últimas 200 rodadas ou não possui histórico suficiente.")
            st.caption("💡 **Sugestão:** Aguarde um sinal validado pelo Ranking ou ajuste o filtro híbrido.")

# ==========================================
# 9. ESTATÍSTICAS E PAINEL VISUAL
# ==========================================
if st.session_state.get("historico"):
    st.markdown("---")
    st.subheader("📊 Estatísticas das Rodadas (Quentes/Frios, Avançada, Últimas 200)")

    total_disponivel = len(st.session_state.historico)
    max_amostra = min(200, total_disponivel)
    
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
        
        st.write(f"🔥 **Mais Frequentes:** {quentes}")
        st.write(f"🧊 **Menos Frequentes:** {frios}")
        
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
        grid_rows = [
            [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
            [0, 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
            [0, 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]
        ]
        text_vals = [[f"{n}<br>({matriz_freq[n]})" for n in row] for row in grid_rows]
        
        custom_colorscale = [
            [0.0, "#FFFFFF"],
            [0.5, "#1E1E1E"],
            [1.0, "#D32F2F"]
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

# Loop de Recarrega Automático
if modo_operacao == "On-line (Captura Automática)":
    time.sleep(5)
    st.rerun()
