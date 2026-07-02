"""SIMULATION / SUPERSEDED media subpackage — NOT used by any production path.

Everything in ``motodiag.media.sim`` is audit-verified dead relative to the
live diagnostic pipeline: no production module imports it. It is retained ONLY
so the Phase 100 / Phase 101 test suites keep their coverage of the original
simulated contracts.

The REAL, production code paths are:

  - ``motodiag.media.ffmpeg`` — real video frame extraction (JPEG frames off
    disk via the ffmpeg binary), superseding the simulated
    ``sim.video_frames`` extractor.
  - ``motodiag.media.vision_analysis_pipeline`` — the real image-bytes Claude
    Vision analyzer, superseding the text-only ``sim.vision_analyzer_textsim``
    analyzer.
  - ``motodiag.media.vision_types`` — the shared, real Vision data types,
    prompt, and color guides consumed by the live pipeline.

Do NOT wire anything in this subpackage into a production import path. If a new
requirement seems to need one of these, use the real module above instead.
"""
