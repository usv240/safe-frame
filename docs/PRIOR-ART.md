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
- HardingFPA Server markets watched-folder, web-service, and network submission
  of many jobs, with each job producing its own frame-level analysis report:
  <https://www.hardingfpa.com/hardingfpa-for-broadcast/broadcast-industry/hardingfpa-server/nest/in-depth-2>.
  Its public product and manuals describe queued files analysed independently;
  they do not document a parent/child comparison or a child-minus-parent
  regression verdict. This answers the narrow competitive question without
  claiming knowledge of private customer integrations.
- Interra explicitly describes BATON as no-reference quality checking and its
  PSE/flashiness check as similar to Harding analysis:
  <https://interrasystems.com/file-based-qc.php/QS/video_tutorial-baton.php>.
  BATON+ documents lifecycle-wide QC data and workflow synchronization, but its
  public materials do not document presentation-time anti-join regression:
  <https://www.interrasystems.com/workflow-qc.php>.

The surviving contribution is aligning a version tree on presentation time,
isolating child-only violations, and attributing each regression to its
transformation. This is a documented public gap, not proof that no private
workflow exists.
