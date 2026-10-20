# ADR: Consent-bound WebRTC

Status: accepted architecture direction; implementation evidence remains in STATUS.md.

Decision: Use LiveKit-compatible rooms with server-issued participant tokens after mutual acceptance. Actual media, metering and revocation need end-to-end validation.

Consequence: additional validation is required at the relevant release gate. Revisit this decision when measured requirements or constraints change, and preserve financial/privacy invariants.
