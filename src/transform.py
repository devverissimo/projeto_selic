from pathlib import Path
import pandas as pd

SILVER_DIR = Path("proj_selic/data/silver")
GOLD_DIR = Path("proj_selic/data/gold")
GOLD_DIR.mkdir(parents=True, exist_ok=True)


def ler_csv(nome_serie):
    caminho = SILVER_DIR / f"{nome_serie.lower()}.csv"
    df = pd.read_csv(caminho, parse_dates=['data'])
    return df


def preencher_dias_faltantes(df, colunas):
    """Preenche os dias faltantes com forward-fill (último valor conhecido)."""
    df = df.set_index('data')
    data_completa = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(data_completa)
    for coluna in colunas:
        df[coluna] = df[coluna].ffill()
    df.index.name = 'data'
    return df.reset_index()


def calcular_indice(df, coluna_valor, nome_indice):
    """Índice acumulado base 100, compondo a coluna_valor (em %) dia a dia ou mês a mês."""
    df[nome_indice] = 100 * (1 + df[coluna_valor] / 100).cumprod()
    return df


def ipca_acumulado_12m(df):
    """IPCA acumulado em janela móvel de 12 meses. Primeiros 11 meses saem NaN."""
    df['ipca_acum_12m'] = (
        (1 + df['valor'] / 100).rolling(12).apply(lambda x: x.prod(), raw=True) - 1
    ) * 100
    return df


def juntar_series(selic, ipca, meta_selic):
    df = selic.merge(ipca, on='data', how='inner', suffixes=('_selic', '_ipca'))
    df = df.merge(
        meta_selic.rename(columns={'valor': 'selic_meta'}),
        on='data', how='left'
    )
    return df


def calcular_indice_real(df):
    df['indice_real'] = df['selic_indice'] / df['ipca_indice'] * 100
    return df


def calcular_juro_real(df):
    """Fisher exato: ((1 + selic_diaria) / (1 + ipca_12m)) - 1"""
    df['juro_real'] = ((1 + df['valor_selic'] / 100) / (1 + df['ipca_acum_12m'] / 100)) - 1
    return df


def marcar_poder_compra_negativo(df):
    df['poder_compra_negativo'] = df['indice_real'] < 100
    return df


def montar_fact_diario():
    # Selic: já é diária, só precisa do índice acumulado
    selic = ler_csv("selic")
    selic = preencher_dias_faltantes(selic, ['valor'])
    selic = calcular_indice(selic, 'valor', 'selic_indice')

    # IPCA: compõe no grão MENSAL primeiro, só depois vira diário
    ipca = ler_csv("ipca")
    ipca = ipca_acumulado_12m(ipca)
    ipca = calcular_indice(ipca, 'valor', 'ipca_indice')
    ipca = preencher_dias_faltantes(ipca, ['valor', 'ipca_acum_12m', 'ipca_indice'])

    # Meta Selic: só pra comparação visual, forward-fill simples
    meta_selic = ler_csv("meta_selic")
    meta_selic = preencher_dias_faltantes(meta_selic, ['valor'])

    df = juntar_series(selic, ipca, meta_selic)
    df = calcular_indice_real(df)
    df = calcular_juro_real(df)
    df = marcar_poder_compra_negativo(df)

    return df


def montar_fact_ipca_mensal():
    ipca = ler_csv("ipca")
    df = ipca[['data', 'valor']].copy()
    df['ano_mes'] = df['data'].dt.to_period('M').astype(str)
    df = df.rename(columns={'valor': 'ipca_mensal'})
    return df[['ano_mes', 'ipca_mensal']]

# testando a função montar_fact_diario() e montar_fact_ipca_mensal()
if __name__ == "__main__":
    fact_diario = montar_fact_diario()
    fact_diario.to_csv(GOLD_DIR / "fact_diario.csv", index=False, sep=';', decimal=',')
    print(f"Salvo: fact_diario.csv ({len(fact_diario)} registros)")

    fact_ipca_mensal = montar_fact_ipca_mensal()
    fact_ipca_mensal.to_csv(GOLD_DIR / "fact_ipca_mensal.csv", index=False, sep=';', decimal=',')
    print(f"Salvo: fact_ipca_mensal.csv ({len(fact_ipca_mensal)} registros)")

    print("\nAmostra fact_diario:")
    print(fact_diario[['data', 'valor_selic', 'ipca_acum_12m', 'indice_real', 'juro_real', 'poder_compra_negativo']].head())
    print("\nAmostra fact_ipca_mensal:")
    print(fact_ipca_mensal.head())
    
periodo_2021 = fact_diario[(fact_diario['data'] >= '2021-01-01') & (fact_diario['data'] <= '2021-12-31')]
print(periodo_2021[['data', 'juro_real', 'poder_compra_negativo']].describe())


print(periodo_2021[['data', 'indice_real']].iloc[[0, -1]])
print(fact_diario[['data', 'indice_real']].describe())