import streamlit as st
import pandas as pd
from collections import Counter
import websocket
import json

# URL da conexão WebSocket capturada do DevTools (aba Network > WS)
# Nota: substitua pela URL exata da sua sessão se houver token dinâmico
WS_URL = "wss://esportesdasorte.bet.br/socket?messageFormat=json&EVOSESSIONID=..." 

def ao_receber_mensagem(ws, mensagem):
    try:
        dados = json.loads(mensagem)
        tipo = dados.get("type")
        
        # Captura a lista inicial com os números recentes
        if tipo == "roulette.recentResults":
            resultados = dados.get("args", {}).get("recentResults", [])
            numeros = [int(n) for n in resultados if str(n).isdigit()]
            print(f"Histórico Inicial Carregado: {numeros}")

        # Captura o novo número sorteado em tempo real na virada de rodada
        elif tipo == "roulette.tableState" and dados.get("args", {}).get("state") == "GAME_RESOLVED":
            resultado_bruto = dados.get("args", {}).get("result", [])
            if resultado_bruto:
                novo_numero = int(resultado_bruto[0])
                print(f"🚨 NOVO SORTEIO DETECTADO: {novo_numero}")

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def ao_abrir(ws):
    print("Conectado ao WebSocket da Evolution!")

def ao_fechar(ws, status, msg):
    print("Conexão encerrada.")

if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        WS_URL,
        on_message=ao_receber_mensagem,
        on_open=ao_abrir,
        on_close=ao_fechar
    )
    ws.run_forever()

# ==========================================
# 1. CONFIGURAÇÃO E CONSTANTES FÍSICAS
# ==========================================
st.set_page_config(page_title="Radar de Roleta Pro - Motor Avançado", layout="wide")

# Cilindro Europeu na ordem física exata (sentido horário)
CILINDRO_EUROPEU = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

# 4 Setores Clássicos do Racetrack
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

TABELA_PUXADORES_FIXA = {
    0: [34, 14, 26, 10], 1: [36, 1, 21, 29], 2: [20, 11, 22, 25],
    3: [35, 4, 33, 6],   4: [12, 22, 2, 19],  5: [18, 6, 24, 2],
    6: [12, 20, 5, 27],  7: [16, 14, 28, 4],  8: [11, 35, 28, 4],
    9: [9, 36, 3, 19],   10: [24, 20, 28, 19],11: [2, 29, 13, 22],
    12: [32, 21, 3, 30], 13: [31, 11, 33, 15],14: [34, 30, 14, 7],
    15: [35, 32, 13, 17],16: [36, 33, 19, 7], 17: [22, 25, 16, 8],
    18: [5, 22, 6, 21],  19: [28, 21, 16, 20],20: [2, 29, 20, 10],
    21: [12, 19, 18, 30],22: [2, 17, 18, 11], 23: [32, 23, 12, 14],
    24: [22, 27, 10, 7], 25: [27, 22, 2, 7],  26: [0, 17, 29, 23],
    27: [25, 24, 13, 22],28: [19, 8, 7, 14],  29: [20, 11, 26, 2],
    30: [8, 14, 12, 36], 31: [13, 28, 11, 4], 32: [12, 23, 15, 22],
    33: [36, 13, 1, 3],  34: [0, 14, 34, 7],  35: [15, 12, 8, 9],
    36: [16, 36, 1, 9]
}

# ==========================================
# 2. FUNÇÕES AUXILIARES E MATEMÁTICA
# ==========================================
def obter_vizinhos_mesa(numero):
    idx = CILINDRO_EUROPEU.index(numero)
    tamanho = len(CILINDRO_EUROPEU)
    return {
        "esquerda_2": CILINDRO_EUROPEU[(idx - 2) % tamanho],
        "esquerda_1": CILINDRO_EUROPEU[(idx - 1) % tamanho],
        "direita_1": CILINDRO_EUROPEU[(idx + 1) % tamanho],
        "direita_2": CILINDRO_EUROPEU[(idx + 2) % tamanho]
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
        return {"status": "ATIVADO", "principais": [9, 19, 27], "protecoes": [7, 25, 28]}
    return {"status": "INATIVO"}

def analisar_progressao(historico):
    if len(historico) < 2:
        return None
    n1, n2 = historico[-2], historico[-1]
    if n2 == n1 + 1:
        return f"Sequência Crescente ({n1} ➔ {n2}): Entrar Terminal {(n2 + 1) % 10}"
    elif n2 == n1 - 1:
        return f"Sequência Decrescente ({n1} ➔ {n2}): Entrar Terminal {(n2 - 1) % 10}"
    elif n2 == n1 + 2:
        return f"Salto de +2 ({n1} ➔ {n2}): Entrar Terminal {(n2 + 2) % 10}"
    return None

def realizar_benchmark_modelos(historico, janela_analise=400):
    if len(historico) < 50:
        return {"modelo_vencedor": "FIXO", "taxa_fixo": 0.0, "taxa_dinamico": 0.0}
    
    amostra = historico[-janela_analise:]
    acertos_fixo, acertos_dinamico = 0, 0
    total_testes = len(amostra) - 1
    
    for i in range(total_testes):
        num_atual = amostra[i]
        proximo_real = amostra[i+1]
        if proximo_real in TABELA_PUXADORES_FIXA.get(num_atual, []):
            acertos_fixo += 1
        pux_dinamicos = calcular_matriz_transicao(amostra[:i+1])
        if proximo_real in pux_dinamicos[:4]:
            acertos_dinamico += 1

    taxa_fixo = (acertos_fixo / total_testes) * 100
    taxa_dinamico = (acertos_dinamico / total_testes) * 100
    return {
        "modelo_vencedor": "DINAMICO" if taxa_dinamico >= taxa_fixo else "FIXO",
        "taxa_fixo": round(taxa_fixo, 2),
        "taxa_dinamico": round(taxa_dinamico, 2)
    }

# ==========================================
# 3. MOTOR DE SCORAGE MULTI-FILTRO
# ==========================================
def motor_de_scoragem(historico, houve_troca):
    if not historico:
        return 0, [], ["Sem dados no histórico."]
    
    ultimo = historico[-1]
    score = 0
    alvos = set()
    detalhes = []

    # 1. Puxadores Otimizados (Fixos vs. Dinâmicos)
    puxadores = obter_puxadores_otimizados(ultimo, historico)
    if puxadores:
        score += 1
        alvos.update(puxadores[:2])
        detalhes.append(f"Puxadores Híbridos Selecionados: {puxadores}")

    # 2. Vizinhos Físicos da Mesa (+-1, +-2)
    vizinhos = obter_vizinhos_mesa(ultimo)
    score += 1
    alvos.update([vizinhos["esquerda_1"], vizinhos["direita_1"]])
    detalhes.append(f"Vizinhos Físicos: Esq({vizinhos['esquerda_1']}), Dir({vizinhos['direita_1']})")

    # 3. Inversão de Dezenas
    invertido = obter_dezena_invertida(ultimo)
    if invertido is not None:
        score += 1
        alvos.add(invertido)
        detalhes.append(f"Inversão Detectada: {ultimo} ➔ {invertido}")

    # 4. Estratégia Fantasma
    fantasma = checar_estrategia_fantasma(historico)
    if fantasma["status"] == "ATIVADO":
        score += 1
        alvos.update(fantasma["principais"])
        detalhes.append("Padrão Fantasma Ativado: Entrada em 9-19-27")

    # 5. Troca de Croupier
    vizinhos_zero = [1, 5, 8, 11, 14, 23, 26, 32]
    if houve_troca and ultimo in vizinhos_zero:
        score += 1
        alvos.update([0, 10, 20, 30])
        detalhes.append("Troca de Croupier em Vizinho do Zero: Cobertura Terminais 0")

    # 6. Análise Temporal da Esteira (Janela de 14 Posições)
    esteira_14 = historico[-14:]
    reincidencia_recente = [num for num in alvos if num in esteira_14[-3:]]
    if reincidencia_recente:
        score += 1
        detalhes.append(f"Esteira 14p: Alvo(s) {reincidencia_recente} quente(s) na ponta da esteira")

    # 7. Setor Dominante do Racetrack (Voisins, Tiers, Orphelins, Zero Spiel)
    if len(historico) >= 10:
        foco_10 = historico[-10:]
        contagem_setores = {setor: 0 for setor in SETORES_ROLETA}
        for num in foco_10:
            for setor, numeros in SETORES_ROLETA.items():
                if num in numeros:
                    contagem_setores[setor] += 1
        
        setor_dominante = max(contagem_setores, key=contagem_setores.get)
        alvos_no_setor = [num for num in alvos if num in SETORES_ROLETA[setor_dominante]]
        if alvos_no_setor:
            score += 1
            detalhes.append(f"Racetrack: Setor Dominante `{setor_dominante}` alinhado com os alvos")

    score_final = min(score, 5)
    return score_final, list(alvos), detalhes

# ==========================================
# 4. INTERFACE GRÁFICA STREAMLIT
# ==========================================
st.title("🎯 Painel Preditivo de Roleta - Motor de Scoragem Avançado")

if "historico" not in st.session_state:
    st.session_state.historico = []

# Sidebar para Inserção de Dados
st.sidebar.header("🕹️ Painel de Operação")
novo_numero = st.sidebar.number_input("Número Sorteado:", min_value=0, max_value=36, step=1)
houve_troca = st.sidebar.checkbox("Troca de Croupier?")

c1, c2 = st.sidebar.columns(2)
if c1.button("Adicionar"):
    st.session_state.historico.append(int(novo_numero))
if c2.button("Limpar"):
    st.session_state.historico = []

# Exibição Visual da Esteira (14 Posições)
st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[-14:]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)
else:
    st.info("Insira rodadas no painel lateral para iniciar os cálculos.")

# Processamento Principal
if st.session_state.historico:
    ultimo = st.session_state.historico[-1]
    score, alvos_sinal, logs = motor_de_scoragem(st.session_state.historico, houve_troca)
    
    st.markdown("---")
    col_score, col_fisiologia, col_analise = st.columns(3)
    
    with col_score:
        st.markdown("**Pontuação Acumulada**")
        st.metric(label="Score do Sinal", value=f"{score} / 5 Pontos")
        if score <= 2:
            st.info("Status: AGUARDAR (Sem convergência forte)")
        elif score == 3:
            st.warning("Status: PRÉ-ALERTA (Preparar ficha no valor base)")
        else:
            st.error(f"🚨 CONFIRMAÇÃO DE ENTRADA: {alvos_sinal}")

    with col_fisiologia:
        st.markdown("**Fisiologia Física da Mesa**")
        viz = obter_vizinhos_mesa(ultimo)
        st.write(f"Último Número: **{ultimo}**")
        st.write(f"Esq: **{viz['esquerda_2']} | {viz['esquerda_1']}**")
        st.write(f"Dir: **{viz['direita_1']} | {viz['direita_2']}**")
        st.write(f"Camuflados: **{obter_camuflados(ultimo)}**")

    with col_analise:
        st.markdown("**Convergência dos Filtros**")
        for log in logs:
            st.write(f"✔️ {log}")

    # Módulo A/B Benchmark de Assertividade
    if len(st.session_state.historico) >= 50:
        st.markdown("---")
        st.subheader("⚡ A/B Benchmark (Fixo vs. Dinâmico)")
        bench = realizar_benchmark_modelos(st.session_state.historico)
        st.write(f"**Modelo Dominante da Mesa:** `{bench['modelo_vencedor']}`")
        st.write(f"Assertividade Fixo: `{bench['taxa_fixo']}%` | Assertividade Dinâmico: `{bench['taxa_dinamico']}%`")
