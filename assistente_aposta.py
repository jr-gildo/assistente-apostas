import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========= FUNÇÕES DE CARREGAMENTO DE DADOS =========
def obter_data_hoje_brasilia():
    """Retorna a data atual no horário de Brasília (UTC-3) sem horário"""
    tz_brasilia = timezone(timedelta(hours=-3))
    agora_brasilia = datetime.now(tz_brasilia)
    return agora_brasilia.date()

def carregar_partidas_do_json():
    """Carrega e filtra apenas partidas de hoje (horário Brasília)"""
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
        # Extrai a data do evento (campo event_date)
        event_date_str = p.get("event_date")
        if not event_date_str:
            continue
        # Converte para datetime (suporta formato ISO com timezone)
        try:
            # Remove o fuso horário e converte para datetime sem timezone
            dt_evento = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
            # Converte para horário de Brasília
            dt_evento_brasilia = dt_evento.astimezone(timezone(timedelta(hours=-3)))
            data_evento = dt_evento_brasilia.date()
        except Exception as e:
            print(f"Erro ao converter data {event_date_str}: {e}")
            continue

        if data_evento == hoje:
            # Validação da prediction: se existir, verificar se o event.id é igual ao id da partida
            pred = p.get("prediction")
            if pred and isinstance(pred, dict):
                event_pred = pred.get("event", {})
                if event_pred.get("id") != p.get("id"):
                    # Remove prediction incorreta
                    p["prediction"] = None
                    print(f"⚠️ Previsão removida para {p['home_team']} x {p['away_team']} (IDs não coincidem)")
            partidas_hoje.append(p)

    return partidas_hoje

def formatar_contexto_partidas(partidas):
    """Converte a lista de partidas (com odds e previsões) em texto para o GPT"""
    if not partidas:
        return "Nenhuma partida disponível para hoje."

    texto = "📅 PARTIDAS DE HOJE (dados da Bzzoiro API com odds e previsões ML):\n\n"
    for p in partidas:
        liga = p.get("league", {}).get("name", "Liga não informada")
        casa = p.get("home_team", "Time A")
        fora = p.get("away_team", "Time B")
        data_str = p.get("event_date", "")
        # Formata horário local (Brasília)
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

        # Previsão ML (se disponível e válida)
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

# ========= FUNÇÕES DOS PROMPTS E OPENAI =========
def carregar_prompt(nome_arquivo):
    caminho = os.path.join(os.path.dirname(__file__), nome_arquivo)
    if not os.path.exists(caminho):
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("Você é um assistente de apostas esportivas.")
        return "Você é um assistente de apostas esportivas."
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def executar_prompt(system_prompt, nome_modo, contexto_partidas):
    print(f"\n🔄 Executando modo {nome_modo} com dados reais...\n")

    user_message = f"""
Abaixo estão as partidas de futebol que acontecem HOJE (dados reais da API Bzzoiro).

{contexto_partidas}

Com base SOMENTE nesses dados, execute sua função: monte os bilhetes conforme as regras descritas no seu prompt (banca R$5, bilhete principal + conservador/moderado/ousado). 
Se houver previsões ML, utilize-as como referência adicional. 
Não diga que faltam dados – trabalhe com o que foi fornecido e complemente com seu conhecimento geral, se necessário.
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
        reply = response.choices[0].message.content
        print(f"\n✅ RESPOSTA DO ASSISTENTE ({nome_modo}):\n")
        print(reply)
        print("\n" + "=" * 60)
    except Exception as e:
        print(f"❌ Erro na OpenAI: {e}")

# ========= MENU PRINCIPAL =========
def menu():
    while True:
        print("\n⚽ ASSISTENTE DE APOSTAS COM DADOS BZZOIRO\n")
        print("1 - Modo Múltiplas (geral: gols, resultados, ambas marcam)")
        print("2 - Modo Escanteios (foco exclusivo em cantos)")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()
        if opcao == "0":
            print("Encerrando...")
            break
        elif opcao in ("1", "2"):
            partidas = carregar_partidas_do_json()
            if not partidas:
                input("Nenhuma partida de hoje encontrada. Pressione Enter para continuar...")
                continue

            contexto = formatar_contexto_partidas(partidas)
            print("\n📋 DADOS OBTIDOS:\n")
            print(contexto)

            if opcao == "1":
                prompt_texto = carregar_prompt("prompt_multiplas.txt")
                executar_prompt(prompt_texto, "Múltiplas", contexto)
            else:
                prompt_texto = carregar_prompt("prompt_escanteios.txt")
                executar_prompt(prompt_texto, "Escanteios", contexto)

            input("\nPressione Enter para voltar ao menu...")
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    menu()