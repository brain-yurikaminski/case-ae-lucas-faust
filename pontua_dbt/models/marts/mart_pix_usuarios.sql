-- Grão: 1 linha por usuário que resgatou Pix (itens APROVADO ou ESTORNADO de fct_resgates).
-- Não há grupo de controle (control_group vazio) e usuários que não resgataram não estão aqui:
-- esta tabela mede ordem dos eventos, não efeito causal da campanha.
-- Horários em BRT: created_at do item convertido de -03:00 e event_ts_brt do CRM (convertido de UTC).
with pix as (
    select
        f.user_id,
        count(*) as itens_pix,
        sum(f.pontos_brutos) as pontos_brutos_pix,
        min(timezone('America/Sao_Paulo', i.created_at)) as primeiro_resgate_pix_brt
    from {{ ref('fct_resgates') }} f
    join {{ ref('stg_order_items') }} i using (order_item_id)
    where f.tipo_resgate = 'PIX'
    group by f.user_id
),

camp as (
    select
        user_id,
        min(event_ts_brt) filter (where event_name = 'Notification Sent') as primeiro_envio_brt,
        min(event_ts_brt) filter (where event_name = 'Notification Viewed') as primeira_abertura_brt,
        min(event_ts_brt) filter (where event_name = 'Notification Clicked') as primeiro_clique_brt
    from {{ ref('stg_crm_events') }}
    where campaign_id like 'CMP_LANCAMENTO_PIX%' and user_id is not null
    group by user_id
)

select
    p.user_id,
    p.itens_pix,
    p.pontos_brutos_pix,
    p.primeiro_resgate_pix_brt,
    c.primeiro_envio_brt,
    c.primeira_abertura_brt,
    c.primeiro_clique_brt,
    c.primeiro_envio_brt is not null as recebeu_campanha,
    c.primeira_abertura_brt is not null as abriu_campanha,
    c.primeiro_clique_brt is not null as clicou_campanha,
    coalesce(c.primeiro_envio_brt < p.primeiro_resgate_pix_brt, false) as recebeu_antes,
    coalesce(c.primeira_abertura_brt < p.primeiro_resgate_pix_brt, false) as abriu_antes,
    coalesce(c.primeiro_clique_brt < p.primeiro_resgate_pix_brt, false) as clicou_antes
from pix p
left join camp c using (user_id)
