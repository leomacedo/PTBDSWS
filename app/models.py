from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    prontuario = db.Column(db.String(32))
    student_name = db.Column(db.String(128))
    email = db.Column(db.String(254), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'confirm': self.id, 'email': self.email}, salt='email-confirm')

    @staticmethod
    def confirm_token(token, max_age=None):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(
                token, salt='email-confirm',
                max_age=max_age or current_app.config.get('EMAIL_CONFIRM_MAX_AGE', 86400))
        except (BadSignature, SignatureExpired, KeyError, TypeError):
            return None
        user = db.session.get(User, data.get('confirm'))
        if user is None or data.get('email') != user.email:
            return None
        user.confirmed = True
        db.session.commit()
        return user

    def generate_reset_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps({'reset': self.id, 'email': self.email}, salt='password-reset')

    @staticmethod
    def reset_password(token, password, max_age=None):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(
                token, salt='password-reset',
                max_age=max_age or current_app.config.get('PASSWORD_RESET_MAX_AGE', 3600))
        except (BadSignature, SignatureExpired, KeyError, TypeError):
            return None
        user = db.session.get(User, data.get('reset'))
        if user is None or data.get('email') != user.email:
            return None
        user.set_password(password)
        db.session.commit()
        return user


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
