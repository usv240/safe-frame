# Prior-art boundary

The project does not claim photosensitivity detection, repair, viewer dimming,
or batch scale as inventions.

- ITU-R BT.1702 publishes guidance for reducing photosensitive seizure risk:
  <https://www.itu.int/rec/R-REC-BT.1702/en>
- FFmpeg ships a `photosensitivity` filter for detection and mitigation:
  <https://ffmpeg.org/ffmpeg-filters.html#photosensitivity>
- Apple publishes VideoFlashingReduction and ships viewer-side mitigation:
  <https://github.com/apple/VideoFlashingReduction>
- EA publishes IRIS photosensitivity analysis tooling:
  <https://github.com/electronicarts/IRIS>
- HardingFPA markets networked and server analysis products; this occupies
  catalogue-scale processing.
- Interra describes BATON PSE checks as no-reference analysis, which is the
  clearest public boundary from reference-based parent/child regression.

The surviving contribution is aligning a version tree on presentation time,
isolating child-only violations, and attributing each regression to its
transformation. This is a documented public gap, not proof that no private
workflow exists.
