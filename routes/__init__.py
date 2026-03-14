from routes.auth import auth_bp
from routes.story import story_bp
from routes.friends import friends_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(story_bp)
    app.register_blueprint(friends_bp)
