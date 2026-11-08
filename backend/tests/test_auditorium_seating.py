"""Real venue permissions and persisted occupancy, including competing attendees."""
import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from backend.tests.test_core import system, register, onboard
from backend.api.models import Presence
from backend.api.auditorium_seating import Seat, CHAIRS

def venue(system):
    c, sessions = system
    people = [register(c, name) for name in ('chairhost', 'chairguest', 'chairthird')]
    for headers, _ in people: onboard(c, headers)
    response = c.post('/api/events', headers=people[0][0], json={
        'title': 'Local seating regression', 'city': 'london',
        'starts_at': time.time(), 'venue_mode': 'virtual_auditorium',
        'communication_mode': 'text'})
    assert response.status_code == 201, response.text
    event_id = response.json()['id']
    assert c.post(f'/api/events/{event_id}/state/start', headers=people[0][0]).status_code == 200
    for headers, _ in people:
        assert c.post(f'/api/events/{event_id}/join', headers=headers).status_code == 200
        assert c.post(f'/api/events/{event_id}/venue/enter', headers=headers).status_code == 200
    return c, sessions, people, event_id

def approach(sessions, person, number=0, moving=False):
    with sessions.begin() as db:
        p = db.get(Presence, person['id'])
        p.x, p.z = CHAIRS[number]
        p.motion_speed = 2 if moving else 0
        p.last_move = time.time() - 2

def test_automatic_seating_persists_and_movement_stands(system):
    c, sessions, people, event_id = venue(system)
    headers, person = people[1]
    approach(sessions, person, moving=True)
    assert not c.get('/api/world/london', headers=headers).json()['position']['seated']
    approach(sessions, person)
    for _ in range(2):
        state = c.get('/api/world/london', headers=headers).json()
        assert state['position']['seated'] and state['position']['seat'] == 0
    other = c.get('/api/world/london', headers=people[0][0]).json()
    remote = next(p for p in other['players'] if p['id'] == person['id'])
    assert remote['seated'] and remote['seat'] == 0
    assert c.post('/api/world/move', headers=headers, json={'dx': 0, 'dz': 1}).status_code == 200
    with sessions() as db: assert db.scalar(select(Seat).where(Seat.user_id == person['id'])) is None
    approach(sessions, person)
    assert c.get('/api/world/london', headers=headers).json()['position']['seated']
    assert c.post(f'/api/events/{event_id}/venue/exit', headers=headers).status_code == 200
    with sessions() as db: assert db.scalar(select(Seat).where(Seat.user_id == person['id'])) is None

def test_competing_attendees_cannot_occupy_one_chair(system):
    c, sessions, people, _ = venue(system)
    for _, person in people[1:]: approach(sessions, person)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda h: c.get('/api/world/london', headers=h), [p[0] for p in people[1:]]))
    assert all(r.status_code == 200 for r in results)
    assert sum(r.json()['position']['seated'] for r in results) == 1
    with sessions() as db: assert len(list(db.scalars(select(Seat)))) == 1

def test_world_coordinates_cannot_claim_an_auditorium_chair(system):
    c, sessions = system
    headers, person = register(c)
    onboard(c, headers)
    approach(sessions, person)
    state = c.get('/api/world/london', headers=headers).json()
    assert not state['position']['seated']
    with sessions() as db: assert not list(db.scalars(select(Seat)))
