import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ========= CONFIGURAÇÃO APENAS DEEPSEEK =========
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY não encontrada no .env")
if not DEEPSEEK_BASE_URL:
    raise ValueError("DEEPSEEK_BASE_URL não encontrada no .env")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
print("✅ Usando DeepSeek API")

# ========= FUNÇÕES DE CARREGAMENTO DE DADOS =========
def obter_data_hoje_brasilia():
    tz_brasilia = timezone(timedelta(hours=-3))
    agora_brasilia = datetime.now(tz_brasilia)
    return agora_brasilia.date()

def carregar_partidas_do_json():
    try:
        with open("jogos_bzzoiro.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        print("❌ Arquivo jogos_bzzoiro.json não encontrado. Execute jogos.py primeiro.")
        return []

    todas_partidas = dados.get("jogos", [])
    hoje = obter_data_hoje_brasilia()
    partidas_hoje = []

    for p in todas_partidas:
        event_date_str = p.get("event_date")
        if not event_date_str:
            continue
        try:
            dt_evento = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
            dt_evento_brasilia = dt_evento.astimezone(timezone(timedelta(hours=-3)))
            data_evento = dt_evento_brasilia.date()
        except Exception as e:
            print(f"Erro ao converter data {event_date_str}: {e}")
            continue

        if data_evento == hoje:
            pred = p.get("prediction")
            if pred and isinstance(pred, dict):
                event_pred = pred.get("event", {})
                if event_pred.get("id") != p.get("id"):
                    p["prediction"] = None
                    print(f"⚠️ Previsão removida para {p['home_team']} x {p['away_team']} (IDs não coincidem)")
            partidas_hoje.append(p)

    return partidas_hoje

def formatar_contexto_partidas(partidas):
    if not partidas:
        return "Nenhuma partida disponível para hoje."

    texto = "📅 PARTIDAS DE HOJE (dados da Bzzoiro API com odds e previsões ML):\n\n"
    for p in partidas:
        liga = p.get("league", {}).get("name", "Liga não informada")
        casa = p.get("home_team", "Time A")
        fora = p.get("away_team", "Time B")
        data_str = p.get("event_date", "")
        try:
            dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
            dt_br = dt.astimezone(timezone(timedelta(hours=-3)))
            horario = dt_br.strftime("%d/%m %H:%M")
        except:
            horario = data_str

        odds = f"1: {p.get('odds_home', '?')} | X: {p.get('odds_draw', '?')} | 2: {p.get('odds_away', '?')}"
        over_25 = p.get("odds_over_25", "?")
        btts_yes = p.get("odds_btts_yes", "?")

        texto += f"🏆 {liga}\n"
        texto += f"🕒 {horario} (horário de Brasília)\n"
        texto += f"{casa} x {fora}\n"
        texto += f"💰 Odds 1X2: {odds}\n"
        texto += f"⚽ Over 2.5: {over_25} | BTTS Sim: {btts_yes}\n"

        pred = p.get("prediction")
        if pred and isinstance(pred, dict):
            prob_h = pred.get("prob_home_win", 0)
            prob_d = pred.get("prob_draw", 0)
            prob_a = pred.get("prob_away_win", 0)
            texto += f"🤖 Previsão ML: H {prob_h:.1f}% | D {prob_d:.1f}% | A {prob_a:.1f}%\n"
            if pred.get("most_likely_score"):
                texto += f"🎯 Placar mais provável: {pred['most_likely_score']}\n"

        texto += "-" * 40 + "\n"

    return texto

def carregar_prompt(nome_arquivo):
    caminho = os.path.join(os.path.dirname(__file__), nome_arquivo)
    if not os.path.exists(caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("Você é um assistente de apostas esportivas.")
        return "Você é um assistente de apostas esportivas."
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def gerar_bilhetes(system_prompt, contexto_partidas):
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
            model="deepseek-chat",      # modelo da DeepSeek
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Erro na DeepSeek API: {e}"