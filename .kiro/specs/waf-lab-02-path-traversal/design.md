# Design — Lab 02: Proteção contra Path Traversal / LFI (ALB + EC2 Linux)

## Visão geral

Dois Application Load Balancers, cada um em seu subdomínio, encaminham para a mesma instância EC2 (Ubuntu + Nginx) via Target Groups. Apenas o ALB "com WAF" tem uma Web ACL regional associada. A única variável entre os caminhos é o WAF.

```
                              INTERNET
                                 |
                              Route 53
                 +---------------+---------------+
                 v                               v
       alb-sem-waf.dev.inhesta.net    alb-com-waf.dev.inhesta.net
                 v                               v
            ALB (sem WAF)                   ALB (com WAF)
                 |                               |
                 |                          AWS WAF (regional)
                 v                               v
           Target Group                    Target Group
                 +---------------+---------------+
                                 v
                          EC2 (Ubuntu + Nginx)
                                 |
                          index.html + /health
```

## Componentes e decisões

| Componente | Decisão | Motivo |
|---|---|---|
| VPC | 2 subnets públicas em AZs distintas + IGW | ALB exige 2+ AZs |
| Security Groups | EC2 aceita 80 só do SG do ALB; SSM para admin | Superfície mínima, sem SSH |
| EC2 + Nginx | Ubuntu, `/health` → 200 JSON | Aplicação simples com health check |
| Target Group | Health check `/health`, sucesso 200 | Marca a instância como Healthy |
| ACM | Certificado na região do ALB, validação DNS | ALB é regional (não us-east-1 obrigatório) |
| ALB | Listener 80 → Redirect → 443 | HTTPS obrigatório |
| AWS WAF | Web ACL regional, 1 regra Path Traversal, Block | Escopo regional para ALB; custo mínimo |
| CloudWatch | Métricas do WAF e do ALB | Comprovar bloqueio e saúde |

## Fluxo sem WAF

`Usuário → Route 53 → ALB (sem Web ACL) → Target Group → EC2/Nginx`. A requisição `../` chega ao Nginx e aparece no `access.log`.

## Fluxo com WAF

`Usuário → Route 53 → ALB → AWS WAF → (detecta ../) → BLOCK → 403`. A requisição não chega ao Target Group/EC2 e **não** aparece no `access.log`.

## Regra `Block-Path-Traversal-Lab`

- **Statement:** Contains string `../` (ou Regex Pattern Set `\.\./`).
- **Componente inspecionado:** Todos os parâmetros de consulta (opcional: URI path).
- **Transformação de texto:** URL decode (captura `%2e%2e%2f`).
- **Ação:** Block. Ação padrão da Web ACL: Allow.

Payload de teste: `?file=../../etc/passwd`. Nenhum arquivo é lido — a aplicação ignora o parâmetro; a string existe só para o WAF inspecionar.

## Evidência central: access.log

O ponto-chave do lab é observar `/var/log/nginx/access.log` via SSM (`tail -f`): a requisição de Path Traversal aparece no endpoint sem WAF e **não** aparece no endpoint com WAF (bloqueada com 403 no ALB).

## Artefatos do projeto

- Site: `aws-waf-lab-02-path-traversal/web/` (`index.html`, `style.css`, `health`).
- Instalação: `aws-waf-lab-02-path-traversal/scripts/install-nginx.sh`.
- Testes: `aws-waf-lab-02-path-traversal/tests/` (`test-path-traversal.py`, `.ps1`).
- Documentação de apoio: `README.md`, `ARQUITETURA.md`, `IMPLANTACAO.md`, `TESTE.md`.

## Estratégia de teste

1. **Validação local (Kiro):** sintaxe dos scripts Python; abrir `web/index.html` no navegador; revisar `install-nginx.sh`.
2. **Validação na AWS (manual):** instância Healthy nos Target Groups; rodar scripts (sem WAF chega ao servidor / com WAF 403); confirmar ausência da linha no `access.log`; conferir CloudWatch.

## Referências de nomes (ambiente real)

| Item | Valor |
|---|---|
| VPC | `vpc-waf-lab02` (`10.0.0.0/16`) |
| SG ALB / SG EC2 | `sg-alb-lab02` / `sg-ec2-lab02` |
| EC2 | `ec2-waf-lab02` (Ubuntu) |
| Target Groups | `tg-sem-waf-lab02` / `tg-com-waf-lab02` |
| ALBs | `alb-sem-waf-lab02` / `alb-com-waf-lab02` |
| Subdomínios | `alb-sem-waf.dev.inhesta.net` / `alb-com-waf.dev.inhesta.net` |
| Web ACL / Regra | `waf-lab-path-traversal` / `Block-Path-Traversal-Lab` |
