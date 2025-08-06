#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
import uvicorn
from contextlib import asynccontextmanager

from src.utils.config import get_config
from src.scheduler import NewsScheduler
from src.web.app import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

scheduler = None

@asynccontextmanager
async def lifespan(app):
    global scheduler
    try:
        config = get_config()
        scheduler = NewsScheduler(config)
        scheduler.start()
        logger.info("Daily Digest started successfully")
        yield
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        raise
    finally:
        if scheduler:
            scheduler.shutdown()
        logger.info("Daily Digest shut down")

app.router.lifespan_context = lifespan

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    if scheduler:
        scheduler.shutdown()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        config = get_config()
        web_config = config.get_web_config()
        
        host = web_config.get('host', '127.0.0.1')
        port = web_config.get('port', 8000)
        reload = web_config.get('reload', False)
        
        logger.info(f"Starting Daily Digest on {host}:{port}")
        
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()