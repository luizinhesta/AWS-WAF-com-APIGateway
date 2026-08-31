"""
AWS WAF Security Lab - Projeto 03 (SQL Injection)
Funcao Lambda por tras de uma API Gateway REST API.

IMPORTANTE (escopo do laboratorio):
  - NAO existe banco de dados.
  - NAO ha execucao de SQL.
  - NAO existe vulnerabilidade real.
  - O parametro 'id' e apenas ecoado de volta na resposta.
  - Uma string com formato de SQL Injection e usada somente para testar a
    inspecao do AWS WAF, nunca para consultar um banco.

Rotas suportadas (integracao proxy do API Gateway REST):
  GET /health   -> status de saude
  GET /produto  -> ecoa o parametro id
  GET /info     -> pagina HTML simples explicando o laboratorio
  GET /         -> mesmo que /info

Logs: registramos apenas dados seguros (method, path, requestId e o valor de
'id' recebido). NUNCA registramos credenciais, tokens ou segredos.
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROJECT = "AWS WAF Security Lab 03"


def _json_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _html_response(status_code, html):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }


def _get_path(event):
    # Compatível com REST API (path / resource) e proxy.
    return event.get("path") or event.get("resource") or "/"


def _get_method(event):
    method = event.get("httpMethod")
    if method:
        return method
    ctx = event.get("requestContext") or {}
    return ctx.get("httpMethod", "GET")


def _get_query(event):
    return event.get("queryStringParameters") or {}


def _get_request_id(event):
    ctx = event.get("requestContext") or {}
    return ctx.get("requestId", "-")


def handle_health():
    return _json_response(200, {
        "status": "healthy",
        "project": PROJECT,
    })


def handle_produto(query):
    # Apenas ecoa o parametro id. Nao consulta banco, nao executa SQL.
    produto_id = query.get("id", "")
    return _json_response(200, {
        "status": "success",
        "id": produto_id,
        "message": "Parametro recebido pela Lambda",
    })


def handle_search(query):
    # Rota adicional que apenas ecoa o termo de busca recebido.
    termo = query.get("q", query.get("search", ""))
    return _json_response(200, {
        "status": "success",
        "query": termo,
        "message": "Parametro recebido pela Lambda",
    })


def handle_info():
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AWS WAF Security Lab - Projeto 03</title>
  <style>
    :root { --dark:#0f1b2d; --orange:#ff9900; --text:#e6edf3; --muted:#9fb3c8; --card:#1b2a41; --border:#2a3d59; }
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:"Segoe UI",Arial,sans-serif; background:var(--dark); color:var(--text); line-height:1.6; }
    .hero { text-align:center; padding:64px 20px; border-bottom:3px solid var(--orange); }
    .badge { display:inline-block; background:var(--orange); color:#14202e; font-weight:700; text-transform:uppercase; font-size:.75rem; padding:6px 16px; border-radius:999px; margin-bottom:20px; letter-spacing:1px; }
    .hero h1 { font-size:2.6rem; }
    .hero h2 { color:var(--orange); margin-top:6px; font-size:1.3rem; }
    .hero p { color:var(--muted); margin-top:10px; }
    main { max-width:760px; margin:0 auto; padding:32px 20px; }
    .card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:24px; margin-bottom:20px; }
    .card h3 { color:var(--orange); margin-bottom:10px; }
    code { color:var(--orange); font-family:Consolas,monospace; }
    table { width:100%; border-collapse:collapse; margin-top:10px; }
    th,td { padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); }
    th { color:var(--orange); font-size:.8rem; text-transform:uppercase; }
    footer { text-align:center; padding:24px; color:var(--muted); font-size:.85rem; border-top:1px solid var(--border); }
  </style>
</head>
<body>
  <header class="hero">
    <div class="badge">AWS WAF Security Lab</div>
    <h1>Projeto 03</h1>
    <h2>Proteção contra SQL Injection</h2>
    <p>API Gateway REST + AWS Lambda</p>
  </header>
  <main>
    <section class="card">
      <h3>Sobre</h3>
      <p>Esta API Serverless demonstra como o AWS WAF bloqueia uma requisição
      contendo um padrão de SQL Injection antes que ela alcance a função Lambda.
      Não há banco de dados nem execução de SQL neste laboratório.</p>
    </section>
    <section class="card">
      <h3>Rotas</h3>
      <table>
        <tr><th>Rota</th><th>Descrição</th></tr>
        <tr><td><code>GET /health</code></td><td>Status de saúde da API.</td></tr>
        <tr><td><code>GET /produto?id=123</code></td><td>Ecoa o parâmetro id.</td></tr>
        <tr><td><code>GET /info</code></td><td>Esta página.</td></tr>
      </table>
    </section>
    <section class="card">
      <h3>Resultado esperado</h3>
      <table>
        <tr><th>Teste</th><th>SEM WAF</th><th>COM WAF</th></tr>
        <tr><td>Normal</td><td>Lambda executa (200)</td><td>Lambda executa (200)</td></tr>
        <tr><td>SQL Injection</td><td>Lambda executa (200)</td><td>WAF bloqueia (403)</td></tr>
      </table>
    </section>
  </main>
  <footer>AWS WAF Security Lab — Projeto 03 — API Gateway + Lambda — Laboratório educacional</footer>
</body>
</html>"""
    return _html_response(200, html)


def lambda_handler(event, context):
    method = _get_method(event)
    path = _get_path(event)
    query = _get_query(event)
    request_id = _get_request_id(event)

    # Log seguro: method, path, requestId e o valor de 'id' recebido.
    # Nunca registrar credenciais, tokens ou segredos.
    logger.info(json.dumps({
        "event": "request",
        "method": method,
        "path": path,
        "requestId": request_id,
        "id_param": query.get("id", ""),
    }, ensure_ascii=False))

    # Roteamento simples baseado no path.
    if path.endswith("/health"):
        return handle_health()
    if path.endswith("/produto"):
        return handle_produto(query)
    if path.endswith("/search"):
        return handle_search(query)
    if path.endswith("/info") or path == "/" or path.endswith("/"):
        return handle_info()

    return _json_response(404, {
        "status": "not_found",
        "path": path,
        "message": "Rota nao encontrada",
    })
