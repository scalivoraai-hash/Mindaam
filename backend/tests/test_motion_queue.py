import asyncio
from types import SimpleNamespace
from backend.api.motion_queue import enqueue

def motion(seq, x=1, city='london', action='move'):
    return SimpleNamespace(seq=seq,x=x,z=0,city=city,zone='world',action=action)

def drain(queue):
    rows=[]
    while not queue.empty(): rows.append(queue.get_nowait())
    return rows

def test_held_direction_does_not_keep_an_obsolete_sample_during_database_delay():
    queue=asyncio.Queue(maxsize=2)
    enqueue(queue,.12,motion(1))
    enqueue(queue,.24,motion(2))
    enqueue(queue,.36,motion(3))
    received,data=queue.get_nowait()
    # Worker becomes available at .48 and authorization takes .18 seconds.
    # The old FIFO would process receipt .24, already stale at .66.
    assert .48+.18-received < .35
    assert data.seq==3
    assert queue.empty()

def test_short_press_and_release_are_both_retained():
    queue=asyncio.Queue(maxsize=2)
    enqueue(queue,0,motion(1))
    enqueue(queue,.03,motion(2,x=0))
    assert [d.seq for _,d in drain(queue)]==[1,2]

def test_latest_release_survives_duplicate_releases():
    queue=asyncio.Queue(maxsize=2)
    for seq,x in [(1,1),(2,1),(3,0),(4,0)]:enqueue(queue,seq,motion(seq,x=x))
    assert [d.seq for _,d in drain(queue)]==[2,4]

def test_new_press_preserves_previous_release_and_queue_bound():
    queue=asyncio.Queue(maxsize=2)
    for seq,x in [(1,1),(2,0),(3,1),(4,-1)]:enqueue(queue,seq,motion(seq,x=x))
    assert [d.seq for _,d in drain(queue)]==[2,4]

def test_location_and_action_transitions_are_not_coalesced():
    for change in [{'city':'paris'},{'action':'drive'}]:
        queue=asyncio.Queue(maxsize=2)
        enqueue(queue,0,motion(1))
        enqueue(queue,.12,motion(2,**change))
        assert [d.seq for _,d in drain(queue)]==[1,2]


def test_sampler_refreshes_only_current_uninterrupted_pedestrian_press():
    from backend.api.motion_queue import HeldInputSampler
    sampler=HeldInputSampler()
    first=motion(1);latest=motion(2,x=-1)
    sampler.publish(first);sampler.publish(latest)
    assert sampler.sample(first) is latest
    stop=motion(3,x=0);sampler.publish(stop)
    assert sampler.sample(first) is first
    resumed=motion(4);sampler.publish(resumed)
    assert sampler.sample(first) is first
    assert sampler.sample(stop) is stop
    sampler.publish(motion(5,city='birmingham'))
    assert sampler.sample(resumed) is resumed
    drive=motion(6,action='drive');sampler.publish(drive);sampler.publish(motion(7,action='drive'))
    assert sampler.sample(drive) is drive
