# Implantação — Passo a Passo pelo Console AWS

Guia completo de implantação do laboratório **exclusivamente pelo Console AWS**, em português.

> Substitua `SEU-DOMINIO.com` pelo seu domínio real e escolha uma **região** para o laboratório (ex.: `sa-east-1` São Paulo ou `us-east-1`). **Toda a Etapa de WAF e o ACM devem ser criados na MESMA região do ALB** (WAF regional e certificado do ALB acompanham a região dos recursos).

> **A sequência importa.** Ordem: **VPC → Security Groups → EC2 (IAM/SSM) → Nginx → Target Groups → ALBs → ACM → Listeners HTTPS → Route 53 → WAF → Testes → Exclusão**.

---

## Antes de começar

- Conta AWS com permissões para VPC, EC2, ELB, WAF, ACM, Route 53, IAM e Systems Manager.
- Domínio com **zona hospedada no Route 53** (ex.: `SEU-DOMINIO.com`).
- Escolha a **região** e a mantenha selecionada no canto superior direito durante todo o lab.

Nomes de referência:

| Item | Valor sugerido |
|---|---|
| VPC | `vpc-waf-lab02` (`10.0.0.0/16`) |
| Subnets públicas | `subnet-lab02-a` (AZ 1), `subnet-lab02-b` (AZ 2) |
| SG do ALB | `sg-alb-lab02` |
| SG da EC2 | `sg-ec2-lab02` |
| Instância EC2 | `ec2-waf-lab02` (Ubuntu) |
| Target Group SEM WAF | `tg-sem-waf-lab02` |
| Target Group COM WAF | `tg-com-waf-lab02` |
| ALB SEM WAF | `alb-sem-waf-lab02` |
| ALB COM WAF | `alb-com-waf-lab02` |
| Subdomínio sem WAF | `alb-sem-waf.SEU-DOMINIO.com` |
| Subdomínio com WAF | `alb-com-waf.SEU-DOMINIO.com` |
| Web ACL | `waf-lab-path-traversal` |
| Regra do WAF (Path Traversal) | `Block-Path-Traversal-Lab` |
| Regra do WAF (CAPTCHA/Geo) | `Captcha-Fora-do-Brasil` |

---

## Etapa 1 — VPC e rede

> Você pode usar a VPC padrão da conta para simplificar. O passo a passo abaixo cria uma VPC dedicada com o assistente.

1. Abra o serviço **VPC**.
2. Clique em **Criar VPC**.
3. Selecione **VPC e mais** (assistente que cria subnets, IGW e rotas de uma vez).
4. **Marcadores de nome:** `vpc-waf-lab02`.
5. **Bloco CIDR IPv4:** `10.0.0.0/16`.
6. **Número de zonas de disponibilidade (AZs):** **2**.
7. **Número de subnets públicas:** **2**. **Subnets privadas:** 0 (para simplificar o lab).
8. **Gateways NAT:** Nenhum. **Endpoints de VPC:** Nenhum.
9. Clique em **Criar VPC**. O assistente cria a VPC, o **Internet Gateway**, as **2 subnets públicas** e a **Route Table** com rota `0.0.0.0/0` para o IGW.

> O ALB exige **pelo menos duas subnets em AZs diferentes** — por isso criamos duas.

---

## Etapa 2 — Security Groups

Crie dois security groups em **VPC > Grupos de segurança > Criar grupo de segurança**, ambos na `vpc-waf-lab02`.

### 2.1 SG do ALB — `sg-alb-lab02`

- **Regras de entrada (inbound):**
  - Tipo **HTTP**, porta **80**, origem **0.0.0.0/0**.
  - Tipo **HTTPS**, porta **443**, origem **0.0.0.0/0**.
- **Regras de saída:** manter padrão (todo o tráfego).

### 2.2 SG da EC2 — `sg-ec2-lab02`

- **Regras de entrada (inbound):**
  - Tipo **HTTP**, porta **80**, origem: **selecione o grupo de segurança `sg-alb-lab02`** (não use 0.0.0.0/0).
- **Regras de saída:** manter padrão (necessário para SSM e updates).

> A porta HTTP da EC2 fica acessível **apenas pelo ALB**. Não abrimos SSH (porta 22) — a administração é via **SSM Session Manager**.

---

## Etapa 3 — Perfil IAM para SSM

Para usar o Session Manager, a EC2 precisa de um perfil de instância com a política do SSM.

1. Abra **IAM > Funções (Roles) > Criar função**.
2. **Entidade confiável:** **Serviço AWS** → **EC2**.
3. Anexe a política gerenciada **AmazonSSMManagedInstanceCore**.
4. **Nome:** `role-ec2-ssm-lab02`. Clique em **Criar função**.

---

## Etapa 4 — Instância EC2 (Ubuntu)

1. Abra **EC2 > Instâncias > Executar instâncias (Launch instances)**.
2. **Nome:** `ec2-waf-lab02`.
3. **Imagem (AMI):** **Ubuntu Server** (LTS).
4. **Tipo de instância:** uma pequena (ex.: `t3.micro`).
5. **Par de chaves:** selecione **Continuar sem par de chaves** (vamos usar SSM, não SSH).
6. **Configurações de rede > Editar:**
   - **VPC:** `vpc-waf-lab02`.
   - **Sub-rede:** `subnet-lab02-a`.
   - **Atribuir IP público automaticamente:** **Habilitar** (necessário para o SSM alcançar a internet nesta topologia simplificada).
   - **Firewall (grupos de segurança):** selecione **grupo existente** → `sg-ec2-lab02`.
7. **Detalhes avançados > Perfil do IAM da instância:** selecione `role-ec2-ssm-lab02`.
8. (Opcional) **Dados do usuário (User data):** cole o conteúdo de `scripts/install-nginx.sh` para instalar o Nginx automaticamente no primeiro boot. Se preferir fazer manualmente, siga a Etapa 5.
9. Clique em **Executar instância**.

---

## Etapa 5 — Nginx via Systems Manager (se não usou User data)

1. Abra **Systems Manager > Session Manager > Iniciar sessão**.
2. Selecione a instância `ec2-waf-lab02` e clique em **Iniciar sessão**.
3. No terminal da sessão, torne-se root e rode a instalação:
   ```bash
   sudo -i
   # cole o conteudo de scripts/install-nginx.sh em um arquivo e execute:
   nano install-nginx.sh   # cole o conteudo, salve (Ctrl+O, Enter) e saia (Ctrl+X)
   bash install-nginx.sh
   ```
   O script instala o Nginx, publica `index.html`, `style.css` e o endpoint `/health`, e executa `systemctl enable nginx` e `systemctl restart nginx`.
4. Verifique localmente:
   ```bash
   systemctl status nginx --no-pager
   curl -s http://localhost/health
   ```
   O `curl` deve retornar `{"status": "healthy"}`.

---

## Etapa 6 — Target Groups

Crie **dois** Target Groups (um para cada ALB), ambos registrando a **mesma EC2**.

1. Abra **EC2 > Grupos de destino (Target Groups) > Criar grupo de destino**.
2. **Tipo de destino:** **Instâncias**.
3. **Nome:** `tg-sem-waf-lab02`.
4. **Protocolo/Porta:** **HTTP / 80**.
5. **VPC:** `vpc-waf-lab02`.
6. **Verificações de integridade (Health checks):**
   - **Caminho:** `/health`.
   - **Códigos de sucesso:** `200`.
7. Avance, **registre o destino** `ec2-waf-lab02` (porta 80) e clique em **Criar grupo de destino**.
8. Repita criando `tg-com-waf-lab02` com as **mesmas configurações**, registrando a **mesma** instância.

---

## Etapa 7 — Certificado ACM (mesma região do ALB)

> Diferente do Lab 01 (CloudFront/us-east-1), aqui o ALB é **regional**: o certificado deve estar na **mesma região do ALB**.

1. Confirme a **região** do laboratório no seletor de região.
2. Abra **AWS Certificate Manager (ACM) > Solicitar > Solicitar um certificado público**.
3. Domínios:
   - `alb-sem-waf.SEU-DOMINIO.com`
   - Adicione `alb-com-waf.SEU-DOMINIO.com` (ou use um curinga `*.SEU-DOMINIO.com`).
4. **Método de validação:** **Validação por DNS**.
5. Clique em **Solicitar**, abra o certificado e clique em **Criar registros no Route 53**.
6. Aguarde o status **Emitido**.

---

## Etapa 8 — Application Load Balancers

Crie **dois** ALBs. Os dois usam as **2 subnets públicas** e o SG `sg-alb-lab02`.

### 8.1 ALB SEM WAF

1. Abra **EC2 > Load Balancers > Criar load balancer**.
2. Escolha **Application Load Balancer**.
3. **Nome:** `alb-sem-waf-lab02`.
4. **Esquema:** **Voltado para a Internet (internet-facing)**.
5. **Mapeamento de rede:** VPC `vpc-waf-lab02`, selecione **as duas subnets** (`subnet-lab02-a` e `subnet-lab02-b`).
6. **Grupos de segurança:** `sg-alb-lab02`.
7. **Listeners e roteamento:**
   - **Listener HTTP :80** → ação **Redirecionar para HTTPS** (443).
   - **Listener HTTPS :443** → encaminhar para o Target Group `tg-sem-waf-lab02`; em **Certificado SSL/TLS**, selecione o certificado ACM da Etapa 7.
8. Clique em **Criar load balancer**.

### 8.2 ALB COM WAF

1. Repita o processo criando `alb-com-waf-lab02`.
2. Mesmas subnets e SG.
3. **Listener HTTP :80** → **Redirecionar para HTTPS**.
4. **Listener HTTPS :443** → encaminhar para o Target Group `tg-com-waf-lab02`; mesmo certificado ACM.
5. Clique em **Criar load balancer**.

### 8.3 Confirmar saúde dos alvos

- Vá em **Target Groups** e confirme que a EC2 aparece como **Healthy** nos dois grupos antes de testar. Se estiver **Unhealthy**, veja a solução de problemas no fim deste documento.

---

## Etapa 9 — AWS WAF (pacote de proteção `waf-lab-path-traversal` + regra)

> A Web ACL deve ser **regional** e criada na **mesma região do ALB**. Ela será associada **somente ao `alb-com-waf-lab02`**.

1. Na busca do Console, digite **WAF** e abra **AWS WAF & Shield**.
2. No menu à esquerda, clique em **Web ACLs**.
3. No seletor **Escopo da região** (topo da lista), selecione **Regional** e confirme a **região do ALB**.
4. Clique em **Criar pacote de proteção (ACL da Web)**.

**Conte-nos sobre sua aplicação**

1. Em **Categoria da aplicação** (obrigatório), abra o dropdown e escolha uma categoria genérica (ex.: **Outro**).
2. Em **Foco da aplicação**, selecione **Web** (aplicação servida por navegador atrás do ALB).

**Selecione recursos para proteger**

1. Clique em **Adicionar recursos** e escolha **Adicionar recursos regionais**.
2. Na lista, selecione o tipo **Application Load Balancer** e marque o **`alb-com-waf-lab02`** (**somente** ele — não marque o `alb-sem-waf-lab02`). Clique em **Adicionar**.
   - Se preferir, clique em **Ignorar por enquanto** e associe depois (ver nota no fim da etapa).

**Escolher proteções iniciais**

1. **Não selecione nenhum pacote gerenciado (Managed Rule Group).** Deixe vazio — usaremos apenas 1 regra customizada.

**Nome e descrição**

1. Em **Nome**, digite `waf-lab-path-traversal`.
2. Em **Descrição** (opcional), digite `Lab 02 - bloqueio de Path Traversal`.
3. Deixe **Métricas do CloudWatch** e **Solicitações de amostra** habilitadas.

**Personalizar pacote de proteção — adicionar a regra**

1. Expanda **Personalizar pacote de proteção (ACL da Web)**.
2. Clique em **Adicionar regras > Adicionar minha própria regra e grupos de regras** e escolha **Construtor de regras (Rule builder)**.
3. Em **Nome**, digite `Block-Path-Traversal-Lab`. Em **Tipo**, deixe **Regra normal**.
4. Em **Instrução (Statement)**:
    - **Inspecionar:** selecione **Todos os parâmetros de consulta (All query parameters)** — opcionalmente adicione outra instrução para o **caminho do URI (URI path)**.
    - **Tipo de correspondência:** selecione **Contém a cadeia de caracteres (Contains string)**.
    - **Cadeia (string) a procurar:** digite `../`
    - **Transformação de texto:** clique em **Adicionar** e escolha **URL decode** (captura também a forma `%2e%2e%2f`).
5. Em **Ação (Action)**, selecione **Bloquear (Block)**.
6. Clique em **Adicionar regra**.

**Personalizar pacote de proteção — adicionar a regra de CAPTCHA (acesso apenas do Brasil)**

> Objetivo: permitir o acesso ao site **direto quando a origem é o Brasil** e **exigir um CAPTCHA quando a origem está fora do Brasil**. Assim, o site só é acessado por quem resolve o desafio (evitando acesso automatizado de fora do país). O CAPTCHA do WAF é renderizado como uma **página interativa no navegador** — por isso o teste principal desta regra é feito **pelo navegador**.

1. Ainda em **Personalizar pacote de proteção**, clique novamente em **Adicionar regras > Adicionar minha própria regra e grupos de regras** e escolha **Construtor de regras (Rule builder)**.
2. Em **Nome**, digite `Captcha-Fora-do-Brasil`. Em **Tipo**, deixe **Regra normal**.
3. Em **Instrução (Statement)**:
    - **Inspecionar:** selecione **Originates from a country in (Origina-se de um país em)**.
    - Ative o botão **Negate statement results (Negar resultados da instrução)** — a regra passa a corresponder quando o país **NÃO** é o selecionado.
    - Em **Country codes (Códigos de país)**, selecione **Brazil - BR**.
    - **Endereço IP a usar para determinar o país de origem:** deixe **Source IP address (Endereço IP de origem)**.
    - Resultado lógico: a regra corresponde quando a origem está **fora do Brasil**.
4. Em **Ação (Action)**, selecione **CAPTCHA**.
    - Em **Imunidade (Immunity time)**, deixe o padrão (ex.: 300 segundos). É o tempo em que o navegador não precisa refazer o desafio após resolvê-lo uma vez.
5. Clique em **Adicionar regra**.

**Ordem e prioridade das regras**

1. Confirme que a Web ACL tem duas regras: `Block-Path-Traversal-Lab` (ação **Block**) e `Captcha-Fora-do-Brasil` (ação **CAPTCHA**).
2. Recomenda-se deixar `Block-Path-Traversal-Lab` com **prioridade mais alta** (avaliada primeiro): um ataque de path traversal deve ser **bloqueado** de imediato, sem oferecer CAPTCHA. Ajuste com as setas de prioridade se necessário.
   - Com essa ordem: uma requisição de fora do Brasil **com** `../` é **bloqueada** (Block vence); uma requisição de fora do Brasil **sem** `../` recebe o **CAPTCHA**; uma requisição do Brasil sem `../` passa direto.
3. Em **Ação padrão da Web ACL**, deixe **Permitir (Allow)**.
4. Revise e clique em **Criar pacote de proteção (ACL da Web)**.

> Alternativa mais abrangente para o path traversal: usar um **Regex Pattern Set** com um padrão como `\.\./` via *Regex pattern set match*. Para o lab, o *Contains string* `../` já é suficiente.

> **Sobre o CAPTCHA:** ele foi feito para clientes que rodam JavaScript e renderizam a página (navegadores). Scripts simples (curl, `Invoke-WebRequest`, os scripts de teste deste lab) **não resolvem** o desafio — eles recebem **HTTP 405** com o corpo do CAPTCHA. Por isso, valide o CAPTCHA **pelo navegador**.

> Para associar o ALB depois (se você pulou a associação): **WAF > Web ACLs > `waf-lab-path-traversal` > aba Recursos AWS associados > Adicionar recursos AWS** e selecione `alb-com-waf-lab02`.

> Para adicionar/editar a regra de CAPTCHA depois da criação: **WAF > Web ACLs > `waf-lab-path-traversal` > aba Regras (Rules) > Adicionar regras > Adicionar minha própria regra e grupos de regras > Rule builder** e repita os passos acima.

---

## Etapa 10 — Route 53 (registros Alias)

1. Abra **Route 53 > Zonas hospedadas > `SEU-DOMINIO.com`**.
2. **Criar registro:**
   - **Nome:** `alb-sem-waf`. **Tipo:** **A**. Ative **Alias**.
   - **Rotear tráfego para:** **Alias para Application/Classic Load Balancer** → região do lab → selecione o `alb-sem-waf-lab02`.
   - **Criar registros**.
3. Repita para `alb-com-waf` apontando para `alb-com-waf-lab02`.
4. Aguarde a propagação DNS e teste com `nslookup`.

---

## Etapa 11 — Testes

Veja o passo a passo completo em [TESTE.md](TESTE.md). Resumo:

- **SEM WAF + normal** → chega ao Nginx (200).
- **SEM WAF + Path Traversal** (`?file=../../etc/passwd`) → chega ao Nginx (200/404) e **aparece no access.log**.
- **COM WAF + normal (do Brasil)** → chega ao Nginx (200).
- **COM WAF + Path Traversal** → **HTTP 403** e **não aparece no access.log**.
- **COM WAF + normal (de fora do Brasil, pelo navegador)** → aparece a **página de CAPTCHA**; só chega ao site após resolver o desafio.

Scripts:

```bash
python tests/test-path-traversal.py --sem-waf https://alb-sem-waf.SEU-DOMINIO.com --com-waf https://alb-com-waf.SEU-DOMINIO.com
```

```powershell
.\tests\test-path-traversal.ps1 -UrlSemWaf "https://alb-sem-waf.SEU-DOMINIO.com" -UrlComWaf "https://alb-com-waf.SEU-DOMINIO.com"
```

---

## Etapa 12 — Exclusão de recursos (faça ao terminar)

> ALB e EC2 **cobram por hora**; a Web ACL do WAF também cobra. Exclua tudo ao concluir. Ordem inversa da criação.

### 12.1 Route 53

- Exclua os registros `alb-sem-waf` e `alb-com-waf`.

### 12.2 AWS WAF

1. **WAF > Web ACLs > `waf-lab-path-traversal`**.
2. Em **Recursos AWS associados**, remova a associação com `alb-com-waf-lab02`.
3. Exclua a Web ACL (isso remove as duas regras: `Block-Path-Traversal-Lab` e `Captcha-Fora-do-Brasil`).

### 12.3 Application Load Balancers

- **EC2 > Load Balancers**, selecione cada ALB e **Excluir** (`alb-sem-waf-lab02` e `alb-com-waf-lab02`).

### 12.4 Target Groups

- **EC2 > Grupos de destino**, exclua `tg-sem-waf-lab02` e `tg-com-waf-lab02`.

### 12.5 EC2

- **EC2 > Instâncias**, selecione `ec2-waf-lab02` e **Encerrar (Terminate)**.

### 12.6 ACM (opcional)

- Exclua o certificado se não for reutilizar (só é possível quando não estiver associado a nenhum ALB).

### 12.7 VPC e rede (se criou VPC dedicada)

- **VPC > Suas VPCs**, exclua `vpc-waf-lab02` (o Console remove subnets, route tables e IGW associados). Exclua também os security groups se não forem removidos automaticamente.

### 12.8 IAM (opcional)

- Exclua a função `role-ec2-ssm-lab02` se não for reutilizar.

### Checklist final

- [ ] Registros Alias removidos do Route 53
- [ ] Web ACL `waf-lab-path-traversal` desassociada e excluída
- [ ] Dois ALBs excluídos
- [ ] Dois Target Groups excluídos
- [ ] Instância EC2 encerrada
- [ ] Certificado ACM excluído (opcional)
- [ ] VPC/subnets/IGW/SGs excluídos (se criou VPC dedicada)
- [ ] Função IAM removida (opcional)
- [ ] Nenhum recurso do laboratório restante gerando custo

---

## Solução de problemas rápida

| Sintoma | O que verificar |
|---|---|
| Alvo **Unhealthy** no Target Group | Nginx ativo? `/health` retorna 200? SG da EC2 permite porta 80 vindo do SG do ALB? Health Check Path = `/health`? |
| 502/504 no ALB | EC2 rodando, Nginx ativo, SG da EC2 liberando o SG do ALB na porta 80. |
| COM WAF **não** bloqueia `../` | Web ACL associada ao `alb-com-waf-lab02`? Regra com ação **Block**? Inspecionando query string? Transformação **URL decode** aplicada? |
| SEM WAF retorna 403 | O ALB SEM WAF não deve ter Web ACL associada. |
| CAPTCHA aparece **mesmo do Brasil** | Regra `Captcha-Fora-do-Brasil` provavelmente sem o **Negate statement**. Ative o botão **Negate** e confirme o país **BR**. |
| CAPTCHA **não** aparece de fora do Brasil | Seu IP realmente sai por outro país? (confirme em site de "meu IP"). A ação da regra é **CAPTCHA**? Está testando pelo **navegador** (não por script)? |
| De fora do Brasil recebo **405** em vez da página | ✅ Esperado quando o cliente é um **script** (curl/Invoke-WebRequest): o 405 traz o corpo do CAPTCHA. Use o **navegador** para ver e resolver o desafio. |
| Certificado não aparece no ALB | Precisa estar **Emitido** e na **mesma região** do ALB. |
| Não consigo abrir sessão SSM | Perfil IAM com `AmazonSSMManagedInstanceCore` anexado e a EC2 com saída para a internet (IP público / rota IGW). |
| DNS não resolve | Registros Alias corretos no Route 53; aguarde propagação. |
