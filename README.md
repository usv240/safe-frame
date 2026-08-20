# Safe Frame

Safe Frame is a master-to-rendition photosensitivity regression pre-check. It asks a narrow question existing file analysers do not publicly document: did a transformation introduce a violation that was absent from the approved parent?

It is **not a certified or broadcaster-approved photosensitivity test device**. The deterministic detector and SQL implement an open pre-check against published criteria; Gemini may describe offending seconds but cannot decide pass/fail.

## First technical finding

The planned 8×8 tile average is unsafe as the source for screen-area measurement. A constructed 64×64 checkerboard reverses every pixel while every 8×8 tile keeps the same average: direct changed area is 100%, tile-derived changed area is 0%. The implementation therefore computes affected area directly before tile aggregation. Tiles remain diagnostic only.

## Prior-art boundary

HardingFPA Server and HardingFPA-X analyze many submitted files across networked workers. Their public documentation describes queued jobs and per-file reports, not parent/child alignment or a child-minus-parent regression. Interra BATON explicitly describes itself as no-reference. The claim is therefore a documented public gap, not proof that no private workflow exists.

## Current integration status

The local detector, lineage anti-join, SQL, API, and constructed boundary tests are implemented. Catalogue reads deliberately return 503 until a real ClickHouse Cloud account and `mcp-clickhouse` transport are configured; the track requires those reads to occur through MCP. ClickPipes/Pub/Sub and Video Intelligence integration remain pending partner credentials.
