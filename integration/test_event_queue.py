
from event_queue import PPEEventQueue


def test_fifo():
    q = PPEEventQueue(maxsize=3)

    assert q.enqueue({"message_id": "evt_1"})
    assert q.enqueue({"message_id": "evt_2"})
    assert q.enqueue({"message_id": "evt_3"})

    assert q.size() == 3

    ids = []

    for _ in range(3):
        event = q.dequeue()
        ids.append(event["message_id"])
        q.task_done()

    assert ids == ["evt_1", "evt_2", "evt_3"]
    assert q.is_empty()

    print("PASS: FIFO ordering")


def test_full_queue():
    q = PPEEventQueue(maxsize=2)

    assert q.enqueue({"message_id": "evt_1"})
    assert q.enqueue({"message_id": "evt_2"})

    assert q.enqueue({"message_id": "evt_3"}) is False

    print("PASS: Full queue handling")


def test_empty_queue():
    q = PPEEventQueue(maxsize=2)

    assert q.dequeue() is None

    print("PASS: Empty queue handling")


if __name__ == "__main__":
    test_fifo()
    test_full_queue()
    test_empty_queue()

    print("\nALL QUEUE TESTS PASSED")
