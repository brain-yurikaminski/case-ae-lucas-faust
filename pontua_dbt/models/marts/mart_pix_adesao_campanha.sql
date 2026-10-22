-- Grão: grupo (RECEBEU_CMP_LANCAMENTO_PIX ou NAO_RECEBEU).
-- Universo: usuários com pelo menos 1 resgate (qualquer tipo, linhas de fct_resgates) entre 01/04 e 30/09/2026 (BRT).
-- Comparação observacional: sem grupo de controle (control_group vazio) e com viés de seleção.
with universo as (
    select
        user_id,
        bool_or(tipo_resgate = 'PIX') as resgatou_pix
    from {{ ref('fct_resgates') }}
    where data_brt between date '2026-04-01' and date '2026-09-30'
    group by user_id
),

recebeu as (
    select distinct user_id
    from {{ ref('stg_crm_events') }}
    where campaign_id like 'CMP_LANCAMENTO_PIX%'
      and event_name = 'Notification Sent'
      and user_id is not null
),

u as (
    select
        universo.user_id,
        universo.resgatou_pix,
        recebeu.user_id is not null as recebeu_campanha
    from universo
    left join recebeu using (user_id)
)

select
    case when recebeu_campanha then 'RECEBEU_CMP_LANCAMENTO_PIX' else 'NAO_RECEBEU' end as grupo,
    count(*) as usuarios,
    count(*) filter (where resgatou_pix) as usuarios_resgataram_pix,
    count(*) filter (where resgatou_pix) / count(*) as pct_resgataram_pix
from u
group by 1
