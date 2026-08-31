#!/usr/bin/env python3
"""
AWS WAF Security Lab - Projeto 03 (SQL Injection)
Teste controlado de deteccao de SQL Injection pelo AWS WAF.

O script executa TRES requisicoes contra cada endpoint:
  1. GET /health              -> 200
  2. GET /produto?id=123       -> 200 (normal)
  3. GET /produto?id=SQLi       -> SEM WAF: 200 | COM WAF: 403 (BLOCKED)

REGRAS DE USO:
  - Execute SOMENTE contra os seus proprios endpoints de laboratorio.
  - Sem threads, sem flood, sem DDoS. Sao apenas 6 requisicoes no total.
  - Nao existe banco de dados; a string de SQLi e enviada apenas como texto
    para testar a inspecao do AWS WAF.

Uso:
  python test-sqli.py --sem-waf https://api-sem-waf.dominio.com \
                      --com-waf https://api-com-waf.dominio.com
"""

import argparse
import sys
import urllib.parse
import urllib.request

# Padrao de SQL Injection usado somente contra os endpoints do laboratorio.
SQLI_PAYLOAD = "1' OR '1'='1"
TIMEOUT = 15


def _url(base, path, params=None):
    base = base.rstrip("/")
    url = "{}{}".format(base, path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def _do_request(url):
    """Executa uma unica requisicao GET e retorna o status HTTP (int) ou None."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "waf-lab-03-sqli/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        # 403 do WAF cai aqui - e o resultado esperado no endpoint COM WAF.
        return e.code
    except Exception as e:
        print("  ! Erro ao acessar {}: {}".format(url, e))
        return None


def _fmt(label, status):
    dots = "." * max(3, 26 - len(label))
    if status == 403:
        return "  {}{}403 BLOCKED".format(label, dots)
    if status is None:
        return "  {}{}ERRO".format(label, dots)
    return "  {}{}{}".format(label, dots, status)


def run_block(title, base_url):
    print(title)
    health = _do_request(_url(base_url, "/health"))
    normal = _do_request(_url(base_url, "/produto", {"id": "123"}))
    sqli = _do_request(_url(base_url, "/produto", {"id": SQLI_PAYLOAD}))
    print(_fmt("Health", health))
    print(_fmt("Normal", normal))
    print(_fmt("SQL Injection", sqli))
    print("")


def main():
    parser = argparse.ArgumentParser(description="Teste controlado de SQL Injection com AWS WAF (Lab 03).")
    parser.add_argument("--sem-waf", dest="sem_waf", required=True, help="URL base do endpoint SEM WAF")
    parser.add_argument("--com-waf", dest="com_waf", required=True, help="URL base do endpoint COM WAF")
    args = parser.parse_args()

    print("=" * 41)
    print("AWS WAF LAB 03 - SQL INJECTION")
    print("=" * 41)
    print("")

    run_block("SEM WAF", args.sem_waf)
    run_block("COM WAF", args.com_waf)

    print("=" * 41)
    return 0


if __name__ == "__main__":
    sys.exit(main())
