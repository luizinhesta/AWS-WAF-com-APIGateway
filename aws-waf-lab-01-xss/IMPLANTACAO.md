# Implantação — Passo a Passo pelo Console AWS

Guia didático de implantação do laboratório **exclusivamente pelo Console AWS**, em português. Cada passo indica **onde clicar**, **qual campo preencher** e **qual opção escolher**.

> **Substitua nos exemplos:**
> - `SEU-DOMINIO` pelo seu domínio real (neste guia usamos `dev.inhesta.net` como exemplo).
> - `SUFIXO` por um identificador único do bucket (ex.: o número da sua conta).
>
> **Nomes usados neste guia** (você pode manter ou trocar, mas anote o que escolher):

| Item | Valor usado no guia |
|---|---|
| Bucket S3 | `waf-lab-01-xss-SUFIXO` |
| Distribuição SEM WAF | `waf-lab-01-xss-sem-waf` |
| Distribuição COM WAF | `waf-lab-01-xss-com-waf` |
| Subdomínio SEM WAF | `site-sem-waf.dev.inhesta.net` |
| Subdomínio COM WAF | `site-com-waf.dev.inhesta.net` |
| Web ACL (pacote de proteção) | `waf-lab-xss` |
| Regra do WAF | `Block-XSS-Lab` |
| Objeto raiz padrão | `index.html` |

> **Ordem das etapas:** S3 → ACM → CloudFront (as duas distribuições) → WAF → Política do bucket → Route 53 → Testes → CloudWatch → Exclusão.
>
> **Por que o CloudFront vem antes do WAF?** O console novo do WAF ("pacote de proteção") exige selecionar um recurso a proteger. Se a distribuição ainda não existir, o fluxo trava. Por isso criamos as distribuições primeiro.

---

## Antes de começar

- Conta AWS com permissões para S3, CloudFront, WAF, ACM, Route 53 e CloudWatch.
- Um domínio com **zona hospedada no Route 53** (ex.: `dev.inhesta.net`).
- **Região dos recursos globais:** o ACM do CloudFront e o WAF de escopo CloudFront ficam em **Leste dos EUA (Norte da Virgínia) / us-east-1**. Sempre que indicado, troque a região no seletor do canto superior direito do Console.

---

## Etapa 1 — Amazon S3 (bucket privado + upload do site)

### 1.1 Criar o bucket

1. Na barra de busca do Console, digite **S3** e clique no serviço **S3**.
2. Clique no botão laranja **Criar bucket** (canto superior direito).
3. No campo **Nome do bucket**, digite `waf-lab-01-xss-SUFIXO` (precisa ser único no mundo).
4. Em **Região da AWS**, escolha **Leste dos EUA (Norte da Virgínia) us-east-1**.
5. Em **Propriedade do objeto**, deixe marcado **ACLs desabilitadas (recomendado)**.
6. Em **Bloquear acesso público (configurações do bucket)**, deixe marcada a caixa **Bloquear todo o acesso público**.
7. Role até o fim e clique em **Criar bucket**.

### 1.2 Enviar os arquivos do site

1. Na lista de buckets, clique no bucket `waf-lab-01-xss-SUFIXO`.
2. Na aba **Objetos**, clique em **Carregar**.
3. Clique em **Adicionar arquivos** e selecione os três arquivos da pasta `site/`: `index.html`, `style.css` e `script.js`.
4. Clique em **Carregar** e aguarde a mensagem de sucesso.
5. Confirme que os três arquivos aparecem na **raiz** do bucket.

> Não é preciso mexer na política do bucket agora. Ao criar as distribuições (Etapa 3) com a opção "Permitir acesso privado ao bucket S3 ao CloudFront", o próprio CloudFront cria/atualiza a política via OAC. A Etapa 5 serve apenas para conferir/ajustar.

---

## Etapa 2 — AWS Certificate Manager (certificado TLS)

> O certificado do CloudFront **precisa** estar em **us-east-1**.

1. No seletor de região (canto superior direito), selecione **Leste dos EUA (Norte da Virgínia) us-east-1**.
2. Na busca do Console, digite **Certificate Manager** e abra o **AWS Certificate Manager (ACM)**.
3. Clique em **Solicitar um certificado** (Request a certificate).
4. Escolha **Solicitar um certificado público** e clique em **Avançar**.
5. Em **Nome de domínio totalmente qualificado**, você tem duas opções:
   - **Opção A (recomendada, mais simples):** digite um curinga `*.dev.inhesta.net` — ele cobre `site-sem-waf...` e `site-com-waf...` de uma vez.
   - **Opção B:** adicione `site-sem-waf.dev.inhesta.net`, clique em **Adicionar outro nome a este certificado** e adicione `site-com-waf.dev.inhesta.net`.
6. Em **Método de validação**, selecione **Validação de DNS - recomendado**.
7. Clique em **Solicitar**.
8. Na lista, clique no certificado que acabou de criar (status **Pendente de validação**).
9. Clique em **Criar registros no Route 53** e depois em **Criar registros**. O ACM cria sozinho os registros de validação na sua zona.
10. Aguarde o **Status** virar **Emitido** (leva alguns minutos). Enquanto isso, siga para a Etapa 3.

---

## Etapa 3 — Amazon CloudFront (criar as DUAS distribuições)

O assistente de criação tem **6 passos**: *Choose a plan → Get started → Specify origin → Enable security → Get TLS certificate → Review and create*. Vamos criar primeiro a distribuição **SEM WAF** e depois repetir para a **COM WAF**.

### 3.1 Criar a distribuição SEM WAF

O assistente mostra os 6 passos na coluna da **esquerda** (Step 1 a Step 6). Siga na ordem:

1. Na busca do Console, digite **CloudFront** e abra o serviço.
2. Clique em **Criar distribuição (Create distribution)**.

**Step 1 — Choose a plan** (escolher o plano — é a PRIMEIRA tela)

1. Selecione **Pay as you go** (pague conforme o uso — melhor para laboratório de baixo tráfego).
2. Clique em **Next**.

**Step 2 — Get started** (aqui você dá o NOME da distribuição)

1. No campo **Distribution name**, digite o nome do site/distribuição: `waf-lab-01-xss-sem-waf`.
2. No campo **Description** (opcional), digite `Lab 01 distribuicao SEM WAF`.
3. Em **Distribution type**, selecione **Single website or app**.
4. Em **Domain (Route 53 managed domain)**, **deixe o campo em branco** (o domínio será configurado manualmente no Step 5). Não clique em "Check domain".
5. Clique em **Next**.

**Step 3 — Specify origin** (de onde vem o conteúdo)

1. Em **Origin type**, selecione **Amazon S3**.
2. Em **S3 origin**, clique em **Browse S3** e selecione o bucket `waf-lab-01-xss-SUFIXO` (o endpoint termina em `.s3.us-east-1.amazonaws.com`).
3. Em **Settings**, deixe marcada a caixa **Allow private S3 bucket access to CloudFront - Recommended** (isso cria o OAC e atualiza a política do bucket automaticamente).
4. Deixe selecionados **Use recommended origin settings** e **Use recommended cache settings tailored to serving S3 content**.
5. Clique em **Next**.

**Step 4 — Enable security** (WAF)

1. Selecione **Do not enable security protections** (esta distribuição fica SEM WAF).
    - Não marque "Enable security protections" — isso criaria uma Web ACL gerenciada e paga (~$14/mês). Nosso WAF será só 1 regra, criada na Etapa 4.
2. Clique em **Next**.

**Step 5 — Get TLS certificate** (domínio + certificado)

1. Clique em **Add domain** e digite `site-sem-waf.dev.inhesta.net`. Deve aparecer **"Covered by the selected certificate"** (verde).
2. Em **Custom SSL certificate**, selecione o certificado ACM da Etapa 2 (o `*.dev.inhesta.net`). Deve aparecer **"Covers all active domains"** (verde).
3. Clique em **Next**.

**Step 6 — Review and create** (revisar)

1. Confira o resumo: **Distribution name**, **Domains to serve** (`site-sem-waf.dev.inhesta.net`), **Billing** (Pay-as-you-go), **Security protections = None** e o **TLS certificate**.
2. Clique em **Create distribution**.
3. **Anote** o **Distribution domain name** (algo como `dXXXX.cloudfront.net`) e o **ARN**.

**Ajuste final desta distribuição — definir o objeto raiz**

1. Ainda na página da distribuição, abra a aba **General** e, no bloco **Settings**, clique em **Edit**.
2. No campo **Default root object**, digite `index.html` e clique em **Save changes**.
    - Sem isso, abrir a raiz (`/`) não carrega o site.

> **Viewer protocol policy:** confirme que ficou **Redirect HTTP to HTTPS** (aba **Behaviors** → comportamento **Default (\*)** → **Edit**, se necessário). O padrão do assistente já costuma vir assim.

### 3.2 Criar a distribuição COM WAF

Clique em **Criar distribuição** novamente e repita **exatamente** o processo da 3.1, mudando apenas:

1. **Step 1 — Choose a plan:** **Pay as you go**.
2. **Step 2 — Get started:** em **Distribution name**, digite `waf-lab-01-xss-com-waf`; em **Description**, `Lab 01 distribuicao COM WAF`; **Single website or app**; deixe o **Domain** em branco.
3. **Step 3 — Specify origin:** selecione o **mesmo** bucket `waf-lab-01-xss-SUFIXO`, com **Allow private S3 bucket access to CloudFront** marcado.
4. **Step 4 — Enable security:** selecione novamente **Do not enable security protections** (o WAF será associado na Etapa 4).
5. **Step 5 — Get TLS certificate:** em **Add domain**, digite `site-com-waf.dev.inhesta.net`; use o mesmo certificado ACM `*.dev.inhesta.net`.
6. **Step 6 — Review and create:** confira o resumo e clique em **Create distribution**. **Anote o domínio e o ARN**.
7. Abra a aba **General > Settings > Edit** e defina **Default root object = `index.html`**. Clique em **Save changes**.

> Como as duas distribuições usam o mesmo bucket, confira a política do bucket na Etapa 5 (a segunda criação pode sobrescrever a autorização da primeira).

---

## Etapa 4 — AWS WAF (pacote de proteção `waf-lab-xss` + regra de XSS)

> A Web ACL usada no CloudFront precisa ter escopo **CloudFront (global)**, gerenciado em **us-east-1**.
>
> **Sobre custo:** o AWS WAF cobra uma **taxa mensal fixa pela Web ACL** (~US$ 5/mês) **+ por regra** (~US$ 1/mês) **+ por requisição inspecionada** (volume mínimo no lab). Essas taxas são cobradas **enquanto a Web ACL existir**, mesmo sem tráfego (proporcional ao tempo). Por isso: crie, teste e **exclua** ao terminar (Etapa 9). Os valores ~$11/$43/$58 mostrados no console são estimativas por 10 milhões de requisições/mês, não uma mensalidade fixa das caixas.

1. Confirme que a região está em **us-east-1**.
2. Na busca do Console, digite **WAF** e abra **AWS WAF & Shield**.
3. No menu à esquerda, clique em **Web ACLs**.
4. No seletor **Escopo da região** (no topo da lista), selecione **CloudFront (global)**.
5. Clique em **Criar pacote de proteção (ACL da Web)**.

**Conte-nos sobre sua aplicação**

1. Em **Categoria da aplicação** (obrigatório), abra o dropdown e escolha uma categoria genérica (ex.: **Outro**). Isso só gera recomendações e não afeta a nossa regra.
2. Em **Foco da aplicação**, selecione **Web**.

**Selecione recursos para proteger**

1. Clique em **Adicionar recursos** e escolha **Adicionar recursos do CloudFront ou do Amplify**.
2. Marque a **distribuição `waf-lab-01-xss-com-waf`** (a COM WAF). **Não** selecione a SEM WAF. Clique em **Adicionar**.
   - Se ela não aparecer, aguarde alguns minutos (a distribuição precisa existir) e clique no ícone de atualizar.
   - No topo da seção deve aparecer **"Selecione recursos para proteger (1/1)"** com a distribuição `site-com-waf.dev.inhesta.net` listada.

**Escolher proteções iniciais**

1. Você verá **3 caixas**: "Regras recomendadas para você" (~$58), "Regras essenciais" (~$43) e **"Crie seu próprio pacote usando todas as proteções oferecidas pelo AWS WAF"** (~$11-12).
2. Selecione a **terceira caixa** — **"Crie seu próprio pacote..."** ("Você o constrói"). Ela **não adiciona nenhum Managed Rule Group** automaticamente, que é o que queremos para manter o custo mínimo.

**Adicionar a regra de XSS (painel "Adicionar regras" à direita)**

1. Abre um painel à direita chamado **Adicionar regras**. Selecione **Regra personalizada** e clique em **Seguinte**.
2. Aparecem os 4 tipos de regra. Selecione novamente **Regra personalizada** (a última da lista, "Crie regras personalizadas...") e clique em **Seguinte**.
3. No construtor da regra, preencha:
    - **Ação:** selecione **Block**.
    - **Nome da regra:** digite `Block-XSS-Lab`.
    - **Se uma solicitação:** deixe **corresponde à instrução**.
    - **Inspecionar:** abra o dropdown e, na seção **"Solicitar componentes"**, escolha **Todos os parâmetros de consulta**.
    - **Tipo de correspondência:** abra o dropdown, role até a seção **"Condição de correspondência de ataques"** e escolha **Contém ataques de injeção de XSS**.
    - **Transformação de texto:** troque de **Nenhum** para **Decodificar URL (URL decode)**.
    - (Ignore "Pre-parse text transformations", "Resposta personalizada" e "Adicionar rótulos" — não são necessários.)
4. Clique em **Adicionar regra**. A regra `Block-XSS-Lab` deve aparecer como **Salvo** no painel da direita.

**Nome e descrição do pacote (rolar para baixo)**

1. Na seção **Nome e descrição**, no campo **Nome**, digite `waf-lab-xss` (campo obrigatório).
2. Em **Descrição** (opcional), digite `Lab 01 - bloqueio de XSS na query string`.
3. Deixe **Ação padrão da Web ACL** em **Permitir (Allow)** e as métricas do CloudWatch / Solicitações de amostra habilitadas (padrão).
4. Clique em **Criar pacote de proteção (ACL da Web)**.

> Ao concluir, aparece uma mensagem verde confirmando a associação: *"A associação dos seguintes recursos a waf-lab-xss foi bem-sucedida: ... site-com-waf.dev.inhesta.net - Lab 01 distribuicao COM WAF"*. Para conferir depois: **CloudFront > distribuição COM WAF > aba Security > AWS WAF** deve mostrar `waf-lab-xss`.

---

## Etapa 5 — Conferir a política do bucket S3 (OAC)

Como você marcou **"Allow private S3 bucket access to CloudFront"** ao criar as distribuições, o CloudFront já ajustou a política. Este passo é para **conferir que as DUAS distribuições estão autorizadas** (a segunda criação pode ter sobrescrito a primeira).

1. Abra o serviço **S3** e clique no bucket `waf-lab-01-xss-SUFIXO`.
2. Clique na aba **Permissões**.
3. Role até **Política do bucket** e clique em **Editar**.
4. Confirme que existem **duas** entradas em `AWS:SourceArn` (uma para cada distribuição). Se faltar alguma, ajuste para ficar assim (troque `ACCOUNT_ID`, `DIST_SEM_WAF` e `DIST_COM_WAF` pelos IDs reais das distribuições):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipalReadOnly",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::waf-lab-01-xss-SUFIXO/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": [
            "arn:aws:cloudfront::ACCOUNT_ID:distribution/DIST_SEM_WAF",
            "arn:aws:cloudfront::ACCOUNT_ID:distribution/DIST_COM_WAF"
          ]
        }
      }
    }
  ]
}
```

5. Clique em **Salvar alterações**.

---

## Etapa 6 — Amazon Route 53 (registros Alias)

1. Na busca do Console, digite **Route 53** e abra **Zonas hospedadas**.
2. Clique na zona `dev.inhesta.net`.
3. Clique em **Criar registro**.
4. Em **Nome do registro**, digite `site-sem-waf` (o restante `.dev.inhesta.net` já vem preenchido).
5. Em **Tipo de registro**, deixe **A**.
6. Ative a chave **Alias**.
7. Em **Rotear tráfego para**, selecione **Alias para distribuição do CloudFront**.
8. No campo abaixo, selecione a distribuição **SEM WAF** (`dXXXX.cloudfront.net` correspondente).
9. Clique em **Criar registros**.
10. Repita os passos 3 a 9 criando **`site-com-waf`** (tipo **A**, Alias) apontando para a distribuição **COM WAF**.

> Aguarde as distribuições ficarem em **Deployed** e o DNS propagar antes de testar.

---

## Etapa 7 — Testes

> Execute **somente** contra os dois endpoints deste laboratório. Sem flood, sem stress test, sem DDoS. São 4 requisições no total.

### Pelo navegador

- **SEM WAF (normal):** `https://site-sem-waf.dev.inhesta.net/` → carrega o site (200).
- **SEM WAF (XSS):** `https://site-sem-waf.dev.inhesta.net/?search=<script>alert(1)</script>` → passa (não bloqueado).
- **COM WAF (normal):** `https://site-com-waf.dev.inhesta.net/` → carrega o site (200).
- **COM WAF (XSS):** `https://site-com-waf.dev.inhesta.net/?search=<script>alert(1)</script>` → **HTTP 403**.

### Com os scripts

Python:

```bash
python tests/test-xss.py --sem-waf https://site-sem-waf.dev.inhesta.net --com-waf https://site-com-waf.dev.inhesta.net
```

PowerShell:

```powershell
.\tests\test-xss.ps1 -UrlSemWaf "https://site-sem-waf.dev.inhesta.net" -UrlComWaf "https://site-com-waf.dev.inhesta.net"
```

Saída esperada:

```
========================================
AWS WAF LAB 01 - XSS
========================================

SEM WAF
  Normal.................... 200
  XSS....................... 200

COM WAF
  Normal.................... 200
  XSS....................... 403 BLOCKED

========================================
```

---

## Etapa 8 — CloudWatch e Sampled Requests (confirmar o bloqueio)

1. Abra **WAF & Shield > Web ACLs** (escopo **CloudFront (global)**) e clique em `waf-lab-xss`.
2. Na aba **Visão geral (Overview)**, veja **Solicitações permitidas** e **Solicitações bloqueadas** — `BlockedRequests` aumenta após o teste de XSS.
3. Abra a aba **Solicitações de amostra (Sampled requests)**, escolha a janela de tempo do teste e localize a requisição com:
   - **Ação: BLOCK**
   - **Regra correspondente: `Block-XSS-Lab`**
   - Query string contendo `<script>...`.

Isso confirma que a regra `Block-XSS-Lab` foi a responsável pelo bloqueio.

---

## Etapa 9 — Exclusão de recursos (faça ao terminar)

> A **Web ACL do WAF é o principal custo contínuo**. Exclua tudo ao concluir, na ordem inversa da criação.

### 9.1 Route 53
1. Abra **Route 53 > Zonas hospedadas > `dev.inhesta.net`**.
2. Marque os registros `site-sem-waf` e `site-com-waf` e clique em **Excluir registros**.

### 9.2 CloudFront
1. Abra **CloudFront**, marque a distribuição e clique em **Desabilitar (Disable)**.
2. Aguarde ficar **Deployed** (já desabilitada) e clique em **Excluir (Delete)**.
3. Repita para a segunda distribuição.

### 9.3 AWS WAF
1. Abra **WAF & Shield > Web ACLs** (CloudFront global) e clique em `waf-lab-xss`.
2. Na aba **Recursos AWS associados**, remova a associação restante (se houver).
3. Volte à lista, marque `waf-lab-xss` e clique em **Excluir**.

### 9.4 Amazon S3
1. Abra o bucket `waf-lab-01-xss-SUFIXO`, clique em **Esvaziar** e confirme.
2. Depois clique em **Excluir** o bucket.

### 9.5 ACM (opcional)
1. Em **ACM (us-east-1)**, selecione o certificado e clique em **Excluir** (só quando não estiver mais associado a nenhuma distribuição).

### Checklist final
- [ ] Registros Alias removidos do Route 53
- [ ] Duas distribuições CloudFront excluídas
- [ ] Web ACL `waf-lab-xss` excluída
- [ ] Bucket S3 esvaziado e excluído
- [ ] Certificado ACM excluído (opcional)
- [ ] Nenhum recurso do laboratório restante gerando custo

---

## Solução de problemas rápida

| Sintoma | O que verificar |
|---|---|
| 403 nos **dois** endpoints (até normal) | Política do bucket / OAC (Etapa 5); aguarde a distribuição ficar **Deployed**. |
| Raiz `/` não carrega (mas `/index.html` sim) | Faltou definir **Default root object = index.html** na distribuição. |
| COM WAF **não** bloqueia XSS (200) | Web ACL `waf-lab-xss` associada à distribuição COM WAF? Regra com ação **Block**? Inspecionando a query string? Adicionou **URL decode**? |
| SEM WAF **bloqueia** XSS | A distribuição SEM WAF não deve ter nenhuma Web ACL associada. |
| Certificado não aparece no CloudFront | Precisa estar em **us-east-1** e com status **Emitido**. |
| Erro de SSL / nome não confere | O domínio alternativo (CNAME) da distribuição precisa bater com o subdomínio e ser coberto pelo certificado. |
| DNS não resolve | Confira os registros Alias no Route 53 e aguarde a propagação. |
| Métricas não aparecem | CloudWatch metrics e Sampled requests habilitados; aguarde alguns minutos. |
