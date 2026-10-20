# Realtime presence

Presence represents virtual x/z coordinates, never private device GPS. Authenticated movements must be bounded by elapsed time and transport entitlement; nearby visibility is privacy/block aware. Redis configuration does not by itself prove distributed multiplayer scaling.

Exercise two real test clients, session expiry, reconnect, ghost privacy, blocks, stale removal and malicious movement. Measure fan-out by city/cell and p95 delivery latency. Keep one API replica until cross-worker coordination is tested. Verify websocket ALB path/idle timeout and authentication before scaling.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
