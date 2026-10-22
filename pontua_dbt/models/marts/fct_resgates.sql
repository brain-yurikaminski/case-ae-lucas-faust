-- Grão: 1 linha por order_item. Só itens APROVADO ou ESTORNADO com paid_points preenchido.
-- COMPRA_PONTOS fica fora (não é resgate). tipo_resgate usa supplier_responsible, não supplier_name
-- (supplier_name foi renomeado em 10/09/2026: 'Casa&Cia (via MegaMagazine)').
with itens as (
    select * from {{ ref('stg_order_items') }}
    where status in ('APROVADO', 'ESTORNADO')
      and paid_points is not null
),

pedidos as (
    select o.order_id, c.user_id
    from {{ ref('stg_orders') }} o
    join {{ ref('stg_carts') }} c using (cart_id)
)

select
    i.order_item_id,
    i.order_id,
    p.user_id,
    cast(timezone('America/Sao_Paulo', i.created_at) as date) as data_brt,
    strftime(timezone('America/Sao_Paulo', i.created_at), '%Y-%m') as mes,
    case
        when i.product_type = 'PASSAGEM' then 'AEREO'
        when i.product_type = 'PRODUTO' then 'VAREJO_PRODUTO'
        when i.product_type = 'TRANSFERENCIA' and i.supplier_responsible = 'Pix Pontua+' then 'PIX'
        when i.product_type = 'TRANSFERENCIA' then 'TRANSFERENCIA_PARCEIRO'
    end as tipo_resgate,
    i.status,
    (i.status = 'ESTORNADO') as flag_estornado,
    i.supplier_responsible,
    i.paid_points as pontos_brutos,
    case when i.status = 'ESTORNADO' then i.paid_points else coalesce(i.refunded_points, 0) end as pontos_estornados,
    case when i.status = 'ESTORNADO' then 0 else i.paid_points - coalesce(i.refunded_points, 0) end as pontos_liquidos,
    i.product_value as valor_reais
from itens i
left join pedidos p using (order_id)
