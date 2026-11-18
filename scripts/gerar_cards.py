#!/usr/bin/env python3
"""Gera as imagens do perfil (SVG) na paleta lavanda.

- assets/banner-claro.svg e banner-escuro.svg: banner do topo, sem fundo (textos editáveis logo abaixo)
- assets/numeros.svg: números do último ano + linguagens mais usadas

Usa só a biblioteca padrão do Python e a API GraphQL do GitHub.
Roda pelo GitHub Actions, que fornece o GITHUB_TOKEN.
"""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

# Textos do banner: edite à vontade
NOME = "Amanda Inagaki"
CARGO = "desenvolvedora front-end"

PASTA = Path(__file__).resolve().parents[1] / "assets"
USUARIA = os.environ.get("GITHUB_USERNAME", "inagakidev")
TOKEN = os.environ.get("GITHUB_TOKEN")
FUSO = ZoneInfo("America/Sao_Paulo")

# Paleta lavanda suave (do mais escuro ao mais claro)
TINTA = "#2B2540"
UVA = "#5B4E80"
LAVANDA = "#8E7FB8"
LILAS = "#B8A9D9"
NEVOA = "#DCD3F0"
PAPEL = "#F5F2FB"
SUAVE = "#6B6185"
LINHA = "#E2DBF0"

FONTE = "Inter,'Segoe UI',Helvetica,Arial,sans-serif"


def texto(x, y, conteudo, tamanho=14, cor=TINTA, peso=400, ancora="start", espaco=0):
    extra = f' letter-spacing="{espaco}"' if espaco else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{FONTE}" font-size="{tamanho}" '
        f'font-weight="{peso}" fill="{cor}" text-anchor="{ancora}"{extra}>{escape(str(conteudo))}</text>'
    )


def brilho(cx, cy, r, cor):
    """Estrelinha de quatro pontas, o símbolo do perfil."""
    k = r * 0.22
    return (
        f'<path d="M {cx} {cy - r} Q {cx + k} {cy - k} {cx + r} {cy} '
        f'Q {cx + k} {cy + k} {cx} {cy + r} Q {cx - k} {cy + k} {cx - r} {cy} '
        f'Q {cx - k} {cy - k} {cx} {cy - r} Z" fill="{cor}"/>'
    )


def salvar(nome, partes):
    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / nome).write_text("\n".join(partes + ["</svg>"]) + "\n", encoding="utf-8")
    print("Gerado:", nome)


def numero(n):
    return f"{n:,}".replace(",", ".")


def gerar_banner(tema):
    """Banner sem fundo, em versão clara e escura (o GitHub escolhe pelo tema)."""
    if tema == "escuro":
        nome, cargo, detalhe = "#EDE8F7", LILAS, "#9D93B5"
        estrela, tons = LILAS, ["#2B2540", "#2B2540", "#3A3350", UVA, "#2B2540", LAVANDA]
    else:
        nome, cargo, detalhe = TINTA, UVA, SUAVE
        estrela, tons = LAVANDA, [NEVOA, NEVOA, "#E8E2F5", LILAS, NEVOA, LAVANDA]

    w, h = 840, 128
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(NOME)}, {escape(CARGO)}">',
        brilho(9, 28, 7, estrela),
        texto(24, 33, "OLÁ, MUNDO", 11, detalhe, 600, espaco=2.5),
        texto(0, 84, NOME, 40, nome, 700),
        texto(2, 113, CARGO, 17, cargo, 500),
    ]
    # Mosaico discreto à direita, lembrando um gráfico de contribuições
    lado, gap = 14, 6
    x0, y0 = w - 8 * (lado + gap), 14
    for linha in range(5):
        for coluna in range(8):
            if (linha + coluna) % 9 == 3 or (linha == 0 and coluna < 3) or (linha == 4 and coluna > 5):
                continue
            cor = tons[(linha * 3 + coluna * 5) % len(tons)]
            x = x0 + coluna * (lado + gap)
            y = y0 + linha * (lado + gap)
            p.append(f'<rect x="{x}" y="{y}" width="{lado}" height="{lado}" rx="4" fill="{cor}"/>')
    salvar(f"banner-{tema}.svg", p)


def buscar_dados():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN não encontrado. Rode este script pelo GitHub Actions.")

    agora = dt.datetime.now(dt.timezone.utc)
    inicio = (agora - dt.timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0)

    consulta = """query($login: String!, $de: DateTime!, $ate: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $de, to: $ate) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
          totalCount
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
      }
    }"""

    corpo = json.dumps({
        "query": consulta,
        "variables": {
            "login": USUARIA,
            "de": inicio.isoformat().replace("+00:00", "Z"),
            "ate": agora.isoformat().replace("+00:00", "Z"),
        },
    }).encode()

    pedido = Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": f"{USUARIA}-readme",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(pedido, timeout=30) as resposta:
        dados = json.load(resposta)

    if dados.get("errors"):
        raise RuntimeError(str(dados["errors"]))
    usuaria = (dados.get("data") or {}).get("user")
    if not usuaria:
        raise RuntimeError("Usuária não encontrada no GitHub.")
    return usuaria


def gerar_numeros(usuaria):
    calendario = usuaria["contributionsCollection"]["contributionCalendar"]
    dias = {
        dt.date.fromisoformat(d["date"]): d["contributionCount"]
        for semana in calendario["weeks"]
        for d in semana["contributionDays"]
    }
    hoje = dt.datetime.now(FUSO).date()

    total = calendario["totalContributions"]
    ativos = sum(1 for d, n in dias.items() if d <= hoje and n > 0)
    repos = usuaria["repositories"]["totalCount"]

    inicio = hoje if dias.get(hoje, 0) > 0 else hoje - dt.timedelta(days=1)
    sequencia = 0
    while dias.get(inicio - dt.timedelta(days=sequencia), 0) > 0:
        sequencia += 1

    bytes_por_lingua = {}
    for repo in usuaria["repositories"]["nodes"]:
        for borda in repo["languages"]["edges"]:
            nome = borda["node"]["name"]
            bytes_por_lingua[nome] = bytes_por_lingua.get(nome, 0) + borda["size"]
    ranking = sorted(bytes_por_lingua.items(), key=lambda x: -x[1])
    principais = ranking[:4]
    outras = sum(n for _, n in ranking[4:])
    if outras:
        principais.append(("Outras", outras))
    soma = sum(n for _, n in principais) or 1

    w, h = 840, 250
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="Números do último ano e linguagens mais usadas">',
        f'<rect width="{w}" height="{h}" rx="22" fill="{PAPEL}"/>',
        brilho(52, 50, 8, LAVANDA),
        texto(68, 55, "NO ÚLTIMO ANO", 12, SUAVE, 600, espaco=2.5),
    ]

    colunas = [
        (numero(total), "contribuições"),
        (numero(ativos), "dias ativos"),
        (numero(sequencia), "dias seguidos agora"),
        (numero(repos), "repositórios públicos"),
    ]
    largura_col = (w - 88) / 4
    for i, (valor, rotulo) in enumerate(colunas):
        x = 44 + i * largura_col
        if i:
            p.append(f'<path d="M {x - 16:.0f} 84 V 140" stroke="{LINHA}" stroke-width="1.5"/>')
        p.append(texto(f"{x:.0f}", 120, valor, 34, TINTA, 700))
        p.append(texto(f"{x:.0f}", 142, rotulo, 13, SUAVE))

    # Barra de linguagens
    cores = [UVA, LAVANDA, LILAS, NEVOA, LINHA]
    x, y, largura_barra = 44, 172, w - 88
    p.append(f'<clipPath id="barra"><rect x="{x}" y="{y}" width="{largura_barra}" height="12" rx="6"/></clipPath>')
    p.append('<g clip-path="url(#barra)">')
    cursor = x
    for i, (_, n) in enumerate(principais):
        fatia = largura_barra * n / soma
        p.append(f'<rect x="{cursor:.1f}" y="{y}" width="{fatia + 0.5:.1f}" height="12" fill="{cores[i]}"/>')
        cursor += fatia
    p.append("</g>")
    if not principais:
        p.append(f'<rect x="{x}" y="{y}" width="{largura_barra}" height="12" rx="6" fill="{NEVOA}"/>')

    lx = 44
    for i, (nome, n) in enumerate(principais):
        rotulo = f"{nome} {round(n / soma * 100)}%"
        p.append(f'<rect x="{lx}" y="205" width="10" height="10" rx="3" fill="{cores[i]}"/>')
        p.append(texto(lx + 16, 214, rotulo, 12, SUAVE, 500))
        lx += 26 + len(rotulo) * 7.2
    salvar("numeros.svg", p)


if __name__ == "__main__":
    gerar_banner("claro")
    gerar_banner("escuro")
    gerar_numeros(buscar_dados())
