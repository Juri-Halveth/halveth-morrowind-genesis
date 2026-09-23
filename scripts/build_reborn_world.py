"""Convert the seven original Reborn World PNG masters to OpenMW DDS overrides.

Only format conversion is performed. Source PNG pixels and all Bethesda data
remain unchanged. ``--check`` validates existing outputs without writing.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIALS = (
    'tx_ai_dirtroad_01',
    'tx_land_darkgravel',
    'tx_rm_redrock_01',
    'tx_rm_rock_02',
    'tx_ac_dirt_01',
    'tx_rm_grayrock_01',
    'tx_ma_crackedearth',
)


def pixel_digest(image) -> str:
    return hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()


def build(check: bool = False) -> list[dict]:
    from PIL import Image

    records = []
    for name in MATERIALS:
        source = ROOT / 'assets' / 'RebornWorld' / f'{name}-source.png'
        target = ROOT / 'mod' / 'Textures' / f'{name}.dds'
        with Image.open(source) as image:
            if image.size != (1254, 1254):
                raise ValueError(f'Expected 1254x1254 material: {source}')
            rgb = image.convert('RGB')
            expected = pixel_digest(rgb)
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                rgb.save(target, format='DDS')
        if target.stat().st_size != 128 + 1254 * 1254 * 3:
            raise ValueError(f'Unexpected DDS size: {target}')
        with Image.open(target) as decoded:
            if decoded.size != (1254, 1254) or pixel_digest(decoded) != expected:
                raise ValueError(f'DDS changed source pixels: {target}')
        records.append({'material': name, 'source': str(source.relative_to(ROOT)),
                        'dds': str(target.relative_to(ROOT)), 'pixelSha256': expected})
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for record in build(args.check):
        print(f"{record['material']} {record['pixelSha256']}")
