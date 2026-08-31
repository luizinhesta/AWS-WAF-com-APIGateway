#!/usr/bin/env bash
#
# AWS WAF Security Lab - Projeto 02 (Path Traversal)
# Instala e configura o Nginx em uma instancia Ubuntu Linux.
#
# O que este script faz:
#   1. Instala o Nginx.
#   2. Publica index.html, style.css e o endpoint /health.
#   3. Habilita e inicia o Nginx.
#
# Uso (na EC2, via SSM Session Manager ou user data):
#   sudo bash install-nginx.sh
#
# Observacao: NAO cria nenhum endpoint vulneravel. O parametro ?file=... usado
# no teste de Path Traversal e ignorado pela aplicacao - existe apenas para
# testar a inspecao do AWS WAF.

set -euo pipefail

WEB_ROOT="/var/www/html"

echo "==> Atualizando pacotes..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx

echo "==> Criando ${WEB_ROOT}/index.html ..."
cat > "${WEB_ROOT}/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AWS WAF Security Lab - Projeto 02 | Path Traversal</title>
    <link rel="stylesheet" href="/style.css" />
</head>
<body>
    <header class="hero">
        <div class="badge">AWS WAF Security Lab</div>
        <h1>Projeto 02</h1>
        <h2>Proteção contra Path Traversal / LFI</h2>
        <p class="sub">Application Load Balancer + EC2 Linux (Nginx)</p>
    </header>
    <main>
        <section class="card">
            <h3>Sobre</h3>
            <p>
                Este servidor Nginx roda em uma instância EC2 Ubuntu por trás de um
                Application Load Balancer. O laboratório compara um endpoint SEM WAF
                com um endpoint COM WAF para demonstrar o bloqueio de Path Traversal.
            </p>
        </section>
        <section class="card">
            <h3>O que é Path Traversal?</h3>
            <p>
                Ataques de Path Traversal tentam usar sequências como <code>../</code>
                para acessar diretórios fora do local esperado pela aplicação.
                Neste laboratório nenhum endpoint vulnerável é criado e nenhum arquivo
                do sistema é lido. A sequência é enviada apenas como parâmetro HTTP,
                por exemplo <code>?file=../../etc/passwd</code>, para testar a inspeção do WAF.
            </p>
        </section>
        <section class="card">
            <h3>Resultado esperado</h3>
            <table>
                <tr><th>Teste</th><th>SEM WAF</th><th>COM WAF</th></tr>
                <tr><td>Normal</td><td>Chega ao Nginx</td><td>Chega ao Nginx</td></tr>
                <tr><td>Path Traversal</td><td>Chega ao Nginx</td><td>403 WAF</td></tr>
                <tr><td>Health Check</td><td>Healthy</td><td>Healthy</td></tr>
            </table>
        </section>
    </main>
    <footer>
        <p>AWS WAF Security Lab — Projeto 02 — ALB + EC2 Linux — Laboratório educacional</p>
    </footer>
</body>
</html>
HTML

echo "==> Criando ${WEB_ROOT}/style.css ..."
cat > "${WEB_ROOT}/style.css" <<'CSS'
:root { --dark:#0f1b2d; --navy:#16243b; --orange:#ff9900; --text:#e6edf3; --muted:#9fb3c8; --card:#1b2a41; --border:#2a3d59; }
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:"Segoe UI",Arial,sans-serif; background:var(--dark); color:var(--text); line-height:1.6; }
.hero { text-align:center; padding:64px 20px; border-bottom:3px solid var(--orange); background:radial-gradient(circle at 20% 20%,#1d3350,var(--dark) 60%); }
.badge { display:inline-block; background:var(--orange); color:#14202e; font-weight:700; text-transform:uppercase; font-size:.75rem; padding:6px 16px; border-radius:999px; margin-bottom:20px; letter-spacing:1px; }
.hero h1 { font-size:2.8rem; }
.hero h2 { color:var(--orange); margin-top:6px; font-size:1.4rem; }
.hero .sub { color:var(--muted); margin-top:10px; }
main { max-width:820px; margin:0 auto; padding:32px 20px; }
.card { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:24px; margin-bottom:20px; }
.card h3 { color:var(--orange); margin-bottom:10px; }
code { color:var(--orange); font-family:Consolas,monospace; }
table { width:100%; border-collapse:collapse; margin-top:10px; }
th,td { padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); }
th { color:var(--orange); font-size:.8rem; text-transform:uppercase; }
footer { text-align:center; padding:28px 20px; border-top:1px solid var(--border); color:var(--muted); font-size:.85rem; }
CSS

echo "==> Criando endpoint ${WEB_ROOT}/health ..."
cat > "${WEB_ROOT}/health" <<'JSON'
{
  "status": "healthy"
}
JSON

# Configura o Nginx para servir /health com Content-Type JSON e status 200.
echo "==> Configurando site do Nginx (server block) ..."
cat > /etc/nginx/sites-available/default <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html;

    server_name _;

    # Health check do Target Group -> retorna JSON com HTTP 200.
    location = /health {
        default_type application/json;
        try_files /health =200;
    }

    location / {
        try_files $uri $uri/ =404;
    }
}
NGINX

echo "==> Testando configuracao do Nginx ..."
nginx -t

echo "==> Habilitando e iniciando o Nginx ..."
systemctl enable nginx
systemctl restart nginx

echo "==> Concluido. Nginx ativo servindo /var/www/html."
echo "    - Site:   http://<host>/"
echo "    - Health: http://<host>/health  -> {\"status\": \"healthy\"}"
