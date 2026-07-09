import time
import requests
import json
from pathlib import Path


CODIGO_SERIE = {
    "SELIC": 11,
    "IPCA": 433,
    "META_SELIC": 432
}

DATA_INICIAL = '01/01/2016'
DATA_FINAL = '01/01/2026'

BRONZE_DIR = Path("proj_selic/data/bronze")
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

def buscar_dados(codigo_serie, data_inicial, data_final):
    codigo = CODIGO_SERIE[codigo_serie]
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
    
    resposta = requests.get(url, timeout=60)
    
    if resposta.status_code != 200:
        return print(f"Erro ao buscar dados para {codigo_serie} status_code: {resposta.status_code}")
    
    dados = resposta.json()
    
    caminho =  BRONZE_DIR / f"{codigo_serie.lower()}.json"
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
           
    print(f"Salvo: {caminho} ({len(dados)} registros)")
    return dados

for nome_serie in CODIGO_SERIE:
    buscar_dados(nome_serie, DATA_INICIAL, DATA_FINAL)
    time.sleep(1)
