# Upwell fittings reference package

Twenty generated documentary-style concept references cover the nineteen named fittings in `web/control-catalog.js` plus the sealed floor observation port. These are **generated reference variants**, not photographs of real manufactured hardware or exact renders of the production Blender geometry. No production renderer, original prop reference, or original mask was changed.

## Contents

- `contact-sheet.jpg`: visually reviewed index of all twenty independent references.
- `refs/<id>.png`: cropped RGBA reference, retaining native resolution.
- `masks/<id>_alpha.png`: exact alpha channel of the corresponding reference.
- `masks/<id>_silhouette.png`: binary silhouette, alpha >=128.
- `sheets/`: five unmodified built-in imagegen outputs, retained for provenance.
- `prompts.json`: complete prompts and original generated-image paths.
- `manifest.json`: catalog descriptions, crop coordinates, source hashes, material assignments and limitations.
- `validation.json`: completeness, registration and material-path checks.
- `process_controls.py`: reproducible extraction, mask generation and validation.

## What was actually obtained

Five successful built-in imagegen calls returned genuine RGBA sheets at **1254 x 1254**, despite prompts requesting2048. The twenty native crops are464–611pixels wide and474–599pixels high. They have not been enlarged or presented as higher-resolution originals. There are20 generated variants and0 geometry-rendered variants in this extension.

The authorized family-sheet method uses four isolated objects per sheet. Each quadrant is extracted independently. Disconnected low-alpha generation spill is removed using the largest opaque alpha component, a2pixel opening and3pixel expansion. Original antialiasing is retained inside that envelope. Masks are derived from the resulting alpha, never from a guessed rectangle or RGB background color. Unmodified sheet alpha remains available for comparison.

All twenty references were inspected together after extraction. Key legends, module identities, tactile ridges, guarded lever, split rocker, paddle, encoder distinction, test-button distinction and the closed floor glazing are visible. The CAM key lacks the requested separate witness slit; tick/fastener counts and some mounting geometry differ from source. These are documented concept differences rather than production instructions. Screen readings are illustrative static reference content.

## Finish assignment

Assignments point to existing real Poly Haven CC0 source maps in `../surface-scans/`; the existing `sources.json` there records download URLs and hashes. No AI-generated reference photograph is proposed as an albedo, normal or roughness map.

| Region | Production material | Existing measured source | Treatment |
|---|---|---|---|
| Housing, graphite bezel | Graphite_Alloy | metal_plate | Dark neutral retint; shallow normal strength0.12; metallic0.8 |
| Guards, stems, caps, retaining rim | Titanium | metal_plate | Neutral silver retint; shallow normal0.10; metallic0.92 |
| Button/rocker face | Carbon_Ceramic | blue_metal_plate | Graphite retint, reduced normal0.06, low metallic0.05 |
| Seals and gaskets | Black_Rubber | rubber_tiles | Near-black retint, reduced normal0.08 |
| Crossbar/lens knob grip | Grip_Elastomer | scuba_suede | Near-black retint, reduced normal0.10 |
| Display/floor glazing | Sapphire_Glass | Analytic dielectric | IOR1.52, roughness0.075; no opaque scan mapped onto glass |
| Witness light/lens | Witness_Teal / Witness_Amber | Analytic tinted dielectric/emission | Restrained teal/amber; not a measured scan |

These sources provide measured microstructure, not proof that the source object was aerospace titanium, ceramic or elastomer. Retinting and roughness remapping are explicit finish approximations. Scan normals use the existing OpenGL convention. Engraved legends should remain geometry/vector decals in production, not be projected from these images.

## Registration and validation limits

The reference, alpha and silhouette for each ID are exactly pixel registered and equal-sized. The concepts are **not** camera-, UV-, geometry- or per-material-segmentation registered to the production meshes. Glass alpha is rendered coverage, not physical transmission. The floor port remains closed in the reference.

Validation confirms19catalog IDs plus1floor port,20references,40masks,5sheets, no empty/full-opaque masks, matching alpha/silhouette values and all assigned source-map paths. Re-run from any directory with Python, Pillow, NumPy and SciPy: `python process_controls.py`.
