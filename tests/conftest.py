"""Configuração compartilhada do pytest para o laboratório AWS WAF Security Lab 03.

Adiciona o diretório ``lambda/`` ao ``sys.path`` para que os testes possam
importar o módulo ``lambda_function`` diretamente (o diretório ``lambda`` não é
um nome de pacote Python importável por si só).
"""

import sys
from pathlib import Path

# Raiz do projeto: diretório pai da pasta ``tests``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Diretório que contém ``lambda_function.py``.
LAMBDA_DIR = PROJECT_ROOT / "lambda"

# Garante que ``import lambda_function`` funcione a partir dos testes.
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))
