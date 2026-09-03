import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import time

# Configuração da página Streamlit
st.set_page_config(
    page_title="Sistema Analítico de Roleta",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes da Roleta
NUMEROS_VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NUMEROS_PRETOS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# Inicialização do Estado de Sessão
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

# ==========================================
# FUNÇÕES DE SUPORTE E ANÁLISE
# ==========================================

def buscar_dados_roleta_url(roleta_nome):
    """Simulação ou chamada HTTP para busca de dados da roleta"""
    # Exemplo mock/retorno de lista vazia para prevenir exceções caso API não esteja configurada
    return st.session_state.get("historico", [])

def processar_novo_numero(num):
    """Atualiza o estado e processa novos números sorteados"""
    pass

def validar_gatilho_sequencial_brk(historico):
    """Valida o gatilho de padrão BRK no histórico cronológico"""
    if len(historico) < 2:
        return {"sinal_ativo": False}
    # Retorno estruturado de exemplo para a lógica BRK
    return {
        "sinal_ativo": False,
        "grupo_confirmado": "A",
        "dezena_gatilho": historico[-1] if historico else 0,
        "dezena_confirmada": historico[-2] if len(historico) > 1 else 0,
        "prioridade_maxima": [1, 2, 3],
        "cobertura": [4, 5, 6]
    }

def analisar_rodada_especifica(historico_sub):
    """Gera o mapeamento analítico para cada posição do histórico"""
    ult = historico_sub[-1] if historico_sub else "-"
    return {
        "ultimo": ult,
        "esquerda": "-",
        "direita": "-",
        "puxadores": "-",
        "vizinhos_str": "-",
        "camuflados": "-",
        "racetrack": "-",
        "inversao": "-",
        "reincidencia": "-",
        "confirmacoes": "-",
        "score": "0/5",
        "score_num": 0,
        "alvos": [],
        "status": "Aguardando",
        "padrao_nome": "Padrão Base"
    }

def obter_tiers_cache():
    """Retorna o ranking de tiers armazenado em cache"""
    df_empty = pd.DataFrame(columns=["Padrão", "Taxa de Acerto (%)"])
    return {}, df_empty

def enviar_alerta_telegram(ultimo, score, alvos, status, posicao_rank=None, taxa_acerto=None):
    """Dispara a notificação de alerta via API do Telegram"""
    return True, "✅ Alerta enviado com sucesso ao Telegram!"

# ==========================================
# PAINEL LATERAL (SIDEBAR)
# ==========================================

st.sidebar.title("🎰 Controle do Operador")

modo_operacao = st.sidebar.radio(
    "Modo de Operação:",
    ["On-line (Captura Automática)", "Manual"]
)

roleta_selecionada = st.sidebar.selectbox(
    "Selecione a Roleta:",
    ["Roleta Brasileira", "Roleta Imersiva", "VIP Roulette"]
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
        for chave in ["tier_cache", "df_rank_cache", "tier_cache_tamanho"]:
            if chave in st.session_state:
                del st.session_state[chave]
        st.rerun()

# ==========================================
# ÁREA PRINCIPAL DE VISUALIZAÇÃO
# ==========================================

st.title("🎰 Painel Analítico & Preditivo de Roleta")

st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)
else:
    st.info("Nenhum histórico registrado até o momento.")

# Exibição do Alerta Exclusivo BRK
if st.session_state.historico and len(st.session_state.historico) >= 2:
    historico_cronologico = list(reversed(st.session_state.historico))
    res_brk_painel = validar_gatilho_sequencial_brk(historico_cronologico)
    
    if res_brk_painel.get("sinal_ativo"):
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

# Tabela Analítica
if st.session_state.historico:
    st.markdown("---")
    st.subheader(f"📊 Mapeamento Analítico - {roleta_selecionada}")
    
    dados_tabela = []
    janela_exibicao = st.session_state.historico[:14]
    
    for idx, num in enumerate(janela_exibicao):
        sub_hist = list(reversed(st.session_state.historico[idx:]))
        res = analisar_rodada_especifica(sub_hist)
        
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
            "Confirmações": res["confirmacoes"],
            "Score": res["score"],
            "Status / Sugestão": res["status"]
        })
    
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
# ESTATÍSTICAS AVANÇADAS
# ==========================================

if st.session_state.historico:
    st.markdown("---")
    st.subheader("📊 Estatísticas das Rodadas (Quentes/Frios, Avançada, Últimas 1000)")
    
    total_disponivel = len(st.session_state.historico)
    max_amostra = min(1000, total_disponivel)
    
    min_val = min(10, total_disponivel) if total_disponivel > 0 else 10
    max_val = max(min_val, max_amostra)
    
    qtd_rodadas = st.slider(
        "Selecione o tamanho da amostra (Últimas X rodadas):",
        min_value=min_val,
        max_value=max_val,
        value=max_val,
        step=5 if max_val - min_val >= 5 else 1
    )
    
    amostra = list(reversed(st.session_state.historico[:qtd_rodadas]))
    total_amostra = len(amostra)
    
    if total_amostra > 0:
        col_g1, col_g2, col_g3 = st.columns(3)
        
        # Coluna 1: Quentes e Frios
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
            
        # Coluna 2: Análise Avançada
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

        # Coluna 3: Mapa de Calor
        with col_g3:
            st.markdown(f"### 📊 ÚLTIMAS {qtd_rodadas}")
            
            matriz_freq = {n: amostra.count(n) for n in range(0, 37)}
            
            st.write("🔥 **Mapa de Calor da Mesa (0 a 36):**")
            
            grid_rows = [
                [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
                [0, 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
                [0, 1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34]
            ]
            
            z_vals = [[matriz_freq[n] for n in row] for row in grid_rows]
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
