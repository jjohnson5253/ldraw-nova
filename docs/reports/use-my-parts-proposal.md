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

## Buy missing parts on BrickLink

Add **Buy missing parts on BrickLink** to the completed model's parts panel.
Generate a BrickLink Wanted List XML from the selected revision's shortages,
using explicitly mapped BrickLink part IDs, color IDs and missing quantities.
If no collection is available, offer **Buy all parts on BrickLink** with a clear
full-list preview. If nothing is missing, show that the collection covers the
model instead of generating an empty shopping list.

The supported initial handoff is:

1. Show the purchase-list summary and any unresolved mappings in Nova.
2. On the user's click, copy the generated XML and open BrickLink's
   [Wanted List upload page](https://www.bricklink.com/v2/wanted/upload.page).
   Offer a visible copy fallback if clipboard access fails. Open the new tab
   directly from the click so browser popup restrictions do not interrupt it.
3. The user signs in if necessary, chooses **Upload BrickLink XML format**,
   pastes the list, verifies the items, and saves to a new model-specific list.
4. BrickLink's **Buy All** or **Easy Buy** finds sellers for that list.

BrickLink officially documents XML import and shopping from Wanted Lists.
[Mass upload help](https://www.bricklink.com/help.asp?helpID=207&viewType=shop),
[Wanted List help](https://www.bricklink.com/helpLang.asp?helpID=1&viewType=shop),
[Easy Buy help](https://www.bricklink.com/help.asp?helpID=2457).

No supported URL parameter for passing an entire parts list into a prefilled
shopping search, or public Wanted List creation API, was found in the published
API references. Treat automatic account import as a separate integration to
investigate; the first button can automatically open BrickLink and prepare the
list, while the user completes import and seller selection there.
[API references](https://www.bricklink.com/v3/api.page?page=references).

Export `ITEMTYPE=P`, mapped `ITEMID`, mapped `COLOR`, and `MINQTY` equal to the
shortage for each resolved part/color row. Use the Wanted List XML dialect,
without an XML declaration. Omit already-owned quantities from this export;
do not also subtract them through `QTYFILLED`. Combine repeated rows and escape
XML correctly. Keep condition flexible unless the user chooses new or used.
Unresolved mappings need a visible count and review; never claim the exported
list covers the entire build when some required rows cannot be exported.

Make a new Wanted List the suggested destination: BrickLink documents that
reimporting quantities into an existing list can add them to existing wanted
quantities. Buying does not update Nova's collection until the user records that
the pieces have arrived. Validate the actual XML import with a small representative
list before presenting this as a verified integration.

## What “use only my parts” means

Every required physical piece must resolve to an available owned part in an
owned color, and total quantities across the model must fit the collection.
There is no separate preference mode or color/shape settings panel. Nova handles
piece selection, recoloring and any necessary reconstruction automatically as
part of generation, while protecting the requested subject and structural checks.

Possible internal strategies include selecting the same part in an owned color,
using reviewed compatible mold variants, and reconstructing a local area with
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
   owned/missing panel with missing-parts CSV export and a BrickLink Wanted List
   XML handoff button. This is useful even before inventory-constrained generation
   exists.
2. **Use only my parts:** add the same option before generation and at the end
   when it was not selected initially. Pass an inventory snapshot to the agent
   and enforce an authoritative parts/quantity check after every rebuild. Nova
   chooses changes automatically; success requires zero missing or unresolved
   required pieces. Keep the original and generated revision available.
3. **Improve constrained generation:** extend internal substitution strategies
   and local reconstruction; add inventory-constrained sculpture packing
   separately, while preserving the same single-option user flow.
4. **Later convenience:** account collection sync, more upload formats, a deeper
   BrickLink account integration if supported, reservations for multiple
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
