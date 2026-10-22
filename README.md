# Pontua+ · Case Analytics Engineer (Brain003)

Entrega do exercício sobre o lançamento do Pontos no Pix (27/05/2026). O enunciado original está no histórico: `git show a37451f:README.md`.

| Peça | Onde |
|---|---|
| Apresentação para a diretoria (8 slides) | [entrega/apresentacao/index.html](entrega/apresentacao/index.html) |
| Dashboard estático (só dados agregados) | [entrega/dashboard/index.html](entrega/dashboard/index.html) |
| Modelos dbt e testes | [pontua_dbt/](pontua_dbt/) |
| Perfil dos CSVs, exportação e gerador da apresentação | [analise/](analise/) |
| Registro de uso de IA | [AI_LOG.md](AI_LOG.md) |

## 1. Resumo e as três afirmações

- Os pontos líquidos resgatados passaram de **17,9M por mês (PRE, fev a abr/26) para 31,4M (POS, jun a set/26)**. O Pix responde por **9,2M** do POS (`mart_pre_pos_pix`).
- **Aéreas cumprem a meta de 50% em todos os 12 meses** (56,4% a 59,1% de jun a set/26). **Varejo estrito nunca chega a 20%** (10,9% a 17,0%, fora jan/26). **Varejo amplo ficou abaixo de 20% em jan, abr e jun a set/26** (`mart_metas_mensal`).
- Sem o Pix, o varejo amplo de jun a set ficaria em **17,3% a 19,0%**, ainda abaixo de 20%. Para chegar a 20% com o Pix faltam **2,6M a 3,1M de pontos de varejo por mês** (amplo) ou **3,0M a 3,6M** (estrito) (`mart_cenarios_meta`; cálculo aritmético).
- Recomendação: **não coibir o Pix e atacar o varejo**. Ela depende de dois dados que não temos: o preço que o banco paga por ponto e a definição contratual de varejo.

| Afirmação | Veredito | Evidência |
|---|---|---|
| CRM: "a comunicação de lançamento explica o sucesso do Pix" | **Não comprovada e não refutada** | 45,5% de quem recebeu a campanha resgatou Pix (1.683 de 3.699) contra 44,7% de quem não recebeu (489 de 1.094). Já havia 14 itens Pix em 27/05, um dia antes do único envio (28/05). `control_group` vazio: sem grupo de controle, causalidade não pode ser provada nem refutada (`mart_pix_adesao_campanha`, `mart_pix_diario`). |
| Operador: "o Pix sai a cerca de R$ 0,016 por ponto" | **Falsa como preço do Pix; o 0,016 é artefato do relatório (hipótese sobre a causa)** | O preço real é R$ 0,019 em todos os meses e status (mai a set/26). O relatório implica R$ 0,0154 a R$ 0,0166. Seus `pix_pontos` e `pix_transacoes` batem exatamente com os itens de **todos os status**, e o `pix_reais` fica perto só dos aprovados (`mart_pix_preco_mensal`). |
| Diretor: "nosso breakage está em 40%" | **Não sustentada pelos dados** | Nenhuma definição de expiração passa de 19,8% em set/26 (8,4% a 19,8%). As que passam de 40% (58,0% e 49,6%) contam saldo ainda válido. O ledger não tem nenhuma expiração de pontos regulares (`mart_breakage_mensal`). |

## 2. Como reconstruir tudo a partir dos CSVs

Os 9 CSVs estão em `dados/` (versão v1; o SHA-256 de cada um bate com `MANIFESTO_v1.csv`). Nada é editado à mão. Python 3.11, rodando sempre da raiz do repositório:

```bash
poetry install
env -u VIRTUAL_ENV poetry run dbt build --project-dir pontua_dbt --profiles-dir pontua_dbt
env -u VIRTUAL_ENV poetry run python analise/02_exportar_dashboard.py
python3 analise/03_gerar_apresentacao.py          # opcional: regenera o deck a partir dos JSONs
env -u VIRTUAL_ENV poetry run python analise/01_perfil.py   # opcional: perfil dos CSVs (saída em analise/01_perfil_saida.txt)
```

- O `env -u VIRTUAL_ENV` é necessário se o shell tiver `VIRTUAL_ENV` apontando para outro Python: sem ele o `poetry run` ignora o `.venv` do projeto e não acha o duckdb.
- O dbt lê os CSVs direto (`external_location: dados/{name}.csv`, sem seeds) e grava `pontua_dbt/pontua.duckdb`, que está no `.gitignore`.
- **Dashboard:** dê duplo clique em `entrega/dashboard/index.html`. Ele usa `dados/dados.js` (mesmos registros dos JSONs, gerado pelo passo 3). Para ler os JSONs por `fetch`: `python3 -m http.server` dentro de `entrega/dashboard` e abra `http://localhost:8000`.
- **Apresentação:** abra `entrega/apresentacao/index.html`. Setas, espaço ou clique avançam; `F` abre tela cheia; `?static` na URL desliga as animações.

## 3. O que entendi dos dados

Evidências: `analise/01_perfil.py` (consultas e resultados em `analise/01_perfil_saida.txt`).

| Arquivo | Uma linha é | Chave | Evidência |
|---|---|---|---|
| `orders` | um pedido | `order_id` (e `cart_id`, 1:1 com `carts`) | 19.785 linhas e 19.785 distintos. `user_id` está **100% vazio**: o usuário vem de `carts`. |
| `order_items` | um item de pedido | `order_item_id` | 19.803 distintos; 18 pedidos têm 2 itens; `quantity` é sempre 1. `paid_points` é nulo nos 520 itens COMPRA_PONTOS. |
| `carts` | um carrinho | `cart_id` | 19.785 distintos, 6.325 usuários, todos existentes em `cards`. |
| `points_ledger` | um movimento de saldo | `movement_id` | 146.739 distintos. Só ocorrem as operações 1, 2, 14, 100 e 103; as 3 (EXPIRACAO) e 13 (ESTORNO_CREDITO) existem em `dim_operation` mas têm zero movimentos. |
| `dim_operation` | um tipo de movimento | `operation_code` | 7 linhas. |
| `cards` | um cartão/conta | `account_id` | 16.168 contas para 12.000 usuários; cada usuário tem exatamente um `is_most_recent`, mas em 1.858 ele não é o de `created_at` mais novo. |
| `redeemed_points` | um movimento de pontos de um item | `(order_item_id, account_id, movement_type)` | 29.838 linhas únicas. `(item, tipo)` **não** é único: 1.471 itens têm o RESGATE dividido em 2 contas. |
| `crm_events` | um evento | não há chave natural | 348.250 linhas, nenhuma duplicada por inteiro. `user_id` nulo em 20.252 (5,8%, só push e in-app). `control_group` vazio em todas. |
| `relatorio_mensal_cliente` | um mês | `mes` | 9 linhas; `pix_*` vazio de jan a abr e `push_enviados` vazio de jan a mar. |

**Relacionamentos** (sem órfãos nem duplicatas): `order_items`→`orders`→`carts`→`cards`; `redeemed_points`→`order_items` e →`cards`; `points_ledger`→`cards` e →`dim_operation`. A conta de cada `redeemed_points` pertence ao mesmo usuário do carrinho em 29.838 de 29.838 linhas.

**Fusos e datas**
- Pedidos, itens, ledger e cartões usam `YYYY-MM-DD HH:MM:SS-03:00` (100% das linhas em -03:00). `valid_until` é só data.
- **`crm_events.event_ts` não tem fuso e está em UTC.** O `Order Approved` do CRM ocorre 3 horas depois do `orders.created_at` do mesmo usuário em 17.506 pares, e 17.494 de 17.494 eventos casam com um pedido quando `created_at` é lido em UTC. O `stg_crm_events` guarda `event_ts_utc` e `event_ts_brt`.
- Todos os meses e dias das análises são em horário de Brasília. Período: pedidos de 01/10/2025 a 30/09/2026; extração em 01/10/2026.
- 17.494 `Order Approved` contra 17.587 pedidos APROVADO: os pedidos sem par ficam nas bordas da janela do CRM (63 em 30/09, 27 em 01 e 02/10, 5 em 29/09).

**Estrutura do JSON `event_properties`** (sempre válido): `campaign_name` (igual ao `campaign_id` em 303.756 de 303.756), `platform` (android ou ios, só em push enviado), `link` (catalogo ou oferta, só em clique de e-mail), `reason` (hard_bounce, soft_bounce ou blocked, só em falha), `open_count` (1 ou 2, só em abertura de e-mail), `audience` (só em Facebook Audiences) e `source` (só em Order Approved).

## 4. Estrutura de dados para o dashboard e o agente

```
dados/*.csv ──> stg_* (9 views) ──> fct_resgates (1 tabela) ──> mart_* (9 tabelas) ──> JSON ──> dashboard e apresentação
```

| Camada | Modelo | Grão |
|---|---|---|
| staging | `stg_orders`, `stg_order_items`, `stg_carts`, `stg_points_ledger`, `stg_dim_operation`, `stg_cards`, `stg_redeemed_points`, `stg_crm_events`, `stg_relatorio_mensal_cliente` | 1 por CSV, só tipagem e renomeação (mesmo grão do arquivo) |
| fato | `fct_resgates` | 1 linha por item de pedido resgatado (17.823) |
| mart | `mart_metas_mensal` | mês |
| mart | `mart_mix_absoluto_mensal` | mês × tipo de resgate |
| mart | `mart_pre_pos_pix` | tipo de resgate × período (PRE, POS) |
| mart | `mart_cenarios_meta` | mês (jun a set/26) × cenário (REAL, SEM_PIX) |
| mart | `mart_pix_preco_mensal` | mês |
| mart | `mart_pix_diario` | dia (BRT) |
| mart | `mart_pix_adesao_campanha` | grupo (recebeu, não recebeu) |
| mart | `mart_breakage_mensal` | mês |
| mart | `mart_pix_usuarios` | usuário que resgatou Pix (**nível de usuário**; fica fora do dashboard) |

- **Nomes:** prefixos `stg_`, `fct_`, `mart_`; `pontos_*` em pontos; `pct_*` em fração de 0 a 1; `*_brt` em horário de Brasília; `atende_*` e `flag_*` booleanos; `relatorio_*` vêm do relatório do operador e `dif_*` é relatório menos o nosso cálculo; `bk_*` são definições candidatas de breakage (sufixo `_acum` = acumulado).
- **Descrições como fonte de significado:** os 19 modelos e as 188 colunas têm descrição em português em [schema.yml](pontua_dbt/models/staging/schema.yml) e [marts/schema.yml](pontua_dbt/models/marts/schema.yml). Cada uma diz o grão, o significado e as ressalvas (por exemplo "sem grupo de controle" ou "cálculo aritmético"). O `dbt build` as grava em `pontua_dbt/target/manifest.json`, que o agente pode ler para descobrir o que cada campo significa.
- **Por que o agente deve consultar só os marts:** o staging preserva as armadilhas da origem (`orders.user_id` vazio, CRM em UTC, `supplier_name` renomeado em 10/09, itens de todos os status e COMPRA_PONTOS misturados). Quem soma `paid_points` direto do staging erra o líquido e as metas. Os marts já trazem as decisões da seção 5, estão testados contra o ledger e carregam as ressalvas na descrição. `mart_pix_usuarios` também deve ficar fora do agente, pela mesma razão pela qual o exportador do dashboard o bloqueia: é nível de usuário.
- **Dashboard e apresentação:** leem os mesmos 8 JSONs agregados em `entrega/dashboard/dados/` (gerados por `analise/02_exportar_dashboard.py`, que aborta se um mart tiver coluna `user_id`, `device_id`, `account_id`, `order_id` ou `order_item_id`). Os números dos slides saem desses JSONs, com `assert`s em `analise/03_gerar_apresentacao.py`.

## 5. Decisões de modelagem e metodologia

- **Resgate líquido.** `pontos_liquidos = paid_points - refunded_points` para itens APROVADO e **0 para itens ESTORNADO**. Com isso o total (**320.027.439**) fecha com o ledger: −(operação 2 + operação 14). `fct_resgates` traz também `pontos_brutos`, `pontos_estornados` e `flag_estornado`.
- **COMPRA_PONTOS fica fora:** não é resgate (520 itens, `paid_points` nulo, sem `redeemed_points`). Itens CANCELADO, INVALIDO e AGUARDANDO_CONFIRMACAO também ficam fora: não têm `redeemed_points`.
- **Classificação por `supplier_responsible`, não por `supplier_name`**, que foi renomeado em 10/09 (`Casa&Cia (via MegaMagazine)`, 139 itens). `tipo_resgate`: PASSAGEM = AEREO; PRODUTO = VAREJO_PRODUTO; TRANSFERENCIA com `Pix Pontua+` = PIX; as demais TRANSFERENCIA (Nuvem Recompensas e Pontos Max) = TRANSFERENCIA_PARCEIRO.
- **Duas definições de varejo.** Estrita: só VAREJO_PRODUTO. Ampla: VAREJO_PRODUTO + TRANSFERENCIA_PARCEIRO, que é como o operador classifica (`category_macro` = Varejo). O contrato não diz qual vale; os dois resultados aparecem sempre lado a lado.
- **Mês e dia** vêm de `order_items.created_at` em horário de Brasília (e não de `status_updated_at`).
- **Janela PRE/POS:** PRE = média mensal de fev a abr/26 (3 meses); POS = jun a set/26 (4 meses). Ficam fora **jan/26** (outlier: 96,8% de aéreas, 88.478.482 pontos) e **mai/26** (mês do lançamento). A comparação é descritiva e não atribui causa.
- **SEM_PIX é aritmética:** tira os pontos Pix do total do mês e mantém o resto igual. Não assume que o cliente trocaria por outro tipo de resgate nem que o volume se manteria. Pontos de varejo a somar: `(0,2 × total − varejo) / 0,8`, com piso em zero.
- **Breakage:** não há definição nos dados nem no enunciado. `mart_breakage_mensal` traz seis candidatas lado a lado, mensais e acumuladas, sem eleger uma.

## 6. Confirmado nos dados × hipótese

**Confirmado nos dados**
- Chaves e grãos da seção 3; ausência de órfãos; SHA-256 e contagens iguais ao manifesto.
- CRM em UTC (17.506 pares a +3h; 17.494 de 17.494 casam).
- O ledger fecha com `redeemed_points` e `order_items`: operação 2 = −323.423.650 em 17.823 itens; operação 14 = 3.396.211 = 3.141.827 (220 itens ESTORNADO) + 254.384 (103 estornos parciais). Conferência por consulta no perfil e nos testes (`assert_breakage_fecha_com_ledger_e_fct`, `assert_reconciliacao_resgates_ledger`).
- Pix a R$ 0,019 por ponto em todos os itens (3.292, qualquer status).
- No relatório, `pix_pontos` = pontos de todos os status e `pix_transacoes` = itens de todos os status em todos os 5 meses.
- Metas, pré e pós, cenários, adesão e breakage da seção 1 (todos em `mart_*`).
- O pico de jan/26 está na origem: o relatório (97%) bate com os dados (96,8%).
- `control_group` vazio em 348.250 de 348.250 eventos.
- O ledger não tem operação 3 nem 13; a menor validade de crédito regular é 25/09/2027, depois da extração. As únicas expirações são as de migração (operação 103: 20.449 movimentos, 64.090.805 pontos).
- E-mails e push do relatório de ago e set/26 são **1,35×** os do CRM; nos outros meses a razão fica entre 0,98 e 1,00 (`analise/01_perfil_saida.txt`; não existe mart para isso).

**Hipóteses (não provadas)**
- O R$ 0,016 vem de dividir os reais dos itens aprovados pelos pontos de todos os status. Hipótese alternativa: o operador fala do custo efetivo ao programa e não do preço ao cliente; os dados não permitem testar.
- A adoção do Pix teria acontecido sem a campanha. Os dados só mostram que ela começou antes do envio; não há controle.
- Em ago e set o CRM perdeu eventos, ou o relatório está inflado. Não dá para saber qual dos dois.
- Os 8.708 movimentos do ledger anteriores ao `created_at` da conta vêm da migração ou de contas recriadas.
- `Casa&Cia (via MegaMagazine)` é o mesmo varejista com outra intermediação, e por isso é tratado como o mesmo fornecedor.
- A causa do pico de jan/26 (1.977 itens aéreos no mês contra 329 a 932 nos outros 11 meses).

## 7. Perguntas ao negócio e aos donos dos sistemas

1. **Preço que o banco paga por ponto**, por tipo de resgate. Sem ele não há margem do programa nem custo de aéreas, varejo e Pix.
2. **Definição contratual de varejo:** estrita ou ampla (transferências a parceiros contam)? Decide se o varejo cumpre a meta.
3. **Causa do pico de jan/26** (88,5M de pontos e 96,8% de aéreas): campanha, migração, erro de carga?
4. **Regra de expiração:** por que não há expiração regular no ledger? Qual a validade dos pontos regulares e da migração? Os créditos migrados têm validade registrada em 2028, mas as expirações de migração ocorrem em 2026.
5. **Origem do R$ 0,016:** como o operador calcula? De onde vêm os reais do relatório?
6. **E-mails e push em ago e set/26:** por que o relatório é 1,35× o CRM? O CRM perdeu eventos (por exemplo, os envios de push de ago estão todos em um único dia, 06/08)?
7. **`control_group` vazio:** a campanha teve grupo de controle? Existe a base de quem foi elegível e não recebeu?
8. **Ledger anterior à criação do cartão:** 8.708 movimentos são anteriores ao `created_at` da conta. Isso é a migração?
9. **Saldos migrados:** 6.551 créditos (324.024.198 pontos) e 20.449 expirações; qual a regra que gerou essas baixas?
10. **`orders.user_id` vazio:** é intencional? O usuário só é recuperável via `carts`.

## 8. Testes

`dbt build`: **129 de 129 passam** (19 modelos e 110 testes).

| Grupo | Qtde | O que garante |
|---|---|---|
| `unique` e `not_null` | 15 e 60 | Chaves únicas e preenchidas nas 9 views, na fato e nos marts. |
| `relationships` | 7 | `order_items`→`orders`, `orders`→`carts`, `redeemed_points`→`order_items` e →`cards`, `ledger`→`cards` e →`dim_operation`, `fct_resgates`→`orders`. |
| `accepted_values` | 15 | Domínios de status, `product_type`, `category_macro`, `tipo_resgate`, `movement_type`, `event_name`, cenário, período e grupo. |
| singulares | 13 | Regras de negócio e fechamentos, abaixo. |

Singulares:
- **Reconciliação com o ledger:** soma de `pontos_liquidos` de `fct_resgates` = −(soma de `points` das operações 2 e 14) = **320.027.439** (valor fixo no teste). `assert_breakage_fecha_com_ledger_e_fct` confere o saldo final com a soma do ledger e os resgatados líquidos com a fato.
- **Pix:** itens PIX a R$ 0,019 por ponto (tolerância 0,0005) e preço mensal dos aprovados entre 0,0185 e 0,0195.
- **`pontos_liquidos >= 0`** e grão de `redeemed_points` único.
- **Marts:** percentuais somam 1 por mês; total de pontos dos meses = 320.027.439; mix e marts Pix fecham com `fct_resgates`; períodos PRE (3 meses) e POS (4 meses); cenários consistentes (REAL = `mart_metas_mensal`, SEM_PIX = REAL menos Pix, pontos a somar levam o varejo a 20%); adesão fecha com o universo.

O que os testes **não** garantem: eles mostram consistência entre os arquivos e com o ledger, não que o resultado de negócio esteja certo (por exemplo, a classificação de varejo ou a definição de breakage).

## 9. Limitações e o que falta

- **O agente (item opcional) NÃO foi feito.**
- Próximo passo para o agente: um ponto de entrada que leia só os 8 marts agregados (por `target/manifest.json`), responda com a descrição do campo, o grão e as ressalvas, leia `GEMINI_API_KEY` de variável de ambiente e **recuse ou responda com ressalva** perguntas que os dados não sustentam (causalidade do CRM, o breakage de 40%, qualquer pergunta sobre usuário individual).
- Não há mart para a divergência de e-mails e push entre CRM e relatório; o 1,35× vem do perfil.
- Sem preço pago pelo banco, a recomendação não mede margem; a comparação pré e pós é descritiva.
- A apresentação foi conferida em Chrome headless no modo `?static`; as animações não foram assistidas até o fim.
- Fora do escopo deste README: abrir o PR de `entrega` para `main`, conforme o enunciado.

## 10. Tempo

Início às 15h15; entrega até 17h00 (cerca de 1h45 de trabalho). O prazo adotado foi 17h (2h a partir do convite, por entendimento do candidato). O enunciado cita 4h de trabalho. **Não houve esclarecimento formal com o recrutador**, então o prazo de 17h não foi confirmado.

## 11. Uso de IA

Ferramenta: Claude Code no VS Code (Opus 5.5 no início e Sonnet 5.5 depois). Nenhum subagente nem skill foi usado. O registro completo, por sessão, está em [AI_LOG.md](AI_LOG.md).

O que foi pedido, em ordem: perfil dos 9 CSVs; modelagem dbt (staging e `fct_resgates`); marts de análise e de cenários; exportação dos JSONs; dashboard; apresentação; este README.

O que foi conferido e corrigido:
- O Claude detectou, antes de modelar, que **a fórmula de pontos líquidos pedida não zerava os itens ESTORNADO** e que a reconciliação com o ledger falharia por **3.141.827** (323.169.266 contra 320.027.439). O candidato escolheu zerar os ESTORNADO e manteve o teste em 320.027.439 sem alterá-lo.
- O Claude apontou **números errados no pedido da apresentação**: a média mensal é 17,9M e 31,4M (e não 17,6M e 30,5M), e o varejo amplo também ficou abaixo de 20% em jan e abr (e não só a partir de jun). Valeram os números dos marts.
- Erros do próprio Claude, corrigidos na sessão: `poetry run` usava o Python errado por causa de `VIRTUAL_ENV`; o perfil por coluna contava vazio como valor distinto; o gerador da apresentação cortou o cabeçalho no comentário do modelo e deixou a página em branco.
- Regras mantidas ao longo do trabalho: não alterar dados nem testes para fazê-los passar, e reportar a causa quando um teste falha.
