# Known-bad journals (Phase 390)

Hand-written. Each must be named by the search on start and kept by
`prune_runs`; `tests/test_phase390_resume_contract.py` plants each in a run
directory and asserts both.

- `stage_truncated.json`: a journal cut off mid-write. The journal is
  written by rename, so a cut write leaves the old file; this stands for a
  file damaged some other way (a disk error, a hand edit). `Journal.load`
  cannot read it, so without the check the run is invisible to the search
  and pruned like a finished one.
