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
choose **Use only my parts** before generation. If it was not selected initially,
show **Use only my parts** at the end to generate a revision from the user's
available inventory. Preserve the original model and show the new revision with
its own parts report and reviewed previews. This is one option; there are no
separate controls for color changes or shape changes.

## What the providers support

| Provider | Verified capability | Proposed role |
| --- | --- | --- |
| Rebrickable | API v3 covers official sets, parts and minifigs; authenticated collection access; set search and set inventories. Full-catalog use must use bulk CSV downloads. | Primary catalog and set inventory source. |
| BrickLink | Catalog API can look up a set and retrieve its constituent items through Get Subsets. Requests use OAuth-style signed credentials. | Optional later catalog provider. |
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
3. **Generate:** an optional **Use only my parts** control reads the current
   collection and enforces its available part, color and quantity limits. Ordinary
   generation remains the default when the option is not selected.
4. **Finish:** always show a parts panel. With a collection, display exact owned
   quantities, shortages, and coverage; without one, show **Add your parts to see
   what you already have**, rather than claiming zero ownership.
5. **Use only my parts:** if the option was not selected initially, show it at the
   end. If no collection exists, selecting it starts collection setup before
   generating the revision. Nova automatically chooses owned pieces and colors
   while preserving the requested subject. Show the new preview and parts report.
   Keep the completed original usable while generation runs or fails. When the
   option was selected initially, show the result's inventory report without
   repeating the same prompt.

Example copy, using illustrative numbers:

> You have 240 of the 300 pieces needed (80%). You're missing 60 pieces across
> 12 part-and-color combinations.
>
> **Use only my parts**

## Purchase button: direct opening only

Include a purchase button only if it opens the marketplace with the required
parts, colors and quantities already loaded. Manual copying, file upload and
pasting into an import page do not satisfy the requested experience. Remove the
previous BrickLink XML handoff button from the planned scope.

BrickOwl is a candidate to investigate. Its API documentation was blocked during
this research, and authenticated list population plus direct navigation to the
populated shopping page have not been verified. Do not promise or ship this
button until that end-to-end flow works. Any necessary one-time account setup
must be made clear before deciding the integration meets the desired simplicity.
[BrickOwl API documentation](https://www.brickowl.com/api_docs).

The parts report still provides accurate missing quantities. A successful direct
purchase integration would use those shortages for the selected revision; it
must not present incomplete part mappings as a complete shopping list.

## What “use only my parts” means

Every required physical piece must resolve to an available owned part in an
owned color, and total quantities across the model must fit the collection.
Implement this through Nova's existing agent workflow: attach the normalized
inventory and instructions to the initial prompt or a follow-up regeneration
request. The existing agent chooses parts and colors while protecting the
requested subject and using its current construction and verification tools.
There is no separate preference mode or color/shape settings panel, custom
substitution engine, curated swap database, or inventory-specific packer.

Example instruction:

> Build this model using only the attached inventory, including its exact colors
> and available quantities. Use your existing tools to revise and verify the
> model. If you cannot complete it within the inventory, report that clearly.

Prompt instructions guide the agent; they do not prove inventory compliance.
Reuse the owned/missing comparison planned for the parts report to verify its
final BOM. Collection import, prompt wiring, the button and comparison need
integration code; piece and color decisions use the existing agent.

Possible internal strategies include selecting the same part in an owned color,
choosing compatible parts with its existing tools, and reconstructing an area with
owned pieces. For example, two 2×2 bricks may replace a 2×4 brick where seams and
surrounding bonds allow it. These are generation strategies, not extra controls.

If Nova cannot produce an acceptable model within the inventory, report that
the attempt could not be completed and preserve the original. Do not present a
revision containing missing or unresolved required pieces as a successful
**Use only my parts** result.

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
| Model comparison | Model revision, collection snapshot, exact owned, missing, unresolved |

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
Compute coverage against the actual final parts and colors, including any
automatic changes made during generation. If a model needs ten matching bricks
and the user has two, count two. For an empty BOM show
coverage as not applicable. Compare the complete model against one inventory
snapshot so multiple sections cannot reuse the same physical piece.

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
  Keep this packer unchanged in this feature. Passing inventory to the agent
  cannot make the packer enforce stock limits; verify the final BOM with the
  collection comparison and report an unsuccessful attempt if it exceeds stock.
- The web app lives in the sibling `ldraw-nova-docker` repository, per Nova's
  README. Collection UI, upload handling and revision controls belong there;
  catalog import, normalization, comparison and agent tools belong here.

Proposed future CLI surface, not implemented commands:

```text
ldraw-agent collection import-set <set-number-or-url>
ldraw-agent collection import-csv <file>
ldraw-agent collection compare <model.mpd>
```

Use set URLs to extract a recognized catalog identifier locally, then query the
configured provider. An arbitrary page URL should not trigger scraping. Distinguish
unsupported URLs, unknown sets, ambiguous variants and unavailable inventories.

## Suggested build sequence

1. **Useful first release:** Rebrickable set search/import, a documented CSV
   format, quantity adjustments, explicit part/color mappings, and the automatic
   owned/missing panel with missing-parts CSV export. This is useful even before
   the generation option exists.
2. **Use only my parts:** add the same option before generation and at the end
   when it was not selected initially. Pass an inventory snapshot and instructions
   into the existing agent generation flow. Reuse the final parts comparison;
   success requires zero missing or unresolved required pieces. Keep the original
   and generated revision available. Do not build separate substitution logic.
3. **Direct purchase feasibility:** investigate BrickOwl or another marketplace.
   Add a purchase button only after verifying automatic list population and
   direct opening. Manual import is outside the requested scope.
4. **Later convenience:** account collection sync, more upload formats,
   reservations for multiple
   simultaneous builds, and barcode entry. Photo-based loose-parts counting is
   a separate recognition project.

On collection import, explicitly choose whether owned sets are available to
dismantle. The generation interface stays simple: ordinary generation or
**Use only my parts**, with that same option available after ordinary generation.

## Acceptance checks for implementation

- Repeated set imports, multiple copies, spares, missing pieces and unavailable
  sets yield correct quantities and reversible source contributions.
- A known multi-section MPD counts physical repeated instances and effective
  colors correctly; unresolved mappings never inflate coverage.
- Import/reimport handles duplicate representations explicitly. Pagination and
  provider throttling do not yield silently incomplete inventories.
- **Use only my parts** appears at the end whenever it was not selected initially;
  it routes through collection setup when needed and exposes no color/shape controls.
- Substitution uses stock only once across modules. Every successful
  **Use only my parts** revision fits available quantities, with zero missing or
  unresolved required pieces.
- Each changed construction passes the applicable existing model checks and
  receives visual review; stronger inventory coverage cannot conceal broken
  geometry or loss of the requested subject.
- A failed adaptation leaves the original available. Reports record both the
  model revision and inventory snapshot used for their quantities.
