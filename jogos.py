import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

BZZOIRO_TOKEN = os.getenv("BZZOIRO_API_KEY")
BASE_URL = "https://sports.bzzoiro.com/api"

HEADERS = {
    "Authorization": f"Token {BZZOIRO_TOKEN}",
    "Content-Type": "application/json"
}

def buscar_partidas_hoje():
    """Busca partidas de futebol do dia atual (inclui odds e previsões)"""
    hoje = datetime.now().strftime("%Y-%m-%d")
    amanha = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"{BASE_URL}/events/"
    params = {
        "date_from": hoje,
        "date_to": amanha,
        "status": "notstarted",
        "tz": "America/Sao_Paulo"
    }
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"Erro {resp.status_code}: {resp.text}")
            return []
        
        dados = resp.json()
        partidas = dados.get("results", [])
        
        # Buscar previsão para cada partida
        for p in partidas:
            pred = buscar_previsao(p["id"])
            if pred:
                p["prediction"] = pred
        
        return partidas
    except Exception as e:
        print(f"Falha na requisicao: {e}")
        return []

def buscar_previsao(event_id):
    """Busca a previsao ML para um evento especifico"""
    url = f"{BASE_URL}/predictions/"
    params = {"event": event_id}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 200:
            dados = resp.json()
            results = dados.get("results", [])
            if results:
                return results[0]
    except:
        pass
    return None

def salvar_jogos():
    partidas = buscar_partidas_hoje()
    if not partidas:
        print("Nenhuma partida encontrada para hoje.")
        return
    
    dados_saida = {
        "data_coleta": datetime.now().isoformat(),
        "total_jogos": len(partidas),
        "jogos": partidas
    }
    
    with open("jogos_bzzoiro.json", "w", encoding="utf-8") as f:
        json.dump(dados_saida, f, ensure_ascii=False, indent=2)
    
    # Print sem emoji para evitar erro de encoding no Windows
    print(f"[OK] {len(partidas)} partidas salvas em jogos_bzzoiro.json")

if __name__ == "__main__":
    salvar_jogos()