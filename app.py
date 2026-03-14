from flask import Flask, redirect, url_for
from flask_login import current_user

from config import Config
from extensions import db, login_manager
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    register_blueprints(app)

    with app.app_context():
        import models  # noqa: F401 - ensure models are registered
        db.create_all()

        # Add missing columns to existing tables (SQLite doesn't support IF NOT EXISTS for columns)
        with db.engine.connect() as conn:
            for table, col, col_type, default in [
                ('daily_stories', 'potion_summary', 'TEXT', "'[]'"),
                ('meal_entries', 'potion_gained', 'VARCHAR(200)', "''"),
                ('daily_stories', 'boss_name', 'VARCHAR(100)', "''"),
                ('daily_stories', 'boss_health', 'INTEGER', "100"),
                ('daily_stories', 'boss_sanity', 'INTEGER', "100"),
                ('daily_stories', 'boss_strength', 'INTEGER', "100"),
                ('users', 'score', 'INTEGER', "0"),
                ('daily_stories', 'victory', 'BOOLEAN', "NULL"),
                ('meal_entries', 'carbs', 'REAL', "NULL"),
                ('meal_entries', 'fat', 'REAL', "NULL"),
                ('meal_entries', 'protein', 'REAL', "NULL"),
            ]:
                try:
                    conn.execute(db.text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default}"
                    ))
                    conn.commit()
                except Exception:
                    pass  # Column already exists

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('story.today'))
        return redirect(url_for('auth.login'))

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=7860)
