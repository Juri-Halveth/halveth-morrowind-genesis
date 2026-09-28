[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE 'AppData\Local\HALVETH\Morrowind Genesis'),
    [switch]$DryRun,
    [switch]$Apply,
    [switch]$Storybook,
    [string]$ExpectedPlanSha256
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($DryRun -and $Apply) { throw 'Choose -DryRun or -Apply, not both.' }
if ($Apply -and $ExpectedPlanSha256 -notmatch '^[a-fA-F0-9]{64}$') {
    throw 'Apply requires -ExpectedPlanSha256 from a current dry run.'
}
$sourceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\','/')
$install = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $InstallRoot).Path).TrimEnd('\','/')
$utf8 = [Text.UTF8Encoding]::new($false)
# This list is the complete write scope; game data, settings and graphics manifests are excluded.
$files = @('server.py', 'dialogue_method.py', 'mod/scripts/halveth/player.lua',
    'scripts/graphics_profile.py', 'mod/shaders/halveth_sculpted.omwfx')
if ($Storybook) { $files += 'mod/shaders/halveth_storybook.omwfx' }

function Hash-Bytes([byte[]]$Raw) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Raw))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
function Bound-Path([string]$Root, [string]$Relative) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or [IO.Path]::IsPathRooted($Relative) -or
        $Relative.Contains(':') -or ($Relative -split '[/\\]') -contains '..') {
        throw 'Invalid relative patch path.'
    }
    $target = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if (-not $target.StartsWith($Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Patch path escaped its selected root.'
    }
    $cursor = $target
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Patch path is a reparse point: $cursor"
            }
        }
        if ($cursor -eq $Root) { break }
        $cursor = Split-Path -Parent $cursor
    }
    return $target
}
function File-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Write-Atomic([string]$Path, [byte[]]$Bytes) {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
    $temporary = $Path + '.visual-refresh-' + [Guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllBytes($temporary, $Bytes)
        if ((File-Hash $temporary) -ne (Hash-Bytes $Bytes)) { throw 'Staged hash mismatch.' }
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporary, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temporary, $Path) }
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary }
    }
}
function Assert-Closed {
    $aliases = @(
        (Join-Path $env:USERPROFILE 'AppData\Local\HALVETH\Morrowind Genesis'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\HALVETH\Morrowind Genesis')
    )
    $samePackagedInstall = $aliases -contains $install
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='openmw.exe' OR Name='HALVETH Morrowind.exe' OR Name='python.exe' OR Name='pythonw.exe'")
    foreach ($process in $processes) {
        $own = ($process.ExecutablePath -and $process.ExecutablePath.StartsWith($install + '\', [StringComparison]::OrdinalIgnoreCase)) -or
            ($process.CommandLine -and $process.CommandLine.IndexOf($install, [StringComparison]::OrdinalIgnoreCase) -ge 0) -or
            ($samePackagedInstall -and $process.ExecutablePath -and ($aliases | Where-Object {
                $process.ExecutablePath.StartsWith($_ + '\', [StringComparison]::OrdinalIgnoreCase)
            }))
        if ($own) { throw "Close the installed game or companion before patching (PID $($process.ProcessId))." }
    }
}
function Assert-Target($Detail) {
    $target = Bound-Path $install $Detail.path
    if ($Detail.existed) {
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
            (File-Hash $target) -ne $Detail.beforeSha256 -or
            (Get-Item -LiteralPath $target).Length -ne $Detail.beforeBytes) {
            throw "Independent installed change: $($Detail.path)"
        }
    } elseif (Test-Path -LiteralPath $target) {
        throw "New patch path already exists outside the manifest: $($Detail.path)"
    }
}

if (-not (Test-Path -LiteralPath (Bound-Path $install 'HALVETH Morrowind.exe') -PathType Leaf)) {
    throw 'Selected directory has no Genesis entry EXE.'
}
$statePath = Bound-Path $install 'install-state.json'
$stateRaw = [IO.File]::ReadAllBytes($statePath)
$state = $utf8.GetString($stateRaw).TrimStart([char]0xFEFF) | ConvertFrom-Json
if ($state.version -ne '1.0.6-preview') { throw 'This additive patch requires Genesis 1.0.6-preview.' }
if (-not $state.PSObject.Properties['files'] -or $null -eq $state.files) { throw 'Missing installed file manifest.' }
$records = @{}
foreach ($record in $state.files) {
    if (-not ($record.path -is [string]) -or [string]::IsNullOrWhiteSpace($record.path) -or
        $record.sha256 -notmatch '^[a-fA-F0-9]{64}$' -or
        [string]$record.bytes -notmatch '^\d+$') { throw 'Invalid installed manifest record.' }
    $normalized = $record.path.Replace('\', '/')
    if ($records.ContainsKey($normalized)) { throw 'Duplicate installed manifest path.' }
    $records[$normalized] = $record
}
if ($state.PSObject.Properties['features'] -and $null -ne $state.features -and
    -not ($state.features -is [pscustomobject])) { throw 'Invalid installed feature metadata.' }
$snapshot = @{}
$details = @()
foreach ($relative in $files) {
    $source = Bound-Path $sourceRoot $relative
    $raw = [IO.File]::ReadAllBytes($source)
    $snapshot[$relative] = $raw
    $name = 'app/' + $relative
    $target = Bound-Path $install $name
    $managed = $records.ContainsKey($name)
    $detail = [ordered]@{
        path = $name
        existed = $managed
        beforeSha256 = $(if ($managed) { $records[$name].sha256.ToLowerInvariant() } else { $null })
        beforeBytes = $(if ($managed) { [long]$records[$name].bytes } else { $null })
        afterSha256 = (Hash-Bytes $raw)
        bytes = $raw.Length
    }
    Assert-Target $detail
    $details += $detail
}
# Only stable inputs form the plan digest. Receipts have separate timestamps and outcomes.
$contract = [ordered]@{
    schema = 'halveth.visual-refresh-patch.v1'
    requiredInstallVersion = '1.0.6-preview'
    install = $install
    installStateBeforeSha256 = (Hash-Bytes $stateRaw)
    features = [ordered]@{ sculptedVisuals = '1.0.0'; dialogueMethod = '1.0.0' }
    files = $details
}
if ($Storybook) { $contract.features['storybookVisuals'] = '1.0.0' }
$planSha256 = Hash-Bytes ($utf8.GetBytes(($contract | ConvertTo-Json -Depth 12 -Compress)))
$receipt = [ordered]@{
    schema = $contract.schema
    status = 'PLAN'
    planSha256 = $planSha256
    recordedAtUtc = [DateTime]::UtcNow.ToString('o')
    contract = $contract
    originalsAndSavesModified = $false
    settingsAndGraphicsManifestModified = $false
    thirdPartyAssetsImported = $false
    restartRequired = $true
}
if (-not $Apply) { $receipt | ConvertTo-Json -Depth 14; return }
if ($ExpectedPlanSha256.ToLowerInvariant() -ne $planSha256) { throw 'Patch plan changed; review a fresh dry run before applying.' }
Assert-Closed
$backup = Bound-Path $install ('app/.local/patch-backups/visual-refresh/' +
    [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
$lockPath = Bound-Path $install 'app/.local/visual-refresh-patching.lock'
[IO.Directory]::CreateDirectory((Split-Path -Parent $lockPath)) | Out-Null
$lock = [IO.File]::Open($lockPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
$written = [Collections.Generic.List[string]]::new()
$stateWritten = $false
$stateAfterHash = $null
$receiptPath = Join-Path $backup 'receipt.json'
try {
    Assert-Closed
    if ((File-Hash $statePath) -ne $contract.installStateBeforeSha256) { throw 'Installation manifest changed after preflight.' }
    foreach ($detail in $details) {
        Assert-Target $detail
        $source = Bound-Path $sourceRoot $detail.path.Substring(4)
        if ((File-Hash $source) -ne $detail.afterSha256) { throw 'Source changed after preflight.' }
    }
    [IO.Directory]::CreateDirectory($backup) | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $backup 'install-state.json'), $stateRaw)
    if ((File-Hash (Join-Path $backup 'install-state.json')) -ne $contract.installStateBeforeSha256) { throw 'Manifest backup hash mismatch.' }
    foreach ($detail in $details) {
        if ($detail.existed) {
            Assert-Target $detail
            $copy = Bound-Path $backup $detail.path
            [IO.Directory]::CreateDirectory((Split-Path -Parent $copy)) | Out-Null
            [IO.File]::Copy((Bound-Path $install $detail.path), $copy, $false)
            if ((File-Hash $copy) -ne $detail.beforeSha256) { throw 'Backup hash mismatch.' }
        }
    }
    $receipt.status = 'APPLYING'
    $receipt['backup'] = $backup
    [IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 14), $utf8)
    foreach ($detail in $details) {
        Assert-Target $detail
        $target = Bound-Path $install $detail.path
        Write-Atomic $target $snapshot[$detail.path.Substring(4)]
        $written.Add($detail.path)
        if ((File-Hash $target) -ne $detail.afterSha256) { throw 'Installed hash mismatch.' }
        if ($records.ContainsKey($detail.path)) {
            $records[$detail.path].sha256 = $detail.afterSha256
            $records[$detail.path].bytes = $detail.bytes
        } else {
            $state.files += [pscustomobject]@{ path = $detail.path; sha256 = $detail.afterSha256; bytes = $detail.bytes }
        }
    }
    if ((File-Hash $statePath) -ne $contract.installStateBeforeSha256) { throw 'Installation manifest changed before commit.' }
    if (-not $state.PSObject.Properties['features'] -or $null -eq $state.features) {
        $state | Add-Member -NotePropertyName features -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    foreach ($feature in $contract.features.Keys) {
        $state.features | Add-Member -NotePropertyName $feature -NotePropertyValue ([pscustomobject]@{
            version = '1.0.0'; installedAtUtc = [DateTime]::UtcNow.ToString('o');
            planSha256 = $planSha256; backup = $backup
        }) -Force
    }
    $stateAfterRaw = $utf8.GetBytes(($state | ConvertTo-Json -Depth 50))
    $stateAfterHash = Hash-Bytes $stateAfterRaw
    Write-Atomic $statePath $stateAfterRaw
    $stateWritten = $true
    if ((File-Hash $statePath) -ne $stateAfterHash) { throw 'Installed manifest hash mismatch.' }
    $receipt.status = 'APPLIED'
    $receipt['completedAtUtc'] = [DateTime]::UtcNow.ToString('o')
    $receipt['writtenPaths'] = @($written.ToArray())
    $receipt['installStateAfterSha256'] = $stateAfterHash
    [IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 14), $utf8)
    $receipt | ConvertTo-Json -Depth 14
} catch {
    $failure = $_
    $rollbackErrors = @()
    if ($stateWritten) {
        try {
            if ((File-Hash $statePath) -ne $stateAfterHash) { throw 'A subsequent manifest edit prevents automatic rollback.' }
            Write-Atomic $statePath $stateRaw
        } catch { $rollbackErrors += 'manifest: ' + $_.Exception.Message }
    }
    for ($index = $written.Count - 1; $index -ge 0; $index--) {
        $name = $written[$index]
        try {
            $detail = $details | Where-Object { $_.path -eq $name }
            $target = Bound-Path $install $name
            if ((File-Hash $target) -ne $detail.afterSha256) { throw 'A subsequent edit prevents automatic rollback.' }
            if ($detail.existed) {
                $copy = Bound-Path $backup $name
                if ((File-Hash $copy) -ne $detail.beforeSha256) { throw 'Rollback backup hash mismatch.' }
                Write-Atomic $target ([IO.File]::ReadAllBytes($copy))
                if ((File-Hash $target) -ne $detail.beforeSha256) { throw 'Restored hash mismatch.' }
            } else { Remove-Item -LiteralPath $target }
        } catch { $rollbackErrors += $name + ': ' + $_.Exception.Message }
    }
    if (Test-Path -LiteralPath $backup) {
        $receipt.status = if ($rollbackErrors.Count) { 'ROLLBACK_INCOMPLETE' } else { 'ROLLED_BACK' }
        $receipt['failure'] = $failure.Exception.Message
        $receipt['rollbackErrors'] = $rollbackErrors
        $receipt['writtenPaths'] = @($written.ToArray())
        [IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 14), $utf8)
    }
    throw $failure
} finally {
    $lock.Dispose()
    if (Test-Path -LiteralPath $lockPath) { Remove-Item -LiteralPath $lockPath }
}
