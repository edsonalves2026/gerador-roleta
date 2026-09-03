# ==========================================
# PROCESSAMENTO DE NOVO NÚMERO
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

            # CORREÇÃO DE INDENTAÇÃO AQUI
            if st.session_state.sinal_ativo:
                if "Fusão" in modo_gale_opcao and tier_do_padrao == "👑 Elite (Top 3)":
                    # 1. Pega apenas alvos inéditos do novo sinal
                    alvos_novos_brutos = [n for n in res_ultimo["alvos"] if n not in st.session_state.alvos_sinal]
                    
                    # 2. Se houver gatilho BRK, prioriza apenas as dezenas ausentes/Tiro Certo
                    if res_ultimo.get("dados_brk", {}).get("sinal_ativo"):
                        prioridades = res_ultimo["dados_brk"].get("prioridade_maxima", [])
                        alvos_novos_filtrados = [n for n in alvos_novos_brutos if n in prioridades]
                        if not alvos_novos_filtrados:
                            alvos_novos_filtrados = alvos_novos_brutos[:2]
                    else:
                        alvos_novos_filtrados = alvos_novos_brutos[:3]

                    # 3. Trava Rígida: Limita o TOTAL ABSOLUTO a no máximo 8 dezenas
                    limite_maximo_alvos = 8
                    vagas_disponiveis = limite_maximo_alvos - len(st.session_state.alvos_sinal)
                    
                    if vagas_disponiveis > 0 and alvos_novos_filtrados:
                        alvos_para_adicionar = alvos_novos_filtrados[:vagas_disponiveis]
                        st.session_state.alvos_sinal.extend(alvos_para_adicionar)
                        
                        enviar_mensagem_telegram(
                            f"🔄 *FUSÃO AFUNILADA (GALE)*\n"
                            f"🎰 Roleta: `{roleta_selecionada}`\n"
                            f"Dezenas adicionadas: `{alvos_para_adicionar}`\n"
                            f"🎯 Alvos Totais (Máx {limite_maximo_alvos}): `{st.session_state.alvos_sinal}`"
                        )

# Execução do Modo de Operação
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

# Visualização Principal
st.subheader("Esteira Temporal (Janela de 14 Rodadas)")
if st.session_state.historico:
    esteira = st.session_state.historico[:14]
    cols = st.columns(min(len(esteira), 14))
    for i, num in enumerate(esteira):
        with cols[i]:
            st.metric(label=f"Pos {i+1:02d}", value=num)
else:
    st.info("Aguardando captura do primeiro sorteio na mesa...")

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
            alvos_limpos = [int(x) for x in res_tiro_certo["alvos_headshot"]]
            sugestao += f": {alvos_limpos}"
        elif res_tiro_certo["alvos_tiro_certo"]:
            alvos_limpos = [int(x) for x in res_tiro_certo["alvos_tiro_certo"]]
            sugestao += f": {alvos_limpos}"

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
    
    df_exibicao = pd.DataFrame(dados_tabela)
    df_exibicao.index = range(1, len(df_exibicao) + 1)
    st.dataframe(df_exibicao, use_container_width=True)

    # Ranking dos Tiers
    tiers_atuais, df_rank = obter_tiers_cache()
    with st.expander("🏆 Ranking dos Padrões (Assertividade ≥ 50% - Últimas 200 Rodadas)", expanded=False):
        if not df_rank.empty:
            df_rank_exib = df_rank.copy()
            df_rank_exib.index = range(1, len(df_rank_exib) + 1)
            st.dataframe(df_rank_exib, use_container_width=True)
        else:
            st.info("Nenhum padrão com no mínimo 50% de acerto foi consolidado ainda.")

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
                roleta_nome=roleta_selecionada,
                posicao_rank=posicao_rank,
                taxa_acerto=taxa_acerto
            )
            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

# ==========================================
# 9. ESTATÍSTICAS E PAINEL VISUAL
# ==========================================
if st.session_state.historico:
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

# Loop de Recarregamento para Modo On-line
if modo_operacao == "On-line (Captura Automática)":
    time.sleep(5)
    st.rerun()
