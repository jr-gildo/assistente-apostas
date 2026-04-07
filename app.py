import streamlit as st
import subprocess
from backend import carregar_partidas_do_json, formatar_contexto_partidas, carregar_prompt, gerar_bilhetes

st.set_page_config(page_title="Assistente de Apostas", layout="wide")

st.markdown("<h1 style='text-align: center;'>⚽ Assistente de Apostas Esportivas</h1>", unsafe_allow_html=True)
st.markdown("---")

# ========= TRÊS COLUNAS: CONFIGURAÇÃO | JOGOS | BILHETES =========
col_config, col_jogos, col_bilhetes = st.columns([0.5, 2, 2])

with col_config:
    st.markdown("#### MODO")
    modo = st.radio(
        "",
        ["Geral", "Escanteios"],
        index=0
    )
    if st.button("Atualizar dados", use_container_width=True):
        with st.spinner("Buscando jogos..."):
            result = subprocess.run(
                ["python", "jogos.py"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode == 0:
                st.success("Dados atualizados com sucesso!")
            else:
                err_msg = result.stderr.encode('ascii', 'ignore').decode()
                st.error(f"Erro: {err_msg[:200]}")
    st.caption("Desenvolvido por Gildo Júnior")

with col_jogos:
    st.subheader("📋 Jogos do Dia")
    partidas = carregar_partidas_do_json()
    if not partidas:
        st.warning("Nenhum jogo encontrado. Clique em 'Atualizar dados' primeiro.")
    else:
        # Inicializa lista de seleção no session_state
        if "selecionados" not in st.session_state:
            st.session_state.selecionados = [False] * len(partidas)
        
        # Botões para selecionar/desmarcar todos
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            if st.button("✅ Selecionar todos"):
                for i in range(len(partidas)):
                    st.session_state.selecionados[i] = True
                st.rerun()
        with col_sel2:
            if st.button("❌ Desmarcar todos"):
                for i in range(len(partidas)):
                    st.session_state.selecionados[i] = False
                st.rerun()
        
        st.markdown("---")
        
        for i, p in enumerate(partidas):
            with st.container():
                col_check, col_expander = st.columns([0.1, 0.9])
                with col_check:
                    st.session_state.selecionados[i] = st.checkbox(
                        "", key=f"chk_{i}", value=st.session_state.selecionados[i]
                    )
                with col_expander:
                    with st.expander(f"{p['home_team']} x {p['away_team']} - {p.get('league', {}).get('name', '')}"):
                        st.write(f"**Horário:** {p.get('event_date', '')}")
                        st.write(f"**Odds 1X2:** {p.get('odds_home')} / {p.get('odds_draw')} / {p.get('odds_away')}")
                        st.write(f"**Over 2.5:** {p.get('odds_over_25')} | **BTTS Sim:** {p.get('odds_btts_yes')}")
                        if p.get("prediction"):
                            pred = p["prediction"]
                            st.write(f"**Previsão ML:** H {pred.get('prob_home_win',0):.1f}% | D {pred.get('prob_draw',0):.1f}% | A {pred.get('prob_away_win',0):.1f}%")
                            st.write(f"**Placar mais provável:** {pred.get('most_likely_score', 'N/A')}")
        
        # Exibe quantos jogos foram selecionados
        selecionados_count = sum(st.session_state.selecionados)
        st.caption(f"✅ {selecionados_count} jogo(s) selecionado(s)")

with col_bilhetes:
    st.subheader("🤖 Gerar Bilhetes")
    if st.button("Executar Análise", use_container_width=True):
        if not partidas:
            st.error("Não há jogos para analisar. Atualize os dados primeiro.")
        else:
            # Filtra as partidas selecionadas
            partidas_selecionadas = [p for i, p in enumerate(partidas) if st.session_state.selecionados[i]]
            if not partidas_selecionadas:
                st.warning("⚠️ Selecione pelo menos um jogo para analisar.")
            else:
                contexto = formatar_contexto_partidas(partidas_selecionadas)
                prompt_file = "prompt_multiplas.txt" if modo == "Geral" else "prompt_escanteios.txt"
                system_prompt = carregar_prompt(prompt_file)
                with st.spinner("Analisando Jogos ..."):
                    resposta = gerar_bilhetes(system_prompt, contexto)
                st.success("Análise concluída!")
                st.markdown("### 📝 Sugestões de Bilhetes")
                st.markdown(resposta)

# Rodapé
st.markdown("---")
st.markdown(
    "<p style='text-align: center; font-size: 0.8rem; color: #888;'>Assistente de Apostas v1.1 - Selecione os jogos desejados</p>",
    unsafe_allow_html=True
)