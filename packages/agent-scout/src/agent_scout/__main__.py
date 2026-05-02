import logging
import signal
import sys

from agent_scout.config import Config
from agent_scout.emitter import Emitter
from agent_scout.state import StateStore
from agent_scout.watcher import Watcher


def main() -> None:
    cfg = Config()

    logging.basicConfig(
        level=cfg.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("agent_scout")

    if not cfg.agent_data_dir.exists():
        logger.error("AGENT_DATA_DIR does not exist: %s", cfg.agent_data_dir)
        sys.exit(1)

    logger.info("AgentScout starting")
    logger.info("  data dir  : %s", cfg.agent_data_dir)
    logger.info("  state dir : %s", cfg.state_dir)
    logger.info("  watchtower: %s", cfg.watchtower_url)

    state = StateStore(cfg.state_dir)
    emitter = Emitter(cfg.watchtower_url, timeout=cfg.emit_timeout_seconds)
    watcher = Watcher(cfg.agent_data_dir, state, emitter)

    watcher.initial_scan()
    watcher.start()

    def _shutdown(sig, frame):
        logger.info("Shutting down (signal %s)", sig)
        watcher.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    watcher.join()


if __name__ == "__main__":
    main()
