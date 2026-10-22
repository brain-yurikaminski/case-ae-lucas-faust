-- Grão: 1 linha por mês (horário de Brasília). Itens Pix de TODOS os status, vindos de stg_order_items
-- (fct_resgates só tem APROVADO e ESTORNADO), para comparar com o relatório do operador.
with pix as (
    select
        strftime(timezone('America/Sao_Paulo', created_at), '%Y-%m') as mes,
        status,
        paid_points,
        product_value
    from {{ ref('stg_order_items') }}
    where product_type = 'TRANSFERENCIA' and supplier_responsible = 'Pix Pontua+'
),

agg as (
    select
        mes,
        count(*) as itens_todos,
        count(*) filter (where status = 'APROVADO') as itens_aprovados,
        sum(paid_points) as pontos_todos,
        sum(paid_points) filter (where status = 'APROVADO') as pontos_aprovados,
        sum(product_value) as reais_todos,
        sum(product_value) filter (where status = 'APROVADO') as reais_aprovados
    from pix
    group by mes
)

select
    a.mes,
    a.itens_todos,
    a.itens_aprovados,
    a.pontos_todos,
    a.pontos_aprovados,
    a.reais_todos,
    a.reais_aprovados,
    a.reais_aprovados / a.pontos_aprovados as preco_por_ponto_aprovados,
    a.reais_todos / a.pontos_todos as preco_por_ponto_todos,
    r.pix_transacoes as relatorio_pix_transacoes,
    r.pix_pontos as relatorio_pix_pontos,
    r.pix_reais as relatorio_pix_reais,
    r.pix_reais / r.pix_pontos as preco_implicito_relatorio,
    r.pix_reais / r.pix_pontos - a.reais_aprovados / a.pontos_aprovados as dif_relatorio_vs_aprovados
from agg a
left join {{ ref('stg_relatorio_mensal_cliente') }} r using (mes)
