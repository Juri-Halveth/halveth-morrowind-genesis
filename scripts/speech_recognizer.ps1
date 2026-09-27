# A child of voice_input.py only. This script is never started without an
# explicit in-game Yes event for the current world session. No audio file is
# created. German dictation is emitted as UTF-8 JSON lines on stdout.
$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$engine = $null
try {
    Add-Type -AssemblyName System.Speech
    $available = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
    $recognizer = $available | Where-Object { $_.Culture.Name -eq 'de-DE' } | Select-Object -First 1
    if ($null -eq $recognizer) { throw 'NO_GERMAN_RECOGNIZER' }
    $engine = [System.Speech.Recognition.SpeechRecognitionEngine]::new($recognizer)
    $engine.LoadGrammar([System.Speech.Recognition.DictationGrammar]::new())
    $engine.SetInputToDefaultAudioDevice()
    Register-ObjectEvent -InputObject $engine -EventName SpeechRecognized -SourceIdentifier HalvethSpeech | Out-Null
    $engine.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Multiple)
    [Console]::Out.WriteLine('{"status":"ready"}')
    while ($true) {
        $event = Wait-Event -SourceIdentifier HalvethSpeech -Timeout 1
        if ($null -eq $event) { continue }
        try {
            $result = $event.SourceEventArgs.Result
            if ($null -ne $result) {
                $record = @{ type = 'recognized'; text = [string]$result.Text;
                    confidence = [double]$result.Confidence }
                [Console]::Out.WriteLine(($record | ConvertTo-Json -Compress -Depth 3))
                [Console]::Out.Flush()
            }
        } finally {
            Remove-Event -EventIdentifier $event.EventIdentifier
        }
    }
} catch {
    [Console]::Out.WriteLine('{"status":"unavailable"}')
    exit 2
} finally {
    if ($null -ne $engine) {
        try { $engine.RecognizeAsyncStop() } catch {}
        $engine.Dispose()
    }
}
