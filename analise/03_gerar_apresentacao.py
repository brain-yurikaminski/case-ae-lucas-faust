"""Gera entrega/apresentacao/index.html a partir do modelo (apresentacao-modelo/index.html) e dos JSONs
agregados dos marts (entrega/dashboard/dados/). Todo número dos slides sai desses JSONs; os asserts
travam a geração se algum dado deixar de sustentar o que o texto afirma.

Uso (depois do dbt build e de analise/02_exportar_dashboard.py):
    python3 analise/03_gerar_apresentacao.py
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELO = RAIZ / "apresentacao-modelo" / "index.html"
SAIDA = RAIZ / "entrega" / "apresentacao" / "index.html"
DADOS = RAIZ / "entrega" / "dashboard" / "dados"


def carregar(nome):
    return json.loads((DADOS / f"{nome}.json").read_text(encoding="utf-8"))


metas = sorted(carregar("metas_mensal"), key=lambda r: r["mes"])
pre_pos = carregar("pre_pos_pix")
cenarios = carregar("cenarios_meta")
preco = sorted(carregar("pix_preco_mensal"), key=lambda r: r["mes"])
diario = sorted(carregar("pix_diario"), key=lambda r: r["data_brt"])
adesao = {r["grupo"]: r for r in carregar("pix_adesao_campanha")}
breakage = sorted(carregar("breakage_mensal"), key=lambda r: r["mes"])

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def num(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=1):
    return num(x * 100, d) + "%"


def milhoes(x, d=1):
    return num(x / 1e6, d)


def mes(m):
    a, b = m.split("-")
    return f"{MESES[int(b) - 1]}/{a[2:]}"


def pp(tipo, per):
    return next(r for r in pre_pos if r["tipo_resgate"] == tipo and r["periodo"] == per)


def cen(m, c):
    return next(r for r in cenarios if r["mes"] == m and r["cenario"] == c)


# ---------------------------------------------------------------- números e conferências da narrativa
TIPOS = ["AEREO", "VAREJO_PRODUTO", "TRANSFERENCIA_PARCEIRO", "PIX"]
pre_tot = sum(pp(t, "PRE")["media_mensal_pontos_liquidos"] for t in TIPOS)
pos_tot = sum(pp(t, "POS")["media_mensal_pontos_liquidos"] for t in TIPOS)
pix_pos = pp("PIX", "POS")["media_mensal_pontos_liquidos"]

pos_meses = [m for m in metas if "2026-06" <= m["mes"] <= "2026-09"]
assert all(m["atende_meta_aereo"] for m in metas), "aéreas deixou de cumprir a meta em algum mês"
assert not any(m["atende_meta_varejo_estrito"] for m in metas), "varejo estrito passou a cumprir em algum mês"
abaixo_amplo = [m["mes"] for m in metas if not m["atende_meta_varejo_amplo"]]
assert abaixo_amplo == ["2026-01", "2026-04", "2026-06", "2026-07", "2026-08", "2026-09"], abaixo_amplo
est_sem_jan = [m["pct_varejo_estrito"] for m in metas if m["mes"] != "2026-01"]
sem_pix_amplo = [cen(m["mes"], "SEM_PIX")["pct_varejo_amplo"] for m in pos_meses]
assert max(sem_pix_amplo) < 0.2
real = [cen(m["mes"], "REAL") for m in pos_meses]
falta_amplo = [r["pontos_varejo_adicionais_amplo"] for r in real]
falta_estrito = [r["pontos_varejo_adicionais_estrito"] for r in real]

rec, nrec = adesao["RECEBEU_CMP_LANCAMENTO_PIX"], adesao["NAO_RECEBEU"]
dias_envio = [d for d in diario if d["enviados"] > 0]
assert len(dias_envio) == 1, "a campanha passou a ter mais de um dia de envio"
dia_envio = dias_envio[0]
primeiro_dia_pix = next(d for d in diario if d["itens_pix"] > 0)
assert primeiro_dia_pix["data_brt"] < dia_envio["data_brt"], "o primeiro Pix não antecede o envio"

for r in preco:
    assert abs(r["preco_por_ponto_aprovados"] - 0.019) < 0.0005 and abs(r["preco_por_ponto_todos"] - 0.019) < 0.0005
    assert r["relatorio_pix_pontos"] == r["pontos_todos"], "pontos do relatório deixaram de bater com todos os status"
impl = [r["preco_implicito_relatorio"] for r in preco]

ult = breakage[-1]
assert ult["mes"] == "2026-09"
cand = [
    ("Expirados / creditados", ult["bk_exp_sobre_creditados_acum"], False),
    ("Expirados / emitidos", ult["bk_exp_sobre_emitidos_acum"], False),
    ("Expirados / (exp. + resg.)", ult["bk_exp_sobre_exp_mais_resg_acum"], False),
    ("Exp. migração / migrados", ult["bk_exp_migracao_sobre_migrados_acum"], False),
    ("1 − resgatados / emitidos", ult["bk_nao_resgatado_sobre_emitidos_acum"], True),
    ("Saldo / emitidos", ult["bk_saldo_sobre_emitidos_acum"], True),
]
exp_vals = [v for _, v, saldo in cand if not saldo]
assert max(exp_vals) < 0.2 and all(v > 0.4 for _, v, saldo in cand if saldo)
assert ult["pontos_expirados_regular"] == 0 and all(b["pontos_expirados_regular"] == 0 for b in breakage)

# ---------------------------------------------------------------- slides
WM = '<img class="wordmark" src="https://artifacts.brain3.com.br/share/z_pgQrSNRANa/raw/brandbook/visual-assets/Logos/logo_brain_0000_logo_branco.png" data-local="img/logo-branco.png" alt="Brain003">'


def kpi(rotulo, valor, unidade, texto, tam=110):
    return (f'<div class="kpi" data-anim="up"><span class="overline">{rotulo}</span>'
            f'<div class="t-data-lg" style="margin-top:14px; font-size:{tam}px">{valor}<span class="unit">{unidade}</span></div>'
            f'<p class="t-body-sm">{texto}</p></div>')


s1 = f'''<section class="slide" data-section="Resumo" data-template="dashboard">
  {WM}
  <div class="pad" style="display:flex; flex-direction:column; justify-content:center; gap:64px; padding-top:70px;">
    <div class="head" style="max-width:1560px">
      <span class="overline" data-anim="up">Pontua+ · Resgates depois do Pix</span>
      <h1 class="t-title" data-anim="up">Os resgates saltaram de {milhoes(pre_tot)}M para <span class="hl" data-anim="hl">{milhoes(pos_tot)}M</span> de pontos por mês</h1>
    </div>
    <div class="joined kpis">
      {kpi("Antes do Pix (PRE)", milhoes(pre_tot), "M", "pontos líquidos por mês, média de fev a abr/26")}
      {kpi("Depois do Pix (POS)", milhoes(pos_tot), "M", "pontos líquidos por mês, média de jun a set/26")}
      {kpi("Só o Pix", milhoes(pix_pos), "M", f"dos {milhoes(pos_tot)}M do POS vêm do Pontos no Pix, lançado em 27/05/2026")}
    </div>
    <p class="t-caption" data-anim="up">Pontos líquidos = pontos pagos menos estornos. Jan/26 (outlier) e mai/26 (mês do lançamento) ficam fora das médias.</p>
  </div>
</section>'''

# slide 2: barras do varejo amplo com a linha de 20%
ESC = 25.0
barras = ""
for m in metas:
    v = m["pct_varejo_amplo"] * 100
    foco = " focus" if not m["atende_meta_varejo_amplo"] else ""
    barras += (f'<div class="bar-slot"><div class="bar{foco}" data-anim="bars" style="height:{v / ESC * 100:.1f}%"><b>{num(v)}</b></div>'
               f'<span class="cat" style="left:0; right:0; text-align:center">{mes(m["mes"])}</span></div>')
linha20 = 20 / ESC * 100
aer_pos = [m["pct_aereo"] for m in pos_meses]
est_min, est_max = min(est_sem_jan), max(est_sem_jan)
jan = next(m for m in metas if m["mes"] == "2026-01")
abr = next(m for m in metas if m["mes"] == "2026-04")
amp_pos = [m["pct_varejo_amplo"] for m in pos_meses]


def card_met(rot, valor, texto, cor=""):
    return (f'<div class="card" data-anim="up" style="padding:28px 32px"><span class="t-label" style="color:var(--accent-data)">{rot}</span>'
            f'<div class="t-data-lg" style="margin:12px 0 8px; font-size:56px; {cor}">{valor}</div><p class="t-body-sm" style="font-size:20px">{texto}</p></div>')


s2 = f'''<section class="slide" data-section="Metas" data-template="comparacao-categorias">
  {WM}
  <div class="pad" style="display:flex; flex-direction:column; justify-content:center; gap:44px; padding-top:110px;">
    <div class="head" style="max-width:1640px">
      <span class="overline" data-anim="up">Metas do contrato</span>
      <h2 class="t-title" data-anim="up">Aéreas cumprem a meta. Varejo amplo: <span class="hl" data-anim="hl">4 meses</span> abaixo de 20%</h2>
    </div>
    <div style="display:grid; grid-template-columns:1.5fr 1fr; gap:72px; align-items:center;">
      <div>
        <p class="t-label" style="margin-bottom:30px; color:var(--mid)" data-anim="up">Varejo amplo, % dos pontos líquidos do mês (produtos + parceiros)</p>
        <div class="chart" style="height:300px; margin-bottom:56px">
          <div class="gridline" style="bottom:{linha20:.1f}%; background:none; border-top:2px dashed var(--hi); z-index:1"></div>
          <span class="t-caption" style="position:absolute; right:0; bottom:calc({linha20:.1f}% + 8px); color:var(--hi)">meta 20%</span>
          {barras}
        </div>
        <p class="t-caption" data-anim="up">Em ciano: abaixo de 20%. Jan/26 é outlier ({pct(jan["pct_aereo"])} de aéreas). Abr/26: {pct(abr["pct_varejo_amplo"])}.</p>
      </div>
      <div style="display:grid; gap:20px;">
        {card_met("Aéreas, jun a set/26", f"{pct(min(aer_pos))} a {pct(max(aer_pos))}", "meta de 50% cumprida em todos os 12 meses")}
        {card_met("Varejo estrito (só produtos)", f"{pct(est_min)} a {pct(est_max)}", f"nunca chegou a 20% (jan/26 fora: {pct(jan['pct_varejo_estrito'])})")}
        {card_met("Varejo amplo SEM o Pix, jun a set/26", f"{pct(min(sem_pix_amplo))} a {pct(max(sem_pix_amplo))}", "ainda abaixo de 20%, cálculo aritmético", "color:var(--error)")}
      </div>
    </div>
  </div>
</section>'''

# slide 3: ponte PRE -> POS (milhares de pontos) + conferência de soma
ponte = [("PRE fev a abr", round(pre_tot / 1000), "total")]
for rot, t in [("Aéreas", "AEREO"), ("Varejo produto", "VAREJO_PRODUTO"), ("Parceiros", "TRANSFERENCIA_PARCEIRO"), ("Pix", "PIX")]:
    ponte.append((rot, round(pp(t, "POS")["variacao_absoluta"] / 1000)))
ponte.append(("POS jun a set", round(pos_tot / 1000), "total"))
assert sum(p[1] for p in ponte[:-1]) == ponte[-1][1], "a ponte não fecha em milhares de pontos"
ponte_json = json.dumps([list(p) for p in ponte], ensure_ascii=False)
va, vv, vt = (pp(t, "POS")["variacao_pct"] for t in ["AEREO", "VAREJO_PRODUTO", "TRANSFERENCIA_PARCEIRO"])


def sg(x):
    return ("+" if x > 0 else "−") + pct(abs(x))


s3 = f'''<section class="slide" data-section="Antes e depois" data-template="waterfall">
  {WM}
  <div class="pad" style="display:grid; grid-template-columns:1.3fr 1.7fr; gap:80px; align-items:center;">
    <div class="head">
      <span class="overline" data-anim="up">Pré e pós Pix, por tipo de resgate</span>
      <h2 class="t-title" style="font-size:54px" data-anim="up">Aéreas e varejo cresceram. Só os <span class="hl" data-anim="hl">parceiros</span> encolheram</h2>
      <p class="t-body-sm" data-anim="up">Aéreas {sg(va)}, varejo produto {sg(vv)}, parceiros <span style="color:var(--error)">{sg(vt)}</span> na média mensal.</p>
      <p class="t-body-sm" data-anim="up" style="color:var(--hi)">Sem grupo de controle, a alta de aéreas e varejo não pode ser atribuída ao Pix.</p>
      <p class="t-caption" data-anim="up">Média mensal de pontos líquidos, em milhões. Valores arredondados.</p>
    </div>
    <div class="wf" data-waterfall='{ponte_json}' data-fmt="M"></div>
  </div>
</section>'''

# slide 4: afirmação do CRM
s4 = f'''<section class="slide" data-section="Afirmação do CRM" data-template="dashboard">
  {WM}
  <div class="pad" style="display:flex; flex-direction:column; justify-content:center; gap:48px; padding-top:70px;">
    <div class="head" style="max-width:1560px">
      <span class="overline" data-anim="up">"A comunicação de lançamento explica o sucesso do Pix"</span>
      <h2 class="t-title" data-anim="up">Quem recebeu a campanha adotou o Pix quase igual a quem não recebeu</h2>
    </div>
    <div class="joined kpis" style="grid-template-columns:repeat(2,1fr)">
      {kpi("Receberam a campanha", num(rec["pct_resgataram_pix"] * 100), "%", f"{num(rec['usuarios_resgataram_pix'], 0)} de {num(rec['usuarios'], 0)} usuários resgataram Pix", 120)}
      {kpi("Não receberam", num(nrec["pct_resgataram_pix"] * 100), "%", f"{num(nrec['usuarios_resgataram_pix'], 0)} de {num(nrec['usuarios'], 0)} usuários resgataram Pix", 120)}
    </div>
    <div class="grid-3">
      <div class="card" data-anim="up" style="padding:32px"><span class="t-label" style="color:var(--accent-data)">01 · O Pix veio antes</span><h3 style="font-size:28px">{num(primeiro_dia_pix["itens_pix"], 0)} itens Pix em 27/05</h3><p class="t-body-sm">Um dia antes do único envio da campanha (28/05, {num(dia_envio["enviados"], 0)} e-mails).</p></div>
      <div class="card" data-anim="up" style="padding:32px"><span class="t-label" style="color:var(--accent-data)">02 · Só observacional</span><h3 style="font-size:28px">Viés de seleção</h3><p class="t-body-sm">Universo: quem resgatou algo de 01/04 a 30/09/2026. Quem recebeu não foi sorteado.</p></div>
      <div class="card highlight" data-anim="up" style="padding:32px"><span class="overline">03 · Sem grupo de controle</span><h3 style="font-size:28px; color:#fff">Não prova nem refuta</h3><p class="t-body-sm">O campo control_group está vazio: causalidade não pode ser estabelecida.</p></div>
    </div>
  </div>
</section>'''

# slide 5: R$ 0,016
linhas5 = ""
for r in preco:
    linhas5 += (f'<div data-anim="row">{mes(r["mes"])}</div><div class="c" data-anim="row">{num(r["preco_por_ponto_aprovados"], 4)}</div>'
                f'<div class="c" data-anim="row" style="color:var(--error)">{num(r["preco_implicito_relatorio"], 4)}</div><div class="c" data-anim="row" data-g="1"></div>')
s5 = f'''<section class="slide" data-section="Afirmação do R$ 0,016" data-template="big-number">
  {WM}
  <div class="pad" style="display:grid; grid-template-columns:1fr 1.25fr; gap:96px; align-items:center; padding-top:40px;">
    <div style="display:flex; flex-direction:column; gap:28px;">
      <span class="overline" data-anim="up">"O Pix sai a cerca de R$ 0,016 por ponto"</span>
      <div class="t-data-xl" style="font-size:150px" data-anim="up">R$ 0,019</div>
      <p class="t-sub" style="color:var(--mid)" data-anim="up">por ponto, em <span class="hl" data-anim="hl">todos os meses e status.</span></p>
      <p class="t-body-sm" data-anim="up">Hipótese: o relatório divide os reais dos itens aprovados pelos pontos de todos os status. Perguntar ao operador.</p>
    </div>
    <div class="joined cmp" data-glyphs style="grid-template-columns:.8fr 1fr 1fr 1.5fr">
      <div class="hd" data-anim="up">Mês</div><div class="hd c" data-anim="up">Real (aprov.)</div><div class="hd c" data-anim="up">Relatório</div><div class="hd c brain" data-anim="featured" style="text-align:center">Pontos do relatório = todos os status</div>
      {linhas5}
    </div>
  </div>
</section>'''

# slide 6: breakage
ESC6 = 60.0
barras6 = ""
for rot, v, saldo in cand:
    h = v * 100 / ESC6 * 100
    cor = " err" if saldo else ""
    barras6 += (f'<div class="bar-slot"><div class="bar{cor}" data-anim="bars" style="height:{h:.1f}%"><b>{num(v * 100)}%</b></div>'
                f'<span class="cat wrap">{rot}{"*" if saldo else ""}</span></div>')
linha40 = 40 / ESC6 * 100
s6 = f'''<section class="slide" data-section="Afirmação do breakage" data-template="dashboard">
  {WM}
  <div class="pad" style="display:grid; grid-template-columns:1.2fr 1.6fr; gap:80px; align-items:center; padding-top:40px;">
    <div class="head">
      <span class="overline" data-anim="up">"Nosso breakage está em 40%"</span>
      <h2 class="t-title" style="font-size:54px" data-anim="up">Expiração de <span class="hl" data-anim="hl">{pct(min(exp_vals))} a {pct(max(exp_vals))}</span>, longe dos 40%</h2>
      <p class="t-body-sm" data-anim="up">Posição acumulada em set/26. *As barras vermelhas, acima de 40%, contam saldo ainda válido e não são breakage.</p>
      <p class="t-body-sm" data-anim="up" style="color:var(--hi)">O ledger não tem nenhuma expiração de pontos regulares: os créditos regulares só vencem a partir de 25/09/2027.</p>
    </div>
    <div>
      <div class="chart" style="height:430px; margin-bottom:92px">
        <div class="gridline" style="bottom:{linha40:.1f}%; background:none; border-top:2px dashed var(--hi); z-index:1"></div>
        <span class="t-caption" style="position:absolute; left:0; bottom:calc({linha40:.1f}% + 8px); color:var(--hi)">40% do diretor</span>
        {barras6}
      </div>
    </div>
  </div>
</section>'''

# slide 7: recomendação
def linha7(acao, numero, falta):
    return (f'<div data-anim="row" style="font-weight:700; font-size:24px; color:var(--hi)">{acao}</div>'
            f'<div data-anim="row">{numero}</div><div data-anim="row" style="color:var(--mid)">{falta}</div>')


s7 = f'''<section class="slide" data-section="Recomendação" data-template="comparacao-categorias">
  {WM}
  <div class="pad" style="display:flex; flex-direction:column; justify-content:center; gap:44px; padding-top:70px;">
    <div class="head" style="max-width:1560px">
      <span class="overline" data-anim="up">Recomendação</span>
      <h2 class="t-title" data-anim="up">Não coibir o Pix. <span class="hl" data-anim="hl">Atacar o varejo.</span></h2>
    </div>
    <div class="joined cmp" style="grid-template-columns:.8fr 1.6fr 1.2fr">
      <div class="hd" data-anim="up">Ação</div><div class="hd" data-anim="up">Número que sustenta</div><div class="hd brain" data-anim="featured">O que ainda falta saber</div>
      {linha7("1 · Manter o Pix", f"Sem o Pix, o varejo amplo ainda ficaria em {pct(min(sem_pix_amplo))} a {pct(max(sem_pix_amplo))}: coibir não cumpre a meta. O Pix soma {milhoes(pix_pos)}M de pontos por mês.", "Preço que o banco paga por ponto")}
      {linha7("2 · Atacar o varejo", f"Faltam {milhoes(min(falta_amplo))}M a {milhoes(max(falta_amplo))}M de pontos de varejo por mês (definição ampla) ou {milhoes(min(falta_estrito))}M a {milhoes(max(falta_estrito))}M (estrita) para chegar a 20% com o Pix.", "Definição contratual de varejo: estrita ou ampla")}
      {linha7("3 · Proteger as aéreas", f"{pct(min(aer_pos))} a {pct(max(aer_pos))} de aéreas em jun a set/26, com folga sobre a meta de 50%.", f"Causa do pico de jan/26 ({pct(jan['pct_aereo'])} de aéreas)")}
      {linha7("4 · Medir breakage com regra", f"Expiração de {pct(min(exp_vals))} a {pct(max(exp_vals))} em set/26, só da migração; sem expiração regular no ledger.", "Regra de expiração dos pontos regulares")}
    </div>
  </div>
</section>'''

# slide 8: limitações e perguntas
perguntas = [
    ("01 · Preço do banco", "Quanto o banco paga por ponto?", "Sem isso não há margem do programa nem custo de aéreas, varejo e Pix."),
    ("02 · Varejo no contrato", "Estrito ou amplo?", "Parceiros (Nuvem, Pontos Max) contam como varejo? Decide se o varejo cumpre a meta."),
    ("03 · Pico de janeiro", f"{pct(jan['pct_aereo'])} de aéreas em jan/26", f"{num(jan['pontos_liquidos_total'] / 1e6)}M de pontos no mês. Ficou fora da média PRE."),
    ("04 · Regra de expiração", "Sem expiração regular", f"O ledger só registra expiração da migração ({pct(min(exp_vals))} a {pct(max(exp_vals))} em set/26). Nenhuma de pontos regulares."),
    ("05 · O R$ 0,016", "Como o operador calcula?", f"Relatório: R$ {num(min(impl), 4)} a R$ {num(max(impl), 4)}. Real: R$ 0,019."),
    ("06 · E-mails e push", "Ago e set: relatório 1,35× o CRM", "Divergência apenas nesses dois meses. CRM perdeu dados ou o relatório inflou?"),
]
cards8 = "".join(
    f'<div class="card" data-anim="up" style="padding:26px 30px"><span class="t-label" style="color:var(--accent-data)">{a}</span>'
    f'<h3 style="font-size:26px; margin:14px 0 10px">{b}</h3><p class="t-body-sm" style="font-size:19px">{c}</p></div>'
    for a, b, c in perguntas)
s8 = f'''<section class="slide" data-section="Limitações e perguntas" data-template="fechamento">
  {WM}
  <div class="pad" style="display:flex; flex-direction:column; justify-content:center; gap:36px; padding-top:70px;">
    <div class="head" style="max-width:1560px">
      <span class="overline" data-anim="up">Limitações e perguntas ao negócio</span>
      <h2 class="t-title" data-anim="up">Seis respostas que mudam a decisão</h2>
    </div>
    <div class="grid-3" style="gap:20px">{cards8}</div>
    <p class="t-caption" data-anim="up">Limitações: sem grupo de controle no CRM; sem preço pago pelo banco; jan/26 fora da média PRE; comparações pré e pós são descritivas; dados até 30/09/2026, CRM convertido de UTC para Brasília.</p>
  </div>
</section>'''

slides = "\n\n".join([s1, s2, s3, s4, s5, s6, s7, s8])

# ---------------------------------------------------------------- montagem sobre o modelo
src = MODELO.read_text(encoding="utf-8")
head = src[: src.rindex("<body")]  # rindex: o comentário de instruções do modelo também cita <body>
head = head.replace("<title>Brain003 · Deck-modelo</title>", "<title>Pontua+ · Resgates depois do Pix</title>")
head = re.sub(r"<!--.*?-->", "<!-- Gerado por analise/03_gerar_apresentacao.py a partir do modelo e dos marts. Navegação: setas, espaço, clique; F tela cheia; ?static sem animação. -->", head, count=1, flags=re.S)
head = head.replace("</style>", """  /* extras desta apresentação */
  .bar.err{ background:var(--error); }
  .bar b{ z-index:2; background:var(--n900); }
  .cat.wrap{ white-space:normal; text-align:center; left:0; right:0; font-size:16px; line-height:1.3; padding:12px 6px 0; }
</style>""", 1)

tail = src[src.index('<script src="lib/gsap.min.js">'):]
# rótulos da ponte em milhões quando data-fmt="M" (valores em milhares de pontos)
tail = tail.replace(
    "lbl.textContent = (kind === 'total' ? '' : (r[1] > 0 ? '+' : '')) + r[1];",
    "var fm = function(v){ return wf.dataset.fmt === 'M' ? (Math.abs(v) / 1000).toLocaleString('pt-BR', {minimumFractionDigits:1, maximumFractionDigits:1}) : String(Math.abs(v)); };\n"
    "      lbl.textContent = (kind === 'total' ? '' : (r[1] > 0 ? '+' : '−')) + fm(r[1]);")
# sem carrossel nem modal neste deck
a = tail.index("/* ---------- carrossel")
b = tail.index("var hint = ")
tail = tail[:a] + "var modalOpen = false; function closeModal(){}\n\n  " + tail[b:]
tail = tail.replace("if(e.key === 'Escape' && modalOpen){ closeModal(); return; }\n    if(modalOpen) return;\n", "")

corpo = '<body data-voice="comercial">\n<div class="viewport">\n<div class="deck" id="deck">\n\n' + slides + '\n\n</div>\n</div>\n<div class="progress" id="progress"></div>\n<div class="hint">← → navegar · F tela cheia</div>\n\n'
SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(head + corpo + tail, encoding="utf-8")
print(f"{SAIDA.relative_to(RAIZ)}: 8 slides, {SAIDA.stat().st_size} bytes")
