"""Testes unitários das rotas da Lambda (tarefa 3.8).

Estes testes cobrem exemplos concretos e edge cases das rotas tratadas pela
função ``handler`` de ``lambda/lambda_function.py`` no formato Lambda Proxy.

Rotas e requisitos cobertos:
  - ``/health``  -> Requisitos 2.1, 2.2
  - ``/produto`` -> Requisitos 3.2, 3.3
  - ``/search``  -> Requisitos 4.1, 4.2 (apoio à tarefa)
  - ``/`` e ``/info`` -> Requisitos 5.1, 5.2, 5.3, 5.4
  - rota inexistente (404) -> Requisitos 6.1, 6.2

O arquivo é dedicado aos testes unitários para evitar conflito com os testes de
propriedade (Hypothesis) criados em outros arquivos.
"""

import json

import lambda_function


def _build_event(method, path, query_string_parameters=None):
    """Monta um evento mínimo no formato Lambda Proxy (REST API).

    ``queryStringParameters`` pode ser ``None`` (evento sem parâmetros), como
    ocorre em requisições sem query string na integração Lambda Proxy.
    """
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_string_parameters,
        "requestContext": {"requestId": "test-request-id"},
    }


# --- /health (Requisitos 2.1, 2.2) ------------------------------------------


def test_health_retorna_200_e_json_fixo():
    """GET /health responde 200 com o corpo JSON fixo do laboratório."""
    response = lambda_function.handler(_build_event("GET", "/health"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    assert body == {"status": "healthy", "project": "AWS WAF Security Lab 03"}


# --- /produto (Requisitos 3.2, 3.3) -----------------------------------------


def test_produto_com_id_ecoa_valor():
    """GET /produto?id=123 responde 200 com o corpo JSON {"id":"123"}."""
    event = _build_event("GET", "/produto", {"id": "123"})
    response = lambda_function.handler(event, None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    assert body == {"id": "123"}


def test_produto_sem_id_retorna_string_vazia():
    """Edge case: GET /produto sem o parâmetro id retorna {"id":""}."""
    # Evento sem parâmetros de query (queryStringParameters é None).
    response = lambda_function.handler(_build_event("GET", "/produto"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    assert body == {"id": ""}


# --- /search (Requisitos 4.1, 4.2) ------------------------------------------


def test_search_com_q_ecoa_valor():
    """GET /search?q=teste responde com o corpo JSON contendo q="teste"."""
    event = _build_event("GET", "/search", {"q": "teste"})
    response = lambda_function.handler(event, None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    assert body == {"q": "teste"}


# --- Páginas HTML / e /info (Requisitos 5.1, 5.2, 5.3, 5.4) -----------------

# Textos obrigatórios que devem estar presentes no HTML (Requisito 5.3).
REQUIRED_HTML_TEXTS = (
    "AWS WAF Security Lab 03",
    "API Gateway",
    "Lambda",
    "SQL Injection",
    "ambiente SEM WAF",
    "ambiente COM WAF",
)


def test_raiz_retorna_html_com_todos_os_textos():
    """GET / responde 200, Content-Type text/html e contém todos os textos."""
    response = lambda_function.handler(_build_event("GET", "/"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/html"

    html = response["body"]
    for text in REQUIRED_HTML_TEXTS:
        assert text in html, "Texto obrigatorio ausente no HTML: {}".format(text)


def test_info_retorna_html_com_todos_os_textos():
    """GET /info responde 200, Content-Type text/html e contém todos os textos."""
    response = lambda_function.handler(_build_event("GET", "/info"), None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "text/html"

    html = response["body"]
    for text in REQUIRED_HTML_TEXTS:
        assert text in html, "Texto obrigatorio ausente no HTML: {}".format(text)


# --- Rota inexistente / 404 (Requisitos 6.1, 6.2) ---------------------------


def test_rota_inexistente_retorna_404_json():
    """Rota não definida responde 404 com corpo JSON descritivo."""
    response = lambda_function.handler(_build_event("GET", "/naoexiste"), None)

    assert response["statusCode"] == 404
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    assert body["error"] == "Not Found"
    # A mensagem deve existir e ser descritiva (não vazia).
    assert "message" in body
    assert isinstance(body["message"], str)
    assert body["message"] != ""
