from flask import Flask
from config import Config
from flask_sock import Sock
import logging
import sys
import warnings

# Filter out specific cryptography deprecation warnings
warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning, 
                       message='.*TripleDES.*')

sock = Sock()

def create_app():
    # Initialize config and validate environment variables first
    config = Config()
    
    # Configure logging
    log_level = logging.DEBUG if config.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )
    logger = logging.getLogger(__name__)
    logger.debug("Starting application initialization")
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
        sock.init_app(app)

        return app

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        sys.exit(1)
