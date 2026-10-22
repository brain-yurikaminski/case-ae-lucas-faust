-- Itens PIX devem valer R$ 0,019 por ponto (tolerância 0,0005).
select order_item_id, pontos_brutos, valor_reais, valor_reais / pontos_brutos as reais_por_ponto
from {{ ref('fct_resgates') }}
where tipo_resgate = 'PIX'
  and (pontos_brutos <= 0 or abs(valor_reais / pontos_brutos - 0.019) > 0.0005)
