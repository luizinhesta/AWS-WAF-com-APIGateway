"""Testes de propriedade (property-based com Hypothesis) do roteamento da Lambda.

Este arquivo concentra as Correctness Properties 1, 2 e 3 do design do laboratório
AWS WAF Security Lab 03, todas relativas ao roteamento interno da função Lambda
(``lambda_function.handler``). Cada teste implementa exatamente UMA propriedade e a
referencia pela tag do design no docstring.

O ``conftest.py`` adiciona ``lambda/`` ao ``sys.path``, portanto ``import
lambda_function`` funciona diretamente.

Propriedades cobertas:
  - Property 1: Eco idêntico nas rotas de eco (tarefa 3.3).
  - Property 2: Rotas indefinidas resultam em 404 (tarefa 3.6).
  - Property 3: Roteamento correto das rotas definidas (tarefa 3.7).
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

import lambda_function


# Conjunto de rotas definidas do laboratório (espelha ``lambda_function.ROUTES``).
DEFINED_ROUTES = ("/", "/health", "/produto", "/search", "/info")


def _build_event(method, path, query_params=None):
    """Monta um evento Lambda Proxy (formato REST API) para os testes.

    Usa ``httpMethod``, ``path`` e ``queryStringParameters``, conforme o contrato
    consumido pelo ``handler``.
    """
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_params,
    }


# --- Property 1: Eco idêntico nas rotas de eco (tarefa 3.3) ------------------
# Feature: aws-waf-lab-03-sqli, Property 1: Eco idêntico nas rotas de eco
# Validates: Requirements 3.1, 3.2, 4.1, 4.2


@settings(max_examples=200)
@given(
    value=st.text(min_size=1, max_size=4096),
    route_choice=st.sampled_from(
        [
            ("/produto", "id"),
            ("/search", "q"),
        ]
    ),
)
def test_property_1_eco_identico_nas_rotas_de_eco(value, route_choice):
    """Feature: aws-waf-lab-03-sqli, Property 1: Eco idêntico nas rotas de eco.

    Para qualquer string de 1 a 4096 caracteres passada como parâmetro de eco
    (``id`` em ``/produto`` ou ``q`` em ``/search``), a resposta HTTP 200 deve
    conter, no campo correspondente do corpo JSON, um valor idêntico caractere a
    caractere ao valor recebido, sem modificação, sanitização ou codificação
    adicional.

    Validates: Requirements 3.1, 3.2, 4.1, 4.2
    """
    path, param_name = route_choice
    event = _build_event("GET", path, {param_name: value})

    response = lambda_function.handler(event, None)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    # O valor ecoado deve ser idêntico caractere a caractere ao valor recebido.
    assert body[param_name] == value


# --- Property 2: Rotas indefinidas resultam em 404 (tarefa 3.6) -------------
# Feature: aws-waf-lab-03-sqli, Property 2: Rotas indefinidas resultam em 404
# Validates: Requirements 6.1, 6.2


def _normalizes_to_defined_route(path):
    """Indica se um ``path`` bruto normaliza para uma rota definida.

    Replica a normalização de ``lambda_function._normalize_path`` para garantir
    que a estratégia gere apenas caminhos que, após a normalização, NÃO pertençam
    ao conjunto de rotas definidas.
    """
    return lambda_function._normalize_path(path) in DEFINED_ROUTES


@settings(max_examples=200)
@given(
    path=st.text(min_size=0, max_size=64).filter(
        lambda p: not _normalizes_to_defined_route(p)
    )
)
def test_property_2_rotas_indefinidas_resultam_em_404(path):
    """Feature: aws-waf-lab-03-sqli, Property 2: Rotas indefinidas resultam em 404.

    Para qualquer caminho que não pertença ao conjunto de rotas definidas
    (``/``, ``/health``, ``/produto``, ``/search``, ``/info``), a Lambda deve
    responder com código HTTP 404 e um corpo JSON contendo uma mensagem
    descritiva de erro.

    Validates: Requirements 6.1, 6.2
    """
    event = _build_event("GET", path)

    response = lambda_function.handler(event, None)

    assert response["statusCode"] == 404
    assert response["headers"]["Content-Type"] == "application/json"

    body = json.loads(response["body"])
    # O corpo JSON deve trazer uma mensagem descritiva de erro (não vazia).
    assert isinstance(body.get("message"), str)
    assert body["message"].strip() != ""


# --- Property 3: Roteamento correto das rotas definidas (tarefa 3.7) --------
# Feature: aws-waf-lab-03-sqli, Property 3: Roteamento correto das rotas definidas
# Validates: Requirements 7.1, 7.2, 7.3


# Contrato esperado por rota definida: (status HTTP, Content-Type).
# /health, /produto, /search -> application/json 200.
# / e /info -> text/html 200.
ROUTE_CONTRACTS = {
    "/": (200, "text/html"),
    "/health": (200, "application/json"),
    "/produto": (200, "application/json"),
    "/search": (200, "application/json"),
    "/info": (200, "text/html"),
}


@settings(max_examples=200)
@given(
    route=st.sampled_from(list(ROUTE_CONTRACTS.keys())),
    method=st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]),
)
def test_property_3_roteamento_correto_das_rotas_definidas(route, method):
    """Feature: aws-waf-lab-03-sqli, Property 3: Roteamento correto das rotas definidas.

    Para qualquer requisição a uma rota definida do laboratório, a Lambda deve
    identificar o método HTTP e o caminho e direcionar o tratamento ao handler
    correspondente, produzindo o contrato de resposta esperado daquela rota
    (código HTTP e ``Content-Type`` corretos): ``/health``, ``/produto`` e
    ``/search`` em ``application/json`` 200; ``/`` e ``/info`` em ``text/html`` 200.

    Validates: Requirements 7.1, 7.2, 7.3
    """
    expected_status, expected_content_type = ROUTE_CONTRACTS[route]
    event = _build_event(method, route)

    response = lambda_function.handler(event, None)

    assert response["statusCode"] == expected_status
    assert response["headers"]["Content-Type"] == expected_content_type
