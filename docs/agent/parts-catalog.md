# External parts palettes

Nova's toolkit contains a generic parts palette reader and validator. It ships
no supplier catalogs, prices, weights, network adapters or refresh scripts.
The application calling Nova owns its supplier data and cost estimates.

`ldraw_tools.parts_catalog.PartsCatalog` accepts any local CSV with
`part_id,color_id` columns using LDraw IDs. Optional columns are `name,sku,
max_quantity`. `sku` is an inventory group identifier: aliases sharing one group
also share its finite quantity limit. An omitted limit means unlimited supply.
Unknown columns are ignored and omitted from canonical palette exports.

```csv
part_id,color_id,name,max_quantity
3001,4,Brick 2 x 4,20
3005,4,Brick 1 x 1,
```

Expand a candidate's submodels and inherited colors, then check every physical
part against the externally supplied palette:

```sh
.venv/bin/python -m ldraw_tools.catalog_inventory model.mpd "$LDRAW_DIR" \
  --catalog /absolute/path/palette.csv
```

Unknown dependencies, custom geometry, custom colors and embedded DAT overrides
fail validation. Palette membership is independent of collision, connectivity,
construction and visual review, which remain necessary.

The companion Nova agent service accepts a local palette path through
`NOVA_PARTS_PALETTE`, or a per-chat palette from its caller. With no palette,
Nova retains its unrestricted behavior. See its `docs/parts-catalog.md`.
