# Test FI Edge Observability with 20 questions
$questions = @(
    'Who is Jake Sully in Avatar 2009?',
    'Who is Frodo Baggins in LOTR?',
    'What is Pandora in Avatar?',
    'What is the One Ring?',
    'What are the Navi in Avatar?',
    'Who is Gandalf?',
    'What is unobtanium?',
    'What is Mordor?',
    'Who is Neytiri?',
    'Who is Aragorn?',
    'What is the Tree of Souls?',
    'What is Mount Doom?',
    'Who is Colonel Quaritch?',
    'Who is Sauron?',
    'What is the Avatar Program?',
    'What are the Nazgul?',
    'What is Eywa?',
    'Who is Gollum?',
    'How does Avatar 2009 end?',
    'How does Return of the King end?'
)

Write-Host "`n=== FI Edge Observability Test ===" -ForegroundColor Yellow
Write-Host "Running 20 questions (Avatar vs LOTR)`n" -ForegroundColor Gray

for ($i = 0; $i -lt $questions.Count; $i++) {
    $q = $questions[$i]
    Write-Host "[$($i+1)/20] $q" -ForegroundColor Cyan

    $body = @{
        model = 'qwen3:1.7b'
        messages = @(@{role='user'; content="$q Answer in 1-2 sentences."})
        think = $false
    } | ConvertTo-Json -Depth 3

    try {
        $resp = Invoke-RestMethod -Uri 'http://localhost:9200/proxy/chat' -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 120

        $content = $resp.message.content
        if ($content.Length -gt 120) { $content = $content.Substring(0,120) + '...' }
        Write-Host "  -> $content" -ForegroundColor Gray
        Write-Host "  Latency: $($resp._latency_ms)ms | Tokens: $($resp.prompt_eval_count + $resp.eval_count)" -ForegroundColor DarkGray
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "`n=== Checking Stats ===" -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri 'http://localhost:9200/stats'
Write-Host "Total calls: $($stats.total_calls)"
Write-Host "Success: $($stats.success_calls) | Errors: $($stats.error_calls)"
Write-Host "Avg latency: $($stats.avg_latency_ms)ms"
Write-Host "Total tokens: $($stats.total_tokens)"

Write-Host "`nBy model:" -ForegroundColor Gray
foreach ($m in $stats.by_model) {
    Write-Host "  $($m.model): $($m.count) calls, $($m.tokens) tokens, avg $($m.avg_latency_ms)ms"
}

Write-Host "`n=== Recent Calls ===" -ForegroundColor Yellow
$calls = Invoke-RestMethod -Uri 'http://localhost:9200/calls?limit=5'
foreach ($c in $calls.calls) {
    $preview = $c.prompt_preview
    if ($preview.Length -gt 50) { $preview = $preview.Substring(0,50) + '...' }
    Write-Host "  [$($c.id)] $preview -> $($c.latency_ms)ms [$($c.status)]" -ForegroundColor Gray
}

Write-Host "`nDone!" -ForegroundColor Green
