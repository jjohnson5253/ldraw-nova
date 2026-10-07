# Supplier inventories and exact part costs

`ldraw_tools.parts_catalog.PartsCatalog` accepts any CSV with `part_id,color_id`
columns using LDraw IDs. Optional columns are `name,sku,unit_price,weight_kg,
max_quantity`. Prices are USD per piece. A missing price is permitted for a pure
allowlist, but never produces a guessed quote. Quantities aggregate by SKU.

The shipped Brickwith snapshot contains 41,664 variants, with 36,374 exact
LDraw part/color mappings. Unmapped supplier variants remain in the CSV with
prices but do not authorize parts. Fetch date, sources, completeness counts and
SHA256 are recorded in `ldraw_tools/data/brickwith_parts.metadata.json`.

Brickwith publishes a Studio palette and exposes anonymous storefront read
endpoints. No documented developer API was found. Refresh explicitly with:

```sh
python scripts/refresh_brickwith_catalog.py
```

The refresh verifies complete products, variants, prices and mappings before
replacing the catalog. Prices are a snapshot, excluding shipping, tax and
retail discounts; refresh before relying on a current order quote.

Expand a candidate's submodels and inherited colors, then check every physical
part against any CSV with the toolkit interpreter:

```sh
.venv/bin/python -m ldraw_tools.catalog_inventory model.mpd "$LDRAW_DIR" \
  --catalog /absolute/path/allowed-parts.csv
```

Unknown dependencies, custom geometry, custom colors and embedded DAT overrides
fail validation. The CSV is an exact part/color allowlist, not a substitute for
collision, connectivity, construction or visual review.

The companion Nova agent service enforces this library during publication;
see its `docs/parts-catalog.md` for per-chat configuration and deployment.
