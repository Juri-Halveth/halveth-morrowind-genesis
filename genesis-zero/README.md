# Genesis Zero — Living Space

An independent, browser-playable graphics slice authored from this directory's own source. It does not load Morrowind, OpenMW, Morrowind.esm, extracted dialogue, old profiles, external textures, downloaded shaders, fonts, analytics, or network services.

## Run

Open `index.html` directly in a WebGL 2-capable browser. The scene needs no local server, listener, open port, or service process.

## Controls

- **IN DIE WELT** enters the scene.
- **W/A/S/D** moves; click the view to capture/release mouse look.
- **Q/E** changes the phase coordinate that drives the four-dimensional field projection.
- **Space** produces a small walking bounce.
- **PULS GEBEN** creates a new world pulse and advances the original design-notes sequence.
- **SOUND** generates a soft local oscillator bed only after a direct click; no audio file or remote endpoint is loaded.

The world uses a ray-marched distance field, procedural terrain and vegetation, generated lighting, and an animated original squirrel-like creature. The fourth coordinate is an explicit time/phase parameter projected into the visible three-dimensional field. This is an interactive art/graphics prototype, not a physics simulator, a complete game, or a replacement for OpenMW.

## Boundaries

`genesis-zero/` is intentionally source-complete and has no dependency on the main Morrowind companion. It creates a genuinely independent visual starting point. It does not rewrite or delete licensed Morrowind files; those remain preserved as the source installation until an independently authored game with its own complete world data, characters, story, audio, interface, and runtime exists.
