"""Exporta marts agregados de pontua_dbt/pontua.duckdb para JSON em entrega/dashboard/dados/.

Somente leitura no banco. Não exporta nada em nível de usuário: só marts da lista abaixo
(mart_pix_usuarios fica de fora) e o script aborta se alguma coluna identificar usuário ou dispositivo.

Também grava dados/dados.js (window.DADOS_PONTUA = {...}) com os mesmos registros, para o dashboard abrir
direto no navegador (file://), onde fetch de JSON é bloqueado.

Uso (depois do dbt build):
    env -u VIRTUAL_ENV poetry run python analise/02_exportar_dashboard.py
"""

import datetime as dt
import json
import math
from decimal import Decimal
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "pontua_dbt" / "pontua.duckdb"
SAIDA = RAIZ / "entrega" / "dashboard" / "dados"

# arquivo JSON -> mart de origem
EXPORTACOES = {
    "metas_mensal": "mart_metas_mensal",
    "pix_preco_mensal": "mart_pix_preco_mensal",
    "pix_diario": "mart_pix_diario",
    "breakage_mensal": "mart_breakage_mensal",
    "mix_absoluto_mensal": "mart_mix_absoluto_mensal",
    "pre_pos_pix": "mart_pre_pos_pix",
    "cenarios_meta": "mart_cenarios_meta",
    "pix_adesao_campanha": "mart_pix_adesao_campanha",
}
COLUNAS_PROIBIDAS = {"user_id", "device_id", "account_id", "cart_id", "order_id", "order_item_id"}


def valor_json(v):
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    raise TypeError(f"tipo sem serialização definida: {type(v)}")


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(BANCO.as_posix(), read_only=True)
    todos = {}
    for arquivo, mart in EXPORTACOES.items():
        cur = con.execute(f"select * from {mart}")
        colunas = [d[0] for d in cur.description]
        proibidas = COLUNAS_PROIBIDAS & set(colunas)
        if proibidas:
            raise SystemExit(f"{mart} tem colunas de nível de linha/usuário: {sorted(proibidas)}")
        registros = [{c: valor_json(v) for c, v in zip(colunas, linha)} for linha in cur.fetchall()]
        todos[arquivo] = registros
        destino = SAIDA / f"{arquivo}.json"
        destino.write_text(json.dumps(registros, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{destino.relative_to(RAIZ)}: {len(registros)} linhas, {len(colunas)} colunas (de {mart})")
    embutido = SAIDA / "dados.js"
    embutido.write_text(
        "// Gerado por analise/02_exportar_dashboard.py. Não editar à mão.\n"
        "window.DADOS_PONTUA = " + json.dumps(todos, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"{embutido.relative_to(RAIZ)}: {embutido.stat().st_size} bytes")


if __name__ == "__main__":
    main()
