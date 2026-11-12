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


class HeldInputSampler:
    """Refresh a held input after database admission without crossing input edges.

    The receiver owns publish; a database worker may sample under the lock.
    Only one current burst is retained, never identities or client timestamps.
    """
    def __init__(self):
        from threading import Lock
        self.lock = Lock()
        self.latest = None
        self.start_seq = 0

    @staticmethod
    def context(data):
        return data.action, data.city, data.zone, bool(data.x or data.z)

    def publish(self, data):
        with self.lock:
            if self.latest is None or self.context(self.latest) != self.context(data):
                self.start_seq = data.seq
            self.latest = data

    def sample(self, data):
        with self.lock:
            latest = self.latest
            # Vehicles retain their existing input integration. Never coalesce a
            # release, an intervening press/release edge, or a location change.
            if (data.action == 'move' and (data.x or data.z) and latest is not None
                    and self.start_seq <= data.seq < latest.seq
                    and self.context(data) == self.context(latest)):
                return latest
            return data
