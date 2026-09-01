#!/usr/bin/env python3
"""
AWS WAF Security Lab - Projeto 01 (XSS)
Teste controlado de deteccao de XSS pelo AWS WAF.

O script executa DUAS requisicoes contra cada endpoint:
  1. Requisicao normal   -> deve retornar 200
  2. Requisicao com XSS   -> SEM WAF: 200 | COM WAF: 403 (BLOCKED)

REGRAS DE USO:
  - Execute SOMENTE contra os endpoints do seu proprio laboratorio.
  - Sem threads, sem flood, sem DDoS. Sao apenas 4 requisicoes no total.

Uso:
  python test-xss.py --sem-waf https://site-sem-waf.dominio.com \
                     --com-waf https://site-com-waf.dominio.com
"""

import argparse
import sys
import urllib.parse
import urllib.request

# Payload de XSS controlado. Nenhum script e executado - apenas enviado como texto.
XSS_PAYLOAD = "<script>alert(1)</script>"
TIMEOUT = 15


def _build_url(base, value):
    base = base.rstrip("/")
    query = urllib.parse.urlencode({"search": value})
    return "{}/?{}".format(base, query)


def _do_request(url):
    """Executa uma unica requisicao GET e retorna o status HTTP (int)."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "waf-lab-01-xss/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.getcode()
    except urllib.error.HTTPError as e:
        # 403 do WAF cai aqui - e um resultado esperado, nao um erro do teste.
        return e.code
    except Exception as e:
        print("  ! Erro ao acessar {}: {}".format(url, e))
        return None


def _fmt(label, status):
    dots = "." * max(3, 26 - len(label))
    if status == 403:
        return "{}{}{} BLOCKED".format(label, dots, status)
    if status is None:
        return "{}{}ERRO".format(label, dots)
    return "{}{}{}".format(label, dots, status)


def run_block(title, base_url):
    print(title)
    normal_status = _do_request(_build_url(base_url, "teste"))
    xss_status = _do_request(_build_url(base_url, XSS_PAYLOAD))
    print("  " + _fmt("Normal", normal_status))
    print("  " + _fmt("XSS", xss_status))
    print("")


def main():
    parser = argparse.ArgumentParser(description="Teste controlado de XSS com AWS WAF (Lab 01).")
    parser.add_argument("--sem-waf", dest="sem_waf", required=True, help="URL do endpoint SEM WAF")
    parser.add_argument("--com-waf", dest="com_waf", required=True, help="URL do endpoint COM WAF")
    args = parser.parse_args()

    print("=" * 40)
    print("AWS WAF LAB 01 - XSS")
    print("=" * 40)
    print("")

    run_block("SEM WAF", args.sem_waf)
    run_block("COM WAF", args.com_waf)

    print("=" * 40)
    return 0


if __name__ == "__main__":
    sys.exit(main())
