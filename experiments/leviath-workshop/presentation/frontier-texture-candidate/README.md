# Frontier materials 0.1.0: texture-only candidate

This isolated VFS layer replaces the three already owned Frontier diffuse
textures. The frozen Frontier ESP, LAND, geometry, region and local material
indices stay byte-identical. Native rendering remains a coordinated root
test. The observed repair target is the obvious repeating grid in the
Frontier native probe `world-candidate/evidence/probe-20261003T022922`,
windows3 and7, reviewed directly by this agent.

The original source uses repeating 128/32-pixel sine patterns. The new source
uses independent seeded random fields at several scales, periodic Gaussian
convolution and smooth domain warping. Ground blends muted grass and soil;
stone has subtle irregular fractures; coastal soil has quieter sand grain.
Each own1024x1024 DXT1 texture has eleven mip levels and occupies699192bytes.
No downloaded image or original-game texture supplies the new material.

Append this line after the Frontier data directory in a separate candidate:

```ini
data="<absolute-path-to-presentation-candidate>/frontier-texture-candidate/mod"
```

There is no new `content=` line. Rollback removes this data layer or restores
the earlier three frozen textures in an owned combined staging copy.

The builder is `build-textures.py`; run it using the existing Python3.14,
NumPy and Pillow through Git Bash. `check-textures.py` independently checks
the exact three-file boundary, DDS mip bytes, decoded border jumps, frozen
Frontier file hashes and a second byte-identical build. The old generator's
six declared FFT peaks account for roughly25percent of decoded variation;
the new files reduce those exact peaks below1percent. That scoped metric
does not prove that every repetition or distant moire is gone.

`TEXTURE_COMPARISON.png` was visually reviewed from decoded DDS pixels.
The new materials have irregular mottling instead of the original diagonal
stripes. It is a flat source preview, not an engine rendering. Every tileable
texture still repeats its complete tile; native filtering, distance and
large-area appearance require comparison at the same position/time/weather.

The root probe should inspect a close ground view, the horizon and a moving
view; visit all three palette materials. Keep geometry and shader settings
fixed during that comparison. A dark or blurry material is still a possible
quality issue and must be assessed from the actual scene.

Own generator, check code and materials use the included MIT license.
The frozen base digest and exact source/runtime versions are in the build
receipt. This is a separate visual candidate, not a mutation of Frontier0.1.0.
