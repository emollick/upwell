# Upwell cabin hardware and furnishings

Eight visual studies cover the axial accelerometer and test plunger, galley sight glass and primer, power and fiber loops, berth quilt and privacy curtain.

## Files

| File or directory | Contents |
| --- | --- |
| `contact-sheet.jpg`, `refs/`, `sheets/` | Family sheets and isolated RGBA reference images |
| `masks/` | One registered alpha and one binary silhouette per reference |
| `evidence/` | Eight in-engine views of the corresponding Blender-authored models |
| `samples/`, `material-samples.jpg` | 46 production maps and a comparison of the textile and cable finishes |
| `manifest.json` | Per-object material assignments, shader parameters, native dimensions, source paths and hashes |
| `prompts.json` | Prompts and reference inputs for the four sheets and two mechanical revisions |
| `validation.json`, `process_bundle.py` | Registration and production map checks, and the extraction script |

## Image registration

The four generated sheets each measure 1,254 × 1,254 pixels. The individual references retain their native crop resolution. The alpha of each reference supplies its grayscale mask. A threshold of 128 supplies its binary silhouette. The masks align with their source images and preserve separate fasteners and labels.

The in-engine views record the actual spring pitch, markings, cable terminations and fabric folds. The generated concepts can differ in these details. Use the scene geometry and UVs for mesh registration. The 77% liquid charge comes from the simulation. Alpha on the reference glass records image coverage.

## Materials

The production material assignments come from `unity/Assets/Upwell/SourceModels/Textures/materials.json`, `source/gravity_authoring.py`, `source/furnishings_authoring.py` and `web/assets/rooms/furnishings.json`. The sealed cell uses shader parameters for its transparent media. The printed instrument scales use the `Gravity_Instruments.jpg` atlas.

The quilt’s outer fabric uses a 5.4 mm ripstop reinforcement and roughness of 0.89. Its lining and outer yarn derive from the same photographed textile. [Poly Haven terlenka](https://polyhaven.com/a/terlenka)

The curtain and its bias tape use a photographed denim weave. The curtain roughness is 0.91. Source records for both CC0 textiles are in `art/surface-scans/sources.json`. [Poly Haven denim](https://polyhaven.com/a/denim_fabric_06) · [License](https://polyhaven.com/license)

The power and fiber spans use `Cable_Orange` and `Cable_Cyan` with separate materials for strain reliefs and witness bands.
