"""Latest held direction, with the most recent press/release edge preserved."""
def enqueue(pending, received, data):
    # This runs without an await on the socket event loop. A worker cannot
    # consume the queue while its at-most-two entries are being replaced.
    entries = []
    while not pending.empty():
        entries.append(pending.get_nowait())
    if entries:
        previous = entries[-1][1]
        same_context = (previous.action, previous.city, previous.zone) == (data.action, data.city, data.zone)
        same_edge = bool(previous.x or previous.z) == bool(data.x or data.z)
        if same_context and same_edge:
            entries.pop()
    entries.append((received, data))
    for entry in entries[-2:]:
        pending.put_nowait(entry)
