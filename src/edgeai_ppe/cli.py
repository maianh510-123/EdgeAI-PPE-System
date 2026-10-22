import argparse
import logging
from edgeai_ppe.config import load_config
from edgeai_ppe.detection.detector import DemoDetector
from edgeai_ppe.communication.interface import ConsoleClient
from edgeai_ppe.pipeline.ppe_pipeline import PPEPipeline
from edgeai_ppe.utils.logger import configure_logging

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic PPE demo; no AI inference or network")
    parser.add_argument("--config", help="Path to JSON-compatible YAML config (optional)")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    configure_logging(config.log_level)
    logging.info("DEMO: synthetic detections, console output only")
    summary = PPEPipeline(config, DemoDetector(), ConsoleClient(), is_demo=True).run_once()
    logging.info("Accepted=%d sent=%d failed=%d", summary.accepted, summary.sent, summary.failed)
    return 1 if summary.failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
