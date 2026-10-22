select
    cast(mes as varchar) as mes,
    cast(aereas_pct as double) as aereas_pct,
    cast(varejo_pct as double) as varejo_pct,
    cast(pix_pct as double) as pix_pct,
    cast(pix_reais as double) as pix_reais,
    cast(pix_pontos as bigint) as pix_pontos,
    cast(pix_transacoes as bigint) as pix_transacoes,
    cast(emails_enviados as bigint) as emails_enviados,
    cast(push_enviados as bigint) as push_enviados
from {{ source('dados', 'relatorio_mensal_cliente') }}
