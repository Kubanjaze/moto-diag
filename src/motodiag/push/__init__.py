"""Phase 199 — mechanic-facing push notifications (APNs direct).

The transport layer Phase 170's queue anticipated — but aimed at APP
USERS (mechanics), not the customer queue (which keeps email/sms/in_app;
see the Phase 199 plan's audience decision).

Modules:
    registry — device-token CRUD (register/rebind/delete/prune)
    sender   — PushSender seam: ApnsSender (HTTP/2 + .p8 ES256 JWT),
               DryRunSender (logs; default in tests/dev)
    events   — recipient resolution + payload copy for the two live
               producers (WO transitions/assignment, analysis complete)
"""
