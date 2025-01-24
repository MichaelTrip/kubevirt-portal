from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"Starting Flask application in {'debug' if debug else 'production'} mode...")
    app.run(debug=debug, host='0.0.0.0', port=5000, use_reloader=debug)
