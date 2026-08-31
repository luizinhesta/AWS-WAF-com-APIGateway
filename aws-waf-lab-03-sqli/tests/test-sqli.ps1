<#
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
      .\test-sqli.ps1 -ApiSemWaf "https://api-sem-waf.dominio.com" -ApiComWaf "https://api-com-waf.dominio.com"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$ApiSemWaf,

    [Parameter(Mandatory = $true)]
    [string]$ApiComWaf
)

# Padrao de SQL Injection usado somente contra os endpoints do laboratorio.
$SqliPayload = "1' OR '1'='1"
$TimeoutSec = 15

function Build-Url {
    param([string]$Base, [string]$Path, [string]$ParamName, [string]$ParamValue)
    $Base = $Base.TrimEnd("/")
    $url = "$Base$Path"
    if ($ParamName) {
        $encoded = [System.Uri]::EscapeDataString($ParamValue)
        $url += "?$ParamName=$encoded"
    }
    return $url
}

function Invoke-TestRequest {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return [int]$resp.StatusCode
    }
    catch {
        # 403 do WAF cai aqui - e o resultado esperado no endpoint COM WAF.
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            return [int]$_.Exception.Response.StatusCode.value__
        }
        Write-Host ("  ! Erro ao acessar {0}: {1}" -f $Url, $_.Exception.Message)
        return $null
    }
}

function Format-Line {
    param([string]$Label, $Status)
    $dots = "." * ([Math]::Max(3, 26 - $Label.Length))
    if ($Status -eq 403)    { return "  {0}{1}403 BLOCKED" -f $Label, $dots }
    if ($null -eq $Status)  { return "  {0}{1}ERRO" -f $Label, $dots }
    return "  {0}{1}{2}" -f $Label, $dots, $Status
}

function Invoke-Block {
    param([string]$Title, [string]$BaseUrl)
    Write-Host $Title
    $health = Invoke-TestRequest (Build-Url -Base $BaseUrl -Path "/health")
    $normal = Invoke-TestRequest (Build-Url -Base $BaseUrl -Path "/produto" -ParamName "id" -ParamValue "123")
    $sqli   = Invoke-TestRequest (Build-Url -Base $BaseUrl -Path "/produto" -ParamName "id" -ParamValue $SqliPayload)
    Write-Host (Format-Line -Label "Health" -Status $health)
    Write-Host (Format-Line -Label "Normal" -Status $normal)
    Write-Host (Format-Line -Label "SQL Injection" -Status $sqli)
    Write-Host ""
}

Write-Host ("=" * 41)
Write-Host "AWS WAF LAB 03 - SQL INJECTION"
Write-Host ("=" * 41)
Write-Host ""

Invoke-Block -Title "SEM WAF" -BaseUrl $ApiSemWaf
Invoke-Block -Title "COM WAF" -BaseUrl $ApiComWaf

Write-Host ("=" * 41)
