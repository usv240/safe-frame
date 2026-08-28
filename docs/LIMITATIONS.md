# Limitations

- Safe Frame is not on a broadcaster-approved device list and cannot replace
  certified delivery testing.
- Current public evaluation is constructed engineering data, not a clinical or
  population-level study.
- The detector implements two of the published rules: general flash and red
  flash. Both are held to the ClickHouse SQL by parity tests. The red rule uses
  a single `red_delta` measure as a stand-in for a full saturated-red transition
  test; it is a defensible pre-check threshold, not a validated reproduction of
  any certified analyser.
- Regular spatial pattern is **not** implemented. A striped or checkerboard
  pattern that meets the published spatial criteria will not be flagged. The
  `regular_pattern` value exists in the schema so the anti-join is already keyed
  on rule, and nothing in the product reports it.
- The live sample begins from transition metrics; production video decoding,
  shot-boundary ingestion, and remediation re-encoding are future integration
  work.
- Prior-art review covers public documentation and cannot establish that no
  private master/rendition comparison exists.
