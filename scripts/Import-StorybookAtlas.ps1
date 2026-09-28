[CmdletBinding()]
param(
    [string]$Archive,
    [Parameter(Mandatory=$true)][string]$Destination
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$commit = '68a838650fb177afb5e6a63c558dc4ae6bf29b56'
$expected = '364c5896a4b181def2420e1b30f54043b3c0ef35812db24b53fe79f1aa1a92f5'
$url = "https://codeload.github.com/MelchiorDahrk/Project-Atlas/zip/$commit"
$root = [IO.Path]::GetFullPath($Destination).TrimEnd('\','/')
if (Test-Path -LiteralPath $root) { throw 'Choose a new destination; existing packs are never overwritten.' }
$ancestor = Split-Path -Parent $root
while ($ancestor) {
    if ((Test-Path -LiteralPath $ancestor) -and
        ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'Destination parents may not be reparse points.'
    }
    $ancestor = Split-Path -Parent $ancestor
}
if (-not $Archive) {
    $cache = Join-Path (Split-Path -Parent $PSScriptRoot) '.local\graphics\downloads'
    [IO.Directory]::CreateDirectory($cache) | Out-Null
    $Archive = Join-Path $cache "Project-Atlas-$commit.zip"
    if (-not (Test-Path -LiteralPath $Archive)) {
        $partial = $Archive + '.partial'
        if (Test-Path -LiteralPath $partial) { throw 'A partial download already exists; inspect it before retrying.' }
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $partial -TimeoutSec 300
        if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
            throw 'Downloaded archive differs from the pinned source; retained without activation.'
        }
        Move-Item -LiteralPath $partial -Destination $Archive
    }
}
$Archive = (Resolve-Path -LiteralPath $Archive).Path
if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'Archive SHA-256 differs from the reviewed Project Atlas snapshot.'
}
$folders = @('00 Core','01 Textures - MET','02 Urns - Smoothed','03 Redware - Smoothed',
    '04 Emperor Parasols - Smoothed','05 Wood Poles - Hi-Res Texture','09 BC Mushrooms - Smoothed')
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($Archive)
$entries = @()
$seen = @{}
[long]$total = 0
try {
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        if (-not $name.StartsWith("Project-Atlas-$commit/", [StringComparison]::Ordinal)) {
            throw 'Unexpected archive root.'
        }
        $rel = $name.Substring(("Project-Atlas-$commit/").Length)
        if (-not $rel -or $rel.EndsWith('/')) { continue }
        if ($rel.Contains('\') -or $rel.Contains(':') -or ($rel -split '/') -contains '..' -or
            $rel.StartsWith('/') -or (($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000) {
            throw 'Unexpected archive path or link.'
        }
        $folder = ($rel -split '/')[0]
        if ($folders -notcontains $folder -and $rel -notin @('README.md','LICENSE')) { continue }
        if ($rel -notin @('README.md','LICENSE') -and [IO.Path]::GetExtension($rel) -notin @('.nif','.dds')) {
            throw 'Selected asset pack contains an unexpected file type.'
        }
        if ($seen.ContainsKey($rel)) { throw 'Case-insensitive duplicate archive path.' }
        $seen[$rel] = $true
        $target = [IO.Path]::GetFullPath((Join-Path $root $rel))
        if (-not $target.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path escaped destination.' }
        $total += $entry.Length
        if ($entry.Length -gt 64MB -or $total -gt 400MB) { throw 'Selected archive exceeds expected asset limits.' }
        $entries += [pscustomobject]@{entry=$entry;relative=$rel;target=$target}
    }
    if ($entries.Count -ne 732) { throw 'Selected archive file count differs from reviewed snapshot.' }
    [IO.Directory]::CreateDirectory($root) | Out-Null
    $files = @()
    foreach ($selected in $entries) {
        [IO.Directory]::CreateDirectory((Split-Path -Parent $selected.target)) | Out-Null
        $source = $selected.entry.Open()
        $output = [IO.File]::Open($selected.target, [IO.FileMode]::CreateNew)
        try { $source.CopyTo($output) } finally { $source.Dispose(); $output.Dispose() }
        if ((Get-Item -LiteralPath $selected.target).Length -ne $selected.entry.Length) { throw 'Extracted size differs.' }
        $files += [ordered]@{path=$selected.relative;bytes=$selected.entry.Length;
            sha256=(Get-FileHash -LiteralPath $selected.target -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    $receipt = [ordered]@{schema='halveth.storybook-atlas-import.v1';status='EXTRACTED_NOT_ACTIVATED';
        recordedAtUtc=[DateTime]::UtcNow.ToString('o');upstream=$url;commit=$commit;archiveSha256=$expected;
        destination=$root;dataDirectories=@($folders | ForEach-Object {Join-Path $root $_});
        meshFiles=659;textureFiles=71;bytes=$total;files=$files;
        scope='Selected author-provided meshes and MET atlases, retained as a local optional asset pack. No scripts executed. No game configuration changed.'}
    [IO.File]::WriteAllText((Join-Path $root 'import-receipt.json'), ($receipt | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
    [pscustomobject]$receipt | Select-Object schema,status,commit,destination,meshFiles,textureFiles,bytes,dataDirectories | ConvertTo-Json -Depth 4
} finally { $zip.Dispose() }
