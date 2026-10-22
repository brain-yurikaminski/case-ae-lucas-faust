-- PRE tem 3 meses (2026-02 a 04), POS tem 4 (2026-06 a 09) e há exatamente 1 linha por tipo e período.
select tipo_resgate, periodo, meses_no_periodo
from {{ ref('mart_pre_pos_pix') }}
where (periodo = 'PRE' and meses_no_periodo <> 3)
   or (periodo = 'POS' and meses_no_periodo <> 4)
   or periodo not in ('PRE', 'POS')
union all
select tipo_resgate, periodo, count(*)
from {{ ref('mart_pre_pos_pix') }}
group by tipo_resgate, periodo
having count(*) > 1
