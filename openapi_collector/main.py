import logging
import time

from openapi_collector import __version__, cmd, shutdown
from openapi_collector.collector import collect_specs
from openapi_collector.helpers import get_kube_api

logger = logging.getLogger('collector')


def main(args=None):
    parser = cmd.get_parser()
    args = parser.parse_args(args)

    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    logger.info(f"Collector v{__version__} started")

    return run_loop(args.interval)


def run_loop(interval):
    handler = shutdown.GracefulShutdown()
    while True:
        try:
            api = get_kube_api()
            collect_specs(api)

        except Exception as e:
            logger.exception("Failed to collect specs: %s", e)

        if handler.shutdown_now:
            return

        with handler.safe_exit():
            time.sleep(interval)
