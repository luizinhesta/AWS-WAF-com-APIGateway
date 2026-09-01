<#
    AWS WAF Security Lab - Projeto 01 (XSS)
    Teste controlado de deteccao de XSS pelo AWS WAF.

    O script executa DUAS requisicoes contra cada endpoint:
      1. Requisicao normal  -> deve retornar 200
      2. Requisicao com XSS  -> SEM WAF: 200 | COM WAF: 403 (BLOCKED)

    REGRAS DE USO:
      - Execute SOMENTE contra os endpoints do seu proprio laboratorio.
      - Sem threads, sem flood, sem DDoS. Sao apenas 4 requisicoes no total.

    Uso:
      .\test-xss.ps1 -UrlSemWaf "https://site-sem-waf.dominio.com" -UrlComWaf "https://site-com-waf.dominio.com"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$UrlSemWaf,

    [Parameter(Mandatory = $true)]
    [string]$UrlComWaf
)

# Payload de XSS controlado. Nenhum script e executado - apenas enviado como texto.
$XssPayload = "<script>alert(1)</script>"
$TimeoutSec = 15

function Build-Url {
    param([string]$Base, [string]$Value)
    $Base = $Base.TrimEnd("/")
    $encoded = [System.Uri]::EscapeDataString($Value)
    return "$Base/?search=$encoded"
}

function Invoke-TestRequest {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        return [int]$resp.StatusCode
    }
    catch {
        # 403 do WAF cai aqui - e um resultado esperado, nao um erro do teste.
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
    if ($Status -eq 403) {
        return "  {0}{1}{2} BLOCKED" -f $Label, $dots, $Status
    }
    if ($null -eq $Status) {
        return "  {0}{1}ERRO" -f $Label, $dots
    }
    return "  {0}{1}{2}" -f $Label, $dots, $Status
}

function Invoke-Block {
    param([string]$Title, [string]$BaseUrl)
    Write-Host $Title
    $normal = Invoke-TestRequest (Build-Url -Base $BaseUrl -Value "teste")
    $xss = Invoke-TestRequest (Build-Url -Base $BaseUrl -Value $XssPayload)
    Write-Host (Format-Line -Label "Normal" -Status $normal)
    Write-Host (Format-Line -Label "XSS" -Status $xss)
    Write-Host ""
}

Write-Host ("=" * 40)
Write-Host "AWS WAF LAB 01 - XSS"
Write-Host ("=" * 40)
Write-Host ""

Invoke-Block -Title "SEM WAF" -BaseUrl $UrlSemWaf
Invoke-Block -Title "COM WAF" -BaseUrl $UrlComWaf

Write-Host ("=" * 40)
