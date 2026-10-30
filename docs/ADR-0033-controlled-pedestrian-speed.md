# ADR 0033: Controlled outdoor pedestrian speed

The owner-reported excessive walking/running was reproduced in the shared speed configuration: outdoor walking was 22.5 m/s and running 70.3125 m/s. Set the existing outdoor multiplier to 0.2 and walk factor to 0.8, producing 2 and 4.6875 m/s respectively. Preserve vehicle speeds, collision checks, authoritative elapsed-time caps and held-input policy.

Browser acceptance measures actual displacement and server acknowledgements, with physical emulated-touch joystick direction, release and cancellation checks. This does not claim physical iOS-device validation. Existing camera, keyboard, vehicle and fallback checks remain required. The guest preview and indoor calibration are unchanged by this targeted authenticated-outdoor hotfix.

The separately requested 503 incident requires real logs. A read-only `inspect-production` operation uses existing workflow identity to collect the current production revision/traffic, bounded seven-day 5xx request summaries and sanitized exception categories. No credentials, query strings, account routes or raw payloads are exported. It does not deploy, scale, approve a release or mutate user data.

Financial corrections remain separate from this stability release; payment gates and wallet history are unchanged.
