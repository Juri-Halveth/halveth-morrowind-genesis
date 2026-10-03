# Material provenance

The own source, copied own MIT geometry kernel, new model, own leaf texture
and plugin use the included MIT license. This does not relicense the bark.

**Bark Brown02 — Rob Tuytel / Poly Haven — CC0 1.0 Universal.**

- Asset: https://polyhaven.com/a/bark_brown_02
- Asset license: https://polyhaven.com/license
- CC0 instrument: https://creativecommons.org/publicdomain/zero/1.0/
- Legal code: https://creativecommons.org/publicdomain/zero/1.0/legalcode

This candidate references the already source-verified1024DDS bark diffuse
and DirectX normal maps from the existing owned vegetation unit. It copies
neither texture. Their exact SHA256 digests are mandatory inputs and appear
in `BUILD_RECEIPT.json`. The earlier source binding includes the asset's own
download metadata, channel/resolution/byte-count/MD5 matches and separate
SHA256 hashes. The generator never writes those files.

The new `Textures/veyra/crown_leaf_01.dds` is generated entirely from own
deterministic code and uses a separate path, leaving old leaf materials
unchanged. The model uses ordinary Phong materials with a small declared
leaf fill emission; it does not implement a physically based leaf model,
transmission, wind animation or a biological species simulation.

No original Morrowind mesh or texture is distributed. The local master is
read to bind its digest/dependency size and to check the new own STAT ID.
