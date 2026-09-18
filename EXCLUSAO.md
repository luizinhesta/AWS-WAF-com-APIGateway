# Guia de Exclusão / Teardown — AWS WAF Security Lab 03 (SQL Injection)

Este documento descreve a **exclusão completa dos recursos** do laboratório **AWS WAF Security Lab — Projeto 03: Proteção contra SQL Injection com API Gateway REST + AWS Lambda**, realizada pelo **Console da AWS em Português (Brasil)**.

> **Quando executar:** após concluir a implantação ([`IMPLANTACAO.md`](./IMPLANTACAO.md)) e os testes de validação ([`TESTES.md`](./TESTES.md)). A limpeza evita custos remanescentes e deixa a conta limpa.

## Convenções deste guia

- Os nomes de menus, abas e botões aparecem em **pt-BR**, com o nome original em inglês entre parênteses quando útil. Exemplo: **Excluir (Delete)**.
- Substitua **`DOMINIO`** pelo seu domínio real, gerenciado na zona hospedada (Hosted zone) do Route 53.
- Substitua **`REGIAO`** pela região AWS usada na implantação.
- Os pontos marcados com **📸 Evidência / Print recomendado** indicam onde capturar telas para comprovação.
- Os blocos **✅ Validação** indicam verificações intermediárias entre as etapas.

---

## Exclusão completa dos recursos (limpeza / teardown)

**Objetivo:** remover **todos** os recursos do laboratório respeitando as **dependências** entre eles, para evitar custos e deixar a conta limpa (Requisitos 24.5, 26.1).

> ⚠️ **Ordem importa.** A remoção segue a ordem inversa das dependências: primeiro desassociamos e removemos a proteção do WAF, depois o DNS, em seguida os Custom Domains e a API, então a Lambda e, **por último**, o certificado ACM (que fica preso enquanto estiver em uso por algum Custom Domain). Seguir a ordem abaixo evita erros de "recurso em uso (resource in use)".
>
> 💡 **Confirme a `REGIAO`.** Todos os recursos regionais (WAF, API Gateway, Custom Domains, ACM) devem ser excluídos na **mesma** `REGIAO` em que foram criados. Verifique o seletor de região antes de começar.

### 1 — Desassociar e excluir a Web ACL `waf-lab-sqli` e suas regras

**Por quê primeiro:** enquanto a Web ACL estiver **associada** ao stage `com-waf`, ela não pode ser excluída. A desassociação também restaura o comportamento do `com-waf` para "sem proteção".

1. Abra **AWS WAF → Web ACLs**, confirme o escopo **Recursos regionais (Regional resources)** e a `REGIAO`.
2. Clique na Web ACL **`waf-lab-sqli`**.
3. Abra a aba **Recursos associados (Associated AWS resources)**.
4. Selecione o stage **`com-waf`** (API `api-waf-lab-sqli`) e clique em **Desassociar (Disassociate)**. Confirme.

   > As regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab` estão **contidas** na Web ACL, portanto serão removidas junto com ela — não é necessário excluí-las separadamente. Se você tiver criado essas regras como **grupos de regras (rule groups)** reutilizáveis (não é o caso deste laboratório, que usa regras próprias na Web ACL), exclua-os depois em **AWS WAF → Grupos de regras (Rule groups)**.
5. Volte à lista **Web ACLs**, marque **`waf-lab-sqli`** e clique em **Excluir (Delete)**.
6. Confirme a exclusão digitando o nome, se solicitado, e clique em **Excluir (Delete)**.

**✅ Validação:**
- A aba **Recursos associados** de `waf-lab-sqli` não lista mais o stage `com-waf` (0 associações) **antes** da exclusão.
- A Web ACL `waf-lab-sqli` **não** aparece mais na lista de Web ACLs regionais da `REGIAO`.
- (Opcional) `GET https://api-com-waf.DOMINIO/produto?id=1' OR '1'='1` volta a retornar **HTTP 200** (sem WAF), confirmando a desassociação.

![Descrição da imagem](<imagens/imagem%20(10).png>)
![Descrição da imagem](<imagens/imagem%20(12).png>)

**📸 Evidência / Print recomendado:** tela de **Recursos associados** já sem o `com-waf` e a lista de Web ACLs sem `waf-lab-sqli`.

---

### 2 — Excluir os registros Alias do Route 53 (`api-sem-waf`, `api-com-waf`)

**Por quê agora:** os registros DNS apontam para os Custom Domains. Removê-los antes dos Custom Domains evita apontamentos órfãos.

1. Abra **Route 53 → Zonas hospedadas (Hosted zones) → DOMINIO**.
2. Localize e selecione o registro **`api-sem-waf`** (Tipo **A**, Alias).
3. Clique em **Excluir registro (Delete record)** e confirme em **Excluir (Delete)**.
4. Repita para o registro **`api-com-waf`** (Tipo **A**, Alias).
5. Se você criou registros **AAAA** (IPv6) para esses subdomínios, exclua-os também.

> ⚠️ **Não** exclua o registro **CNAME de validação do ACM** neste momento — ele será tratado (opcionalmente) na etapa 6, após a exclusão do certificado. E **nunca** exclua os registros **NS** e **SOA** da zona hospedada.

**✅ Validação:**
- Os registros `api-sem-waf` e `api-com-waf` **não** aparecem mais na zona hospedada de `DOMINIO`.
- (Opcional, após propagação) `https://api-sem-waf.DOMINIO/health` e `https://api-com-waf.DOMINIO/health` deixam de resolver.

**📸 Evidência / Print recomendado:** tela do Route 53 mostrando a zona `DOMINIO` sem os registros `api-sem-waf` e `api-com-waf`.

---

### 3 — Excluir os mapeamentos e os Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO`

**Por quê agora:** os Custom Domains **usam** o certificado ACM e mapeiam para os stages. É preciso removê-los **antes** de excluir o certificado (etapa 6) e antes de excluir a API/stages (etapa 4).

1. No **API Gateway**, abra **Nomes de domínio personalizados (Custom domain names)**.
2. Abra o Custom Domain **`api-sem-waf.DOMINIO`**.
3. Na aba **Mapeamentos de API (API mappings)**, remova o mapeamento para o stage `sem-waf`: clique em **Configurar mapeamentos de API (Configure API mappings)**, remova a linha do mapeamento e clique em **Salvar (Save)**.
4. Volte à lista de Custom Domains, selecione **`api-sem-waf.DOMINIO`** e clique em **Excluir (Delete)**. Confirme.
5. Repita os passos 2 a 4 para o Custom Domain **`api-com-waf.DOMINIO`** (removendo o mapeamento para o stage `com-waf` e, em seguida, excluindo o domínio).

**✅ Validação:**
- Nenhum dos Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` aparece mais na lista de **Nomes de domínio personalizados**.

**📸 Evidência / Print recomendado:** tela de **Nomes de domínio personalizados** vazia (ou sem os dois domínios do laboratório).

---

### 4 — Excluir os stages (`sem-waf`, `com-waf`) e a REST API `api-waf-lab-sqli`

**Por quê agora:** com os Custom Domains e o WAF já removidos, a API e seus stages podem ser excluídos sem dependências pendentes.

> 💡 Excluir a **REST API** inteira remove automaticamente seus stages, recursos, métodos e deploys. Se preferir apenas remover os stages e manter a API, use o passo opcional a seguir; caso contrário, vá direto para a exclusão da API.

1. (Opcional) Excluir stages individualmente:
   - No **API Gateway**, abra a API **`api-waf-lab-sqli`** → **Estágios (Stages)**.
   - Selecione o stage **`com-waf`** e clique em **Excluir (Delete)**. Confirme.
   - Repita para o stage **`sem-waf`**.
2. Excluir a REST API completa:
   - Em **API Gateway**, localize a API **`api-waf-lab-sqli`**.
   - Abra a API e use **Ações da API (API actions) → Excluir API (Delete API)** (ou selecione a API na lista e clique em **Excluir (Delete)**).
   - Confirme digitando o nome da API, se solicitado, e clique em **Excluir (Delete)**.

**✅ Validação:**
- A API **`api-waf-lab-sqli`** e seus stages `sem-waf` e `com-waf` **não** aparecem mais no API Gateway da `REGIAO`.

**📸 Evidência / Print recomendado:** lista de APIs do API Gateway sem a `api-waf-lab-sqli`.

---

### 5 — Excluir a função Lambda `waf-lab-sqli` (e, opcionalmente, o grupo de logs)

**Por quê agora:** a Lambda só era invocada pela API, que já foi removida. Não há mais dependências.

1. Abra **Lambda** (na `REGIAO`).
2. Selecione a função **`waf-lab-sqli`**.
3. Clique em **Ações (Actions) → Excluir (Delete)** (ou **Excluir função / Delete function**). Confirme digitando `delete`/o nome, se solicitado.

**Grupo de logs do CloudWatch (opcional):**

4. Abra **CloudWatch → Grupos de logs (Log groups)**.
5. Localize o grupo **`/aws/lambda/waf-lab-sqli`** (padrão `/aws/lambda/{nome-da-funcao}`).
6. Selecione o grupo e clique em **Ações (Actions) → Excluir (Delete)**. Confirme.

   > A exclusão do grupo de logs é **opcional** — mantê-lo preserva as evidências (por exemplo, os `requestId` usados nos testes do `sem-waf`). Excluí-lo evita cobrança de retenção de logs.

**Função de execução IAM (opcional):**

7. Se você quiser limpar também a **função IAM (execution role)** criada automaticamente para a Lambda, abra **IAM → Funções (Roles)**, localize a role associada (nome geralmente iniciado por `waf-lab-sqli-role-...`) e exclua-a **somente** se não estiver em uso por outros recursos.

**✅ Validação:**
- A função **`waf-lab-sqli`** não aparece mais na lista do Lambda.
- (Se excluído) o grupo de logs `/aws/lambda/waf-lab-sqli` não aparece mais no CloudWatch.

**📸 Evidência / Print recomendado:** lista do Lambda sem a função `waf-lab-sqli` (e, se aplicável, a lista de grupos de logs sem `/aws/lambda/waf-lab-sqli`).

---

### 6 — Excluir o certificado ACM `*.DOMINIO` (por último) e o CNAME de validação

**Por quê por último:** o certificado só pode ser excluído quando **não** estiver mais **em uso** por nenhum Custom Domain (removidos na etapa 3). Tentar excluí-lo antes resulta em erro de "certificado em uso (in use)".

1. Abra **Certificate Manager (ACM)** na `REGIAO`.
2. Localize o certificado **`*.DOMINIO`** (curinga).
3. Confirme que o campo **Em uso (In use)** / **Recursos associados (Associated resources)** está **vazio**. Se ainda aparecer algum recurso, volte e conclua a etapa 3.
4. Selecione o certificado e clique em **Excluir (Delete)**. Confirme.
5. **(Opcional) Registro CNAME de validação:** o certificado foi validado por DNS na implantação, o que criou um registro **CNAME** na zona hospedada de `DOMINIO`. Após excluir o certificado, esse CNAME de validação fica obsoleto:
   - Abra **Route 53 → Zonas hospedadas → DOMINIO**.
   - Localize o registro **CNAME** de validação do ACM (nome no formato `_<hash>.DOMINIO` apontando para `*.acm-validations.aws`).
   - Selecione-o e clique em **Excluir registro (Delete record)** e confirme.

   > Este passo é **opcional**; deixar o CNAME de validação não gera custo, mas removê-lo mantém a zona hospedada limpa.

**✅ Validação:**
- O certificado `*.DOMINIO` **não** aparece mais na lista do ACM da `REGIAO`.
- (Se excluído) o CNAME de validação do ACM não aparece mais na zona hospedada de `DOMINIO`.

**📸 Evidência / Print recomendado:** lista do ACM sem o certificado `*.DOMINIO` e, se aplicável, a zona do Route 53 sem o CNAME de validação.

---

### 7 — Checklist final de limpeza

Confirme, ao final, que **todos** os recursos do laboratório foram removidos (Requisitos 24.5, 26.1):

- [ ] Web ACL `waf-lab-sqli` desassociada do `com-waf` e **excluída** (com as regras `Block-Fora-do-Brasil` e `Block-SQLi-Lab`).
- [ ] Registros Alias `api-sem-waf` e `api-com-waf` (A/AAAA) **excluídos** do Route 53.
- [ ] Custom Domains `api-sem-waf.DOMINIO` e `api-com-waf.DOMINIO` (com seus mapeamentos) **excluídos**.
- [ ] Stages `sem-waf` e `com-waf` e a REST API `api-waf-lab-sqli` **excluídos**.
- [ ] Função Lambda `waf-lab-sqli` **excluída** (grupo de logs `/aws/lambda/waf-lab-sqli` opcionalmente excluído).
- [ ] Certificado ACM `*.DOMINIO` **excluído** (CNAME de validação opcionalmente removido do Route 53).
- [ ] Preservados a **zona hospedada (Hosted zone)** de `DOMINIO` e seus registros **NS**/**SOA**.

> ✅ Após concluir este checklist, o laboratório está totalmente removido e não deve gerar custos remanescentes (exceto a cobrança fixa da zona hospedada do Route 53, que **não** faz parte deste laboratório e deve ser mantida).
