# Use my parts: collection import and inventory-aware revisions

Status: implemented on `codex/use-my-parts` in the toolkit and sibling
`ldraw-nova-docker` repositories. Research date: October 4, 2026.

## Implemented scope

- **My parts:** search Rebrickable by set name or number, or paste a supported
  LEGO, Rebrickable, or BrickLink set URL. URLs supply a set number; inventories
  come from Rebrickable. Review the matched set and parts before adding stock.
- Upload a CSV of owned pieces. LDraw CSV works offline; Rebrickable CSV uses
  its API to map provider IDs to installed LDraw parts and colors.
- Each source has a name, copy count, availability checkbox and editable
  per-copy quantities. Spare pieces are excluded unless explicitly included.
  Duplicate sources show a warning before adding another contribution.
- Model cards show exact owned/missing counts and an expandable parts table.
  Unmapped collection pieces cannot inflate owned counts. Without a collection,
  the card asks the user to add parts instead of claiming zero ownership.
- **Use only my parts** is a single checkbox before generation and a single
  action on ordinary completed models. If no usable stock exists, the action
  opens collection setup with a return link. A revision preserves the original.
- Generation uses the existing agent, tools and document attachment flow. It
  receives a frozen inventory snapshot and instructions to respect exact part,
  color and quantity limits. There are no color/shape preference controls,
  custom substitution algorithms, or changes to the sculpture packer.
- `publish_model` independently compares the finished, validated model against
  the authoritative snapshot. Shortages or unresolved pieces block publication
  in this mode. A failure leaves the earlier model available. Inventory matching
  does not prove physical buildability or visual similarity; the existing review
  workflow still applies.
- There is no purchase button or BrickOwl integration.

## Minimal architecture

The toolkit adds `ldraw_tools/collection.py` and extends the existing BOM command:

```sh
./ldraw-agent bom output/model.mpd --inventory owned-parts.json --report output/bom.json
```

Snapshot format:

```json
{"parts": [{"part": "3001", "colour": 4, "quantity": 2}]}
```

The physical BOM already expands repeated submodels and inherited colors. Stock
is counted once across the entire model. Duplicate stock rows add quantities.
The comparison returns required, owned, missing, unresolved, unmapped collection
pieces and per-part/color rows. Exit 1 means a nonmatching or invalid model;
exit 2 means an input/tool error. Empty models do not count as success.

The Docker app adds a conventional `web/backend/collection.py`, a `pages/Parts.tsx`
page and a `components/PartsList.tsx` component. It reuses the existing Settings
Environment editor for `REBRICKABLE_API_KEY`, chat continuation, document uploads,
model cards, and validation/publication tools. Its collection is persisted in
`data/collection.json`, separate from generated models and catalog data. Like the
rest of this local app, it is one shared collection per instance.

Saving a Rebrickable key downloads the complete set catalog and theme names in
the background to `data/catalog/rebrickable.sqlite`. Search uses that persistent
local index, including theme names and parent themes. Settings and My parts show
progress and offer refresh/retry; failed refreshes preserve the previous catalog.
Search controls and API requests are blocked until the set index finishes,
including during refreshes of an existing catalog. Ten supporting bulk files
then index in the background to `data/catalog/rebrickable-inventories.sqlite`:
inventories, inventory parts/minifigs/sets, parts, colors, minifigs, relationships,
elements and part categories. Latest-version inventories expand minifigures and
contained sets, aggregate part/color quantities and filter spare pieces.
Imports use local inventories, falling back to the API while indexing or if a
referenced inventory is absent. LDraw mappings still use batched API lookups,
cached in memory and rate limited. Images are not downloaded.
Import follows provider pagination and fails instead
of saving a truncated inventory. Set URLs are parsed locally and never scraped.
Provider parts/colors must have an unambiguous mapping to installed LDraw entries.
Unknown mappings remain visible in the source and are excluded from matching.

Backend BOM checks use a separate private cache via `LDRAW_NOVA_CACHE_DIR`, so
backend-owned cache files cannot interfere with the unprivileged agent's cache.
The authoritative inventory stays in server memory for the running turn; the
agent receives an editable attachment copy. Model cards compare against the
current available collection; the publication tool result records the report
from the captured build inventory.

## CSV formats

LDraw IDs, with an optional `.dat` suffix and explicit LDraw color codes:

```csv
part,colour,quantity
3001.dat,4,2
3003,1,4
```

Rebrickable export (requires `REBRICKABLE_API_KEY`):

```csv
part_num,color_id,quantity
3001,5,2
```

Provider color IDs are mapped explicitly, never treated as LDraw color codes.
Quantities must be nonnegative integers; colors 16 and 24 do not describe owned
colors. Correct incomplete sets in the review table and increase Copies for
multiple identical sets. Adding an overlapping CSV is additional stock: review
its contribution rather than importing the same collection twice.

## Provider research

Rebrickable API v3 exposes official set search, parts, minifigs and set inventories.
Catalog calls require a key and average one request per second. No authenticated
live request was made during this implementation; provider behavior is covered
by offline API fixtures. [Official API guide](https://rebrickable.com/api/v3/docs/).

```text
GET /api/v3/lego/sets/{set_num}/
GET /api/v3/lego/sets/{set_num}/parts/?inc_part_details=1&inc_minifig_parts=1
GET /api/v3/lego/parts/?part_nums=...&inc_part_details=1
GET /api/v3/lego/colors/
```

[Official endpoint schema](https://rebrickable.com/api/v3/swagger/?format=openapi).
The local catalogs use the provider's set/theme and inventory/part CSV bulk
downloads rather than crawling the API. [Provider guidance](https://rebrickable.com/api/).

BrickLink also exposes a catalog API for set constituents, with signed credentials:
`GET /api/store/v1/items/SET/{set_num}/subsets`.
[Get Subsets](https://www.bricklink.com/v3/api.page?page=get-subsets),
[authentication](https://www.bricklink.com/v3/api.page?page=auth).
The initial implementation accepts BrickLink set URLs but uses Rebrickable for
inventory retrieval, keeping one catalog adapter. No documented public LEGO
full-inventory API was located; LEGO product URLs are only set-number inputs.

Account collection sync, extra upload formats, build reservations and a complete
local mirror of external part/color ID mappings are outside this implementation.
