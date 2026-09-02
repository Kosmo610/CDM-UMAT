<#
    verify_bibliography.ps1 — 참고문헌 서지를 Crossref REST API로 대조한다.

    왜 PowerShell인가:
      Abaqus 워크스테이션에는 인터넷이 없고, 인터넷이 되는 PC는 Windows다.
      PowerShell 5.1 이상이면 추가 설치 없이 돈다 (python, curl, API 키 전부 불필요).

    ★ PowerShell에서 `curl`은 `Invoke-WebRequest`의 별칭이라 `-s` 같은 리눅스 옵션을
      받지 않는다. 그래서 이 스크립트는 `Invoke-RestMethod`만 쓴다.

    사용법:
        powershell -ExecutionPolicy Bypass -File verification\verify_bibliography.ps1

    옵션:
        -InputCsv   기본 data\literature\refs_candidates.csv
        -OutputCsv  기본 verification\bibliography_check.csv
        -Mail       Crossref polite pool용 이메일 (넣으면 응답이 빨라진다)
        -Only       특정 key만 (쉼표 구분, 예: -Only S1,B34)

    판정:
        OK        DOI·권·쪽이 전부 일치 (비어 있는 기대값은 검사하지 않음)
        FILLED    기대값이 비어 있던 칸을 Crossref가 채움 -> 문서에 반영할 것
        MISMATCH  기대값과 다름 -> ★ 반드시 원문 확인
        LOWSCORE  제목 매칭 신뢰도가 낮음 -> 사람이 눈으로 확인
        NOTFOUND  Crossref에 없음 (학회 프로시딩·구소련지·NASA TM 등은 정상)
#>

[CmdletBinding()]
param(
    [string]$InputCsv  = "",
    [string]$OutputCsv = "",
    [string]$Mail      = "",
    [string]$Only      = ""
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- 경로: 스크립트 위치 기준으로 저장소 루트를 잡는다 -----------------------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
if (-not $InputCsv)  { $InputCsv  = Join-Path $repoRoot 'data\literature\refs_candidates.csv' }
if (-not $OutputCsv) { $OutputCsv = Join-Path $scriptDir 'bibliography_check.csv' }

if (-not (Test-Path $InputCsv)) { throw "입력 CSV를 찾을 수 없습니다: $InputCsv" }

$ua = 'CDM-UMAT-bibcheck/1.0 (https://github.com/Kosmo610/CDM-UMAT)'
if ($Mail) { $ua += " mailto:$Mail" }
$headers = @{ 'User-Agent' = $ua }

# --- 정규화 헬퍼 -------------------------------------------------------------
function Normalize-Text([string]$s) {
    if ($null -eq $s) { return '' }
    $s = $s.ToLowerInvariant()
    $s = $s -replace '[^a-z0-9 ]', ' '
    $s = $s -replace '\s+', ' '
    return $s.Trim()
}

function Normalize-Pages([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return '' }
    # en-dash / em-dash / minus / 물결표를 전부 하이픈으로, 공백 제거
    # (문자를 직접 쓰면 파일 인코딩에 좌우되므로 \uXXXX 로 적는다)
    $s = $s -replace '[‐‑‒–—―−~]', '-'
    return ($s -replace '\s', '')
}

# 두 제목의 단어 집합 겹침 비율 (0~1). 완전 일치에 가까울수록 1.
function Get-TitleScore([string]$a, [string]$b) {
    $wa = @(Normalize-Text $a -split ' ' | Where-Object { $_.Length -gt 2 })
    $wb = @(Normalize-Text $b -split ' ' | Where-Object { $_.Length -gt 2 })
    if ($wa.Count -eq 0 -or $wb.Count -eq 0) { return 0.0 }
    $setB = @{}
    foreach ($w in $wb) { $setB[$w] = $true }
    $hit = 0
    foreach ($w in $wa) { if ($setB.ContainsKey($w)) { $hit++ } }
    return [double]$hit / [double]$wa.Count
}

# --- 실행 -------------------------------------------------------------------
$rows = Import-Csv -Path $InputCsv
if ($Only) {
    $keep = $Only -split ',' | ForEach-Object { $_.Trim() }
    $rows = $rows | Where-Object { $keep -contains $_.key }
}

Write-Host ""
Write-Host "Crossref 서지 대조 — $($rows.Count)건" -ForegroundColor Cyan
Write-Host ("=" * 78)

$results = @()
$i = 0

foreach ($r in $rows) {
    $i++
    Write-Progress -Activity 'Crossref 조회' -Status "$i / $($rows.Count)  $($r.key)" `
                   -PercentComplete ([int](100 * $i / $rows.Count))

    $best = $null; $bestScore = 0.0; $status = ''; $note = ''; $method = ''

    # --- 1) DOI를 알고 있으면 직접 조회한다 (가장 확실) ----------------------
    #     검색은 학술지명이 원어로 등재된 경우(예: Materials and Structures 가
    #     Crossref에는 "Materiaux et Constructions")나 제목이 길 때 0건을 낸다.
    #     실제로 첫 판에서 S1(Bazant & Oh)이 그래서 NOTFOUND 로 잘못 나왔다.
    if ($r.expected_doi) {
        try {
            $u = 'https://api.crossref.org/works/' + [uri]::EscapeUriString($r.expected_doi)
            $resp = Invoke-RestMethod -Uri $u -Headers $headers -TimeoutSec 40
            if ($resp.message) {
                $best = $resp.message
                $t = ''
                if ($best.title -and $best.title.Count -gt 0) { $t = $best.title[0] }
                $bestScore = Get-TitleScore $r.title $t
                $method = 'doi'
            }
        } catch {
            $method = 'doi-fail'      # DOI가 틀렸거나 Crossref 미등재
        }
    }

    # --- 2) 제목 + 학술지 검색 ----------------------------------------------
    if ($null -eq $best) {
        $q = "https://api.crossref.org/works?rows=5&query.bibliographic=" +
             [uri]::EscapeDataString($r.title)
        if ($r.journal) {
            $q += "&query.container-title=" + [uri]::EscapeDataString($r.journal)
        }
        try {
            $resp = Invoke-RestMethod -Uri $q -Headers $headers -TimeoutSec 40
            foreach ($it in $resp.message.items) {
                $t = ''
                if ($it.title -and $it.title.Count -gt 0) { $t = $it.title[0] }
                $sc = Get-TitleScore $r.title $t
                if ($sc -gt $bestScore) { $bestScore = $sc; $best = $it }
            }
            if ($best) { $method = 'title+journal' }
        } catch {
            $status = 'ERROR'
            $note   = $_.Exception.Message
        }
    }

    # --- 3) 학술지명을 빼고 제목만으로 다시 --------------------------------
    if (($null -eq $best) -and (-not $status) -and $r.journal) {
        Start-Sleep -Milliseconds 250
        $q2 = "https://api.crossref.org/works?rows=5&query.bibliographic=" +
              [uri]::EscapeDataString($r.title)
        try {
            $resp = Invoke-RestMethod -Uri $q2 -Headers $headers -TimeoutSec 40
            foreach ($it in $resp.message.items) {
                $t = ''
                if ($it.title -and $it.title.Count -gt 0) { $t = $it.title[0] }
                $sc = Get-TitleScore $r.title $t
                if ($sc -gt $bestScore) { $bestScore = $sc; $best = $it }
            }
            if ($best) { $method = 'title-only' }
        } catch {
            $status = 'ERROR'
            $note   = $_.Exception.Message
        }
    }

    # ★ Windows PowerShell 5.1 은 `$x = if (...) {...}` 형태의 대입을 파싱하지 못한다.
    #   (PowerShell 7 부터 가능) 따라서 아래는 전부 명시적 if 문으로 쓴다.
    $gotDoi = ''; $gotVol = ''; $gotIss = ''; $gotPage = ''
    $gotYear = ''; $gotJournal = ''; $gotTitle = ''
    if ($null -ne $best) {
        if ($best.DOI)    { $gotDoi  = [string]$best.DOI }
        if ($best.volume) { $gotVol  = [string]$best.volume }
        if ($best.issue)  { $gotIss  = [string]$best.issue }
        if ($best.page)   { $gotPage = [string]$best.page }
        if ($best.title -and $best.title.Count -gt 0) { $gotTitle = [string]$best.title[0] }
        $ct = $best.'container-title'
        if ($ct -and $ct.Count -gt 0) { $gotJournal = [string]$ct[0] }
        $dp = $best.issued.'date-parts'
        if ($dp) { $gotYear = [string](@($dp)[0][0]) }
    }

    if (-not $status) {
        if ($null -eq $best) {
            $status = 'NOTFOUND'
        } else {
            $bad = @(); $filled = @()

            if ($r.expected_doi) {
                if ($gotDoi -and ($gotDoi.ToLowerInvariant() -ne $r.expected_doi.ToLowerInvariant())) {
                    $bad += "doi(want=$($r.expected_doi) got=$gotDoi)"
                }
            } elseif ($gotDoi) { $filled += "doi=$gotDoi" }

            if ($r.expected_volume) {
                if ($gotVol -and ($gotVol -ne $r.expected_volume)) {
                    $bad += "vol(want=$($r.expected_volume) got=$gotVol)"
                }
            } elseif ($gotVol) { $filled += "vol=$gotVol" }

            # Some publishers (notably Chinese-language journals) register only
            # the START page.  "1367" against an expected "1367-1376" is not a
            # contradiction, it is an incomplete record -- do not call it a
            # mismatch, or a correct entry gets flagged forever.
            $wantPage = Normalize-Pages $r.expected_page
            $havePage = Normalize-Pages $gotPage
            $partial  = @()
            if ($wantPage) {
                if ($havePage -and ($havePage -ne $wantPage)) {
                    if ($wantPage.StartsWith($havePage + '-')) {
                        $partial += "page(Crossref has start page only: $gotPage)"
                    } else {
                        $bad += "page(want=$($r.expected_page) got=$gotPage)"
                    }
                }
            } elseif ($havePage) { $filled += "page=$gotPage" }

            # A row resolved BY DOI is identified by that DOI.  A weak title
            # score then says the stored title string is rough (Greek letters,
            # subscripts, slashes), not that the wrong paper came back -- so it
            # must not be downgraded to LOWSCORE.  Flag it and move on.
            $titleWarn = ($bestScore -lt 0.6)

            if     ($bad.Count -gt 0)         { $status = 'MISMATCH'; $note = ($bad -join '; ') }
            elseif ($partial.Count -gt 0)     { $status = 'PARTIAL';  $note = ($partial + $filled) -join '; ' }
            elseif ($titleWarn -and $method -ne 'doi') {
                                                $status = 'LOWSCORE'; $note = "titleScore=$([math]::Round($bestScore,2))" }
            elseif ($filled.Count -gt 0)      { $status = 'FILLED';   $note = ($filled -join '; ') }
            else                              { $status = 'OK' }

            if ($titleWarn -and $method -eq 'doi') {
                $note = (@($note, "titleScore=$([math]::Round($bestScore,2)) (stored title is rough; DOI resolved)") |
                         Where-Object { $_ }) -join '; '
            }
        }
    }

    $results += [pscustomobject]@{
        key         = $r.key
        status      = $status
        method      = $method
        titleScore  = [math]::Round($bestScore, 2)
        got_doi     = $gotDoi
        got_volume  = $gotVol
        got_issue   = $gotIss
        got_page    = $gotPage
        got_year    = $gotYear
        got_journal = $gotJournal
        got_title   = $gotTitle
        note        = $note
        want_doi    = $r.expected_doi
        want_volume = $r.expected_volume
        want_page   = $r.expected_page
    }

    $colour = switch ($status) {
        'OK'       { 'Green' }
        'FILLED'   { 'Cyan' }
        'PARTIAL'  { 'DarkCyan' }
        'MISMATCH' { 'Red' }
        'LOWSCORE' { 'Yellow' }
        'NOTFOUND' { 'DarkGray' }
        default    { 'Magenta' }
    }
    $line = "{0,-6} {1,-9} {2}" -f $r.key, $status, $note
    Write-Host $line -ForegroundColor $colour

    Start-Sleep -Milliseconds 250   # Crossref 예의상 호출 간격
}

Write-Progress -Activity 'Crossref 조회' -Completed
$results | Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8

Write-Host ("=" * 78)
$summary = $results | Group-Object status | Sort-Object Name
foreach ($g in $summary) { Write-Host ("{0,-9} {1}" -f $g.Name, $g.Count) }
Write-Host ""
Write-Host "결과 저장: $OutputCsv" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음: MISMATCH 를 먼저 보세요 — 문서의 값이 틀렸다는 뜻입니다." -ForegroundColor Yellow
Write-Host "      FILLED 는 빈칸이 채워진 것이니 docs/REFS_CANDIDATES.md 에 반영하면 됩니다."
Write-Host ""
Write-Host "★ NOTFOUND 는 '그 논문이 없다'는 뜻이 아닙니다 — '이 질의로는 못 찾았다'는 뜻입니다." -ForegroundColor Yellow
Write-Host "  학회 프로시딩·NASA TM·구소련지는 애초에 Crossref에 없으므로 정상이고,"
Write-Host "  DOI를 아는 항목은 method 열이 'doi' 로 뜨면 직접 조회로 확인된 것입니다."
Write-Host "  method='doi-fail' 은 그 DOI 자체가 틀렸을 수 있다는 신호이니 눈으로 확인하세요."
