from app.index.progress import fail, finishing, finish, snapshot, start, try_start, update


def test_start_is_zero_percent() -> None:
    start("sentence")
    status = snapshot()
    assert status.running is True
    assert status.granularity == "sentence"
    assert status.done == 0
    assert status.percent == 0.0
    assert status.phase == "embedding"
    fail()


def test_update_computes_percent() -> None:
    start("document")
    update(14, 24)
    status = snapshot()
    assert status.done == 14
    assert status.total == 24
    assert status.percent == 100.0 * 14 / 24
    finish()
    done = snapshot()
    assert done.running is False
    assert done.percent == 100.0
    assert done.phase == "idle"


def test_try_start_rejects_second_job() -> None:
    assert try_start("sentence") is True
    assert try_start("document") is False
    assert snapshot().granularity == "sentence"
    fail()


def test_finishing_keeps_running_at_100() -> None:
    start("document")
    update(10, 10)
    finishing()
    status = snapshot()
    assert status.running is True
    assert status.percent == 100.0
    assert status.phase == "finishing"
    fail()
