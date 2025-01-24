from flask import Flask
from config import Config
import logging
import sys

def create_app():
    try:
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

        # Initialize config and validate environment variables
        config = Config()
        
        app = Flask(__name__)
        app.config.from_object(config)

        from app.routes import main
        app.register_blueprint(main)

        return app

    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    from app.routes import main
    app.register_blueprint(main)

    return app
