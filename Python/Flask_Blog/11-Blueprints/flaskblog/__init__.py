from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flaskblog.config import Config


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from flaskblog.users.routes import users
    from flaskblog.posts.routes import posts
    from flaskblog.main.routes import main
    app.register_blueprint(users)
    app.register_blueprint(posts)
    app.register_blueprint(main)

    @app.after_request
    def add_security_headers(response):
        # Fixes: Content Security Policy (CSP) Header Not Set
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://code.jquery.com https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net https://stackpath.bootstrapcdn.com;"
        )

        # Fixes common Low/Medium risks:
        response.headers['X-Content-Type-Options'] = 'nosniff' 
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'     
        response.headers['X-XSS-Protection'] = '1; mode=block' 
        
        return response # <--- Don't forget this!

    return app
