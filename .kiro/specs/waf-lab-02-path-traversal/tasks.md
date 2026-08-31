# Tarefas — Lab 02: Proteção contra Path Traversal / LFI (ALB + EC2 Linux)

Implantação **manual pelo Console AWS**. Marque cada item conforme concluir. O detalhamento está em `aws-waf-lab-02-path-traversal/IMPLANTACAO.md`.

## 1. Rede (VPC)
- [ ] 1.1 Criar VPC `vpc-waf-lab02` (`10.0.0.0/16`) com 2 subnets públicas em AZs diferentes + IGW + route table
- _Requisitos: 2_

## 2. Security Groups
- [ ] 2.1 Criar `sg-alb-lab02` (inbound 80 e 443 de 0.0.0.0/0)
- [ ] 2.2 Criar `sg-ec2-lab02` (inbound 80 somente do `sg-alb-lab02`)
- _Requisitos: 3_

## 3. IAM / SSM
- [ ] 3.1 Criar função IAM `role-ec2-ssm-lab02` com `AmazonSSMManagedInstanceCore`
- _Requisitos: 3_

## 4. EC2 + Nginx
- [ ] 4.1 Criar instância Ubuntu `ec2-waf-lab02` (SG `sg-ec2-lab02`, perfil IAM SSM, sem par de chaves)
- [ ] 4.2 Instalar Nginx via `install-nginx.sh` (User data ou SSM Session Manager)
- [ ] 4.3 Confirmar `/health` retornando `{"status":"healthy"}` (curl local)
- _Requisitos: 4_

## 5. Target Groups
- [ ] 5.1 Criar `tg-sem-waf-lab02` (HTTP 80, health check `/health`, sucesso 200) e registrar a EC2
- [ ] 5.2 Criar `tg-com-waf-lab02` (mesmas configs) e registrar a mesma EC2
- _Requisitos: 1, 4_

## 6. ACM
- [ ] 6.1 Solicitar certificado público na região do ALB (subdomínios ou wildcard), validar por DNS
- _Requisitos: 5_

## 7. Application Load Balancers
- [ ] 7.1 Criar `alb-sem-waf-lab02` (2 subnets, SG do ALB, listener 80→Redirect→443, HTTPS→`tg-sem-waf-lab02`, cert ACM)
- [ ] 7.2 Criar `alb-com-waf-lab02` (mesmas configs, HTTPS→`tg-com-waf-lab02`)
- [ ] 7.3 Confirmar EC2 Healthy nos dois Target Groups
- _Requisitos: 1, 5_

## 8. AWS WAF (pacote de proteção)
- [ ] 8.1 Criar Web ACL `waf-lab-path-traversal` (Regional, opção "Crie seu próprio pacote")
- [ ] 8.2 Associar o `alb-com-waf-lab02` (Adicionar recursos regionais)
- [ ] 8.3 Adicionar regra `Block-Path-Traversal-Lab`: inspecionar query string, "Contém a string" `../`, transformação URL decode, ação Block
- [ ] 8.4 Ação padrão = Allow e criar o pacote
- _Requisitos: 6_

## 9. Route 53 (DNS)
- [ ] 9.1 Criar Alias A `alb-sem-waf` → `alb-sem-waf-lab02`
- [ ] 9.2 Criar Alias A `alb-com-waf` → `alb-com-waf-lab02`
- _Requisitos: 5_

## 10. Testes (validação na AWS)
- [ ] 10.1 Rodar `test-path-traversal.py` / `.ps1` contra os dois endpoints
- [ ] 10.2 Confirmar: sem WAF Path Traversal → chega ao servidor; com WAF → 403 BLOCKED
- [ ] 10.3 Comprovar no `access.log` (via SSM `tail -f`): aparece sem WAF, não aparece com WAF
- [ ] 10.4 Conferir CloudWatch (WAF `BlockedRequests`; ALB 4XX / HealthyHostCount)
- _Requisitos: 7, 8_

## 11. Validação local (Kiro) — opcional
- [ ] 11.1 Verificar sintaxe do `test-path-traversal.py`
- [ ] 11.2 Abrir `web/index.html` no navegador
- [ ] 11.3 Revisar `scripts/install-nginx.sh`
- _Requisitos: 8_

## 12. Encerramento (exclusão de recursos)
- [ ] 12.1 Excluir registros Alias no Route 53
- [ ] 12.2 Desassociar e excluir a Web ACL
- [ ] 12.3 Excluir os dois ALBs
- [ ] 12.4 Excluir os dois Target Groups
- [ ] 12.5 Encerrar (terminate) a EC2
- [ ] 12.6 (Opcional) Excluir certificado ACM, VPC/subnets/IGW/SGs e função IAM
- _Requisitos: 9_
