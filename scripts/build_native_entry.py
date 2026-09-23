"""Build a reversible native Morrowind direct-entry candidate from local sources.

Never overwrites the source workshop, installed EXE, shortcuts, or game files.
The candidate's --check-genesis <profile> validates its local paths without
starting Python, the companion, OpenMW, tkinter, or a browser.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(args):
    source = args.native_source.resolve()
    python = args.python.resolve()
    sdk = args.compiler.resolve()
    framework = args.framework.resolve()
    for path in (source / 'Core.cs', source / 'Workshop.cs', source / 'app.manifest', python, sdk):
        if not path.is_file():
            raise FileNotFoundError(path)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = PROJECT / '.local' / 'native-entry-candidate' / stamp
    target.mkdir(parents=True, exist_ok=False)
    baseline = target / 'baseline'
    baseline.mkdir()
    edited = target / 'source'
    edited.mkdir()
    originals = {}
    for name in ('Core.cs', 'Workshop.cs', 'app.manifest'):
        shutil.copy2(source / name, baseline / name)
        shutil.copy2(source / name, edited / name)
        originals[name] = sha(source / name)
        if originals[name] != sha(baseline / name):
            raise IOError('Baseline copy mismatch: ' + name)
    workshop = (edited / 'Workshop.cs').read_text(encoding='utf-8-sig')
    marker = '        if(args.Length==2&&args[0]=="--launch")'
    if workshop.count(marker) != 1:
        raise ValueError('Expected exactly one native launch route; source requires review.')
    insert = ('        if(args.Length==2&&args[0]=="--check-genesis") { GenesisEntry.Validate(root,args[1]); return 0; }\n'
              '        if(args.Length==2&&args[0]=="--genesis") { GenesisEntry.Launch(root,args[1]); return 0; }\n')
    workshop = workshop.replace(marker, insert + marker)
    error_marker = 'args.Length==0||args[0]=="--launch"'
    if workshop.count(error_marker) != 1:
        raise ValueError('Expected exactly one native startup error route; source requires review.')
    workshop = workshop.replace(error_marker, error_marker + '||args[0]=="--genesis"')
    (edited / 'Workshop.cs').write_text(workshop, encoding='utf-8')
    shutil.copy2(PROJECT / 'native' / 'GenesisEntry.cs', edited / 'GenesisEntry.cs')
    exe = target / 'Morrowind-Workshop.exe'
    refs = ('mscorlib', 'System', 'System.Core', 'System.Drawing', 'System.Windows.Forms',
            'System.Web.Extensions', 'System.IO.Compression', 'System.IO.Compression.FileSystem', 'Microsoft.CSharp')
    command = ['dotnet', str(sdk), '/nologo', '/noconfig', '/nostdlib+', '/langversion:latest',
               '/target:winexe', '/platform:x64', '/optimize+', '/utf8output',
               '/main:Halveth.Morrowind.Program', '/out:' + str(exe),
               '/win32manifest:' + str(edited / 'app.manifest')]
    command += ['/reference:' + str(framework / (ref + '.dll')) for ref in refs]
    command += [str(edited / name) for name in ('Core.cs', 'Workshop.cs', 'GenesisEntry.cs')]
    subprocess.run(command, check=True)
    (target / 'genesis-entry.json').write_text(json.dumps({
        'Schema': 1, 'Python': str(python), 'Launcher': str(PROJECT / 'launcher.py')
    }, indent=2) + '\n', encoding='utf-8')
    subprocess.run([str(exe), '--check-genesis', 'beauty'], check=True)
    for name, digest in originals.items():
        if sha(source / name) != digest:
            raise IOError('Original source changed during candidate build: ' + name)
    receipt = {'recordedUtc': datetime.now(timezone.utc).isoformat(),
               'status': 'CANDIDATE_COMPILED_PREFLIGHT_PASS_NOT_INSTALLED',
               'candidateExe': str(exe), 'candidateSha256': sha(exe),
               'configSha256': sha(target / 'genesis-entry.json'),
               'sourceBaseline': str(baseline), 'originalSourcesPreserved': originals,
               'playRoute': ['--genesis', 'beauty'],
               'preflightRoute': ['--check-genesis', 'beauty'],
               'directGenesisRoute': [str(python), str(PROJECT / 'launcher.py'), '--play', '--profile', 'beauty'],
               'startedGame': False, 'installed': False, 'shortcutsChanged': False,
               'knownBoundary': 'Native entry invokes existing local Python internally; OpenMW and its assets remain installed separately.'}
    (target / 'candidate-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-source', type=Path, required=True)
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--compiler', type=Path,
                        default=Path('C:/Program Files/dotnet/sdk/10.0.401/Roslyn/bincore/csc.dll'))
    parser.add_argument('--framework', type=Path,
                        default=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319'))
    build(parser.parse_args())
