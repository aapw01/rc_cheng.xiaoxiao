"""Entry point for Dramatiq worker containers.

Reads enabled provider queues from the `providers` table, registers a Dramatiq
actor per queue, then hands control to the Dramatiq CLI so the worker starts
listening on those queues. New providers require restarting this process to
take effect (SPEC §8).
"""

import os
import sys

from dramatiq.cli import main as dramatiq_main

from app.tasks.delivery import bootstrap_actors_from_db


def main() -> None:
    queues = bootstrap_actors_from_db()
    if not queues:
        sys.exit("No enabled providers found; refusing to start worker without queues.")
    os.environ["DRAMATIQ_BOOTSTRAP_PROVIDER_ACTORS"] = "1"
    sys.argv = ["dramatiq", "--threads", "1", "app.tasks.delivery"]
    dramatiq_main()


if __name__ == "__main__":
    main()
