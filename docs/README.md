# Projeto Selic — Juro real e poder de compra
## -- Em construção --
**Investir atrelado à Selic preservou o poder de compra do consumidor brasileiro nos últimos 10 anos? E em quais períodos isso falhou?**

Análise de 10 anos de dados do Banco Central (Selic e IPCA) pra responder se quem investiu no ativo "livre de risco" do Brasil realmente ficou protegido da inflação, ou se houve janelas em que o dinheiro perdeu valor mesmo rendendo.

---

## Por que essa pergunta

A resposta óbvia — "Selic sempre bate a inflação, é o ativo mais seguro do país" — não é verdade o tempo todo. Em alguns períodos (Selic emergencial baixa + IPCA acelerando), quem deixou o dinheiro parado perdeu poder de compra mesmo vendo o saldo crescer. Esse projeto identifica *quando* isso aconteceu e *por quanto*, em vez de assumir a resposta.

## O que o projeto responde

- Quanto R$ 1.000 investidos há 10 anos valem hoje, em termos nominais vs. reais (ajustados pela inflação)
- Em quantos meses/anos o rendimento real foi negativo
- Quais eventos econômicos explicam esses períodos (ex: Selic emergencial 2020-21, choque inflacionário 2021-22)
- Qual foi o rendimento real acumulado no período todo



## Fonte de dados

API SGS do Banco Central do Brasil ([dadosabertos.bcb.gov.br](https://dadosabertos.bcb.gov.br)):

| Série | Código SGS | Frequência |
|---|---|---|
| Selic meta (definida pelo Copom) | 432 | Diária (dia útil) |
| Selic efetiva (over) | 11 | Diária (dia útil) |
| IPCA (variação mensal) | 433 | Mensal |

Janela: 01/01/2016 até hoje (janela fixa, não móvel — ver decisão abaixo).

## Decisões técnicas (e por quê)

Essa seção existe porque a decisão importa mais que a implementação.

- **Janela fixa, não móvel.** Se a janela fosse sempre "últimos 10 anos a partir de hoje", o dataset mudaria a cada execução e os números do README ficariam desatualizados sozinhos. Com data inicial fixa (2016-01-01), o projeto é reproduzível: quem rodar hoje ou daqui 1 ano parte da mesma base histórica, só com dados novos no final.
- **Forward-fill na Selic, não interpolação.** A Selic só é publicada em dia útil e o valor não muda até a próxima decisão do Copom — então o valor do dia anterior é o valor correto pro fim de semana, não uma média ou interpolação.
- **Fisher exato, não subtração simples.** Juro real = `((1 + selic) / (1 + inflação)) - 1`, não `selic - inflação`. A aproximação por subtração distorce quando as duas taxas estão em dois dígitos — e isso aconteceu em boa parte da janela analisada (Selic passou de 14% em 2016).
- **Índice acumulado em vez de taxa isolada.** Selic e IPCA em % ao mês/ano não respondem "quanto meu dinheiro valeria hoje". Por isso o projeto constrói dois índices (base 100 na data inicial) — um simulando o valor investido, outro simulando o custo de vida — e divide um pelo outro. Essa razão é o gráfico central do projeto.
- **CSV, não Parquet.** Com ~2.600 linhas (10 anos diário), Parquet não traz ganho de performance — traria só overhead. CSV tem a vantagem de renderizar direto no GitHub, então o dado fica visível sem precisar abrir nada.

## Arquitetura

```
## Arquitetura

![Arquitetura do pipeline: bronze, silver e gold](docs/images/arquitetura.png)

- `extract.py`: busca as 3 séries na API, salva o JSON bruto (auditoria/reprodutibilidade)
- `clean.py`: tipagem, deduplicação, validação (bronze → silver)
- ...
```

- `extract.py`: busca as três séries na API, salva o JSON bruto (auditoria/reprodutibilidade)
- `transform.py`: parsing, forward-fill, cálculo de índices acumulados, juro real, marcação de eventos
- `data/processed/fact_diario.csv`: data, selic_meta, selic_efetiva, ipca_acum_12m, selic_indice_acumulado, ipca_indice_acumulado, indice_real_acumulado, poder_compra_negativo
- `data/processed/fact_ipca_mensal.csv`: ano_mes, ipca_mensal
- Power BI consome os CSVs diretamente — sem transformação em Power Query, já chegam tratados

O pipeline roda automaticamente via GitHub Actions (agendado), então o dado no repositório se mantém atualizado sem intervenção manual.

## Stack

Python (pandas) · API SGS/BCB · GitHub Actions · Power BI

## Como rodar localmente

```bash
git clone https://github.com/devverissimo/projeto-selic.git
cd projeto-selic
pip install -r requirements.txt
python src/pipeline.py
```

Isso gera os CSVs em `data/processed/`. Abra `powerbi/projeto_selic.pbix` e clique em atualizar pra carregar os dados mais recentes.

## Estrutura do repositório

```
projeto_selic/
├── data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── extract.py
│   ├── transform.py
│   └── pipeline.py
├── powerbi/
│   └── projeto_selic.pbix
├── requirements.txt
└── README.md
```

## Limitações

- IPCA é média nacional — não captura variação de consumo por região ou faixa de renda
- Simulação assume reinvestimento diário na Selic efetiva, sem custos de transação, come-cotas ou IR
- Não considera outros ativos (CDI, poupança, ações) — o escopo é especificamente Selic vs. IPCA

## Próximos passos

- [ ] Comparar com poupança e CDI no mesmo período
- [ ] Adicionar testes de qualidade de dados (gaps, valores fora de faixa)

---

Projeto de **Maria Veríssimo** — [LinkedIn](https://linkedin.com/in/mariaverissimo-dev/) · [GitHub](https://github.com/devverissimo)
