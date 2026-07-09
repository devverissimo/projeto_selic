# Documento de Arquitetura de Alto Nível (HLA) — Projeto Selic

## 1. Objetivo e pergunta de negócio

Determinar se investir atrelado à Selic preservou o poder de compra do consumidor brasileiro nos últimos 10 anos, e identificar em quais períodos isso falhou.

O sistema extrai, trata e disponibiliza séries históricas do Banco Central (Selic e IPCA) para responder essa pergunta através de um dashboard analítico, com um pipeline de dados reprodutível e auditável como suporte.

## 2. Escopo

### 2.1 Requisitos Funcionais (RF)

| ID | Requisito |
|---|---|
| RF01 | Extrair as séries 432 (Selic meta), 11 (Selic efetiva) e 433 (IPCA) via API SGS/BCB |
| RF02 | Persistir o dado bruto extraído sem nenhuma alteração (camada bronze) |
| RF03 | Padronizar tipos (data, valor) e consolidar em formato tabular limpo (camada silver) |
| RF04 | Calcular métricas derivadas: IPCA acumulado 12m, índices acumulados (base 100), juro real, índice de poder de compra (camada gold) |
| RF05 | Simular rendimento de valor investido na Selic vs. perda de poder de compra pela inflação |
| RF06 | Identificar e sinalizar períodos de poder de compra negativo |
| RF07 | Disponibilizar dado da camada gold para consumo direto no Power BI |
| RF08 | Executar o pipeline de forma automatizada e recorrente, sem intervenção manual |

### 2.2 Requisitos Não-Funcionais (RNF)

| ID | Requisito | Como é atendido |
|---|---|---|
| RNF01 | Disponibilidade | Retry com backoff exponencial em falhas transitórias da API (ex: HTTP 502) |
| RNF02 | Auditabilidade | Camada bronze é imutável; nunca sobrescrita, apenas re-extraída |
| RNF03 | Idempotência | Reexecutar o pipeline não duplica nem corrompe dado já existente |
| RNF04 | Qualidade de dado | Validações automáticas entre camadas (ver seção 6) |
| RNF05 | Manutenibilidade | Código modular por camada (extract/clean/transform), testável isoladamente |
| RNF06 | Portabilidade | Pipeline roda igual localmente e em CI (GitHub Actions), sem mudança de código |

### 2.3 Fora de escopo

- Dados de renda/salário individual (exigiria fonte adicional, ex: PNAD)
- Segmentação regional de inflação (IPCA usado é média nacional)
- Simulação com custos de transação, come-cotas ou Imposto de Renda
- Comparação com outros ativos (CDI, poupança, ações)

## 3. Arquitetura

Arquitetura em camadas (padrão medalhão), com três estágios de refinamento de dado entre a fonte e o consumo:

```
API SGS/BCB (séries 432, 11, 433)
        │
        ▼
  BRONZE (data/bronze/)
  JSON bruto, exatamente como a API devolveu — imutável
        │
        ▼
  SILVER (data/silver/)
  Tipado, validado, sem duplicata — uma tabela por série,
  ainda sem métrica de negócio calculada
        │
        ▼
  GOLD (data/gold/)
  Métricas de negócio: índices acumulados, juro real,
  sinalização de poder de compra — pronto para consumo
        │
        ▼
     Power BI
  Modelo relacional + relatório
```

Cada seta representa uma transformação com validação própria (seção 6) — dado só avança de camada se passar no portão de qualidade correspondente.

## 4. Modelo de dados por camada

### 4.1 Bronze

Um arquivo JSON por série, estrutura idêntica à resposta da API (`[{data: string, valor: string|number}, ...]`):

- `data/bronze/selic.json`
- `data/bronze/meta_selic.json`
- `data/bronze/ipca.json`

### 4.2 Silver

Um CSV por série, tipos padronizados:

| Arquivo | Colunas | Tipos |
|---|---|---|
| `selic.csv` | `data`, `valor` | `date`, `float` |
| `meta_selic.csv` | `data`, `valor` | `date`, `float` |
| `ipca.csv` | `data`, `valor` | `date`, `float` |

### 4.3 Gold

| Arquivo | Colunas | Descrição |
|---|---|---|
| `fact_diario.csv` | `data`, `selic_meta`, `selic_efetiva`, `ipca_acum_12m`, `selic_indice_acumulado`, `ipca_indice_acumulado`, `indice_real_acumulado`, `juro_real_diario`, `poder_compra_negativo` | Grão diário, base para a simulação de investimento |
| `fact_ipca_mensal.csv` | `ano_mes`, `ipca_mensal` | Grão mensal, base para gráficos de sazonalidade |

## 5. Fluxo de execução

| Script | Entrada | Saída | Responsabilidade |
|---|---|---|---|
| `extract.py` | API SGS/BCB | `data/bronze/*.json` | Requisição HTTP com retry, persistência do dado bruto |
| `clean.py` | `data/bronze/*.json` | `data/silver/*.csv` | Parsing de tipos, deduplicação, validação de schema |
| `transform.py` | `data/silver/*.csv` | `data/gold/*.csv` | Forward-fill, cálculo de índices, juro real, sinalização |
| `pipeline.py` | — | — | Orquestra os três scripts em sequência |

Execução automatizada via **GitHub Actions** (cron agendado), commitando os CSVs atualizados no repositório. Power BI consome os arquivos da camada gold e é atualizado manualmente (`Refresh` no Power Query) após cada execução do pipeline.

## 6. Decisões arquiteturais

| Decisão | Alternativa considerada | Motivo da escolha |
|---|---|---|
| Janela fixa (2016-01-01 até hoje) | Janela móvel (hoje − 10 anos) | Reprodutibilidade — dataset não muda de tamanho a cada execução, README permanece consistente |
| Forward-fill na Selic | Interpolação linear | Selic não muda entre decisões do Copom; o valor do dia útil anterior é o valor correto, não uma média |
| Fisher exato para juro real | Subtração simples (selic − ipca) | Taxas de dois dígitos (Selic chegou a 14%+ em 2016) tornam a aproximação por subtração imprecisa |
| CSV na camada gold | Parquet | Volume pequeno (~2.600 linhas), CSV renderiza direto no GitHub, sem ganho real de Parquet nesse tamanho |
| Três camadas (bronze/silver/gold) | Duas camadas (raw/processed) | Separa "consertar tipo de dado" (silver) de "calcular métrica de negócio" (gold) — permite validar e testar cada etapa isoladamente |

## 7. Riscos e limitações

- **Limite de 10 anos por requisição** — a API do BCB retorna erro se o intervalo entre `dataInicial` e `dataFinal` ultrapassar 10 anos; qualquer extensão futura da janela exige fatiar em múltiplas requisições
- **Instabilidade da API** — falhas HTTP 502 observadas durante o desenvolvimento; mitigado com retry, mas não elimina o risco de indisponibilidade prolongada
- **IPCA é média nacional** — não captura variação de consumo por região ou faixa de renda
- **Dependência de execução manual do refresh no Power BI** — a automação cobre o pipeline de dados, não a atualização do relatório

## 8. Estratégia de qualidade de dados

Validações executadas entre camadas antes de promover o dado adiante:

| Transição | Validação |
|---|---|
| Bronze → Silver | Schema esperado presente (`data`, `valor`); conversão de tipo bem-sucedida (sem `NaN` inesperado); sem data duplicada |
| Silver → Gold | Sem gap de data não explicado após forward-fill; valores dentro de faixa plausível (Selic entre 0% e 30% a.a.; IPCA mensal entre -5% e 5%); datas das três séries com sobreposição de período coerente |

Falha em qualquer validação interrompe o pipeline (`raise`, não *fail silently*) — condição alinhada ao RNF04.