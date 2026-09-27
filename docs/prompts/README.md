# Phase prompts

The prompt that starts a phase session is written here, as
`<phase>_<slug>.txt`, before the session is started. A GLM run's `start.sh`
reads its prompt from this folder; nothing else keeps a copy. The operator,
2026-09-27: "phase prompts move from ~/.cache/motodiag/prompts/ … into the
repo under docs/prompts/, and future ones are written there."

## Moved in on 2026-09-27 (Phase 358)

Each file is the original byte for byte; its sha256 is the original's. The
originals were deleted from the cache after this commit. Phase 257 and
earlier left no prompt file.

| file | moved from | written | sha256 |
|---|---|---|---|
| `258_glm_builder.txt` | `~/.cache/motodiag/glm-builder/258_20260924_190801/prompt.txt` | 2026-09-24 19:10 | `5e68ff993ff75fa69b9dd457f90cf1d7a25969c08a4ea113d3ddb0122970b07a` |
| `259_glm_builder.txt` | `~/.cache/motodiag/glm-builder/259_20260924_211014/prompt.txt` | 2026-09-24 21:10 | `9bd8f37e820e1e8ed3c4919976edf55c12005f2426c02364b96115d246ee34d0` |
| `260_glm_builder.txt` | `~/.cache/motodiag/glm-builder/260_20260925_005511/prompt.txt` | 2026-09-25 00:55 | `92270b65d14203a61a0f711d5ab213c88e8dd321ec4ca61b882daa47c362dbb6` |
| `260_opus_landing.txt` | `~/.cache/motodiag/glm-builder/260_20260925_005511/opus_landing_prompt.txt` | 2026-09-25 01:47 | `a8e1a4d580bafce9e19173d7f96082b07081e9b17a69005378e0bbfabb05684d` |
| `355_parallel_tests.txt` | `~/.cache/motodiag/prompts/355_parallel_tests.txt` | 2026-09-25 01:58 | `ef0427003d7fe257daf054a06bc42359fcb5e5f12d6cfd2f6ae28644ccf36b33` |
| `261_track_n_batch1.txt` | `~/.cache/motodiag/prompts/261_track_n_batch1.txt` | 2026-09-25 12:49 | `da60d8403d73892cbdae251b211e67dea61a1793230a036171f6ae9130147b56` |
| `264_track_n_batch2.txt` | `~/.cache/motodiag/prompts/264_track_n_batch2.txt` | 2026-09-26 12:07 | `8964f4707ea6099edf6c0dc27623a92bb0f88ecf046819c9702ed230aadac571` |
| `262_track_n_batch3.txt` | `~/.cache/motodiag/prompts/262_track_n_batch3.txt` | 2026-09-26 14:36 | `6b4f4cabe99b1959107c7a3ef0705940df1db881a97b2655a53c027ceb4e48e1` |
| `272_gate15.txt` | `~/.cache/motodiag/prompts/272_gate15.txt` | 2026-09-26 17:55 | `9ea0ba91281c2abab5aec7123f58ff0aafc830da7173eb2bbe23a8a76b5e2e37` |
| `358_process_cleanup.txt` | `~/.cache/motodiag/prompts/358_process_cleanup.txt` | 2026-09-27 10:00 | `67d256fc7d903cf2b36f3054e19ab44eb6dbb9de2a8a197b6b81342bc1501294` |

Check any file with `shasum -a 256 docs/prompts/<file>`.

The GLM run folders still hold what is not a prompt: `start.sh`,
`sandbox.sb`, `baseline.txt` and the run's `tmp/`. Their `start.sh` read
`$RUN/prompt.txt`, which is now here; those runs are finished.
