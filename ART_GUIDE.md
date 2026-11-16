# ART GUIDE — "Via Romana" map and sprites

This is the brief for the map art, and a record of how the final art was made. Every PNG is drawn by `tools/make_final_art.py`: sprites are hand-authored character grids in that file (one character per pixel), larger buildings are assembled from hand-authored parts, and only the ground tiles use seeded noise. **Swapping art needs no code changes:** replace each PNG at the same path and size, or edit its entry in `assets/assets.json` (file, size, frame count, fps, anchor). The app reads nothing else.

To change a sprite, edit its grid and run `python3 tools/make_final_art.py` (needs Pillow); it rewrites the PNGs and keeps the size fields of `assets.json` in step. `--sheet out.png` also writes a 4× contact sheet, `--check` builds without writing. Do not run `tools/make_placeholder_art.py`: it overwrites the PNGs with the old placeholders and regenerates this file.

## Style

- Dignified retro pixel art, 16/32-bit era (think late SNES / early GBA), warm earthy palette. Nothing cartoonish or candy-coloured.
- Hard pixel edges, no anti-aliasing, no semi-transparent pixels except where noted. Transparent PNG backgrounds.
- Sprites use a 1px dark outline (`ink` #2b1d16) or selective outlining.
- Light comes from the upper left.
- The map is drawn at an integer scale (×2 on iPhones, ×3 on larger screens) with nearest-neighbour scaling.
- Total asset budget: keep everything under 5 MB (currently about 50 KB).

## Palette (32 colours)

The art uses these colours, plus the six in-family extras listed under the table. Ground-tile textures also blend neighbouring palette colours to keep their contrast low.

| name | hex | name | hex |
|---|---|---|---|
| ink | `#2b1d16` | dkbrown | `#4a3426` |
| brown | `#6b4a32` | ltbrown | `#8f6a48` |
| tan | `#b8916a` | sand | `#d9bf8f` |
| parch | `#ecdcb3` | cream | `#f6ecd2` |
| terra_dk | `#7a3223` | terra | `#a84a2f` |
| terra_lt | `#c96f47` | ochre | `#c9962f` |
| gold | `#e0b84a` | olive_dk | `#3c4a24` |
| olive | `#5d6b34` | sage | `#8a9455` |
| leaf | `#b0b57a` | stone_dk | `#5a5550` |
| stone | `#8a847a` | stone_lt | `#b5ad9e` |
| marble | `#ddd6c8` | sea_dk | `#23394a` |
| sea | `#3e5f73` | sea_lt | `#6f8f9c` |
| sky | `#a9bfc4` | wine | `#5e2333` |
| purple | `#5a3a5e` | white | `#f8f4ea` |
| black | `#140e0b` | skin | `#c98f62` |
| skin_dk | `#9c6440` | red | `#8e2b22` |

Extras: gold_lt `#f3dc8c` (glint on gold), forest `#2b3620` (deep foliage shadow), marble_dk `#c7bfb0` (marble mid-shade), skin_lt `#e0ab7e`, bronze `#7c5a2c`, foam `#cfe0df` (water and cloud highlights).

## Map layout (how assets are used)

- The map is a tall vertical scroll. The road (`tile_via`) winds upward from chapter I at the bottom to the Capitol at the top.
- 364 stops: 312 reading days + 52 rest stops (one after every 6 reading days). Each rest stop shows `landmark_fountain` or `landmark_shrine` (alternating) plus a `landmark_milestone` with the week number in Roman numerals (`font_roman`).
- Each chapter is a district: its ground is the district tile (`bg_*`), decorated with that district's `props` scattered beside the road. A `landmark_arch` stands on the boundary wherever the chapter changes (not after the last chapter, where the Capitol stands); the chapter title card (HTML, framed by `ui_frame`) appears when entering a new district.
- **City districts.** A district with a `buildings` list in `assets.json` (at present `taberna`, `urbs` and `forum`) is laid out as part of Rome: rows of those buildings stand shoulder to shoulder on both sides of the road, each row far enough behind the one in front that its upper floors show above the roofs, with a pavement beside the road, the odd alley and a small square now and then (`open` is the chance of a gap, 0 to 1). The district's `props` (people, carts, lamps, statues) then stand on the pavement and in the gaps. A name listed twice is picked twice as often. `density` (0 to 1) sets how many loose props any district gets. The other districts stay open country.
- Nothing overlaps: props keep clear of the road for their whole height, of every landmark and of each other's ground, and small things are never hidden behind buildings. Rest-stop landmarks slide along the road when an arch or the Capitol is in the way.
- `landmark_capitolium` crowns the very top (end of chapter XXXV).
- Scale: one consistent scale, set by the 16×24 hero. A door is about his height, a house or shop is 44 px wide, the temple 48, the arch 56 and the Capitol 96. An apartment block (insula) is 42×60, the baths 60×46, the basilica 68×46; townspeople are 22 px tall.
- Ground tiles are 64×64 and the road tile 32×32, so repeats are hard to spot on a phone (the visible map is about 190 art px wide).
- Numerals: `font_roman` is ink on a transparent ground. The app carves each numeral into the `face` rectangle (`[x, y, w, h]` inside the sprite) given in `assets.json` for `landmark_milestone` and `landmark_arch`, centred; a week numeral too wide for the milestone goes on two lines, tens above units (XXX over VIII). If you repaint the milestone or the arch, keep the face flat `marble` and update `face` if it moves.
- Waypoints: `wp_done`, `wp_current`, `wp_locked`, `wp_rest`.
- The player is `hero_base` (always worn: tunic, belt, sandals) with optional overlay layers drawn on top in this fixed order: `hero_cloak`, `hero_toga`, `hero_satchel`, `hero_laurel`. Any combination can be worn at once (all four by the end), so every layer must look right over the base alone and stacked with the others.

### Chapter → district

| chapter | district |
|---|---|
| 1 | `provinciae` — The provinces of the Empire (chapter I) |
| 2 | `villa` — The family villa and household |
| 3 | `villa` — The family villa and household |
| 4 | `villa` — The family villa and household |
| 5 | `hortus` — The garden (hortus) and peristyle |
| 6 | `via` — The Via Latina toward Tusculum |
| 7 | `hortus` — The garden (hortus) and peristyle |
| 8 | `taberna` — The shops of Rome |
| 9 | `rus` — Farm and countryside |
| 10 | `silva` — Forest of wild beasts |
| 11 | `villa` — The family villa and household |
| 12 | `castra` — Army camp / frontier |
| 13 | `templa` — Temples and the calendar |
| 14 | `villa` — The family villa and household |
| 15 | `ludus` — The school (ludus) |
| 16 | `mare` — Harbor and open sea |
| 17 | `ludus` — The school (ludus) |
| 18 | `ludus` — The school (ludus) |
| 19 | `forum` — The Forum and the Capitol (finale) |
| 20 | `villa` — The family villa and household |
| 21 | `urbs` — Streets of Rome |
| 22 | `villa` — The family villa and household |
| 23 | `ludus` — The school (ludus) |
| 24 | `villa` — The family villa and household |
| 25 | `creta` — Crete and the Labyrinth (myth) |
| 26 | `caelum` — Cliffs and sky (Daedalus and Icarus) |
| 27 | `rus` — Farm and countryside |
| 28 | `mare` — Harbor and open sea |
| 29 | `mare` — Harbor and open sea |
| 30 | `triclinium` — The dining room (banquet) |
| 31 | `triclinium` — The dining room (banquet) |
| 32 | `mare` — Harbor and open sea |
| 33 | `castra` — Army camp / frontier |
| 34 | `theatrum` — Theater and circus |
| 35 | `forum` — The Forum and the Capitol (finale) |

## Asset list

| id | file | size (px) | frames | where it appears | what it depicts |
|---|---|---|---|---|---|
| `hero_base` | `sprites/hero_base.png` | 16×24 per frame (sheet 96×96) | 6 @ 8 fps | Map: the player character (always drawn) | A young Roman in a cream tunic with a belt and sandals, dark hair. Sprite sheet, 6 columns x 4 rows of 16x24 frames. Columns: idle 0, idle 1, walk 0-3. Rows: facing down, up, left, right. Feet at the bottom-centre of each frame (anchor 8,23). |
| `hero_toga` | `sprites/hero_toga.png` | 16×24 per frame (sheet 96×96) | 6 @ 8 fps | Map: outfit layer drawn over hero_base when equipped | Overlay layer: white toga with a purple border (toga praetexta) draped over the tunic. Same frame layout as hero_base; transparent elsewhere. |
| `hero_cloak` | `sprites/hero_cloak.png` | 16×24 per frame (sheet 96×96) | 6 @ 8 fps | Map: outfit layer drawn over hero_base when equipped | Overlay layer: terracotta travelling cloak (paenula) with a gold clasp. Same frame layout as hero_base; transparent elsewhere. |
| `hero_laurel` | `sprites/hero_laurel.png` | 16×24 per frame (sheet 96×96) | 6 @ 8 fps | Map: outfit layer drawn over hero_base when equipped | Overlay layer: green laurel wreath on the head (final reward). Same frame layout as hero_base; transparent elsewhere. |
| `hero_satchel` | `sprites/hero_satchel.png` | 16×24 per frame (sheet 96×96) | 6 @ 8 fps | Map: outfit layer drawn over hero_base when equipped | Overlay layer: leather school satchel (capsa) on a strap. Same frame layout as hero_base; transparent elsewhere. |
| `tile_via` | `tiles/tile_via.png` | 32×32 | 1 | Map: the stone-paved road (repeating texture along the path) | Seamless 32x32 tile of Roman basalt paving (polygonal blocks), grey with darker joints; no direction, so it sits under any curve. |
| `bg_provinciae` | `tiles/bg_provinciae.png` | 64×64 | 1 | Map background, district: The provinces of the Empire (chapter I) | Seamless 64x64 ground tile: an old parchment map-land: pale sand, faint contour specks. |
| `bg_villa` | `tiles/bg_villa.png` | 64×64 | 1 | Map background, district: The family villa and household | Seamless 64x64 ground tile: trimmed grass and garden borders around the villa. |
| `bg_hortus` | `tiles/bg_hortus.png` | 64×64 | 1 | Map background, district: The garden (hortus) and peristyle | Seamless 64x64 ground tile: lush garden ground with flowers (roses, lilies). |
| `bg_via` | `tiles/bg_via.png` | 64×64 | 1 | Map background, district: The Via Latina toward Tusculum | Seamless 64x64 ground tile: roadside meadow, dusty verges. |
| `bg_taberna` | `tiles/bg_taberna.png` | 64×64 | 1 | Map background, district: The shops of Rome | Seamless 64x64 ground tile: packed earth and paving in front of shops. |
| `bg_rus` | `tiles/bg_rus.png` | 64×64 | 1 | Map background, district: Farm and countryside | Seamless 64x64 ground tile: fields with furrows, pasture. |
| `bg_silva` | `tiles/bg_silva.png` | 64×64 | 1 | Map background, district: Forest of wild beasts | Seamless 64x64 ground tile: dark forest floor. |
| `bg_castra` | `tiles/bg_castra.png` | 64×64 | 1 | Map background, district: Army camp / frontier | Seamless 64x64 ground tile: trampled earth of a legionary camp. |
| `bg_templa` | `tiles/bg_templa.png` | 64×64 | 1 | Map background, district: Temples and the calendar | Seamless 64x64 ground tile: marble paving. |
| `bg_ludus` | `tiles/bg_ludus.png` | 64×64 | 1 | Map background, district: The school (ludus) | Seamless 64x64 ground tile: stone floor of a schoolroom portico. |
| `bg_mare` | `tiles/bg_mare.png` | 64×64 | 1 | Map background, district: Harbor and open sea | Seamless 64x64 ground tile: sea water with small waves. |
| `bg_urbs` | `tiles/bg_urbs.png` | 64×64 | 1 | Map background, district: Streets of Rome | Seamless 64x64 ground tile: basalt street paving. |
| `bg_creta` | `tiles/bg_creta.png` | 64×64 | 1 | Map background, district: Crete and the Labyrinth (myth) | Seamless 64x64 ground tile: ochre Cretan earth. |
| `bg_caelum` | `tiles/bg_caelum.png` | 64×64 | 1 | Map background, district: Cliffs and sky (Daedalus and Icarus) | Seamless 64x64 ground tile: pale sky with clouds. |
| `bg_triclinium` | `tiles/bg_triclinium.png` | 64×64 | 1 | Map background, district: The dining room (banquet) | Seamless 64x64 ground tile: mosaic floor in deep reds. |
| `bg_theatrum` | `tiles/bg_theatrum.png` | 64×64 | 1 | Map background, district: Theater and circus | Seamless 64x64 ground tile: sand of the arena. |
| `bg_forum` | `tiles/bg_forum.png` | 64×64 | 1 | Map background, district: The Forum and the Capitol (finale) | Seamless 64x64 ground tile: gleaming marble and gold-flecked paving. |
| `prop_cypress` | `props/prop_cypress.png` | 14×36 | 1 | Map decoration scattered beside the road in districts: provinciae, villa, via, silva, templa | tall slender Italian cypress. Anchor at bottom centre. |
| `prop_pine` | `props/prop_pine.png` | 30×31 | 1 | Map decoration scattered beside the road in districts: via, silva | Italian umbrella (stone) pine. Anchor at bottom centre. |
| `prop_olive` | `props/prop_olive.png` | 24×23 | 1 | Map decoration scattered beside the road in districts: provinciae, hortus, rus, creta | olive tree, silvery leaves. Anchor at bottom centre. |
| `prop_bush` | `props/prop_bush.png` | 14×10 | 1 | Map decoration scattered beside the road in districts: villa, hortus, silva | low shrub with a few rose blossoms. Anchor at bottom centre. |
| `prop_column` | `props/prop_column.png` | 10×28 | 1 | Map decoration scattered beside the road in districts: villa, hortus, templa, ludus, urbs, creta, triclinium, theatrum, forum | single marble column. Anchor at bottom centre. |
| `prop_statue` | `props/prop_statue.png` | 14×31 | 1 | Map decoration scattered beside the road in districts: hortus, templa, ludus, urbs, theatrum, forum | marble statue on a plinth. Anchor at bottom centre. |
| `prop_house` | `props/prop_house.png` | 44×36 | 1 | Map: built in rows in the city districts: taberna; Map decoration scattered beside the road in districts: villa, via | small Roman house with terracotta roof. Anchor at bottom centre. |
| `prop_shop` | `props/prop_shop.png` | 44×34 | 1 | Map: built in rows in the city districts: taberna | taberna (shop front) with striped awning and goods. Anchor at bottom centre. |
| `prop_sheep` | `props/prop_sheep.png` | 14×11 | 1 | Map decoration scattered beside the road in districts: rus | white sheep (pastor et ovēs). Anchor at bottom centre. |
| `prop_rock` | `props/prop_rock.png` | 13×9 | 1 | Map decoration scattered beside the road in districts: provinciae, via, rus, silva, castra, mare, creta, caelum | grey boulder. Anchor at bottom centre. |
| `prop_vine` | `props/prop_vine.png` | 12×19 | 1 | Map decoration scattered beside the road in districts: rus | grapevine on a stake with purple grapes. Anchor at bottom centre. |
| `prop_wheat` | `props/prop_wheat.png` | 12×12 | 1 | Map decoration scattered beside the road in districts: rus | sheaf of ripe wheat. Anchor at bottom centre. |
| `prop_boat` | `props/prop_boat.png` | 33×28 | 1 | Map decoration scattered beside the road in districts: mare | merchant ship with a square sail. Anchor at bottom centre. |
| `prop_wave` | `props/prop_wave.png` | 14×4 | 1 | Map decoration scattered beside the road in districts: mare | small wave crest (decor on water). Anchor at bottom centre. |
| `prop_tent` | `props/prop_tent.png` | 36×23 | 1 | Map decoration scattered beside the road in districts: castra | legionary goatskin tent, gable end on, with a red pennant. Anchor at bottom centre. |
| `prop_standard` | `props/prop_standard.png` | 10×30 | 1 | Map decoration scattered beside the road in districts: castra | legion standard (aquila) with red banner. Anchor at bottom centre. |
| `prop_amphora` | `props/prop_amphora.png` | 10×16 | 1 | Map decoration scattered beside the road in districts: villa, taberna, triclinium | clay amphora. Anchor at bottom centre. |
| `prop_bench` | `props/prop_bench.png` | 20×12 | 1 | Map decoration scattered beside the road in districts: ludus | school bench with a wax tablet. Anchor at bottom centre. |
| `prop_templum` | `props/prop_templum.png` | 48×46 | 1 | Map: built in rows in the city districts: forum; Map decoration scattered beside the road in districts: provinciae, templa | small temple facade. Anchor at bottom centre. |
| `prop_wall` | `props/prop_wall.png` | 32×18 | 1 | Map decoration scattered beside the road in districts: castra | crenellated stone wall segment. Anchor at bottom centre. |
| `prop_labyrinth` | `props/prop_labyrinth.png` | 24×23 | 1 | Map decoration scattered beside the road in districts: creta | stone slab carved with a labyrinth (Crete). Anchor at bottom centre. |
| `prop_cloud` | `props/prop_cloud.png` | 28×9 | 1 | Map decoration scattered beside the road in districts: caelum | small cloud. Anchor at bottom centre. |
| `prop_feather` | `props/prop_feather.png` | 10×12 | 1 | Map decoration scattered beside the road in districts: caelum | loose feather (Icarus). Anchor at bottom centre. |
| `prop_couch` | `props/prop_couch.png` | 30×15 | 1 | Map decoration scattered beside the road in districts: triclinium | dining couch (lectus triclinii). Anchor at bottom centre. |
| `prop_lamp` | `props/prop_lamp.png` | 8×22 | 1 | Map decoration scattered beside the road in districts: taberna, ludus, urbs, triclinium | standing oil lamp. Anchor at bottom centre. |
| `prop_mask` | `props/prop_mask.png` | 12×18 | 1 | Map decoration scattered beside the road in districts: theatrum | painted theatre mask on a short stone post. Anchor at bottom centre. |
| `prop_arena` | `props/prop_arena.png` | 44×24 | 1 | Map decoration scattered beside the road in districts: theatrum | small circus/arena oval. Anchor at bottom centre. |
| `prop_insula` | `props/prop_insula.png` | 42×60 | 1 | Map: built in rows in the city districts: taberna, urbs | apartment block (insula): shops at street level, a timber balcony and three floors of small windows. Anchor at bottom centre. |
| `prop_insula_b` | `props/prop_insula_b.png` | 34×50 | 1 | Map: built in rows in the city districts: taberna, urbs | smaller apartment block in bare brick with travertine string courses and an arched shop. Anchor at bottom centre. |
| `prop_domus` | `props/prop_domus.png` | 54×34 | 1 | Map: built in rows in the city districts: urbs | town house (domus): blind street wall, tall doorway, the atrium roof with its open compluvium behind. Anchor at bottom centre. |
| `prop_thermae` | `props/prop_thermae.png` | 60×46 | 1 | Map: built in rows in the city districts: urbs | public baths (thermae): vaulted hall with a lunette window, a domed hot room and a smoking furnace flue. Anchor at bottom centre. |
| `prop_basilica` | `props/prop_basilica.png` | 68×46 | 1 | Map: built in rows in the city districts: forum | basilica: two storeys of marble arcades under a long tiled roof. Anchor at bottom centre. |
| `prop_pistrinum` | `props/prop_pistrinum.png` | 42×37 | 1 | Map: built in rows in the city districts: taberna | bakery (pistrinum): brick oven with a fire, loaves on shelves, two lava millstones and a grain sack. Anchor at bottom centre. |
| `prop_tholos` | `props/prop_tholos.png` | 36×42 | 1 | Map: built in rows in the city districts: forum; Map decoration scattered beside the road in districts: templa | round temple (tholos, like the Temple of Vesta) with a conical roof. Anchor at bottom centre. |
| `prop_portico` | `props/prop_portico.png` | 46×30 | 1 | Map: built in rows in the city districts: urbs, forum | a stretch of colonnade (porticus) under a tiled roof. Anchor at bottom centre. |
| `prop_aqueduct` | `props/prop_aqueduct.png` | 54×46 | 1 | Map: built in rows in the city districts: urbs | three arches of an aqueduct carrying its water channel; the arches are transparent. Anchor at bottom centre. |
| `prop_theatre` | `props/prop_theatre.png` | 60×42 | 1 | Map decoration scattered beside the road in districts: theatrum | theatre: the curved outer wall of the seating, two tiers of arcades below an attic. Anchor at bottom centre. |
| `prop_obelisk` | `props/prop_obelisk.png` | 12×46 | 1 | Map decoration scattered beside the road in districts: theatrum | red granite obelisk with a gilded tip, as on the spina of the Circus. Anchor at bottom centre. |
| `prop_columna` | `props/prop_columna.png` | 16×56 | 1 | Map decoration scattered beside the road in districts: forum | honorary column with a spiral of reliefs and a gilded statue on top. Anchor at bottom centre. |
| `prop_rostra` | `props/prop_rostra.png` | 46×22 | 1 | Map decoration scattered beside the road in districts: forum | the Rostra: speakers' platform hung with the bronze rams of captured ships. Anchor at bottom centre. |
| `prop_altar` | `props/prop_altar.png` | 13×16 | 1 | Map decoration scattered beside the road in districts: templa, forum | marble altar with a garland and a burning offering. Anchor at bottom centre. |
| `prop_civis` | `props/prop_civis.png` | 11×22 | 1 | Map decoration scattered beside the road in districts: taberna, urbs, theatrum, forum | citizen in a toga, standing (static, facing the viewer). Anchor at bottom centre. |
| `prop_matrona` | `props/prop_matrona.png` | 11×22 | 1 | Map decoration scattered beside the road in districts: taberna, urbs, theatrum, forum | woman in a stola with her palla drawn over her head (static). Anchor at bottom centre. |
| `prop_mercator` | `props/prop_mercator.png` | 11×22 | 1 | Map decoration scattered beside the road in districts: taberna, urbs | street seller in a tunic carrying a tray of loaves on his head (static). Anchor at bottom centre. |
| `prop_plaustrum` | `props/prop_plaustrum.png` | 26×15 | 1 | Map decoration scattered beside the road in districts: taberna, urbs | two-wheeled cart (plaustrum) loaded with amphorae. Anchor at bottom centre. |
| `landmark_milestone` | `landmarks/landmark_milestone.png` | 21×28 | 1 | Map: every rest stop (one per week) | Roman milestone (miliarium). `face` is its flat marble inscription field; the week number is carved there with font_roman, on two lines (tens above units) when it is too long for one. Anchor at bottom centre. |
| `landmark_fountain` | `landmarks/landmark_fountain.png` | 30×25 | 1 | Map: rest stop (catch-up day), alternates with shrine | public fountain with a basin and a spout. Anchor at bottom centre. |
| `landmark_shrine` | `landmarks/landmark_shrine.png` | 22×31 | 1 | Map: rest stop (catch-up day), alternates with fountain | small roadside shrine (lararium/aedicula) with a gilded image. Anchor at bottom centre. |
| `landmark_arch` | `landmarks/landmark_arch.png` | 56×44 | 1 | Map: end of every chapter | triumphal arch spanning the road where the chapter changes; `face` is the marble panel in the gold frame on the attic, which takes the chapter numeral. Anchor at bottom centre. |
| `landmark_capitolium` | `landmarks/landmark_capitolium.png` | 96×72 | 1 | Map: final destination (end of chapter XXXV) | Temple of Jupiter on the Capitoline: wide steps, columns, gilded pediment. Anchor at bottom centre. |
| `wp_locked` | `ui/wp_locked.png` | 12×12 | 1 | Map: waypoint marker on the road | dim grey stepping stone (future day, locked). |
| `wp_current` | `ui/wp_current.png` | 12×12 | 1 | Map: waypoint marker on the road | glowing golden marker (today's unlocked stop). |
| `wp_done` | `ui/wp_done.png` | 12×12 | 1 | Map: waypoint marker on the road | terracotta stamped marker with a gold dot (completed day). |
| `wp_rest` | `ui/wp_rest.png` | 12×12 | 1 | Map: waypoint marker on the road | blue-grey marker for rest stops. |
| `coin_as` | `ui/coin_as.png` | 24×24 | 1 | Rewards screen: streak coin | A bronze as seen face-on, with a ship's prow. |
| `coin_dupondius` | `ui/coin_dupondius.png` | 24×24 | 1 | Rewards screen: streak coin | A brass dupondius seen face-on, with a radiate head. |
| `coin_sestertius` | `ui/coin_sestertius.png` | 24×24 | 1 | Rewards screen: streak coin | An orichalcum sestertius seen face-on, with a laureate head. |
| `coin_quinarius` | `ui/coin_quinarius.png` | 24×24 | 1 | Rewards screen: streak coin | A small silver quinarius seen face-on, with a winged Victory. |
| `coin_denarius` | `ui/coin_denarius.png` | 24×24 | 1 | Rewards screen: streak coin | A silver denarius seen face-on, with a helmeted head. |
| `coin_aureus` | `ui/coin_aureus.png` | 24×24 | 1 | Rewards screen: streak coin | A gold aureus seen face-on, with a laureate head. |
| `icon_tunic` | `ui/icon_tunic.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: tunic. |
| `icon_toga` | `ui/icon_toga.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: folded toga with purple border. |
| `icon_cloak` | `ui/icon_cloak.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: travelling cloak. |
| `icon_laurel` | `ui/icon_laurel.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: laurel wreath. |
| `icon_satchel` | `ui/icon_satchel.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: school satchel. |
| `icon_streak` | `ui/icon_streak.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: small flame / hearth for the streak counter. |
| `icon_scroll` | `ui/icon_scroll.png` | 20×20 | 1 | UI icon (wardrobe, stats) | Icon: scroll for "words learned". |
| `ui_frame` | `ui/ui_frame.png` | 24×24 | 1 | UI: 9-slice frame for chapter title cards and panels (8px slices) | Parchment panel with a terracotta double border and gold corner studs. Must work as CSS border-image with 8px slices. |
| `ui_tablet` | `ui/ui_tablet.png` | 48×24 | 1 | Rewards screen: background of each collected chapter inscription | Marble inscription tablet (tabula ansata) with a carved inner border; text is overlaid by the app. |
| `font_roman` | `ui/font_roman.png` | 3×7 per glyph (sheet 28×7) | 7 | Map: Roman numerals on milestones and arches | Bitmap font sheet: glyphs I V X L C D M in that order, ink on transparent, 7 high. Each glyph sits left-aligned in a cell; cells are `advance` (4) apart, so the sheet is 28x7. `widths` is each glyph's width and `gap` the space the app leaves between glyphs. |
| `app_icon_180` | `../icons/icon-180.png` | 180×180 | 1 | Home-screen / PWA icon | App icon: a laurel wreath around a cream letter L on a terracotta field, pixel-art style (24x24 art upscaled ×7 on a 180px field). |
| `app_icon_192` | `../icons/icon-192.png` | 192×192 | 1 | Home-screen / PWA icon | App icon: a laurel wreath around a cream letter L on a terracotta field, pixel-art style (24x24 art upscaled ×8). |
| `app_icon_512` | `../icons/icon-512.png` | 512×512 | 1 | Home-screen / PWA icon | App icon: a laurel wreath around a cream letter L on a terracotta field, pixel-art style (32x32 art upscaled ×16; the wreath stays inside the maskable safe zone). |

## Animation notes

- `hero_*` sheets: columns = [idle0, idle1, walk0, walk1, walk2, walk3]; rows = [down, up, left, right]. The `anim` field in assets.json maps animation names to column indices — you may add frames and update `frames`/`anim`.
- Each frame is assembled from an upper body, a pair of legs and (side views) a swinging arm. The upper body drops one pixel on idle1 and on the two contact frames of the walk (walk0, walk2); every outfit layer is shifted by the same amount in the generator, which is what keeps the layers aligned with the base in every frame. The right-facing row is the left-facing row mirrored, except that the toga and satchel are drawn for the correct side of the body (the toga leaves the right arm bare; the satchel hangs on the left hip).
- Coins are 24×24 and wardrobe icons 20×20, so both are shown at exactly ×2 (48 px and 40 px), the same pixel size as the map on a phone.
- Walk cycle plays at `fps` while the character moves between waypoints; idle alternates slowly (the app halves the fps for idle).


## Checklist for the artist

1. Keep each file name and pixel size (or update assets.json to match). If you edit grids in `tools/make_final_art.py`, the script does this for you.
2. Keep transparent backgrounds for sprites/props/landmarks; tiles must be seamless.
3. Run `node tools/validate.mjs` afterwards: it checks every asset in assets.json exists and matches its declared size.

