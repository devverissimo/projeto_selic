from pathlib import Path
import json
import pandas as pd

BRONZE_DIR = Path("proj_selic/data/bronze")
SILVER_DIR = Path("proj_selic/data/silver")
SILVER_DIR.mkdir(parents=True, exist_ok=True)

def ler_json(nome_serie):
    caminho = BRONZE_DIR / f"{nome_serie.lower()}.json"
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados


def limpar_dados(nome_serie):
    df = pd.DataFrame(ler_json(nome_serie))
    
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    
    linhas_antes = len(df)
    df = df.drop_duplicates(subset=['data'], keep='first')
    if len(df) < linhas_antes:
        print(f"Removidos {linhas_antes - len(df)} registros duplicados para a série {nome_serie}.")
        
    assert set(df.columns) == {'data', 'valor'}, f"Colunas inesperadas na série {nome_serie}: {df.columns.tolist()}"
    assert df['valor'].isnull().sum() == 0, f"Existem valores nulos na coluna 'valor' da série {nome_serie}."
    
    df = df.sort_values(by='data').reset_index(drop=True)
    return df

def salvar_silver(df, nome_serie):
    caminho = SILVER_DIR / f"{nome_serie.lower()}.csv"
    df.to_csv(caminho, index=False)
    print(f"Série {nome_serie} salva em {caminho}.")
    
for serie in ["SELIC", "IPCA", "META_SELIC"]:
    df_limpo = limpar_dados(serie)
    salvar_silver(df_limpo, serie)

