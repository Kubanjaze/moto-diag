import time

def test_outlives_the_alarm():
    """Runs after the leaking test in the same worker; 400 s > 345 s."""
    time.sleep(400)
