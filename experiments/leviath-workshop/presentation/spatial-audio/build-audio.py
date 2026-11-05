#!/usr/bin/env python3
"""MIT. Decode one digest-bound local CC0 source; no network or installation."""
import argparse
import array
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave
import zipfile

ARCHIVE_SHA = '029d734af1582474edf3a694d1b0cebc97c1c152f2f39fa34d4c2bafc5de77f8'
MEMBER = 'Audio/impactBell_heavy_000.ogg'
SOURCE_SHA = '94b8bb5f2d43ab65e4bcc32b28562416e9bc2c51d9fd4be1e333660ee52f977f'
LICENSE_SHA = 'b49aa9c56b04528b95913de13e506a0f7c5e807b9925db9bfef86af1f91120db'
BASE = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--ffmpeg', required=True, type=Path)
    args = parser.parse_args()
    archive = args.archive.read_bytes()
    if sha(archive) != ARCHIVE_SHA:
        raise ValueError('Source archive SHA256 does not match the pinned CC0 package')
    with zipfile.ZipFile(args.archive) as z:
        source, license_data = z.read(MEMBER), z.read('License.txt')
    if sha(source) != SOURCE_SHA or sha(license_data) != LICENSE_SHA:
        raise ValueError('Bound source or license member differs')
    version = subprocess.run([str(args.ffmpeg), '-version'], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    output = BASE / 'mod' / 'Sound' / 'veyra' / 'courier_bell_mono.wav'
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='veyra-audio-') as temporary:
        input_file = Path(temporary) / 'source.ogg'
        candidate = Path(temporary) / 'candidate.wav'
        input_file.write_bytes(source)
        subprocess.run([str(args.ffmpeg), '-hide_banner', '-loglevel', 'error',
            '-nostdin', '-y', '-i', str(input_file), '-map_metadata', '-1',
            '-af', 'pan=mono|c0=0.5*c0+0.5*c1', '-ar', '44100',
            '-c:a', 'pcm_s16le', str(candidate)], check=True)
        with wave.open(str(candidate), 'rb') as wav:
            channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
            samples = array.array('h', wav.readframes(frames))
        if sys.byteorder != 'little': samples.byteswap()
        if channels != 1 or width != 2 or rate != 44100 or not samples:
            raise ValueError('Unexpected decoded PCM contract')
        peak = max(abs(s) for s in samples)
        clipped = sum(1 for s in samples if s <= -32768 or s >= 32767)
        if clipped: raise ValueError('Clipping found in mono PCM')
        data = candidate.read_bytes()
        output.write_bytes(data)
    (BASE/'KENNEY-LICENSE.txt').write_bytes(license_data)
    receipt = {
        'schema':'veyra.spatial-audio-asset.v1', 'version':'0.1.0',
        'recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':{'publisher':'Kenney', 'package':'Impact Sounds1.0',
            'url':'https://kenney.nl/assets/impact-sounds', 'license':'CC0-1.0',
            'archiveSha256':ARCHIVE_SHA, 'member':MEMBER, 'memberSha256':SOURCE_SHA,
            'licenseMemberSha256':LICENSE_SHA},
        'transform':{'operator':'equal stereo-channel mean', 'channelsIn':2, 'channelsOut':1,
            'formula':'mono=0.5*left+0.5*right', 'filter':'pan=mono|c0=0.5*c0+0.5*c1',
            'codec':'pcm_s16le','resamplingHz':44100, 'normalization':False,
            'ffmpegVersion':version, 'ffmpegExecutableSha256':sha(args.ffmpeg.read_bytes())},
        'output':{'path':'mod/Sound/veyra/courier_bell_mono.wav','bytes':len(data),
            'sha256':sha(data),'channels':channels,'sampleWidthBytes':width,
            'sampleRateHz':rate,'frames':frames,'durationSeconds':frames/rate,
            'peakAmplitudeInt16':peak,'rmsNormalized':math.sqrt(sum(s*s for s in samples)/len(samples))/32768,
            'clippedSamples':clipped},
        'buildSourceSha256':sha(Path(__file__).read_bytes()),
        'sourceMutation':False,'networkEffects':0,'temporarySourceRemoved':True,
        'claimCeiling':'FORMAT_AND_PCM_OBSERVATION_ONLY',
        'humanAudition':'NOT_PERFORMED','nativeSpatialPlayback':'PENDING_ROOT_PROBE',
    }
    (BASE/'ASSET_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt['output'],indent=2))

if __name__ == '__main__': main()
