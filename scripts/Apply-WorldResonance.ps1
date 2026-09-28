[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $env:USERPROFILE 'AppData\Local\HALVETH\Morrowind Genesis'),
    [switch]$Apply
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$install = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $InstallRoot).Path).TrimEnd('\','/')
$utf8 = [Text.UTF8Encoding]::new($false)
$files = @('mod/halveth.omwscripts','mod/scripts/halveth/player.lua','server.py',
    'mod/scripts/halveth/resonance_rules.lua','mod/scripts/halveth/world_resonance.lua',
    'mod/scripts/halveth/world_resonance_global.lua')
function Hash-Bytes([byte[]]$Raw) {
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Raw))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
function Bound-Path([string]$Relative) {
    if ([IO.Path]::IsPathRooted($Relative) -or ($Relative -split '[/\\]') -contains '..') { throw 'Invalid relative patch path.' }
    $target=[IO.Path]::GetFullPath((Join-Path $install $Relative))
    if (-not $target.StartsWith($install+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Patch path escaped the selected installation.' }
    $cursor=$target
    while ($cursor -and $cursor -ne $install) {
        if (Test-Path -LiteralPath $cursor) {
            $item=Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Patch child is a reparse point: $cursor" }
        }
        $cursor=Split-Path -Parent $cursor
    }
    return $target
}
function Write-Atomic([string]$Path,[byte[]]$Bytes) {
    $parent=Split-Path -Parent $Path
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $temporary=$Path+'.resonance-'+[Guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllBytes($temporary,$Bytes)
        if ((Get-FileHash -LiteralPath $temporary -Algorithm SHA256).Hash.ToLowerInvariant() -ne (Hash-Bytes $Bytes)) { throw 'Staged hash mismatch.' }
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporary,$Path,[NullString]::Value) }
        else { [IO.File]::Move($temporary,$Path) }
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
}
function Assert-Closed {
    $knownAliases=@(
        (Join-Path $env:USERPROFILE 'AppData\Local\HALVETH\Morrowind Genesis'),
        (Join-Path $env:USERPROFILE 'AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\HALVETH\Morrowind Genesis')
    )
    $samePackagedInstall=$knownAliases -contains $install
    $processes=@(Get-CimInstance Win32_Process -Filter "Name='openmw.exe' OR Name='HALVETH Morrowind.exe' OR Name='python.exe' OR Name='pythonw.exe'")
    foreach($process in $processes) {
        # Check both path forms on packaged Windows hosts; never stop processes here.
        $own=($process.ExecutablePath -and $process.ExecutablePath.StartsWith($install+'\',[StringComparison]::OrdinalIgnoreCase)) -or
            ($process.CommandLine -and $process.CommandLine.IndexOf($install,[StringComparison]::OrdinalIgnoreCase) -ge 0) -or
            ($samePackagedInstall -and $process.ExecutablePath -and ($knownAliases | Where-Object {
                $process.ExecutablePath.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase)
            }))
        if ($own) { throw "Close the installed game or companion before patching (PID $($process.ProcessId))." }
    }
}
if (-not (Test-Path -LiteralPath (Bound-Path 'HALVETH Morrowind.exe'))) { throw 'Selected directory has no Genesis entry EXE.' }
$statePath=Bound-Path 'install-state.json'
$stateRaw=[IO.File]::ReadAllBytes($statePath)
$state=$utf8.GetString($stateRaw).TrimStart([char]0xFEFF) | ConvertFrom-Json
if ($state.version -ne '1.0.6-preview') { throw 'This additive patch requires Genesis 1.0.6-preview.' }
$records=@{}
foreach($record in $state.files) {
    if ($records.ContainsKey($record.path)) { throw 'Duplicate installed manifest path.' }
    $records[$record.path]=$record
}
$snapshot=@{}
$details=@()
foreach($relative in $files) {
    $source=Join-Path $sourceRoot $relative
    $raw=[IO.File]::ReadAllBytes($source)
    $snapshot[$relative]=$raw
    $name='app/'+$relative
    $target=Bound-Path $name
    $exists=Test-Path -LiteralPath $target -PathType Leaf
    $before=if($exists){(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()}else{$null}
    if ($records.ContainsKey($name)) {
        if (-not $exists -or $before -ne $records[$name].sha256 -or (Get-Item -LiteralPath $target).Length -ne $records[$name].bytes) { throw "Independent installed change: $name" }
    } elseif($exists) { throw "New patch path already exists outside the manifest: $name" }
    $details += [ordered]@{path=$name;existed=$exists;beforeSha256=$before;afterSha256=(Hash-Bytes $raw);bytes=$raw.Length}
}
$plan=[ordered]@{schema='halveth.world-resonance-patch.v1';status='PLAN';recordedAtUtc=[DateTime]::UtcNow.ToString('o');
    install=$install;installStateBeforeSha256=(Hash-Bytes $stateRaw);files=$details;
    originalsAndSavesModified=$false;modelFilesModified=$false;restartRequired=$true}
if (-not $Apply) { $plan | ConvertTo-Json -Depth 8; return }
Assert-Closed
$backup=Bound-Path ('app/.local/patch-backups/world-resonance/'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
$lockPath=Bound-Path 'app/.local/world-resonance-patching.lock'
[IO.Directory]::CreateDirectory((Split-Path -Parent $lockPath)) | Out-Null
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
$written=[Collections.Generic.List[string]]::new()
$stateWritten=$false
$receiptPath=Join-Path $backup 'receipt.json'
try {
    Assert-Closed
    if ((Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.installStateBeforeSha256) { throw 'Installation manifest changed after preflight.' }
    [IO.Directory]::CreateDirectory($backup) | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $backup 'install-state.json'),$stateRaw)
    foreach($detail in $details) {
        $target=Bound-Path $detail.path
        if($detail.existed) {
            if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $detail.beforeSha256) { throw 'Target changed after preflight.' }
            $copy=Join-Path $backup $detail.path
            [IO.Directory]::CreateDirectory((Split-Path -Parent $copy)) | Out-Null
            [IO.File]::Copy($target,$copy,$false)
            if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash.ToLowerInvariant() -ne $detail.beforeSha256) { throw 'Backup hash mismatch.' }
        }
    }
    $plan.status='APPLYING';$plan['backup']=$backup
    [IO.File]::WriteAllText($receiptPath,($plan | ConvertTo-Json -Depth 8),$utf8)
    foreach($detail in $details) {
        $target=Bound-Path $detail.path
        if($detail.existed) {
            if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $detail.beforeSha256) { throw 'Target changed before write.' }
        } elseif(Test-Path -LiteralPath $target) { throw 'New target appeared before write.' }
        Write-Atomic $target $snapshot[$detail.path.Substring(4)]
        $written.Add($detail.path)
        if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $detail.afterSha256) { throw 'Installed hash mismatch.' }
        if($records.ContainsKey($detail.path)) { $records[$detail.path].sha256=$detail.afterSha256;$records[$detail.path].bytes=$detail.bytes }
        else { $state.files += [pscustomobject]@{path=$detail.path;sha256=$detail.afterSha256;bytes=$detail.bytes} }
    }
    if(-not $state.PSObject.Properties['features']) { $state | Add-Member -NotePropertyName features -NotePropertyValue ([pscustomobject]@{}) }
    $state.features | Add-Member -NotePropertyName worldResonance -NotePropertyValue ([pscustomobject]@{version=1;installedAtUtc=[DateTime]::UtcNow.ToString('o');backup=$backup}) -Force
    Write-Atomic $statePath ($utf8.GetBytes(($state | ConvertTo-Json -Depth 50)))
    $stateWritten=$true
    $plan.status='APPLIED';$plan['completedAtUtc']=[DateTime]::UtcNow.ToString('o')
    $plan['writtenPaths']=@($written.ToArray())
    $plan['installStateAfterSha256']=(Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText($receiptPath,($plan | ConvertTo-Json -Depth 8),$utf8)
    $plan | ConvertTo-Json -Depth 8
} catch {
    $failure=$_
    $rollbackErrors=@()
    if($stateWritten) { try { Write-Atomic $statePath $stateRaw } catch { $rollbackErrors += 'manifest: '+$_.Exception.Message } }
    foreach($name in $written) {
        try {
            $detail=$details | Where-Object { $_.path -eq $name }
            $target=Bound-Path $name
            if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $detail.afterSha256) { throw 'A subsequent edit prevents automatic rollback.' }
            if($detail.existed) { Write-Atomic $target ([IO.File]::ReadAllBytes((Join-Path $backup $name))) }
            else { Remove-Item -LiteralPath $target }
        } catch { $rollbackErrors += $name+': '+$_.Exception.Message }
    }
    if(Test-Path -LiteralPath $backup) {
        $plan.status=if($rollbackErrors.Count){'ROLLBACK_INCOMPLETE'}else{'ROLLED_BACK'}
        $plan['failure']=$failure.Exception.Message;$plan['rollbackErrors']=$rollbackErrors
        $plan['writtenPaths']=@($written.ToArray())
        [IO.File]::WriteAllText($receiptPath,($plan | ConvertTo-Json -Depth 8),$utf8)
    }
    throw $failure
} finally {
    $lock.Dispose()
    if(Test-Path -LiteralPath $lockPath) { Remove-Item -LiteralPath $lockPath }
}
