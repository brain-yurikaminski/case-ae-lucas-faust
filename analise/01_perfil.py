"""Perfil dos 9 CSVs em dados/ com DuckDB.

Somente leitura: não altera nada em dados/. Cada bloco imprime a consulta e o
resultado, para servir de evidência no README.

Uso:
    poetry run python analise/01_perfil.py | tee analise/01_perfil_saida.txt

Convenções:
- Os arquivos com fuso explícito (-03:00) são lidos como TIMESTAMPTZ e a sessão
  usa America/Sao_Paulo, então strftime/::date devolvem horário de Brasília.
- crm_events.event_ts não tem fuso; a seção 3 mostra a evidência de que está em UTC.
"""

import hashlib
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
TABELAS = [
    "orders",
    "order_items",
    "carts",
    "points_ledger",
    "dim_operation",
    "cards",
    "redeemed_points",
    "crm_events",
    "relatorio_mensal_cliente",
]
CATEGORICAS = {
    "orders": ["status"],
    "order_items": ["status", "product_type", "category_macro", "supplier_name", "supplier_responsible", "quantity"],
    "carts": ["channel"],
    "points_ledger": ["operation_code"],
    "cards": ["card_class", "card_flag", "is_most_recent"],
    "redeemed_points": ["movement_type"],
    "crm_events": ["event_name", "campaign_type", "control_group"],
}
# Marcador que nunca aparece nos dados: assim campo vazio no CSV vira '' na leitura "crua".
NULO_CRU = "__NULO__"

con = duckdb.connect()
con.execute("set timezone = 'America/Sao_Paulo'")


def secao(titulo):
    print(f"\n{'=' * 100}\n{titulo}\n{'=' * 100}")


def q(titulo, sql, limite=60):
    """Executa a consulta e imprime SQL + resultado em tabela simples."""
    print(f"\n--- {titulo}")
    print("SQL: " + " ".join(sql.split()))
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    linhas = cur.fetchall()
    larg = [len(c) for c in cols]
    fmt = [[("" if v is None else str(v)) for v in linha] for linha in linhas[:limite]]
    for linha in fmt:
        larg = [max(a, len(v)) for a, v in zip(larg, linha)]
    print(" | ".join(c.ljust(w) for c, w in zip(cols, larg)))
    print("-+-".join("-" * w for w in larg))
    for linha in fmt:
        print(" | ".join(v.ljust(w) for v, w in zip(linha, larg)))
    if len(linhas) > limite:
        print(f"... ({len(linhas) - limite} linhas omitidas)")
    return linhas


# ---------------------------------------------------------------------------
# 0. Carga e integridade contra o manifesto
# ---------------------------------------------------------------------------
secao("0. CARGA E CONFERÊNCIA COM MANIFESTO_v1.csv")

for t in TABELAS:
    arq = (DADOS / f"{t}.csv").as_posix()
    con.execute(f"create view {t} as select * from read_csv('{arq}')")
    con.execute(f"create view raw_{t} as select * from read_csv('{arq}', all_varchar = true, nullstr = '{NULO_CRU}')")

manifesto = con.execute(f"select arquivo, linhas, sha256 from read_csv('{(RAIZ / 'MANIFESTO_v1.csv').as_posix()}')").fetchall()
print("arquivo | linhas_manifesto | linhas_lidas | sha256_confere")
for arquivo, linhas, sha in manifesto:
    t = arquivo.removesuffix(".csv")
    lidas = con.execute(f"select count(*) from {t}").fetchall()[0][0]
    sha_ok = hashlib.sha256((DADOS / arquivo).read_bytes()).hexdigest() == sha
    print(f"{arquivo} | {linhas} | {lidas} | {sha_ok}")

# ---------------------------------------------------------------------------
# 1. Perfil por coluna: tipo, nulos, vazios
# ---------------------------------------------------------------------------
secao("1. PERFIL POR COLUNA (tipo inferido, % nulos, % vazios, distintos)")

for t in TABELAS:
    tipos = con.execute(f"describe {t}").fetchall()
    partes = []
    for nome, tipo, *_ in tipos:
        partes.append(f"""
            select '{nome}' coluna, '{tipo}' tipo_inferido,
                   count(*) linhas,
                   round(100.0 * count(*) filter (where "{nome}" = '') / count(*), 2) pct_vazio_lido_como_nulo,
                   round(100.0 * count(*) filter (where "{nome}" <> '' and trim("{nome}") = '') / count(*), 2) pct_so_espacos,
                   round(100.0 * count(*) filter (where trim("{nome}") in ('null', 'NULL', 'None', 'NaN', 'nan')) / count(*), 2) pct_texto_nulo,
                   count(distinct nullif("{nome}", '')) distintos_nao_vazios
            from raw_{t}""")
    q(f"{t}: colunas", " union all ".join(partes) + " order by 1", limite=20)

# ---------------------------------------------------------------------------
# 2. Grão e chaves candidatas
# ---------------------------------------------------------------------------
secao("2. GRÃO E CHAVES CANDIDATAS (teste de unicidade)")

q("orders: order_id e cart_id únicos?", "select count(*) linhas, count(distinct order_id) d_order_id, count(distinct cart_id) d_cart_id from orders")
q("order_items: order_item_id único? itens por pedido", "select count(*) linhas, count(distinct order_item_id) d_order_item_id, count(distinct order_id) d_order_id from order_items")
q("order_items: distribuição de itens por pedido", "select n_itens, count(*) pedidos from (select order_id, count(*) n_itens from order_items group by 1) group by 1 order by 1")
q("carts: cart_id único?", "select count(*) linhas, count(distinct cart_id) d_cart_id, count(distinct user_id) d_user_id from carts")
q("points_ledger: movement_id único?", "select count(*) linhas, count(distinct movement_id) d_movement_id, count(distinct user_id) d_user, count(distinct account_id) d_account from points_ledger")
q("dim_operation: operation_code único?", "select count(*) linhas, count(distinct operation_code) d_code from dim_operation")
q("cards: account_id único? cartões por usuário", "select count(*) linhas, count(distinct account_id) d_account_id, count(distinct user_id) d_user_id from cards")
q("redeemed_points: quais combinações são únicas?", """
    select count(*) linhas,
           count(distinct order_item_id) d_item,
           count(distinct (order_item_id, movement_type)) d_item_tipo,
           count(distinct (order_item_id, account_id, movement_type)) d_item_conta_tipo,
           count(distinct (order_item_id, account_id, movement_type, points)) d_linha_inteira
    from redeemed_points""")
q("redeemed_points: padrões de movimentos por item", """
    select movimentos, count(*) itens from (
        select order_item_id, string_agg(movement_type, '+' order by movement_type) movimentos
        from redeemed_points group by 1) group by 1 order by 2 desc""")
q("redeemed_points: exemplo de item com 2 RESGATE (contas diferentes)", """
    select order_item_id, account_id, movement_type, points from redeemed_points
    where order_item_id = (select order_item_id from redeemed_points where movement_type = 'RESGATE'
                           group by 1 having count(*) > 1 order by 1 limit 1)
    order by movement_type, account_id""")
q("crm_events: há linhas 100% duplicadas? (não há chave natural)", """
    select count(*) linhas, count(distinct (event_ts, user_id, device_id, event_name, campaign_type, campaign_id, event_properties)) d_linha_inteira
    from crm_events""")
q("crm_events: device_id x user_id", """
    select count(distinct device_id) d_device, count(distinct user_id) d_user,
           (select count(*) from (select user_id from crm_events where user_id is not null group by 1 having count(distinct device_id) > 1)) users_com_mais_de_1_device,
           (select count(*) from (select device_id from crm_events where user_id is not null group by 1 having count(distinct user_id) > 1)) devices_com_mais_de_1_user
    from crm_events""")
q("relatorio_mensal_cliente: mes único?", "select count(*) linhas, count(distinct mes) d_mes from relatorio_mensal_cliente")

# ---------------------------------------------------------------------------
# 3. Categóricas
# ---------------------------------------------------------------------------
secao("3. VALORES DISTINTOS DAS CATEGÓRICAS")

for t, cols in CATEGORICAS.items():
    for c in cols:
        q(f"{t}.{c}", f"select {c}, count(*) n from {t} group by 1 order by 2 desc")

q("dim_operation completa", "select * from dim_operation order by 1")
q("order_items: product_type x category_macro x fornecedor", """
    select product_type, category_macro, supplier_name, supplier_responsible, count(*) itens,
           count(paid_points) com_paid_points, min(created_at)::date primeiro, max(created_at)::date ultimo
    from order_items group by all order by 1, 2, 3""")
q("orders.status x order_items.status (divergências)", """
    select o.status status_pedido, i.status status_item, count(*) itens
    from orders o join order_items i using (order_id) group by all order by 3 desc""")

# ---------------------------------------------------------------------------
# 4. Datas, formatos e fusos
# ---------------------------------------------------------------------------
secao("4. FORMATOS DE DATA/HORA, FUSOS E INTERVALOS")

COLS_DATA = [
    ("orders", "created_at"), ("orders", "status_updated_at"),
    ("order_items", "created_at"), ("points_ledger", "movement_at"),
    ("points_ledger", "valid_until"), ("cards", "created_at"),
    ("crm_events", "event_ts"), ("relatorio_mensal_cliente", "mes"),
]
for t, c in COLS_DATA:
    q(f"{t}.{c}: padrão do texto bruto (9=dígito)", f"""
        select regexp_replace(regexp_replace({c}, '[0-9]', '9', 'g'), '[A-Za-z]', 'a', 'g') padrao,
               count(*) n, min({c}) minimo, max({c}) maximo
        from raw_{t} group by 1 order by 2 desc""")

q("offsets de fuso distintos nos arquivos com fuso", """
    select 'orders.created_at' col, right(created_at, 6) fuso, count(*) from raw_orders group by 2
    union all select 'orders.status_updated_at', right(status_updated_at, 6), count(*) from raw_orders group by 2
    union all select 'order_items.created_at', right(created_at, 6), count(*) from raw_order_items group by 2
    union all select 'points_ledger.movement_at', right(movement_at, 6), count(*) from raw_points_ledger group by 2
    union all select 'cards.created_at', right(created_at, 6), count(*) from raw_cards group by 2""")

q("orders.created_at = order_items.created_at?", "select count(*) itens, count(*) filter (where o.created_at = i.created_at) iguais from orders o join order_items i using (order_id)")
q("orders: status_updated_at < created_at?", "select count(*) from orders where status_updated_at < created_at")

# Fuso do CRM: 'Order Approved' é um evento de pedido; comparamos com orders.created_at (BRT).
q("CRM: diferença em horas entre 'Order Approved' e orders.created_at (BRT, sem fuso) do mesmo usuário", """
    with o as (select c.user_id, o.created_at at time zone 'America/Sao_Paulo' ts_brt_ingenuo
               from orders o join carts c using (cart_id) where o.status = 'APROVADO'),
         e as (select user_id, event_ts from crm_events where event_name = 'Order Approved')
    select round(epoch(e.event_ts - o.ts_brt_ingenuo) / 3600)::int dif_horas, count(*) pares
    from e join o using (user_id)
    where abs(epoch(e.event_ts - o.ts_brt_ingenuo)) < 6 * 3600
    group by 1 order by 2 desc limit 6""")
q("CRM: cada 'Order Approved' tem pedido do mesmo usuário com created_at em UTC até 10 min antes?", """
    select count(*) order_approved,
           count(*) filter (where exists (
               select 1 from orders o join carts c using (cart_id)
               where c.user_id = e.user_id
                 and e.event_ts between o.created_at at time zone 'UTC'
                                    and (o.created_at at time zone 'UTC') + interval 10 minute)) casam_em_utc
    from crm_events e where event_name = 'Order Approved'""")
q("CRM vs pedidos: 'Order Approved' vs pedidos APROVADO", """
    select (select count(*) from crm_events where event_name = 'Order Approved') crm_order_approved,
           (select count(*) from orders where status = 'APROVADO') orders_aprovado,
           (select count(*) from order_items where status = 'APROVADO') itens_aprovado""")

q("Pedidos APROVADO sem 'Order Approved' no CRM (mesmo usuário, até 10 min depois em UTC), por dia", """
    with o as (select o.order_id, c.user_id, o.created_at
               from orders o join carts c using (cart_id) where o.status = 'APROVADO')
    select o.created_at::date dia_brt, count(*) pedidos_sem_evento
    from o where not exists (
        select 1 from crm_events e
        where e.event_name = 'Order Approved' and e.user_id = o.user_id
          and e.event_ts between o.created_at at time zone 'UTC' and (o.created_at at time zone 'UTC') + interval 10 minute)
    group by 1 order by 2 desc limit 10""")
q("Intervalo de datas por arquivo (BRT; CRM convertido de UTC)", """
    select 'orders.created_at' col, min(created_at)::date ini, max(created_at)::date fim from orders
    union all select 'orders.status_updated_at', min(status_updated_at)::date, max(status_updated_at)::date from orders
    union all select 'order_items.created_at', min(created_at)::date, max(created_at)::date from order_items
    union all select 'points_ledger.movement_at', min(movement_at)::date, max(movement_at)::date from points_ledger
    union all select 'points_ledger.valid_until', min(valid_until), max(valid_until) from points_ledger
    union all select 'cards.created_at', min(created_at)::date, max(created_at)::date from cards
    union all select 'crm_events.event_ts (UTC->BRT)', min(event_ts - interval 3 hour)::date, max(event_ts - interval 3 hour)::date from crm_events
    union all select 'relatorio.mes', strptime(min(mes), '%Y-%m')::date, strptime(max(mes), '%Y-%m')::date from relatorio_mensal_cliente""")
q("CRM: dias sem nenhum evento entre o primeiro e o último dia", """
    with d as (select range::date dia from range(date '2025-10-03', date '2026-09-30', interval 1 day))
    select count(*) dias_sem_evento from d
    where dia not in (select (event_ts - interval 3 hour)::date from crm_events)""")

# ---------------------------------------------------------------------------
# 5. Relacionamentos
# ---------------------------------------------------------------------------
secao("5. RELACIONAMENTOS (órfãos e cardinalidade)")

q("order_items -> orders", "select count(*) itens, count(o.order_id) com_pedido from order_items i left join orders o using (order_id)")
q("orders -> order_items (pedido sem item)", "select count(*) pedidos, count(*) filter (where order_id not in (select order_id from order_items)) sem_item from orders")
q("orders -> carts (1:1?)", "select count(*) pedidos, count(c.cart_id) com_carrinho, (select count(*) from carts where cart_id not in (select cart_id from orders)) carrinhos_sem_pedido from orders o left join carts c using (cart_id)")
q("orders.user_id (100% nulo -> usuário só via carts)", "select count(*) pedidos, count(user_id) com_user_id from orders")
q("carts.user_id -> cards.user_id", "select count(*) carrinhos, count(*) filter (where user_id in (select user_id from cards)) user_em_cards from carts")
q("redeemed_points -> order_items", "select count(*) linhas, count(i.order_item_id) com_item from redeemed_points r left join order_items i using (order_item_id)")
q("redeemed_points -> cards (account_id)", "select count(*) linhas, count(c.account_id) com_conta from redeemed_points r left join cards c using (account_id)")
q("redeemed_points: conta pertence ao mesmo usuário do carrinho?", """
    select count(*) linhas, count(*) filter (where k.user_id = c.user_id) mesmo_usuario
    from redeemed_points r join order_items i using (order_item_id) join orders o using (order_id)
    join carts c using (cart_id) join cards k on k.account_id = r.account_id""")
q("order_items x redeemed_points por status/tipo", """
    select i.status, i.product_type, count(*) itens, count(r.order_item_id) com_redeemed
    from order_items i left join (select distinct order_item_id from redeemed_points) r using (order_item_id)
    group by all order by 1, 2""")
q("redeemed_points fecha com order_items.paid_points?", """
    with r as (select order_item_id,
                      sum(points) filter (where movement_type = 'RESGATE') resgate,
                      sum(points) filter (where movement_type = 'RESERVA') reserva,
                      sum(points) filter (where movement_type = 'CANCELADO_RESERVA') cancelado_reserva
               from redeemed_points group by 1)
    select count(*) itens, count(*) filter (where -resgate = i.paid_points) resgate_igual_paid,
           count(reserva) com_reserva, count(*) filter (where reserva = -cancelado_reserva) reserva_anulada
    from r join order_items i using (order_item_id)""")
q("points_ledger -> cards (account_id e user_id)", """
    select count(*) movimentos, count(c.account_id) com_conta, count(*) filter (where c.user_id = l.user_id) mesmo_user
    from points_ledger l left join cards c using (account_id)""")
q("points_ledger -> dim_operation", "select count(*) movimentos, count(d.operation_code) com_operacao from points_ledger l left join dim_operation d using (operation_code)")
q("points_ledger: sinal dos pontos x direction e valid_until por operação", """
    select l.operation_code, d.operation_name, d.direction, count(*) n,
           count(*) filter (where points > 0) positivos, count(*) filter (where points < 0) negativos,
           count(valid_until) com_valid_until, sum(points)::bigint soma_pontos,
           min(movement_at)::date ini, max(movement_at)::date fim
    from points_ledger l left join dim_operation d using (operation_code) group by all order by 1""")
q("points_ledger: pontos fracionários?", "select count(*) from points_ledger where points <> round(points)")
q("points_ledger: prazo de validade (dias entre movimento e valid_until)", """
    select operation_code, datediff('day', movement_at::date, valid_until) dias, count(*) n
    from points_ledger where valid_until is not null group by all order by 3 desc limit 8""")
q("ledger RESGATE (op 2) x redeemed_points/order_items", """
    select (select count(*) from points_ledger where operation_code = 2) ledger_resgates,
           (select sum(points)::bigint from points_ledger where operation_code = 2) ledger_pts,
           (select count(distinct order_item_id) from redeemed_points where movement_type = 'RESGATE') itens_resgatados,
           (select sum(points) from redeemed_points where movement_type = 'RESGATE') redeemed_pts""")
q("ledger ESTORNO_PEDIDO (op 14) x itens ESTORNADO + estornos parciais (refunded_points)", """
    select (select count(*) from points_ledger where operation_code = 14) ledger_estornos,
           (select sum(points)::bigint from points_ledger where operation_code = 14) ledger_pts,
           (select count(*) from order_items where status = 'ESTORNADO') itens_estornados,
           (select sum(paid_points) from order_items where status = 'ESTORNADO') pts_itens_estornados,
           (select count(*) from order_items where refunded_points > 0) itens_refund_parcial,
           (select sum(refunded_points) from order_items) pts_refund_parcial""")
q("order_items.refunded_points por status", """
    select status, count(*) itens, count(*) filter (where refunded_points > 0) com_refund,
           count(*) filter (where refunded_points = paid_points) refund_total, sum(refunded_points) pts_refund
    from order_items group by 1 order by 2 desc""")
q("Migração: expiração (103) x crédito migrado (100) por usuário", """
    with u as (select user_id, sum(points) filter (where operation_code = 100) cred_mig,
                      -sum(points) filter (where operation_code = 103) exp_mig
               from points_ledger group by 1)
    select count(cred_mig) users_migrados, count(exp_mig) users_com_expiracao,
           count(*) filter (where exp_mig is not null and cred_mig is null) exp_sem_credito,
           count(*) filter (where exp_mig > cred_mig) exp_maior_que_credito,
           sum(cred_mig)::bigint pts_migrados, sum(exp_mig)::bigint pts_expirados_mig
    from u""")
q("Migração: valid_until dos créditos migrados x datas das expirações", """
    select (select min(valid_until) from points_ledger where operation_code = 100) valid_until_min_mig,
           (select max(valid_until) from points_ledger where operation_code = 100) valid_until_max_mig,
           (select min(movement_at)::date from points_ledger where operation_code = 103) primeira_expiracao_mig,
           (select max(movement_at)::date from points_ledger where operation_code = 103) ultima_expiracao_mig""")
q("Ledger: algum usuário com saldo acumulado negativo?", """
    with s as (select user_id, sum(points) over (partition by user_id order by movement_at, movement_id rows unbounded preceding) saldo
               from points_ledger)
    select count(distinct user_id) users_saldo_negativo from s where saldo < 0""")
q("cards: exatamente um is_most_recent por usuário? e é o cartão mais novo?", """
    select (select count(*) from (select user_id from cards group by 1 having sum(is_most_recent::int) <> 1)) users_sem_exatamente_1,
           (select count(*) from cards c where is_most_recent
               and created_at < (select max(created_at) from cards c2 where c2.user_id = c.user_id)) most_recent_nao_e_o_mais_novo""")
q("cards: movimentos do ledger anteriores a cards.created_at", """
    select l.operation_code, count(*) movimentos, count(*) filter (where l.movement_at < c.created_at) antes_do_cartao
    from points_ledger l join cards c using (account_id) group by 1 order by 1""")
q("cards: card_class x card_flag", "select card_class, card_flag, count(*) from cards group by all order by 1, 2")
q("crm_events.user_id -> cards.user_id", """
    select count(distinct user_id) users_crm, count(distinct user_id) filter (where user_id in (select user_id from cards)) em_cards,
           count(*) filter (where user_id is null) eventos_sem_user
    from crm_events""")

# ---------------------------------------------------------------------------
# 6. JSON de crm_events.event_properties
# ---------------------------------------------------------------------------
secao("6. ESTRUTURA DO JSON event_properties")

q("JSON válido?", "select json_valid(event_properties) valido, count(*) from crm_events group by 1")
q("Conjunto de chaves por event_name", """
    select event_name, list_sort(json_keys(event_properties::json)) chaves, count(*) n
    from crm_events group by all order by 1, 3 desc""")
q("Tipo JSON de cada chave", """
    select k chave, json_type(event_properties::json -> k) tipo, count(*) n
    from (select event_properties, unnest(json_keys(event_properties::json)) k from crm_events)
    group by all order by 3 desc""")
q("Valores das chaves não-ID", """
    select k chave, json_extract_string(event_properties, '$.' || k) valor, count(*) n
    from (select event_properties, unnest(json_keys(event_properties::json)) k from crm_events)
    where k <> 'campaign_name' group by all order by 1, 3 desc""")
q("campaign_name (JSON) = campaign_id (coluna)?", """
    select count(*) filter (where json_extract_string(event_properties, '$.campaign_name') is not null) com_campaign_name,
           count(*) filter (where json_extract_string(event_properties, '$.campaign_name') = campaign_id) iguais
    from crm_events""")
q("event_name x campaign_type (+ user_id nulo)", """
    select event_name, campaign_type, count(*) n, count(distinct campaign_id) campanhas, count(*) - count(user_id) sem_user
    from crm_events group by all order by 1, 2""")
q("Prefixos de campaign_id", """
    select regexp_extract(campaign_id, '^CMP_([A-Z_]+_)?', 0) prefixo, count(distinct campaign_id) campanhas, count(*) eventos
    from crm_events where campaign_id is not null group by 1 order by 2 desc""")
q("Campanhas com nome semântico (não hash)", """
    select campaign_id, campaign_type, min(event_ts) inicio_utc, max(event_ts) fim_utc,
           count(*) filter (where event_name = 'Notification Sent') enviados
    from crm_events where campaign_id similar to 'CMP_[A-Z_]+_[0-9a-f]+' group by all order by 3""")
q("Lançamento: primeiro Pix (BRT) x envio da campanha CMP_LANCAMENTO_PIX (UTC->BRT)", """
    select (select min(created_at) from order_items where supplier_name = 'Pix Pontua+') primeiro_pix_brt,
           (select min(event_ts) - interval 3 hour from crm_events where campaign_id like 'CMP_LANCAMENTO_PIX%' and event_name = 'Notification Sent') inicio_envio_brt,
           (select count(*) from order_items where supplier_name = 'Pix Pontua+'
              and created_at < (select min(event_ts) from crm_events where campaign_id like 'CMP_LANCAMENTO_PIX%') at time zone 'UTC') itens_pix_antes_do_envio""")
q("control_group preenchido?", "select count(*) linhas, count(control_group) com_control_group from crm_events")

# ---------------------------------------------------------------------------
# 7. Relatório mensal x dados brutos
# ---------------------------------------------------------------------------
secao("7. RELATÓRIO MENSAL x DADOS BRUTOS")

q("Pix: valor por ponto no item", """
    select status, count(*) itens, sum(paid_points) pontos, round(sum(product_value), 2) reais,
           round(sum(product_value) / sum(paid_points), 5) reais_por_ponto,
           count(*) filter (where abs(paid_points * 0.019 - product_value) <= 0.01) itens_a_0019,
           sum(paid_currency) paid_currency
    from order_items where supplier_name = 'Pix Pontua+' group by 1 order by 2 desc""")
q("Pix por mês: relatório x itens (todos os status e só APROVADO)", """
    select r.mes,
           r.pix_transacoes rel_transacoes, count(i.order_item_id) itens_todos, count(*) filter (where i.status = 'APROVADO') itens_aprov,
           r.pix_pontos::bigint rel_pontos, sum(i.paid_points) pts_todos, sum(i.paid_points) filter (where i.status = 'APROVADO') pts_aprov,
           r.pix_reais rel_reais, round(sum(i.product_value), 2) reais_todos, round(sum(i.product_value) filter (where i.status = 'APROVADO'), 2) reais_aprov,
           round(r.pix_reais / sum(i.product_value) filter (where i.status = 'APROVADO'), 4) rel_sobre_aprov,
           round(r.pix_reais / r.pix_pontos, 5) rel_reais_por_ponto
    from relatorio_mensal_cliente r
    join order_items i on strftime(i.created_at, '%Y-%m') = r.mes and i.supplier_name = 'Pix Pontua+'
    group by r.mes, r.pix_transacoes, r.pix_pontos, r.pix_reais order by 1""")
q("Mix por mês: pontos de itens APROVADO por category_macro (transferências a parceiros = Varejo) x relatório", """
    with b as (
        select strftime(created_at, '%Y-%m') mes, paid_points pts,
               case when supplier_name = 'Pix Pontua+' then 'pix' when category_macro = 'Aereas' then 'aereas'
                    when category_macro = 'Varejo' then 'varejo' end cat,
               product_type
        from order_items where status = 'APROVADO' and product_type <> 'COMPRA_PONTOS')
    select b.mes,
           round(100.0 * sum(pts) filter (where cat = 'aereas') / sum(pts), 1) aereas_calc, any_value(r.aereas_pct) aereas_rel,
           round(100.0 * sum(pts) filter (where cat = 'varejo') / sum(pts), 1) varejo_calc, any_value(r.varejo_pct) varejo_rel,
           round(100.0 * coalesce(sum(pts) filter (where cat = 'pix'), 0) / sum(pts), 1) pix_calc, any_value(r.pix_pct) pix_rel,
           round(100.0 * sum(pts) filter (where product_type = 'PRODUTO') / sum(pts), 1) varejo_so_produto_calc
    from b left join relatorio_mensal_cliente r using (mes) group by 1 order by 1""")
q("Mix junho com todos os status (tentativa de reproduzir 55/13/32)", """
    with b as (
        select paid_points pts,
               case when supplier_name = 'Pix Pontua+' then 'pix' when category_macro = 'Aereas' then 'aereas' else 'varejo' end cat
        from order_items where strftime(created_at, '%Y-%m') = '2026-06' and product_type <> 'COMPRA_PONTOS')
    select round(100.0 * sum(pts) filter (where cat = 'aereas') / sum(pts), 1) aereas,
           round(100.0 * sum(pts) filter (where cat = 'varejo') / sum(pts), 1) varejo,
           round(100.0 * sum(pts) filter (where cat = 'pix') / sum(pts), 1) pix
    from b""")
q("E-mails e push enviados: relatório x CRM (Notification Sent, mês em BRT)", """
    with e as (select strftime(event_ts - interval 3 hour, '%Y-%m') mes, campaign_type
               from crm_events where event_name = 'Notification Sent'),
         a as (select mes, count(*) filter (where campaign_type = 'Email') emails_crm,
                      count(*) filter (where campaign_type like 'Mobile Push%') push_crm
               from e group by 1)
    select r.mes, r.emails_enviados emails_rel, a.emails_crm, round(r.emails_enviados / a.emails_crm, 4) razao_email,
           r.push_enviados::bigint push_rel, a.push_crm, round(r.push_enviados / nullif(a.push_crm, 0), 4) razao_push
    from relatorio_mensal_cliente r left join a using (mes) order by 1""")
q("Itens por mês e grupo (contexto para jan/2026 e mudanças de fornecedor)", """
    select strftime(created_at, '%Y-%m') mes,
           count(*) filter (where category_macro = 'Aereas') aereas,
           count(*) filter (where product_type = 'PRODUTO') produtos,
           count(*) filter (where supplier_name in ('Nuvem Recompensas', 'Pontos Max')) transf_parceiros,
           count(*) filter (where supplier_name = 'Pix Pontua+') pix,
           count(*) filter (where product_type = 'COMPRA_PONTOS') compra_pontos
    from order_items group by 1 order by 1""")

print("\nFim do perfil.", file=sys.stderr)
