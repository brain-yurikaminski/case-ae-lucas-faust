-- Em cada mês, os percentuais dos 4 tipos de resgate somam 1 (tolerância 1e-9).
select mes, pct_aereo + pct_varejo_produto + pct_transferencia_parceiro + pct_pix as soma_pct
from {{ ref('mart_metas_mensal') }}
where abs(pct_aereo + pct_varejo_produto + pct_transferencia_parceiro + pct_pix - 1) > 1e-9
