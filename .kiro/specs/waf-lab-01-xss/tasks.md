# Tarefas — Lab 01: Proteção contra XSS (CloudFront + S3)

## Regra de execução

Este laboratório será implantado manualmente por mim através do Console AWS.

A implantação manual completa deve ser conduzida dentro da MESMA task e da MESMA sessão.

O Kiro deve:

- apresentar somente uma etapa por vez;
- informar exatamente onde entrar no Console AWS;
- informar campos, valores e opções;
- aguardar eu responder "pronto", "feito", "ok" ou "concluído";
- após minha confirmação, continuar IMEDIATAMENTE para o próximo passo;
- não perguntar se desejo continuar;
- não encerrar a sessão enquanto ainda existirem passos pendentes;
- não criar recursos AWS automaticamente.

## Estado já concluído

- Route 53 / domínio confirmado
- Região us-east-1 definida
- Bucket S3 criado
- Arquivos enviados ao S3
- Certificado ACM criado e emitido
- CloudFront SEM WAF criado
- CloudFront COM WAF criado
- Web ACL `waf-lab-xss` criada
- Regra `Block-XSS-Lab` criada
- WAF associado ao CloudFront protegido

---

## 1. Implantação manual completa pelo Console AWS

- [x] 1.1 Conduzir comigo toda a implantação restante e os testes do laboratório

Dentro desta task, executar sequencialmente os seguintes passos:

### Passo A — CloudFront COM WAF

Configurar:

Default root object:

`index.html`

Depois aguardar minha confirmação.

### Passo B — Identificar distribuições

Localizar e registrar:

- domínio CloudFront SEM WAF
- ARN CloudFront SEM WAF
- domínio CloudFront COM WAF
- ARN CloudFront COM WAF

Depois aguardar minha confirmação.

### Passo C — Política S3

Conferir se a Bucket Policy permite acesso pelas DUAS distribuições CloudFront através de `AWS:SourceArn`.

Depois aguardar minha confirmação.

### Passo D — Route 53 SEM WAF

Criar:

`site-sem-waf.dev.inhesta.net`

Tipo:

A

Alias:

Sim

Destino:

CloudFront SEM WAF

Depois aguardar minha confirmação.

### Passo E — Route 53 COM WAF

Criar:

`site-com-waf.dev.inhesta.net`

Tipo:

A

Alias:

Sim

Destino:

CloudFront COM WAF

Depois aguardar minha confirmação.

### Passo F — Propagação

Confirmar:

- CloudFront SEM WAF = Deployed
- CloudFront COM WAF = Deployed
- DNS resolvendo
- HTTPS funcionando

Depois aguardar minha confirmação.

### Passo G — Teste normal

Testar:

`https://site-sem-waf.dev.inhesta.net`

e:

`https://site-com-waf.dev.inhesta.net`

Esperado:

HTTP 200 nos dois.

Depois aguardar minha confirmação.

### Passo H — Teste XSS

Executar o script de teste já criado.

Testar padrão XSS controlado nos dois endpoints.

Esperado:

SEM WAF:
200 ou requisição permitida

COM WAF:
403 BLOCKED

Depois aguardar minha confirmação.

### Passo I — Validar AWS WAF

Abrir AWS WAF.

Verificar:

- `BlockedRequests`
- Sampled Requests
- regra `Block-XSS-Lab`

Confirmar que a requisição XSS foi bloqueada.

Depois aguardar minha confirmação.

### Passo J — Encerramento do laboratório

Quando todos os testes forem concluídos, apresentar a sequência de exclusão dos recursos.

NÃO excluir automaticamente.

Apresentar somente as orientações.

---

## Critério para concluir a Task 1.1

A task somente poderá ser marcada `[x]` quando:

1. os dois sites estiverem acessíveis;
2. o teste normal funcionar;
3. o endpoint SEM WAF permitir o teste;
4. o endpoint COM WAF bloquear o XSS;
5. o bloqueio aparecer no AWS WAF;
6. eu confirmar que o laboratório foi concluído.