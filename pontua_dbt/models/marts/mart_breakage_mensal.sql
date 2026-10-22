-- Grão: 1 linha por mês (mes, horário de Brasília), a partir de stg_points_ledger.
-- Candidatas a "breakage" calculadas lado a lado, mensais e acumuladas (_acum). Nenhuma é declarada a oficial.
-- Atenção: o ledger não tem expiração regular (op 3) e a menor validade de crédito regular (op 1) é 25/09/2027,
-- depois da extração. As únicas expirações são as de migração (op 103).
with mov as (
    select
        strftime(timezone('America/Sao_Paulo', movement_at), '%Y-%m') as mes,
        operation_code,
        points
    from {{ ref('stg_points_ledger') }}
),

m as (
    select
        mes,
        cast(coalesce(sum(points) filter (where operation_code = 1), 0) as bigint) as pontos_creditados_acumulo,
        cast(coalesce(sum(points) filter (where operation_code = 100), 0) as bigint) as pontos_migrados,
        cast(-coalesce(sum(points) filter (where operation_code = 2), 0) as bigint) as pontos_resgatados_brutos,
        cast(coalesce(sum(points) filter (where operation_code = 14), 0) as bigint) as pontos_estornados,
        cast(-coalesce(sum(points) filter (where operation_code = 3), 0) as bigint) as pontos_expirados_regular,
        cast(-coalesce(sum(points) filter (where operation_code = 103), 0) as bigint) as pontos_expirados_migracao,
        cast(sum(points) as bigint) as variacao_saldo
    from mov
    group by mes
),

base as (
    select
        *,
        pontos_resgatados_brutos - pontos_estornados as pontos_resgatados_liquidos,
        pontos_expirados_regular + pontos_expirados_migracao as pontos_expirados,
        cast(sum(variacao_saldo) over (order by mes) as bigint) as saldo_acumulado,
        cast(sum(pontos_creditados_acumulo) over (order by mes) as bigint) as creditados_acum,
        cast(sum(pontos_migrados) over (order by mes) as bigint) as migrados_acum,
        cast(sum(pontos_resgatados_brutos - pontos_estornados) over (order by mes) as bigint) as resgatados_liquidos_acum,
        cast(sum(pontos_expirados_regular + pontos_expirados_migracao) over (order by mes) as bigint) as expirados_acum,
        cast(sum(pontos_expirados_migracao) over (order by mes) as bigint) as expirados_migracao_acum
    from m
)

select
    mes,
    pontos_creditados_acumulo,
    pontos_migrados,
    pontos_resgatados_brutos,
    pontos_estornados,
    pontos_resgatados_liquidos,
    pontos_expirados_regular,
    pontos_expirados_migracao,
    pontos_expirados,
    variacao_saldo,
    saldo_acumulado,
    -- candidatas do mês
    pontos_expirados / nullif(pontos_creditados_acumulo, 0) as bk_exp_sobre_creditados,
    pontos_expirados / nullif(pontos_creditados_acumulo + pontos_migrados, 0) as bk_exp_sobre_emitidos,
    pontos_expirados / nullif(pontos_expirados + pontos_resgatados_liquidos, 0) as bk_exp_sobre_exp_mais_resg,
    1 - pontos_resgatados_liquidos / nullif(pontos_creditados_acumulo + pontos_migrados, 0) as bk_nao_resgatado_sobre_emitidos,
    pontos_expirados_migracao / nullif(pontos_migrados, 0) as bk_exp_migracao_sobre_migrados,
    -- candidatas acumuladas até o mês
    expirados_acum / nullif(creditados_acum, 0) as bk_exp_sobre_creditados_acum,
    expirados_acum / nullif(creditados_acum + migrados_acum, 0) as bk_exp_sobre_emitidos_acum,
    expirados_acum / nullif(expirados_acum + resgatados_liquidos_acum, 0) as bk_exp_sobre_exp_mais_resg_acum,
    1 - resgatados_liquidos_acum / nullif(creditados_acum + migrados_acum, 0) as bk_nao_resgatado_sobre_emitidos_acum,
    expirados_migracao_acum / nullif(migrados_acum, 0) as bk_exp_migracao_sobre_migrados_acum,
    saldo_acumulado / nullif(creditados_acum + migrados_acum, 0) as bk_saldo_sobre_emitidos_acum
from base
