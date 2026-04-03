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
        ["Múltiplas (geral)", "Escanteios"],
        index=0
    )
    if st.button("Atualizar dados", use_container_width=True):
        with st.spinner("Buscando jogos"):
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
    st.caption("")

with col_jogos:
    st.subheader("📋 Jogos do Dia")
    partidas = carregar_partidas_do_json()
    if not partidas:
        st.warning("Nenhum jogo encontrado. Clique em 'Atualizar dados' primeiro.")
    else:
        for p in partidas:
            with st.expander(f"{p['home_team']} x {p['away_team']} - {p.get('league', {}).get('name', '')}"):
                st.write(f"**Horário:** {p.get('event_date', '')}")
                st.write(f"**Odds 1X2:** {p.get('odds_home')} / {p.get('odds_draw')} / {p.get('odds_away')}")
                st.write(f"**Over 2.5:** {p.get('odds_over_25')} | **BTTS Sim:** {p.get('odds_btts_yes')}")
                if p.get("prediction"):
                    pred = p["prediction"]
                    st.write(f"**Previsão ML:** H {pred.get('prob_home_win',0):.1f}% | D {pred.get('prob_draw',0):.1f}% | A {pred.get('prob_away_win',0):.1f}%")
                    st.write(f"**Placar mais provável:** {pred.get('most_likely_score', 'N/A')}")

with col_bilhetes:
    st.subheader("🤖 Gerar Bilhetes")
    if st.button("Executar Análise", use_container_width=True):
        if not partidas:
            st.error("Não há jogos para analisar. Atualize os dados.")
        else:
            contexto = formatar_contexto_partidas(partidas)
            prompt_file = "prompt_multiplas.txt" if modo == "Múltiplas (geral)" else "prompt_escanteios.txt"
            system_prompt = carregar_prompt(prompt_file)
            with st.spinner("Analisando os Jogos"):
                resposta = gerar_bilhetes(system_prompt, contexto)
            st.success("Análise concluída!")
            st.markdown("### 📝 Sugestões de Bilhetes")
            st.markdown(resposta)