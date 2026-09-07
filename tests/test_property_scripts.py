"""Testes de propriedade (property-based com Hypothesis) da logica do script de teste.

Este arquivo concentra as Correctness Properties 8 e 9 do design do laboratorio
AWS WAF Security Lab 03, ambas relativas a logica pura do script de teste da API
(``tests/test-sqli.py``). Cada teste implementa exatamente UMA propriedade e a
referencia pela tag do design no docstring.

O script alvo tem hifen no nome (``test-sqli.py``), portanto e importado via
``importlib`` a partir do proprio diretorio deste arquivo de testes.

Propriedades cobertas:
  - Property 8: Scripts exigem parametros obrigatorios (tarefa 5.3).
  - Property 9: Codigo de saida agrega o veredito dos testes (tarefa 5.4).
"""

import importlib.util
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st


# --- Importacao do script alvo (nome com hifen) via importlib ---------------
_spec = importlib.util.spec_from_file_location(
    "test_sqli_script", Path(__file__).resolve().parent / "test-sqli.py"
)
test_sqli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(test_sqli)


# --- Property 8: Scripts exigem parametros obrigatorios (tarefa 5.3) --------
# Feature: aws-waf-lab-03-sqli, Property 8: Scripts exigem parametros obrigatorios
# Validates: Requirements 20.3


# Valores considerados "ausentes" para os parametros obrigatorios: None e as
# variacoes de string vazia (incluindo apenas espacos, que sao normalizados).
_MISSING_VALUES = st.sampled_from([None, "", "   ", "\t", "\n"])

# Valores considerados "presentes" (nao vazios) para a URL base.
_PRESENT_BASE_URL = st.text(min_size=1, max_size=128).filter(
    lambda s: s.strip() != ""
)

# Ambientes validos, presentes e aceitos por ``validate_args``.
_VALID_ENVIRONMENT = st.sampled_from(list(test_sqli.VALID_ENVIRONMENTS))


@settings(max_examples=200)
@given(
    base_url=st.one_of(_MISSING_VALUES, _PRESENT_BASE_URL),
    environment=st.one_of(_MISSING_VALUES, _VALID_ENVIRONMENT),
)
def test_property_8_scripts_exigem_parametros_obrigatorios(base_url, environment):
    """Feature: aws-waf-lab-03-sqli, Property 8: Scripts exigem parametros obrigatorios.

    Para qualquer invocacao em que falte ao menos um parametro obrigatorio
    (``base_url`` vazio/None ou ``environment`` vazio/None), ``validate_args``
    deve retornar uma lista NAO vazia, indicando o(s) parametro(s) ausente(s).
    Quando ambos estao presentes e o ``environment`` e valido, a lista deve ser
    vazia (parametros validos).

    Validates: Requirements 20.3
    """
    base_url_missing = base_url is None or str(base_url).strip() == ""
    environment_missing = environment is None or str(environment).strip() == ""

    errors = test_sqli.validate_args(base_url, environment)

    if base_url_missing or environment_missing:
        # Falta ao menos um parametro obrigatorio: deve haver erro reportado.
        assert errors, "Esperava lista de erros nao vazia para parametro ausente."
    else:
        # Ambos presentes e ambiente valido: parametros validos, sem erros.
        assert errors == [], "Esperava lista de erros vazia para parametros validos."


# --- Property 9: Codigo de saida agrega o veredito dos testes (tarefa 5.4) --
# Feature: aws-waf-lab-03-sqli, Property 9: Codigo de saida agrega o veredito dos testes
# Validates: Requirements 20.11


def _make_result(passed):
    """Cria um resultado de teste com o atributo ``passed`` informado.

    Reutiliza o namedtuple ``TestResult`` do script, preenchendo os demais campos
    com valores neutros que nao afetam a agregacao do codigo de saida.
    """
    return test_sqli.TestResult(
        name="teste",
        endpoint="https://exemplo.com/health",
        expected_status=200,
        received_status=200 if passed else 500,
        passed=passed,
        detail=None,
    )


@settings(max_examples=200)
@given(passed_flags=st.lists(st.booleans(), min_size=0, max_size=20))
def test_property_9_codigo_de_saida_agrega_o_veredito_dos_testes(passed_flags):
    """Feature: aws-waf-lab-03-sqli, Property 9: Codigo de saida agrega o veredito dos testes.

    Para qualquer conjunto de resultados, ``aggregate_exit_code`` retorna 0 se e
    somente se todos os testes forem aprovados (``passed=True``); caso contrario,
    retorna um codigo diferente de 0.

    Validates: Requirements 20.11
    """
    results = [_make_result(flag) for flag in passed_flags]

    exit_code = test_sqli.aggregate_exit_code(results)

    if all(passed_flags):
        # Lista vazia ou todos aprovados: codigo de saida 0.
        assert exit_code == 0
    else:
        # Ao menos um reprovado: codigo de saida diferente de 0.
        assert exit_code != 0
