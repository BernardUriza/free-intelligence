$models = @('qwen3:1.7b', 'qwen3:8b')
$tests = @(
    @{ Name = 'Short'; Prompt = 'Say hi' },
    @{ Name = 'Medium'; Prompt = 'Explain what a CPU is in 2 sentences' },
    @{ Name = 'Long'; Prompt = 'Write a haiku about programming, then explain each line' }
)

Write-Host ''
Write-Host '  ========================================' -ForegroundColor Cyan
Write-Host '  FI EDGE BENCHMARK' -ForegroundColor Yellow
Write-Host '  ========================================' -ForegroundColor Cyan
Write-Host ''

$results = @()

foreach ($model in $models) {
    Write-Host "  Testing: $model" -ForegroundColor Yellow
    Write-Host '  ----------------------------------------' -ForegroundColor DarkGray

    foreach ($test in $tests) {
        Write-Host "    $($test.Name): " -NoNewline -ForegroundColor Gray

        $body = @{
            model = $model
            messages = @(@{ role = 'user'; content = $test.Prompt })
            think = $false
            stream = $false
        } | ConvertTo-Json -Depth 3

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri 'http://localhost:11434/api/chat' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 120
        $sw.Stop()

        $totalMs = $sw.ElapsedMilliseconds
        $evalTokens = $response.eval_count
        $evalDurationNs = $response.eval_duration
        $loadDurationNs = $response.load_duration
        $promptDurationNs = $response.prompt_eval_duration

        $tokensPerSec = if ($evalDurationNs -gt 0) { [math]::Round($evalTokens / ($evalDurationNs / 1000000000), 1) } else { 0 }
        $ttftMs = [math]::Round(($loadDurationNs + $promptDurationNs) / 1000000, 0)

        Write-Host "$($totalMs)ms" -NoNewline -ForegroundColor Green
        Write-Host ' | ' -NoNewline -ForegroundColor DarkGray
        Write-Host "$tokensPerSec t/s" -NoNewline -ForegroundColor Cyan
        Write-Host ' | ' -NoNewline -ForegroundColor DarkGray
        Write-Host "TTFT: $($ttftMs)ms" -NoNewline -ForegroundColor Magenta
        Write-Host ' | ' -NoNewline -ForegroundColor DarkGray
        Write-Host "$evalTokens tokens" -ForegroundColor DarkGray

        $results += @{
            Model = $model
            Test = $test.Name
            TotalMs = $totalMs
            TokensPerSec = $tokensPerSec
            TTFTMs = $ttftMs
            Tokens = $evalTokens
        }
    }
    Write-Host ''
}

Write-Host '  ========================================' -ForegroundColor Cyan
Write-Host '  SUMMARY' -ForegroundColor Yellow
Write-Host '  ========================================' -ForegroundColor Cyan
Write-Host ''

$modelGroups = $results | Group-Object -Property Model
foreach ($group in $modelGroups) {
    $avgTps = [math]::Round(($group.Group | Measure-Object -Property TokensPerSec -Average).Average, 1)
    $avgTtft = [math]::Round(($group.Group | Measure-Object -Property TTFTMs -Average).Average, 0)

    Write-Host "  $($group.Name)" -ForegroundColor Yellow
    Write-Host "    Avg Speed: " -NoNewline -ForegroundColor Gray
    Write-Host "$avgTps tokens/sec" -ForegroundColor Cyan
    Write-Host "    Avg TTFT:  " -NoNewline -ForegroundColor Gray
    Write-Host "$($avgTtft)ms" -ForegroundColor Magenta
    Write-Host ''
}
