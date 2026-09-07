"""Property-based tests for Lambda CloudWatch logging (tasks 2.3 to 2.6).

Este arquivo concentra os testes de propriedade (Hypothesis) que validam o
comportamento do registro de log da Lambda (`lambda_function`), conforme as
Correctness Properties 4 a 7 do design.

Propriedades cobertas:
  - Property 4 (task 2.3): o log contém os campos obrigatorios (method, path,
    requestId).                                        -> Requirement 8.1
  - Property 5 (task 2.4): resiliencia do registro de log (falha do logger nao
    interrompe a resposta ao cliente).                 -> Requirement 8.2
  - Property 6 (task 2.5): truncamento de valores de parametros no log
    (maximo 256 caracteres).                           -> Requirement 8.3
  - Property 7 (task 2.6): ocultacao de campos sensiveis no log (valor
    registrado e o marcador, nunca o original).        -> Requirements 8.4, 8.5

Cada entrada de log e emitida via `logger.info(json.dumps(...))`. Os testes
capturam a saida do logger com `caplog` e desserializam o JSON registrado para
inspecionar os campos.
"""

import json
import logging
from unittest import mock

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import lambda_function


# Nome do logger usado pela Lambda (constante do modulo).
LOGGER_NAME = "aws-waf-lab-03-sqli"

# Configuracao padrao de PBT: no minimo 100 iteracoes por propriedade.
# `caplog` e um fixture com escopo de funcao, portanto suprimimos o
# HealthCheck.function_scoped_fixture (o uso aqui e intencional e seguro).
PBT_SETTINGS = settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def _build_event(method, path, query_params, request_id):
    """Monta um evento Lambda Proxy (formato REST API) minimo para os testes."""
    return {
        "httpMethod": method,
        "path": path,
        "queryStringParameters": query_params,
        "requestContext": {"requestId": request_id},
    }


def _extract_log_entries(caplog):
    """Recupera as entradas de log JSON emitidas pela Lambda durante o teste.

    A Lambda registra cada requisicao com `logger.info(json.dumps(entry))`.
    Este helper filtra apenas as mensagens do logger da Lambda que sao JSON
    validos e as desserializa em dicionarios.
    """
    entries = []
    for record in caplog.records:
        if record.name != LOGGER_NAME:
            continue
        try:
            entries.append(json.loads(record.getMessage()))
        except (ValueError, TypeError):
            # Mensagens nao-JSON (ex.: log de excecao) sao ignoradas aqui.
            continue
    return entries


# Estrategias reutilizaveis --------------------------------------------------

# Metodos HTTP comuns (o roteamento so usa GET, mas o log registra o metodo
# recebido, qualquer que seja).
_http_methods = st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"])

# Caminhos: mistura de rotas definidas e caminhos arbitrarios.
_paths = st.one_of(
    st.sampled_from(["/", "/health", "/produto", "/search", "/info", "/nao-existe"]),
    st.text(min_size=1, max_size=64),
)

# requestId: texto arbitrario (inclui vazio).
_request_ids = st.text(min_size=0, max_size=64)


# ---------------------------------------------------------------------------
# Feature: aws-waf-lab-03-sqli, Property 4: Log contém os campos obrigatórios
# Validates: Requirements 8.1
# ---------------------------------------------------------------------------
@PBT_SETTINGS
@given(method=_http_methods, path=_paths, request_id=_request_ids)
def test_property_4_log_contains_required_fields(caplog, method, path, request_id):
    """Feature: aws-waf-lab-03-sqli, Property 4: Log contém os campos obrigatórios.

    Para qualquer requisicao processada pela Lambda, a entrada de log gerada
    deve conter o metodo HTTP, o caminho da requisicao e o requestId.

    Validates: Requirements 8.1
    """
    event = _build_event(method, path, None, request_id)

    # `caplog` acumula registros entre iteracoes do Hypothesis; limpamos para
    # inspecionar apenas o log gerado por esta requisicao.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        lambda_function.handler(event, None)

    entries = _extract_log_entries(caplog)

    # Ao menos uma entrada de log deve ter sido gerada para a requisicao.
    assert entries, "nenhuma entrada de log foi registrada"

    entry = entries[0]
    # Os tres campos obrigatorios devem estar presentes.
    assert "method" in entry
    assert "path" in entry
    assert "requestId" in entry
    # E devem refletir os valores da requisicao.
    assert entry["method"] == method
    assert entry["requestId"] == request_id
    # O path registrado corresponde ao path normalizado pela Lambda.
    assert entry["path"] == lambda_function._normalize_path(path)


# ---------------------------------------------------------------------------
# Feature: aws-waf-lab-03-sqli, Property 5: Resiliência do registro de log
# Validates: Requirements 8.2
# ---------------------------------------------------------------------------
@PBT_SETTINGS
@given(
    method=_http_methods,
    path=st.sampled_from(["/", "/health", "/produto", "/search", "/info"]),
    request_id=_request_ids,
    param_value=st.text(min_size=0, max_size=64),
)
def test_property_5_logging_resilience(method, path, request_id, param_value):
    """Feature: aws-waf-lab-03-sqli, Property 5: Resiliência do registro de log.

    Para qualquer requisicao, mesmo quando o registro de log falha, a Lambda
    deve concluir o processamento e retornar uma resposta valida ao cliente,
    sem interrupcao.

    A falha do logger e forcada por um mock que faz `logger.info` lançar
    excecao a cada chamada.

    Validates: Requirements 8.2
    """
    event = _build_event(method, path, {"id": param_value}, request_id)

    # Forca o logger a lançar excecao em qualquer tentativa de registro.
    with mock.patch.object(
        lambda_function.logger, "info", side_effect=RuntimeError("logger indisponivel")
    ):
        response = lambda_function.handler(event, None)

    # A resposta deve ser valida no formato Lambda Proxy, apesar da falha no log.
    assert isinstance(response, dict)
    assert "statusCode" in response
    assert "headers" in response
    assert "body" in response
    # As rotas exercitadas sao todas definidas -> nunca 404/erro por causa do log.
    assert response["statusCode"] == 200


# ---------------------------------------------------------------------------
# Feature: aws-waf-lab-03-sqli, Property 6: Truncamento de valores de parâmetros no log
# Validates: Requirements 8.3
# ---------------------------------------------------------------------------
@PBT_SETTINGS
@given(
    param_name=st.text(min_size=1, max_size=32).filter(
        lambda n: not lambda_function._is_sensitive_param_name(n)
    ),
    param_value=st.text(min_size=0, max_size=1024),
)
def test_property_6_param_value_truncation(caplog, param_name, param_value):
    """Feature: aws-waf-lab-03-sqli, Property 6: Truncamento de valores de parâmetros no log.

    Para qualquer valor de parametro de query (nao sensivel), o valor
    registrado no log deve ter no maximo MAX_PARAM_VALUE_LENGTH (256)
    caracteres.

    Validates: Requirements 8.3
    """
    event = _build_event("GET", "/produto", {param_name: param_value}, "req-trunc")

    # Limpa registros acumulados de iteracoes anteriores do Hypothesis.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        lambda_function.handler(event, None)

    entries = _extract_log_entries(caplog)
    assert entries, "nenhuma entrada de log foi registrada"

    query_params = entries[0].get("queryParams", {})
    assert param_name in query_params

    logged_value = query_params[param_name]
    # O valor registrado nunca excede o limite maximo.
    assert len(logged_value) <= lambda_function.MAX_PARAM_VALUE_LENGTH
    # E deve ser exatamente o prefixo do valor original (truncamento simples).
    assert logged_value == param_value[: lambda_function.MAX_PARAM_VALUE_LENGTH]


# ---------------------------------------------------------------------------
# Feature: aws-waf-lab-03-sqli, Property 7: Ocultação de campos sensíveis no log
# Validates: Requirements 8.4, 8.5
# ---------------------------------------------------------------------------

# Fragmentos que tornam o nome de um parametro sensivel (Requisitos 8.4, 8.5).
_sensitive_fragments = st.sampled_from(lambda_function.SENSITIVE_NAME_FRAGMENTS)

# Afixos arbitrarios (podem ser vazios) usados para compor nomes sensiveis
# variados, como "user_token", "SENHA_admin", "x-authorization-y".
_affixes = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
    min_size=0,
    max_size=12,
)


@st.composite
def _sensitive_param_names(draw):
    """Gera nomes de parametro que contem um fragmento sensivel (case-insensitive)."""
    fragment = draw(_sensitive_fragments)
    prefix = draw(_affixes)
    suffix = draw(_affixes)
    # Varia a caixa do fragmento para exercitar a deteccao case-insensitive.
    case_choice = draw(st.sampled_from(["lower", "upper", "title"]))
    if case_choice == "upper":
        fragment = fragment.upper()
    elif case_choice == "title":
        fragment = fragment.capitalize()
    return prefix + fragment + suffix


@PBT_SETTINGS
@given(
    param_name=_sensitive_param_names(),
    # Valor original deliberadamente diferente do marcador de ocultacao.
    param_value=st.text(min_size=1, max_size=128).filter(
        lambda v: v != lambda_function.REDACTED_MARKER
    ),
)
def test_property_7_sensitive_field_redaction(caplog, param_name, param_value):
    """Feature: aws-waf-lab-03-sqli, Property 7: Ocultação de campos sensíveis no log.

    Para qualquer parametro cujo nome corresponda a um campo sensivel (token,
    senha, credencial, secret ou dado de autorizacao), o valor registrado no
    log deve ser o marcador de ocultacao, nunca o valor original.

    Validates: Requirements 8.4, 8.5
    """
    event = _build_event("GET", "/produto", {param_name: param_value}, "req-redact")

    # Limpa registros acumulados de iteracoes anteriores do Hypothesis.
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        lambda_function.handler(event, None)

    entries = _extract_log_entries(caplog)
    assert entries, "nenhuma entrada de log foi registrada"

    query_params = entries[0].get("queryParams", {})
    assert param_name in query_params

    logged_value = query_params[param_name]
    # O valor registrado para o parametro sensivel deve ser exatamente o
    # marcador de ocultacao, nunca o valor original (Requisitos 8.4, 8.5).
    assert logged_value == lambda_function.REDACTED_MARKER
    # Como o valor gerado e sempre diferente do marcador, o log nao expoe o
    # valor original: o unico valor registrado para o campo e o marcador.
    assert logged_value != param_value
