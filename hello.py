import os
from flask import Flask, render_template, session, redirect, url_for
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-para-formularios'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return f'<User {self.username}>'

class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    role = SelectField('Role?:', choices=[
        ('Administrator', 'Administrator'),
        ('Moderator', 'Moderator'),
        ('User', 'User')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

def criar_funcoes():
    nomes = ['Administrator', 'Moderator', 'User']
    for nome in nomes:
        if Role.query.filter_by(name=nome).first() is None:
            db.session.add(Role(name=nome))
    db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    criar_funcoes()
    form = NameForm()

    if form.validate_on_submit():
        nome = form.name.data.strip()
        user = User.query.filter_by(username=nome).first()

        if user is None:
            role = Role.query.filter_by(name=form.role.data).first()
            user = User(username=nome, role=role)
            db.session.add(user)
            db.session.commit()
            session['known'] = False
        else:
            session['known'] = True

        session['name'] = nome
        form.name.data = ''
        return redirect(url_for('index'))

    usuarios = User.query.order_by(User.id.asc()).all()
    ordem_funcoes = ['Administrator', 'Moderator', 'User']
    funcoes = []

    for nome in ordem_funcoes:
        role = Role.query.filter_by(name=nome).first()
        if role:
            funcoes.append({
                'nome': role.name,
                'usuarios': role.users.order_by(User.id.asc()).all()
            })

    total_usuarios = User.query.count()
    total_funcoes = Role.query.count()

    return render_template(
        'index.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        usuarios=usuarios,
        funcoes=funcoes,
        total_usuarios=total_usuarios,
        total_funcoes=total_funcoes
    )

if __name__ == '__main__':
    app.run(debug=True)