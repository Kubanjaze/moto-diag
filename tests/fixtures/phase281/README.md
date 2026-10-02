# Phase 281's service fixtures

No test reaches the network (`tests/support/network_guard.py`). Each
service is exercised through these files, swapped in for
`motodiag.core.outbound._open`. Each file is either **recorded** (the real
service's bytes) or **built** (written from the recorded or documented
format), and says which here.

| file | kind | where it came from |
|---|---|---|
| `nhtsa_recalls_mp3_500_2020.json` | recorded | the build's one smoke call to NHTSA's recall service, 2026-09-30T22:36:26Z, HTTP 200, 2149 bytes (`281_phase_log.md`). Byte for byte (sha256 `dfbd533ed6051648…`) |
| `nhtsa_recalls_none_400.json` | recorded | the body `api.nhtsa.gov/recalls/recallsByVehicle` returns with **HTTP 400** for a query with no result: the first record of `~/research/motodiag/all_recalls.jsonl`, fetched 2026-09-20 (Phase 251; F103). Tests serve it with status 400 |
| `nhtsa_blocked_403.html` | recorded | the Akamai "Access Denied" page `www.nhtsa.gov` returned to curl with HTTP 403 on 2026-09-30, read at Step 0. Line endings normalised. F103 records the same kind of page from `api.nhtsa.gov` |
| `vpic_partial_1HD1FRW177Y600001.json` | recorded | the build's one smoke call to vPIC, 2026-09-30T22:36:27Z, HTTP 200, 4126 bytes. The VIN is made up (a valid check digit, serial 600001), so vPIC decodes it partially (error codes 3 and 14, no make or model). Byte for byte (`8c7d0b83288a1f52…`) |
| `vpic_clean_built.json` | built | the recorded vPIC format (the same top-level keys and field names), cut to the fields the app reads, for a clean decode (`ErrorCode` 0) of a made-up VIN |
| `ecb_daily_2026-09-30.xml` | recorded | the build's one smoke call to the ECB's daily feed, 2026-09-30T22:36:28Z, HTTP 200, 1547 bytes, 29 currencies. Byte for byte (`83b221d44f9b2842…`) |
| `service_error_503_built.html` | built | a generic HTTP 503 page, for vPIC and the ECB answering with an error. Neither service's own error page was recorded: that would have taken a live call beyond the one allowed |

A connection that cannot be made (DNS, refused, timeout) is simulated by
raising `urllib.error.URLError` from the swapped transport, which is what
`urllib` raises.
