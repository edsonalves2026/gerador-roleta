import os
import time
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import streamlit.components.v1 as components

# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Roulette Analytics & Signals",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CONSTANTES E MAPEAMENTOS DA ROLETA
# ==========================================
NUMEROS_VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
NUMEROS_PRETO = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# Ordem real dos números na roleta europeia
CILINDRO_EUROPEU = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

# Dicionário com URLs/IDs típicos de roletas para integração via API
ROLETA_CONFIG = {
    "Immersive Roulette": {"id": "immersive", "provider": "evolution"},
    "VIP Roulette": {"id": "vip", "provider": "evolution"},
    "Speed Roulette": {"id": "speed", "provider": "evolution"},
    "Auto-Roulette": {"id": "autoroulette", "provider": "evolution"},
    "Brazilian Roulette": {"id": "roleta_brasileira", "provider": "evolution"}
}

# ==========================================
# INICIALIZAÇÃO DO SESSION STATE
# ==========================================
if "historico" not in st.session_state:
    st.session_state.historico = []

if "sinal_ativo" not in st.session_state:
    st.session_state.sinal_ativo = False

if "tentativa_atual" not in st.session_state:
    st.session_state.tentativa_atual = 0

if "alvos_sinal" not in st.session_state:
    st.session_state.alvos_sinal = []

if "telegram_token" not in st.session_state:
    st.session_state.telegram_token = ""

if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# ==========================================
# FUNÇÕES AUXILIARES DE CÁLCULO E API
# ==========================================
def calcular_estatisticas(historico):
    """Calcula estatísticas de Dúzias, Colunas, Paridade, Altas/Baixas."""
    if not historico:
        return {}
    
    total = len(historico)
    d1 = sum(1 for n in historico if 1 <= n <= 12)
    d2 = sum(1 for n in historico if 13 <= n <= 24)
    d3 = sum(1 for n in historico if 25 <= n <= 36)

    c1 = sum(1 for n in historico if n > 0 and n % 3 == 1)
    c2 = sum(1 for n in historico if n > 0 and n % 3 == 2)
    c3 = sum(1 for n in historico if n > 0 and n % 3 == 0)

    par = sum(1 for n in historico if n > 0 and n % 2 == 0)
    impar = sum(1 for n in historico if n > 0 and n % 2 != 0)

    baixas = sum(1 for n in historico if 1 <= n <= 18)
    altas = sum(1 for n in historico if 19 <= n <= 36)

    return {
        "d1": d1, "d2": d2, "d3": d3,
        "c1": c1, "c2": c2, "c3": c3,
        "par": par, "impar": impar,
        "baixas": baixas, "altas": altas,
        "total": total
    }

def buscar_dados_roleta(roleta_nome):
    """
    Simulação/Fetch de dados da API.
    Em um cenário de produção real, conecta ao endpoint de dados da roleta.
    """
    # Gerador mock para garantia de funcionamento na ausência do backend ao vivo
    import random
    num_sorteado = random.choice(CILINDRO_EUROPEU)
    return num_sorteado

def enviar_telegram(token, chat_id, mensagem):
    """Envia alerta para o canal/grupo do Telegram informado."""
    if not token or not chat_id:
        return False, "Token ou Chat ID ausente."
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            return True, "Mensagem enviada com sucesso!"
        else:
            return False, f"Erro {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Falha na conexão: {e}"

# ==========================================
# PAINEL OPERACIONAL (SIDEBAR)
# ==========================================
st.sidebar.title("⚙️ Painel de Operação")

st.sidebar.subheader("🎯 Seleção de Roleta")
roleta_selecionada = st.sidebar.selectbox(
    "Escolha a Mesa:",
    options=list(ROLETA_CONFIG.keys()),
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Atualização de Dados")

col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:
    if st.button("📥 Capturar (1x)", use_container_width=True):
        novo_num = buscar_dados_roleta(roleta_selecionada)
        st.session_state.historico.insert(0, novo_num)
        st.sidebar.success(f"Adicionado: {novo_num}")

with col_btn2:
    if st.button("🎲 Gerar 80 Rodadas", use_container_width=True):
        import random
        st.session_state.historico = [random.choice(CILINDRO_EUROPEU) for _ in range(80)]
        st.sidebar.success("80 números carregados!")

if st.sidebar.button("🗑️ Limpar Histórico", use_container_width=True):
    st.session_state.historico = []
    st.sidebar.warning("Histórico limpo!")

st.sidebar.markdown("---")
st.sidebar.subheader("✈️ Configuração Telegram")
st.session_state.telegram_token = st.sidebar.text_input("Bot Token:", value=st.session_state.telegram_token, type="password")
st.session_state.telegram_chat_id = st.sidebar.text_input("Chat ID:", value=st.session_state.telegram_chat_id)

if st.sidebar.button("📲 Testar Alerta Telegram", use_container_width=True):
    ok, msg = enviar_telegram(
        st.session_state.telegram_token,
        st.session_state.telegram_chat_id,
        "🚨 <b>TESTE DE ALERTA ROULETTE ANALYTICS</b>\n\nConexão estabelecida com sucesso!"
    )
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

# ==========================================
# CORPO PRINCIPAL: CABEÇALHO & SINAIS
# ==========================================
st.title("🎰 Roulette Analytics & Signals System")
st.markdown(f"**Mesa Conectada:** `{roleta_selecionada}` | **Total Registrado:** `{len(st.session_state.historico)} rodadas`")

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
                    elif n in NUMEROS_VERMELHOS:
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

ultimas_80 = st.session_state.historico[:80]
qtd = len(ultimas_80)

if qtd >= 20:
    try:
        cont = pd.Series(ultimas_80).value_counts().reindex(range(37), fill_value=0)
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

        # HTML e CSS colapsados
        raw_html = f"""<style>body {{ background-color: transparent; color: white; margin: 0; font-family: Arial, sans-serif; }} .rt-wrapper {{ width: 100%; max-width: 950px; margin: 0 auto; background: #08080a; padding: 12px; border-radius: 80px; border: 2px solid #d4af37; box-sizing: border-box; }} .rt-outer {{ display: flex; flex-direction: column; width: 100%; }} .rt-row {{ display: flex; width: 100%; justify-content: center; }} .rt-spacer {{ width: 45px; flex-shrink: 0; }} .rt-cell {{ flex: 1; height: 46px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #fff; font-weight: bold; font-size: 12px; margin: 1px; border-radius: 3px; box-sizing: border-box; }} .rt-cell small {{ font-size: 8px; color: #bbb; font-weight: normal; }} .rt-middle {{ display: flex; height: 75px; width: 100%; margin: 1px 0; }} .rt-curva-esq, .rt-curva-dir {{ width: 45px; display: flex; flex-direction: column; flex-shrink: 0; }} .rt-center-area {{ flex: 1; display: flex; background: #050505; border: 1px solid #333; margin: 0 2px; border-radius: 4px; align-items: center; }} .rt-sector {{ display: flex; align-items: center; justify-content: center; color: #d4af37; font-weight: bold; font-size: 11px; letter-spacing: 1px; height: 100%; }} .sec-tier {{ flex: 3; border-right: 1px solid #333; }} .sec-orphelins {{ flex: 2.5; border-right: 1px solid #333; }} .sec-voisins {{ flex: 3.5; border-right: 1px solid #333; }} .sec-zero {{ flex: 2; border: 1px solid #555; border-radius: 30px; margin: 4px; background: #0d0d10; height: 80%; }}</style><div class="rt-wrapper"><div class="rt-outer"><div class="rt-row"><div class="rt-spacer"></div>{topo_html}<div class="rt-spacer"></div></div><div class="rt-middle"><div class="rt-curva-esq">{esq_0}{esq_1}{esq_2}</div><div class="rt-center-area"><div class="rt-sector sec-tier">TIER</div><div class="rt-sector sec-orphelins">ORPHELINS</div><div class="rt-sector sec-voisins">VOISINS</div><div class="rt-sector sec-zero">ZERO</div></div><div class="rt-curva-dir">{dir_0}{dir_1}{dir_2}</div></div><div class="rt-row"><div class="rt-spacer"></div>{base_html}<div class="rt-spacer"></div></div></div></div>"""

        components.html(raw_html, height=210)
        st.caption("Dica: As casas destacam dinamicamente conforme a frequência das últimas rodadas.")
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
