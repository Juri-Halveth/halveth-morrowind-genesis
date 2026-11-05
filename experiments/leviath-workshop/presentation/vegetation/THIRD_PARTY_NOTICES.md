# Source licenses

The generator, newly authored tree geometry, new leaf texture and plugin source
are covered by the MIT license in the parent package. This does not relicense
the bark texture.

**Bark Brown 02** — Rob Tuytel / Poly Haven, **CC0 1.0 Universal**.

- Asset: https://polyhaven.com/a/bark_brown_02
- Poly Haven asset license: https://polyhaven.com/license
- CC0 instrument: https://creativecommons.org/publicdomain/zero/1.0/
- Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode

The local source contains the asset's original `files.json` download metadata.
The generator requires both input files to match the listed byte count and
MD5 for their exact channel, format and resolution, and separately binds SHA256.
The generated 1024-pixel diffuse and normal maps retain that CC0 source license.
Their source and output digests appear in `BUILD_RECEIPT.json`.

No original Morrowind mesh or texture is distributed. `Morrowind.esm` is a
local prerequisite used to resolve the target static ID and bind existing
references. It remains at its original source location. The generator never
modifies it or the previous corrected meshes.

The model uses classic Phong materials plus the existing OpenMW automatic
normal-map option. It does not implement or claim a physically based BRDF.
