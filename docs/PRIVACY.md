# Privacy engineering

Separate real device coordinates from virtual location. Record explicit purpose/version/time for consent; ghost/friends settings must apply on the server. Minimise GPS collection and avoid storing precise fixes in logs or public analytics.

Account export and deletion APIs need field completeness and irreversible erasure review across backups, provider media, logs, analytics, financial retention and social references. Do not promise immediate deletion of all records where limited retention is necessary. Complete a reviewed retention schedule and DPIA assessment before public launch.

Status: this document records architecture and validation requirements. See STATUS.md for demonstrated implementation and RELEASE_CHECKLIST.md for acceptance; unrecorded provider/deployment coverage remains pending.
