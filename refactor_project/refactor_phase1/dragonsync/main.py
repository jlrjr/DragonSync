"""
DragonSync main entry point.

This module provides the CLI interface and application startup.
"""

import asyncio
import argparse
import signal
import sys
from pathlib import Path

from dragonsync.config.loader import ConfigLoader
from dragonsync.config.validator import ConfigValidator
from dragonsync.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="DragonSync - Drone Detection Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -c config.ini
  %(prog)s -c /etc/dragonsync/config.ini --log-level DEBUG
  
For more information: https://github.com/jlrjr/DragonSync
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config.ini",
        help="Path to configuration file (default: config.ini)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Override log level from config file"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="DragonSync 2.0.0"
    )
    
    return parser.parse_args()


async def run_application(config_path: str, log_level: str = None) -> None:
    """
    Run the DragonSync application.
    
    Args:
        config_path: Path to configuration file
        log_level: Optional log level override
    """
    # Load configuration
    logger.info(f"Loading configuration from {config_path}")
    try:
        config = ConfigLoader.from_ini(config_path)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        logger.info("Create config.ini from config.ini.example")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Validate configuration
    errors = ConfigValidator.validate(config)
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info("Configuration loaded and validated successfully")
    
    # TODO: Initialize and start orchestrator
    # This will be implemented in Phase 5
    logger.info("DragonSync initialized (Phase 1 - Core models only)")
    logger.info("Full orchestration coming in Phase 5")
    
    # For now, just demonstrate the config is working
    logger.info(f"ZMQ listening on {config.zmq.host}:{config.zmq.drone_port}")
    if config.tak_multicast.enabled:
        logger.info(f"TAK multicast enabled: {config.tak_multicast.address}:{config.tak_multicast.port}")
    if config.mqtt.enabled:
        logger.info(f"MQTT enabled: {config.mqtt.host}:{config.mqtt.port}")
    if config.adsb.enabled:
        logger.info(f"ADS-B enabled: {config.adsb.json_url}")
    
    # Keep running until interrupted
    logger.info("Press Ctrl+C to stop")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


def main() -> None:
    """Main entry point"""
    args = parse_args()
    
    # Setup logging
    log_level = args.log_level or "INFO"
    setup_logging(log_level)
    
    logger.info("=" * 60)
    logger.info("DragonSync 2.0 - Drone Detection Gateway")
    logger.info("=" * 60)
    
    # Run the application
    try:
        asyncio.run(run_application(args.config, args.log_level))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
