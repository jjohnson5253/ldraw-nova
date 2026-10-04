# Use my parts: collection import and inventory-aware model revisions

Status: brainstorm and proposed implementation sequence; no feature code yet.
Research date: October 4, 2026.

## Recommendation

Use Rebrickable as the first catalog provider. Give Nova its own searchable set
index populated from the provider's bulk catalog, while keeping the user's
collection separate. Accept a set number, a supported LEGO/Rebrickable/BrickLink
set URL, or an uploaded parts list. Turn the imported collection into quantities
of particular parts in particular colors.

Every completed model should show an owned-versus-missing comparison. A user can
choose **Use my parts** before generation, or choose **Adapt to my parts** after
seeing an ordinary generation. Preserve the original model and show the adapted
model as a new revision, with its own parts report and reviewed previews.

## What the providers support

| Provider | Verified capability | Proposed role |
| --- | --- | --- |
| Rebrickable | API v3 covers official sets, parts and minifigs; authenticated collection access; set search and set inventories. Full-catalog use must use bulk CSV downloads. | Primary catalog and set inventory source. |
| BrickLink | Catalog API can look up a set and retrieve its constituent items through Get Subsets. Requests use OAuth-style signed credentials. | Optional later provider, plus missing-parts exports. |
| LEGO website | No documented public full-catalog inventory API was located in this research. | Accept product URLs as set-number input; resolve against the catalog. |

Rebrickable catalog calls require an API key; the published average throttle is
one request per second. Its API does not supply pricing. General MOC inventory
access is unavailable. These are catalog capabilities, not a guarantee that
every historical set has a complete, perfectly accurate inventory.
[Rebrickable API guide](https://rebrickable.com/api/v3/docs/).

Useful verified Rebrickable endpoints:

```text
GET /api/v3/lego/sets/?search=...
GET /api/v3/lego/sets/{set_num}/parts/?inc_part_details=1
GET /api/v3/lego/parts/{part_num}/
GET /api/v3/lego/colors/
```

Search accepts set names and numbers. Inventory results are paginated;
`inc_minifig_parts=1` optionally expands minifigs into parts.
[Public endpoint schema](https://rebrickable.com/api/v3/swagger/?format=openapi).

For a complete local catalog, Rebrickable explicitly directs developers to its
[Downloads page](https://rebrickable.com/downloads/) rather than crawling the API.
[Provider guidance](https://rebrickable.com/api/).
The downloads page itself was blocked during this research, so exact current
file schemas, update frequency, and distribution/image permissions remain to
be checked before shipping an ingestion job. No authenticated inventory requests
were made.

BrickLink's relevant call is:

```text
GET https://api.bricklink.com/api/store/v1/items/SET/{set_num}/subsets
```

It offers minifig and nested-set expansion. Results contain matching groups,
including alternate items; import must preserve those choices rather than add
every alternate to the user's stock. Extras are separately represented.
[Get Subsets](https://www.bricklink.com/v3/api.page?page=get-subsets),
[subset representation](https://www.bricklink.com/v3/api.page?page=resource-representations-catalog).

BrickLink's API references do not document a general list/search endpoint for
the entire set catalog. That makes it a less direct starting point for Nova's
search database. Store inventory is also distinct from a user's personal parts
collection.
[API references](https://www.bricklink.com/v3/api.page?page=references),
[authentication](https://www.bricklink.com/v3/api.page?page=auth).

## Proposed user flow

1. **My parts:** search sets by name or number, paste a supported set URL, upload
   CSV, or add individual parts. Show the matched set for confirmation, including
   variant and copy count, before adding its inventory.
2. **Check availability:** choose whether each set can be taken apart. Let users
   subtract missing pieces, exclude pieces they want to keep, and opt into spare
   parts. Mark imported complete-set inventories as assumed stock until checked.
3. **Generate:** an optional **Use my parts** control reads the current collection.
   Default to preferring owned parts while preserving the requested subject.
4. **Finish:** always show a parts panel. With a collection, display exact owned
   quantities, shortages, and coverage; without one, show **Add your parts to see
   what you already have**, rather than claiming zero ownership.
5. **Adapt:** if shortages remain, offer **Try adapting this model to my parts**.
   Show before/after previews, coverage, missing pieces and a short change list.
   Keep the completed original usable while adaptation runs or fails.

Example copy, using illustrative numbers:

> You have 240 of the 300 pieces needed (80%). You're missing 60 pieces across
> 12 part-and-color combinations. Try adapting this model to your parts?

## What “use my parts” should mean

Start with **Prefer my parts**: minimize shortages while protecting recognizable
shape, important features and structural checks. Always report remaining
shortages; a best-effort revision must not imply that it is fully buildable from
the collection.

Offer these understandable choices when adapting:

- **Keep the colors:** favor geometry-compatible alternatives in the same color.
- **Allow color changes:** adjust coherent regions together, preserving important
  accents unless the user permits changes. Hidden internal pieces can be more
  flexible than visible surfaces.
- **Allow small shape changes:** alter local constructions while preserving the
  subject and important dimensions.

A later **Only my parts** mode can enforce hard inventory limits. If it cannot
find an acceptable model, explain the limiting pieces and offer a smaller model
or relaxed constraints. Do not silently add unavailable parts.

Substitution should grow in stages:

1. Same part in a permitted owned color.
2. Explicitly reviewed mold variants with compatible interfaces.
3. Local reconstruction, such as two 2×2 bricks replacing a 2×4 brick where seams
   and surrounding bonds allow it.
4. Larger changes to scale, silhouette or important features, with user choice.

Matching dimensions alone does not establish an interchangeable part. Even an
apparently simple split can weaken a bond. Edit the plan/generator, then rebuild,
check collisions and connectivity, recalculate the BOM and render reviewed
previews. A new render by itself cannot change the parts used.

## Collection and catalog design

Use a separate SQLite catalog with full-text search for the local Docker app.
Rebuild it from provider snapshots without changing Nova's existing reference
database. Keep timestamps and source versions so imports can be reproduced.
For hosted multi-user use, the same conceptual tables can move to a server
database with user-owned collection records.

Proposed entities:

| Entity | Main fields |
| --- | --- |
| Catalog set | Provider, set number/variant, name, year, theme, inventory version, source URL |
| Catalog inventory row | Set inventory ID, provider part, provider color, quantity, spare/alternate status |
| Part/color mapping | Provider namespace and ID, LDraw reference/color, mapping provenance and confidence |
| Collection source | Collection ID, set copies or imported file, selected inventory version, availability, adjustments |
| Model comparison | Model revision, collection snapshot, exact owned, missing, unresolved, permitted substitutions |

Do not assume Rebrickable, BrickLink and LDraw identifiers are interchangeable.
Map both parts and colors explicitly, retaining printed parts, assemblies and
mold distinctions. Unknown or ambiguous mappings must appear as **unresolved**,
not silently match by name or nearest RGB color. Inspect mapping coverage as an
early feasibility experiment before promising broad substitution support.

Prevent double counting: a file export of the same sets is another representation
of that collection, not automatically additional loose stock. Let the user choose
replace, merge, or add independent stock, and show an import preview. Preserve
provenance so a source can be removed without guessing what it contributed.
Reserved sets or active builds reduce available stock; merely generating a model
must not permanently consume pieces.

For each exactly resolved part/color pair:

```text
owned_for_model = min(available_quantity, required_quantity)
missing = max(required_quantity - available_quantity, 0)
coverage = sum(owned_for_model) / sum(required_quantity)
```

Include unresolved required pieces in the total and report them separately.
Keep exact-color coverage separate from possible color substitutions. If a model
needs ten matching bricks and the user has two, count two. For an empty BOM show
coverage as not applicable. Adaptation must use one inventory ledger across all
modules so multiple sections cannot reuse the same physical piece.

## Fit with Nova today

- `ldraw_tools/cli.py` already exposes `bom` using the physical model context and
  `bill_of_materials()`. Build the comparison on that output, including inherited
  colors and repeated submodel instances, rather than writing a new LDraw parser.
- `ldraw_tools/discovery.py` already uses disposable SQLite/FTS5 indexes. Reuse
  that approach for a separate set catalog, not the existing index's contents.
- `ldraw_tools/catalog.py` describes installed geometry and colors; installed
  LDraw geometry alone does not establish a purchasable part/color combination.
- The optional sculpture packer in `ldraw_tools/sculpture/voxel2brick.py` applies
  voxel/color constraints but does not accept an owned-parts quantity ledger.
  Inventory-aware packing would require changes to candidate selection and
  repair/merge passes. A final stock check must still verify the result.
- The web app lives in the sibling `ldraw-nova-docker` repository, per Nova's
  README. Collection UI, upload handling and revision controls belong there;
  catalog import, normalization, comparison and agent tools belong here.

Proposed future CLI surface, not implemented commands:

```text
ldraw-agent collection import-set <set-number-or-url>
ldraw-agent collection import-csv <file>
ldraw-agent collection compare <model.mpd>
ldraw-agent collection candidates <part> --colour <code>
```

Use set URLs to extract a recognized catalog identifier locally, then query the
configured provider. An arbitrary page URL should not trigger scraping. Distinguish
unsupported URLs, unknown sets, ambiguous variants and unavailable inventories.

## Suggested build sequence

1. **Useful first release:** Rebrickable set search/import, a documented CSV
   format, quantity adjustments, explicit part/color mappings, and the automatic
   owned/missing panel with missing-parts CSV export. This is useful even before
   adaptation exists.
2. **First adaptation:** permit controlled recoloring, pass an inventory snapshot
   to the agent, and add an authoritative comparison tool after every rebuild.
   Show original and adapted revisions with changes and remaining shortages.
3. **Geometry-aware adaptation:** curated substitutes and local reconstructions;
   add inventory-constrained sculpture packing separately. Consider hard
   inventory mode after best-effort results are reliable.
4. **Later convenience:** account collection sync, more upload formats, BrickLink
   wanted-list export, reservations for multiple simultaneous builds, and barcode
   entry. Photo-based loose-parts counting is a separate recognition project.

Before implementation, settle two product defaults: whether owned sets are
available to dismantle, and how much visible color change is acceptable. Suggested
defaults are an explicit availability choice on import and recoloring off until
selected. Keep the first release focused on an accurate collection comparison;
the harder value proposition is improving coverage while retaining a good model.

## Acceptance checks for implementation

- Repeated set imports, multiple copies, spares, missing pieces and unavailable
  sets yield correct quantities and reversible source contributions.
- A known multi-section MPD counts physical repeated instances and effective
  colors correctly; unresolved mappings never inflate coverage.
- Import/reimport handles duplicate representations explicitly. Pagination and
  provider throttling do not yield silently incomplete inventories.
- Substitution uses stock only once across modules. No adapted revision exceeds
  stock in hard mode or conceals shortages in preference mode.
- Each changed construction passes the applicable existing model checks and
  receives visual review; stronger inventory coverage cannot conceal broken
  geometry or loss of the requested subject.
- A failed adaptation leaves the original available. Reports record both the
  model revision and inventory snapshot used for their quantities.
