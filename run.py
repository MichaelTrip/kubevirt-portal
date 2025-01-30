from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    from config import Config
    config = Config()
    print(f"Starting Flask application in {'debug' if config.DEBUG else 'production'} mode...")
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000, use_reloader=config.DEBUG)
