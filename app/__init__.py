from flask import Flask
from config import Config
import logging
import sys

def create_app():
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )
    logger = logging.getLogger(__name__)
    logger.debug("Starting application initialization")

    # Initialize config and validate environment variables first
    config = Config()
    try:
        config.validate_config()  # Explicitly validate before creating app
    except EnvironmentError as e:
        logger.error(f"Missing required environment variables: {str(e)}")
        # Exit immediately without returning app object
        sys.exit(1)
        
    try:
        app = Flask(__name__)
        app.config.from_object(config)

        from app.routes import main
        app.register_blueprint(main)

        return app

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        sys.exit(1)
