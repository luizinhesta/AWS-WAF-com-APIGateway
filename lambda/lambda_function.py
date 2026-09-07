"""AWS WAF Security Lab 03 — função Lambda única (integração Lambda Proxy).

Esta função trata TODAS as rotas do laboratório por meio de roteamento interno,
conforme o design (Requisitos 7 e 9.2). A mesma função é compartilhada pelos dois
stages (``sem-waf`` e ``com-waf``); a única diferença observável entre os ambientes
é a presença do AWS WAF no stage ``com-waf``.

Somente a biblioteca padrão do Python é utilizada (é uma Lambda), sem dependências
externas no código de runtime.

Escopo desta implementação (tarefa 2.1):
  - Extração de método HTTP e caminho (path) do evento Lambda Proxy (formato REST API).
  - Normalização do path para a rota relativa, independentemente do stage de origem.
  - Despachante (dispatcher) que direciona para o handler da rota correspondente
    e devolve 404 para rotas fora do conjunto definido.
  - Respostas sempre no formato Lambda Proxy (``statusCode``, ``headers``, ``body``).

O registro de log no CloudWatch (tarefa 2.2) já está implementado: cada requisição
gera uma entrada com ``method``, ``path``, ``requestId`` e os parâmetros de query,
com truncamento e ocultação de campos sensíveis, de forma não bloqueante (Requisito 8).

As rotas concretas (``/health``, ``/produto``, ``/search``, ``/`` e ``/info``) serão
completadas nas tarefas 3.x. Os handlers abaixo já respondem de forma mínima para que
o despacho funcione.
"""

import json
import logging

# Conjunto de rotas definidas do laboratório (Requisitos 7.3, 9.3).
# O dispatcher usa este mapeamento para direcionar cada rota ao seu handler.
# Rotas fora deste conjunto recebem 404 (Requisito 6).

# Cabeçalhos de Content-Type reutilizados pelos handlers.
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_HTML = "text/html"

# --- Configuração de logging (CloudWatch) -----------------------------------
# No ambiente Lambda, o runtime já direciona o logger raiz para o CloudWatch
# Logs (grupo /aws/lambda/{funcao}). Usamos um logger nomeado no nível INFO para
# registrar uma entrada por requisição (Requisito 8.1).
logger = logging.getLogger("aws-waf-lab-03-sqli")
logger.setLevel(logging.INFO)

# Limite de truncamento por valor de parâmetro de query no log (Requisito 8.3).
MAX_PARAM_VALUE_LENGTH = 256

# Marcador de ocultação para valores sensíveis (Requisitos 8.4, 8.5).
REDACTED_MARKER = "***REDACTED***"

# Fragmentos (substrings) que identificam parâmetros sensíveis pelo nome.
# A detecção é por correspondência de substring, case-insensitive (Requisito 8.5).
SENSITIVE_NAME_FRAGMENTS = (
    "token",
    "senha",
    "password",
    "credencial",
    "credential",
    "secret",
    "authorization",
)


def _is_sensitive_param_name(name):
    """Indica se o nome de um parâmetro corresponde a um campo sensível.

    A correspondência é por substring, case-insensitive, contra o conjunto
    ``SENSITIVE_NAME_FRAGMENTS`` (token, senha/password, credencial/credential,
    secret, authorization) — Requisitos 8.4 e 8.5.
    """
    lowered = str(name).lower()
    return any(fragment in lowered for fragment in SENSITIVE_NAME_FRAGMENTS)


def _sanitize_query_params(query_params):
    """Prepara os parâmetros de query para registro no log.

    Regras aplicadas:
      - parâmetros sensíveis têm o valor substituído pelo marcador de ocultação
        (Requisitos 8.4, 8.5);
      - os demais valores são truncados a ``MAX_PARAM_VALUE_LENGTH`` caracteres
        (Requisito 8.3).

    ``query_params`` igual a ``None`` (evento sem ``queryStringParameters``) é
    tratado sem lançar exceção, retornando um dicionário vazio.
    """
    if not query_params:
        return {}

    sanitized = {}
    for name, value in query_params.items():
        if _is_sensitive_param_name(name):
            sanitized[name] = REDACTED_MARKER
            continue
        # Normaliza para string antes de truncar (valores podem não ser string).
        text_value = value if isinstance(value, str) else str(value)
        sanitized[name] = text_value[:MAX_PARAM_VALUE_LENGTH]
    return sanitized


def _log_request(event, method, path):
    """Registra no CloudWatch uma entrada de log por requisição (Requisito 8).

    A entrada contém ``method``, ``path`` e ``requestId`` (de
    ``requestContext.requestId``) além dos parâmetros de query, com truncamento
    (Requisito 8.3) e ocultação de campos sensíveis (Requisitos 8.4, 8.5).

    O registro é NÃO BLOQUEANTE: qualquer falha do logger é capturada e o
    processamento da requisição continua normalmente (Requisito 8.2).
    """
    try:
        request_context = event.get("requestContext") or {}
        request_id = request_context.get("requestId", "")

        query_params = _sanitize_query_params(event.get("queryStringParameters"))

        log_entry = {
            "method": method,
            "path": path,
            "requestId": request_id,
            "queryParams": query_params,
        }
        logger.info(json.dumps(log_entry, ensure_ascii=False))
    except Exception:  # noqa: BLE001 — log é observacional e não pode derrubar a resposta.
        # Falha no registro de log não deve interromper a resposta ao cliente
        # (Requisito 8.2). Tentamos apenas registrar a exceção, também de forma
        # protegida, para não propagar erros.
        try:
            logger.exception("Falha ao registrar log da requisicao")
        except Exception:  # noqa: BLE001
            pass


def _json_response(status_code, payload, headers=None):
    """Monta uma resposta Lambda Proxy com corpo JSON serializado.

    ``ensure_ascii=False`` preserva os valores recebidos caractere a caractere
    (importante para o eco idêntico exigido pela rota ``/produto`` — Requisito 3.1).
    """
    response_headers = {"Content-Type": CONTENT_TYPE_JSON}
    if headers:
        response_headers.update(headers)
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _html_response(status_code, html, headers=None):
    """Monta uma resposta Lambda Proxy com corpo HTML."""
    response_headers = {"Content-Type": CONTENT_TYPE_HTML}
    if headers:
        response_headers.update(headers)
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": html,
    }


def _extract_method(event):
    """Extrai o método HTTP do evento Lambda Proxy (Requisito 7.1).

    Usa ``httpMethod`` (formato REST API). Retorna string vazia quando ausente.
    """
    method = event.get("httpMethod")
    return method if isinstance(method, str) else ""


def _extract_path(event):
    """Extrai o caminho (path) do evento Lambda Proxy (Requisito 7.2).

    Usa ``path`` (formato REST API). Retorna string vazia quando ausente.
    """
    path = event.get("path")
    return path if isinstance(path, str) else ""


def _normalize_path(path):
    """Normaliza o path para a rota relativa do laboratório.

    Com Custom Domain e mapeamento de stage, o ``path`` recebido pela Lambda já
    representa a rota relativa (ex.: ``/produto``), independentemente do stage de
    origem. Ainda assim, normalizamos de forma defensiva:
      - garante que a rota comece com ``/``;
      - remove barra final redundante, preservando a raiz ``/``.
    """
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    # Remove barra final redundante, mas mantém a raiz ("/").
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
        if path == "":
            path = "/"
    return path


# --- Página HTML informativa (rotas / e /info) ------------------------------
# Página explicativa e didática do laboratório. Contém obrigatoriamente os
# textos exigidos pelo Requisito 5.3: "AWS WAF Security Lab 03", "API Gateway",
# "Lambda", "SQL Injection", "ambiente SEM WAF" e "ambiente COM WAF".
_INFO_PAGE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AWS WAF Security Lab 03</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; line-height: 1.6; margin: 0; padding: 2rem; color: #1b1b1b; background: #f5f7fa; }
    main { max-width: 820px; margin: 0 auto; background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }
    h1 { color: #232f3e; }
    h2 { color: #d13212; margin-top: 2rem; }
    code { background: #eef1f5; padding: .15rem .35rem; border-radius: 4px; }
    .env { display: flex; gap: 1rem; flex-wrap: wrap; }
    .card { flex: 1 1 260px; border: 1px solid #d5dbdb; border-radius: 6px; padding: 1rem; }
    ul { padding-left: 1.25rem; }
  </style>
</head>
<body>
  <main>
    <h1>AWS WAF Security Lab 03</h1>
    <p>
      Laboratório educacional que demonstra, de forma prática, a diferença de
      comportamento entre uma API protegida e uma API desprotegida contra
      <strong>SQL Injection</strong>. A arquitetura usa o <strong>API Gateway</strong>
      (REST) integrado por Lambda Proxy a uma única função <strong>Lambda</strong> em Python.
    </p>

    <h2>Como funciona</h2>
    <p>
      A mesma <strong>API Gateway</strong> e a mesma <strong>Lambda</strong> atendem os
      dois ambientes. A única diferença observável é a presença do AWS WAF. A rota
      <code>/produto</code> apenas ecoa o parâmetro recebido: não há banco de dados e
      nenhum comando SQL é executado. A requisição de <strong>SQL Injection</strong> de
      teste serve somente para acionar a inspeção do WAF.
    </p>

    <div class="env">
      <div class="card">
        <h3>ambiente SEM WAF</h3>
        <p>
          Grupo de controle. A requisição de <strong>SQL Injection</strong> de teste
          chega à <strong>Lambda</strong> e recebe HTTP 200 com o valor ecoado.
        </p>
      </div>
      <div class="card">
        <h3>ambiente COM WAF</h3>
        <p>
          Grupo protegido. O AWS WAF bloqueia a requisição de <strong>SQL Injection</strong>
          de teste com HTTP 403, antes de alcançar a <strong>Lambda</strong>.
        </p>
      </div>
    </div>

    <h2>Rotas disponíveis</h2>
    <ul>
      <li><code>GET /health</code> — verificação de saúde (JSON).</li>
      <li><code>GET /produto?id=...</code> — ecoa o parâmetro <code>id</code> (JSON).</li>
      <li><code>GET /search?q=...</code> — ecoa o parâmetro <code>q</code> (JSON).</li>
      <li><code>GET /</code> e <code>GET /info</code> — esta página informativa (HTML).</li>
    </ul>
  </main>
</body>
</html>"""


# --- Handlers de rota -------------------------------------------------------
# Cada handler recebe o evento Lambda Proxy e devolve uma resposta Lambda Proxy
# (statusCode, headers, body), mantendo a assinatura handler(event).


def _get_query_param(event, name):
    """Lê um parâmetro de query do evento Lambda Proxy sem lançar exceção.

    Trata ``queryStringParameters`` igual a ``None`` (evento sem parâmetros)
    retornando string vazia, conforme o comportamento defensivo exigido pelas
    rotas de eco (Requisitos 3.3, 4.x). Quando o parâmetro está presente, o
    valor é retornado sem qualquer modificação, para preservar o eco idêntico
    caractere a caractere (Requisitos 3.1, 4.1).
    """
    query_params = event.get("queryStringParameters")
    if not query_params:
        return ""
    value = query_params.get(name)
    return value if value is not None else ""


def _handle_health(event):
    """GET /health — health check da API/Lambda (Requisitos 2.1, 2.2).

    Responde HTTP 200 com o corpo JSON fixo do laboratório e
    ``Content-Type: application/json``.
    """
    return _json_response(200, {"status": "healthy", "project": "AWS WAF Security Lab 03"})


def _handle_produto(event):
    """GET /produto — ecoa o parâmetro ``id`` (Requisitos 3.1, 3.2, 3.3, 3.4, 3.5).

    Regras:
      - o valor de ``id`` é ecoado idêntico, caractere a caractere, sem
        modificação, sanitização ou codificação adicional (Requisito 3.1);
      - sem o parâmetro ``id`` (ou com ``queryStringParameters`` igual a
        ``None``), retorna ``{"id":""}`` (Requisito 3.3);
      - nenhum SQL é executado, nenhuma conexão de banco é aberta e nenhum
        serviço de persistência é chamado — a rota apenas ecoa (Requisito 3.5).

    ``_json_response`` usa ``ensure_ascii=False``, preservando o valor recebido.
    """
    produto_id = _get_query_param(event, "id")
    return _json_response(200, {"id": produto_id})


def _handle_search(event):
    """GET /search — ecoa o parâmetro ``q`` (Requisitos 4.1, 4.2).

    Sem o parâmetro ``q`` (ou com ``queryStringParameters`` igual a ``None``),
    retorna ``{"q":""}``. O valor é ecoado sem modificação.
    """
    query = _get_query_param(event, "q")
    return _json_response(200, {"q": query})


def _handle_info(event):
    """GET / e GET /info — página HTML explicativa (Requisitos 5.1, 5.2, 5.3, 5.4).

    Responde HTTP 200 com ``Content-Type: text/html`` e inclui os textos
    obrigatórios exigidos pelo Requisito 5.3.
    """
    return _html_response(200, _INFO_PAGE_HTML)


def _handle_not_found(event, path):
    """Rota não definida — resposta 404 descritiva (Requisitos 6.1, 6.2).

    Responde HTTP 404 com corpo JSON contendo os campos ``error`` e ``message``
    e ``Content-Type: application/json``. A mensagem descreve a rota solicitada
    e as rotas disponíveis, ajudando a diferenciar um erro de rota (404 da
    Lambda) de um bloqueio do WAF (403 da Web ACL).
    """
    known_routes = ", ".join(sorted(ROUTES.keys()))
    message = (
        "Rota nao encontrada: {}. Rotas disponiveis: {}.".format(path, known_routes)
    )
    return _json_response(404, {"error": "Not Found", "message": message})


# Mapa de despacho: rota relativa -> handler correspondente (Requisito 7.3).
# As rotas ``/`` e ``/info`` compartilham o mesmo handler de páginas HTML.
ROUTES = {
    "/": _handle_info,
    "/health": _handle_health,
    "/produto": _handle_produto,
    "/search": _handle_search,
    "/info": _handle_info,
}


def _dispatch(event, path):
    """Despacha para o handler da rota correspondente ou devolve 404.

    Direciona o tratamento para a resposta correspondente à rota (Requisito 7.3).
    Rotas fora do conjunto definido recebem 404 (Requisitos 6.1, 6.2).
    """
    handler = ROUTES.get(path)
    if handler is None:
        return _handle_not_found(event, path)
    return handler(event)


def handler(event, context=None):
    """Ponto de entrada da Lambda (integração Lambda Proxy).

    Fluxo:
      1. Extrai o método HTTP e o caminho do evento (Requisitos 7.1, 7.2).
      2. Normaliza o path para a rota relativa (independe do stage de origem).
      3. Registra o log da requisição no CloudWatch — a implementar na tarefa 2.2
         (Requisito 8). Ponto de extensão marcado abaixo.
      4. Despacha para o handler da rota e retorna no formato Lambda Proxy.
    """
    if event is None:
        event = {}

    method = _extract_method(event)
    path = _normalize_path(_extract_path(event))

    # Registra o log da requisição no CloudWatch (method, path, requestId e
    # parâmetros de query, com truncamento e ocultação). O registro é não
    # bloqueante: falhas são tratadas internamente (Requisito 8.2).
    _log_request(event, method, path)

    return _dispatch(event, path)


# Alias de compatibilidade com a convenção comum de nome de handler da AWS
# (``lambda_function.lambda_handler``) usada no guia IMPLANTACAO.md. Aponta para
# a mesma função ``handler`` (ponto de entrada real), de modo que tanto
# ``lambda_function.handler`` (usado pelos testes) quanto
# ``lambda_function.lambda_handler`` (Console/documentação) funcionem.
lambda_handler = handler
