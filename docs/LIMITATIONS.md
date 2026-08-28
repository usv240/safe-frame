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
- Measurement runs from decoded frames (`safe_frame.ingest`), but Safe Frame
  does not decode containers. Wiring ffmpeg or PyAV in front of it, shot-boundary
  ingestion, and remediation re-encoding are integration work that is not done.
- The public catalogue is generated directly as transition rows rather than
  measured from frames, so the corpus exercises the criteria and the anti-join
  at scale but does not exercise the measurement stage. `tests/test_ingest.py`
  covers that stage separately, on constructed frame sequences.
- Prior-art review covers public documentation and cannot establish that no
  private master/rendition comparison exists.
