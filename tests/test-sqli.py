#!/usr/bin/env python3
"""Script de teste da API do laboratorio AWS WAF Security Lab 03 (SQL Injection).

Este script executa um conjunto reduzido de requisicoes HTTP contra os endpoints
do laboratorio para comparar o comportamento dos ambientes ``sem-waf`` e
``com-waf``. Ele usa apenas a biblioteca padrao do Python (``urllib``) para nao
exigir dependencias extras, e ``argparse`` para os parametros de linha de comando.

Uso responsavel (Requisito 21): o script envia um numero reduzido de requisicoes,
somente aos endpoints do laboratorio, sem loops de repeticao continua, sem testes
de stress, sem flood e sem DDoS.

Comportamento por ambiente:
  - ``sem-waf``:
      * ``GET /health``                     -> esperado HTTP 200
      * ``GET /produto?id=1``               -> esperado HTTP 200
      * SQL Injection de teste (`/produto`) -> esperado HTTP 200
  - ``com-waf`` (origem no Brasil):
      * ``GET /health``                     -> esperado HTTP 200
      * ``GET /produto?id=1``               -> esperado HTTP 200
      * SQL Injection de teste (`/produto`) -> esperado HTTP 403 (bloqueado pelo WAF)

A funcao ``build_test_plan`` centraliza a lista de testes por ambiente para que a
tarefa 5.2 (bloco de teste geografico) possa reutiliza-la nas duas origens
(Brasil e fora do Brasil). As funcoes ``validate_args`` e ``aggregate_exit_code``
sao expostas de forma importavel para os testes de propriedade (tarefas 5.3/5.4).

Requisitos: 20.1, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.10, 20.11,
            21.1, 21.2, 21.3.
"""

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple


# --- Constantes do laboratorio ---------------------------------------------

# Ambientes validos (nomes dos stages da REST API).
ENV_SEM_WAF = "sem-waf"
ENV_COM_WAF = "com-waf"
VALID_ENVIRONMENTS = (ENV_SEM_WAF, ENV_COM_WAF)

# Timeout por requisicao, em segundos (Requisito 20.8).
REQUEST_TIMEOUT_SECONDS = 30

# Payload de SQL Injection usado apenas para acionar a inspecao do WAF.
# Nao representa vulnerabilidade real: a rota /produto apenas ecoa o parametro.
SQLI_TEST_PAYLOAD = "1' OR '1'='1"


# --- Estruturas de dados ----------------------------------------------------

# Descreve um teste a ser executado: um nome legivel, o caminho relativo do
# endpoint (com query string quando aplicavel) e o codigo HTTP esperado.
TestCase = namedtuple("TestCase", ["name", "path", "expected_status"])

# Resultado de um teste executado, usado para a apresentacao e a agregacao do
# codigo de saida. ``passed`` indica o veredito (aprovado/reprovado); ``detail``
# traz a causa da falha (ex.: timeout/conexao) quando houver.
TestResult = namedtuple(
    "TestResult",
    ["name", "endpoint", "expected_status", "received_status", "passed", "detail"],
)


# --- Validacao de parametros (Requisito 20.3) -------------------------------


def validate_args(base_url, environment):
    """Valida os parametros obrigatorios do script.

    Retorna uma lista de mensagens de erro (em pt-BR). A lista vazia indica que
    os parametros sao validos. Esta funcao e pura (sem efeitos colaterais) para
    ser reutilizada pelos testes de propriedade (Property 8).

    Sao obrigatorios a URL base do endpoint alvo (``base_url``) e o identificador
    de ambiente (``environment``), que deve ser ``sem-waf`` ou ``com-waf``.
    """
    errors = []

    if base_url is None or str(base_url).strip() == "":
        errors.append("Parametro obrigatorio ausente: URL base do endpoint alvo (--base-url).")

    if environment is None or str(environment).strip() == "":
        errors.append("Parametro obrigatorio ausente: identificador de ambiente (--env: sem-waf ou com-waf).")
    elif environment not in VALID_ENVIRONMENTS:
        errors.append(
            "Identificador de ambiente invalido: '{}'. Use 'sem-waf' ou 'com-waf'.".format(environment)
        )

    return errors


# --- Plano de testes por ambiente -------------------------------------------


def build_test_plan(environment):
    """Monta a lista de ``TestCase`` para o ambiente informado.

    Centraliza os testes por ambiente para permitir o reuso pela tarefa 5.2
    (bloco de teste geografico), que executa o mesmo conjunto a partir de origem
    no Brasil e de origem fora do Brasil.

    - ``sem-waf``: /health 200, /produto 200 e SQL Injection de teste 200.
    - ``com-waf`` (origem Brasil): /health 200, /produto 200 e SQL Injection
      de teste 403 (bloqueado pela regra de SQLi do WAF).
    """
    # A SQL Injection de teste e sempre enviada para /produto via parametro id.
    sqli_path = "/produto?id=" + _url_encode(SQLI_TEST_PAYLOAD)

    if environment == ENV_SEM_WAF:
        return [
            TestCase("Health check", "/health", 200),
            TestCase("Produto (parametro simples)", "/produto?id=1", 200),
            TestCase("SQL Injection de teste", sqli_path, 200),
        ]

    if environment == ENV_COM_WAF:
        return [
            TestCase("Health check", "/health", 200),
            TestCase("Produto (parametro simples)", "/produto?id=1", 200),
            # No ambiente protegido e a partir do Brasil, o WAF bloqueia a SQLi.
            TestCase("SQL Injection de teste", sqli_path, 403),
        ]

    # Nunca deve ocorrer: os argumentos ja foram validados por validate_args.
    raise ValueError("Ambiente desconhecido: {}".format(environment))


def _url_encode(value):
    """Codifica um valor para uso seguro em query string."""
    return urllib.parse.quote(value, safe="")


# --- Execucao das requisicoes -----------------------------------------------


def perform_request(url, timeout=REQUEST_TIMEOUT_SECONDS):
    """Executa uma requisicao GET e retorna ``(status, error_detail)``.

    ``status`` e o codigo HTTP recebido (inclui codigos de erro como 403 e 404,
    que sao respostas HTTP validas). ``error_detail`` traz a causa quando houver
    falha de conexao ou timeout; nesse caso ``status`` e ``None``.

    Timeout e falha de conexao nao interrompem a execucao: sao reportados ao
    chamador para que o teste seja marcado como falha e os demais prossigam
    (Requisito 20.8).
    """
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.getcode(), None
    except urllib.error.HTTPError as exc:
        # Respostas HTTP com codigo de erro (403, 404, ...) chegam por aqui e sao
        # respostas validas para efeito de verificacao.
        return exc.code, None
    except urllib.error.URLError as exc:
        # Falha de conexao (DNS, recusa, TLS) ou timeout de socket.
        return None, "Falha de conexao: {}".format(exc.reason)
    except TimeoutError:
        return None, "Timeout apos {}s".format(timeout)
    except Exception as exc:  # noqa: BLE001 - relatar qualquer falha sem parar os demais
        return None, "Erro inesperado: {}".format(exc)


def run_test(base_url, test_case, timeout=REQUEST_TIMEOUT_SECONDS):
    """Executa um unico ``TestCase`` e retorna um ``TestResult``.

    Monta a URL absoluta a partir da ``base_url`` e do caminho do teste, executa
    a requisicao e compara o codigo recebido com o esperado. Falhas de conexao ou
    timeout marcam o teste como reprovado, registrando o endpoint e a causa.
    """
    endpoint = _join_url(base_url, test_case.path)
    received_status, error_detail = perform_request(endpoint, timeout=timeout)

    if received_status is None:
        # Falha de conexao ou timeout: teste reprovado, com a causa registrada.
        return TestResult(
            name=test_case.name,
            endpoint=endpoint,
            expected_status=test_case.expected_status,
            received_status=None,
            passed=False,
            detail=error_detail,
        )

    passed = received_status == test_case.expected_status
    return TestResult(
        name=test_case.name,
        endpoint=endpoint,
        expected_status=test_case.expected_status,
        received_status=received_status,
        passed=passed,
        detail=None,
    )


def run_test_plan(base_url, test_cases, timeout=REQUEST_TIMEOUT_SECONDS):
    """Executa uma lista de ``TestCase`` e retorna a lista de ``TestResult``.

    Todos os testes sao executados; uma falha de conexao/timeout em um teste nao
    interrompe os demais (Requisito 20.8).
    """
    return [run_test(base_url, test_case, timeout=timeout) for test_case in test_cases]


def _join_url(base_url, path):
    """Concatena a URL base com o caminho relativo evitando barras duplicadas."""
    return base_url.rstrip("/") + "/" + path.lstrip("/")


# --- Apresentacao e agregacao (Requisitos 20.10, 20.11) ---------------------


def format_result_line(result):
    """Formata uma linha de resultado para exibicao (Requisito 20.10).

    Apresenta o endpoint testado, o codigo HTTP recebido, o esperado e o veredito.
    """
    verdict = "APROVADO" if result.passed else "REPROVADO"
    received = result.received_status if result.received_status is not None else "sem resposta"
    line = (
        "[{verdict}] {name}\n"
        "    Endpoint: {endpoint}\n"
        "    HTTP recebido: {received} | HTTP esperado: {expected}"
    ).format(
        verdict=verdict,
        name=result.name,
        endpoint=result.endpoint,
        received=received,
        expected=result.expected_status,
    )
    if result.detail:
        line += "\n    Causa: {}".format(result.detail)
    return line


def print_results(results, header=None):
    """Imprime um bloco de resultados, com cabecalho opcional.

    O ``header`` permite identificar blocos (ex.: origem "Brasil" ou "Fora do
    Brasil") para o teste geografico da tarefa 5.2.
    """
    if header:
        print("=" * 60)
        print(header)
        print("=" * 60)
    for result in results:
        print(format_result_line(result))
        print("-" * 60)


def aggregate_exit_code(results):
    """Agrega o veredito dos testes em um codigo de saida (Requisito 20.11).

    Retorna 0 se e somente se todos os testes forem aprovados; caso contrario,
    retorna 1. Funcao pura para reuso pelos testes de propriedade (Property 9).
    """
    if all(result.passed for result in results):
        return 0
    return 1


# --- Bloco de teste geografico (Requisito 20.9) -----------------------------

# Identificadores das duas origens geograficas do teste. A origem real e
# determinada pela AWS a partir do IP de quem executa o script; o script NAO
# forja nem simula a origem. Cada rotulo apenas identifica o bloco de saida.
GEO_ORIGIN_BRAZIL = "Origem no Brasil"
GEO_ORIGIN_OUTSIDE = "Origem fora do Brasil"


def build_geo_note(environment, origin_label):
    """Descreve o comportamento esperado de cada bloco geografico (Requisito 20.9).

    A origem geografica e determinada pela AWS a partir do endereco de origem
    (IP), portanto o script nao consegue forjar a origem: ele apenas executa as
    requisicoes reais e identifica, no cabecalho de cada bloco, o que se espera
    quando o script e realmente executado a partir daquela origem.

    - ``com-waf`` + fora do Brasil: espera-se HTTP 403 pela regra
      ``Block-Fora-do-Brasil`` (a requisicao nem chega a inspecao de SQLi).
    - ``com-waf`` + Brasil: comportamento normal (`/health` e `/produto` 200) e
      a SQL Injection de teste bloqueada com HTTP 403 pela regra de SQLi.
    - ``sem-waf``: nao ha WAF associado, portanto a origem geografica nao altera
      o comportamento; ambos os blocos tendem ao mesmo resultado.
    """
    if environment == ENV_COM_WAF:
        if origin_label == GEO_ORIGIN_OUTSIDE:
            return (
                "Observacao: no ambiente com-waf, requisicoes de fora do Brasil "
                "devem ser bloqueadas com HTTP 403 pela regra Block-Fora-do-Brasil, "
                "antes mesmo da inspecao de SQLi. Os codigos esperados abaixo "
                "referem-se ao comportamento do Brasil; execute este bloco a partir "
                "de fora do Brasil para observar o bloqueio geografico."
            )
        return (
            "Observacao: no ambiente com-waf, requisicoes do Brasil seguem o "
            "comportamento normal (/health e /produto com HTTP 200) e a SQL "
            "Injection de teste e bloqueada com HTTP 403 pela regra Block-SQLi-Lab."
        )

    # sem-waf: sem WAF associado, a origem geografica nao altera o resultado.
    return (
        "Observacao: o ambiente sem-waf nao possui WAF associado, portanto a "
        "origem geografica nao altera o comportamento; ambos os blocos tendem ao "
        "mesmo resultado."
    )


def run_geo_test(base_url, environment, timeout=REQUEST_TIMEOUT_SECONDS):
    """Executa o conjunto de testes para as duas origens geograficas (Requisito 20.9).

    Roda o mesmo plano de testes duas vezes, apresentando os resultados em dois
    blocos separados e identificados: "Origem no Brasil" e "Origem fora do
    Brasil". Reutiliza ``build_test_plan``, ``run_test_plan`` e ``print_results``.

    Importante: a origem geografica real e definida pela AWS a partir do IP de
    quem executa o script. O script nao forja a origem; ele executa as
    requisicoes reais e identifica, em cada bloco, o comportamento esperado
    daquela origem. Assim, o resultado observado depende de onde o script e
    efetivamente executado.

    Retorna a lista combinada de ``TestResult`` das duas execucoes para que o
    ``main`` agregue o codigo de saida (Requisito 20.11).
    """
    test_cases = build_test_plan(environment)
    combined_results = []

    for origin_label in (GEO_ORIGIN_BRAZIL, GEO_ORIGIN_OUTSIDE):
        header = "Teste geografico ({}) - ambiente: {}".format(origin_label, environment)
        print("=" * 60)
        print(header)
        print(build_geo_note(environment, origin_label))
        print("=" * 60)

        results = run_test_plan(base_url, test_cases, timeout=timeout)
        # Sem cabecalho aqui: o cabecalho identificado do bloco ja foi impresso
        # acima junto da observacao explicativa daquela origem.
        print_results(results, header=None)

        combined_results.extend(results)

    return combined_results


# --- Interface de linha de comando ------------------------------------------


def build_arg_parser():
    """Cria o ``ArgumentParser`` com os parametros do script."""
    parser = argparse.ArgumentParser(
        description=(
            "Testa a API do laboratorio AWS WAF Security Lab 03 comparando os "
            "ambientes sem-waf e com-waf (uso responsavel, poucas requisicoes)."
        )
    )
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="URL base do endpoint alvo (obrigatorio). Ex.: https://api-sem-waf.exemplo.com",
    )
    parser.add_argument(
        "--env",
        dest="environment",
        default=None,
        help="Identificador de ambiente (obrigatorio): 'sem-waf' ou 'com-waf'.",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=REQUEST_TIMEOUT_SECONDS,
        help="Timeout por requisicao em segundos (padrao: {}).".format(REQUEST_TIMEOUT_SECONDS),
    )
    parser.add_argument(
        "--geo",
        dest="geo",
        action="store_true",
        default=False,
        help=(
            "Aciona o teste geografico (Requisito 20.9): executa o conjunto de "
            "requisicoes em dois blocos separados e identificados, um para "
            "'Origem no Brasil' e outro para 'Origem fora do Brasil'. A origem "
            "real e determinada pela AWS a partir do IP; o script nao a forja."
        ),
    )
    return parser


def main(argv=None):
    """Ponto de entrada do script. Retorna o codigo de saida.

    Retorna codigo diferente de 0 quando faltar parametro obrigatorio (exibindo
    quais faltam) ou quando ao menos um teste for reprovado; retorna 0 quando
    todos os testes forem aprovados.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # Validacao dos parametros obrigatorios (Requisito 20.3).
    errors = validate_args(args.base_url, args.environment)
    if errors:
        print("Erro: parametros obrigatorios ausentes ou invalidos.", file=sys.stderr)
        for error in errors:
            print("  - " + error, file=sys.stderr)
        parser.print_usage(sys.stderr)
        return 2

    # Modo geografico (Requisito 20.9): executa o conjunto em dois blocos
    # separados e identificados (Brasil e fora do Brasil). Caso contrario,
    # executa o plano padrao do ambiente informado.
    if args.geo:
        results = run_geo_test(args.base_url, args.environment, timeout=args.timeout)
    else:
        test_cases = build_test_plan(args.environment)
        header = "Testes do ambiente: {}".format(args.environment)
        results = run_test_plan(args.base_url, test_cases, timeout=args.timeout)
        print_results(results, header=header)

    exit_code = aggregate_exit_code(results)
    total = len(results)
    approved = sum(1 for r in results if r.passed)
    print("Resumo: {}/{} testes aprovados.".format(approved, total))
    if exit_code == 0:
        print("Resultado geral: TODOS OS TESTES APROVADOS.")
    else:
        print("Resultado geral: HA TESTES REPROVADOS.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
