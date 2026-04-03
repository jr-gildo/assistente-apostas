import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st  

# Tenta carregar .env local (ignora se não existir)
load_dotenv()

# Prioriza st.secrets (nuvem) e depois os.getenv (local)
openai_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
if not openai_key:
    openai_key = os.getenv("OPENAI_API_KEY")

bzzoiro_key = st.secrets.get("BZZOIRO_API_KEY") if hasattr(st, "secrets") else None
if not bzzoiro_key:
    bzzoiro_key = os.getenv("BZZOIRO_API_KEY")

client = OpenAI(api_key=openai_key)

os.environ["OPENAI_API_KEY"] = openai_key
os.environ["BZZOIRO_API_KEY"] = bzzoiro_key

def carregar_partidas_do_json():
    """Carrega os jogos do arquivo gerado pelo jogos.py"""
    try:
        with open("jogos_bzzoiro.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados.get("jogos", [])
    except FileNotFoundError:
        return []

def formatar_contexto_partidas(partidas):
    """Formata as partidas para enviar ao GPT"""
    if not partidas:
        return "Nenhuma partida disponível para hoje."
    texto = "PARTIDAS DE HOJE (dados da Bzzoiro API com odds e previsões ML):\n\n"
    for p in partidas:
        liga = p.get("league", {}).get("name", "Liga não informada")
        casa = p.get("home_team", "Time A")
        fora = p.get("away_team", "Time B")
        data_str = p.get("event_date", "")
        try:
            dt = datetime.fromisoformat(data_str)
            horario = dt.strftime("%d/%m/%Y %H:%M")
        except:
            horario = data_str
        odds = f"1: {p.get('odds_home', '?')} | X: {p.get('odds_draw', '?')} | 2: {p.get('odds_away', '?')}"
        over_25 = p.get("odds_over_25", "?")
        btts_yes = p.get("odds_btts_yes", "?")
        texto += f"Liga: {liga}\nHorario: {horario}\n{casa} x {fora}\nOdds 1X2: {odds}\nOver 2.5: {over_25} | BTTS Sim: {btts_yes}\n"
        pred = p.get("prediction")
        if pred:
            prob_h = pred.get("prob_home_win", 0)
            prob_d = pred.get("prob_draw", 0)
            prob_a = pred.get("prob_away_win", 0)
            texto += f"Previsao ML: H {prob_h:.1f}% | D {prob_d:.1f}% | A {prob_a:.1f}%\n"
            if pred.get("most_likely_score"):
                texto += f"Placar mais provavel: {pred['most_likely_score']}\n"
        texto += "-" * 40 + "\n"
    return texto

def carregar_prompt(nome_arquivo):
    caminho = os.path.join(os.path.dirname(__file__), nome_arquivo)
    if not os.path.exists(caminho):
        return "Você é um assistente de apostas esportivas."
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def gerar_bilhetes(system_prompt, contexto_partidas):
    """Chama a OpenAI e retorna a resposta em texto"""
    user_message = f"""
Abaixo estão as partidas de futebol que acontecem HOJE (dados reais da API Bzzoiro).

{contexto_partidas}

Com base SOMENTE nesses dados, execute sua função: monte os bilhetes conforme as regras descritas no seu prompt (banca R$5, bilhete principal + conservador/moderado/ousado). 
Se houver previsões ML, utilize-as como referência adicional.
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro na OpenAI: {e}"