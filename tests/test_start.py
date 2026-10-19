import signal

import pytest

import start


def _run(command, *, force=False, stubborn=False):
    killed = []
    alive_after_term = {"state": stubborn}

    def kill(pid, sig):
        killed.append(sig)
        if sig == signal.SIGKILL:
            alive_after_term["state"] = False
        elif not stubborn:
            alive_after_term["state"] = False

    start.free_port(8000, force, find=lambda port: [(4242, command)], kill=kill,
                    alive=lambda pid: alive_after_term["state"], grace_seconds=0.2)
    return killed


def test_our_own_dev_server_is_stopped_gracefully():
    killed = _run(f"python -m uvicorn src.api.server:app --port 8000")
    assert killed == [signal.SIGTERM]


def test_a_process_that_ignores_sigterm_is_killed_after_the_grace_period():
    assert _run(f"node {start.PROJECT_DIR}/frontend/node_modules/.bin/vite", stubborn=True) == [signal.SIGTERM, signal.SIGKILL]


def test_a_foreign_process_is_never_touched_without_force():
    with pytest.raises(SystemExit) as exit_:
        _run("postgres -D /var/lib/postgresql")
    assert "postgres" in str(exit_.value) and "--force" in str(exit_.value)


def test_force_stops_a_foreign_process():
    assert _run("postgres -D /var/lib/postgresql", force=True) == [signal.SIGTERM]


def test_nothing_listening_means_nothing_to_do():
    start.free_port(8000, find=lambda port: [], kill=lambda *a: pytest.fail("must not kill"))
