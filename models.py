import json
from datetime import datetime, date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stories = db.relationship('DailyStory', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class DailyStory(db.Model):
    __tablename__ = 'daily_stories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    opening_text = db.Column(db.Text, default='')
    ending_text = db.Column(db.Text, default='')
    health = db.Column(db.Integer, default=100)
    sanity = db.Column(db.Integer, default=100)
    strength = db.Column(db.Integer, default=100)
    equipment_summary = db.Column(db.Text, default='[]')
    potion_summary = db.Column(db.Text, default='[]')
    boss_name = db.Column(db.String(100), default='')
    boss_health = db.Column(db.Integer, default=100)
    boss_sanity = db.Column(db.Integer, default=100)
    boss_strength = db.Column(db.Integer, default=100)
    current_phase = db.Column(db.Integer, default=0)
    is_complete = db.Column(db.Boolean, default=False)
    victory = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    meals = db.relationship('MealEntry', backref='story', lazy='dynamic',
                            order_by='MealEntry.created_at')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_user_date'),
    )

    def get_equipment_list(self):
        try:
            return json.loads(self.equipment_summary)
        except (json.JSONDecodeError, TypeError):
            return []

    def add_equipment(self, item):
        items = self.get_equipment_list()
        if item:
            items.append(item)
        self.equipment_summary = json.dumps(items, ensure_ascii=False)

    def get_potion_list(self):
        try:
            return json.loads(self.potion_summary)
        except (json.JSONDecodeError, TypeError):
            return []


class MealEntry(db.Model):
    __tablename__ = 'meal_entries'

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey('daily_stories.id'), nullable=False)
    meal_type = db.Column(db.String(10), nullable=False)
    food_input = db.Column(db.Text, nullable=False)
    story_text = db.Column(db.Text, default='')
    health_change = db.Column(db.Integer, default=0)
    sanity_change = db.Column(db.Integer, default=0)
    strength_change = db.Column(db.Integer, default=0)
    equipment_gained = db.Column(db.String(200), default='')
    potion_gained = db.Column(db.String(200), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Friendship(db.Model):
    __tablename__ = 'friendships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref='sent_requests')
    friend = db.relationship('User', foreign_keys=[friend_id], backref='received_requests')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='uq_user_friend'),
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
