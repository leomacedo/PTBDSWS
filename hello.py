
import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

# Configurações
basedir = os.path.abspath(os.path.dirname(__file__))
os.chdir(basedir)
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-para-formularios')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['API_URL'] = os.environ.get('API_URL')
app.config['API_KEY'] = os.environ.get('API_KEY')
app.config['API_FROM'] = os.environ.get('API_FROM')
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modelos do banco
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

# Formulário
class NameForm(FlaskForm):
    name = StringField('Qual o seu nome?', validators=[DataRequired()])
    submit = SubmitField('Enviar')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

# Envio de e-mail pelo Mailgun
def enviar_email(usuario):
    url = app.config['API_URL']
    chave = app.config['API_KEY']
    remetente = app.config['API_FROM']
    admin = app.config['FLASKY_ADMIN']

    if not all([url, chave, remetente, admin]):
        raise RuntimeError('Configuração do Mailgun incompleta no .env')

    # aguardando confirmação do email do professor
    destinatarios = [admin, 'flaskaulasweb@zohomail.com']

    mensagem = (
        'Novo usuário cadastrado no Flasky.\n\n'
        'Prontuário: PT3035867\n'
        'Nome do aluno: Leonardo Macedo Aurieni\n'
        f'Usuário cadastrado: {usuario.username}'
    )

    resposta = requests.post(
        url,
        auth=('api', chave),
        data={'from': remetente, 'to': destinatarios, 'subject': '[Flasky] Novo usuário cadastrado', 'text': mensagem},
        timeout=15
    )
    if not resposta.ok:
        app.logger.error('Mailgun HTTP %s: %s', resposta.status_code, resposta.text)
        resposta.raise_for_status()
    return resposta.json()

# Cadastro de usuários
@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()

    if form.validate_on_submit():
        nome = form.name.data.strip()
        user = User.query.filter_by(username=nome).first()

        if user is None and nome:
            user = User(username=nome)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            try:
                enviar_email(user)
                flash('Novo usuário cadastrado! E-mail aceito pelo Mailgun.', 'success')
            except (requests.RequestException, RuntimeError, ValueError):
                app.logger.exception('Falha ao enviar e-mail de novo usuário')
                flash('Usuário cadastrado, mas não foi possível confirmar o envio do e-mail.', 'warning')

        elif user is not None:
            session['known'] = True

        else:
            flash('Digite um nome válido.', 'warning')
            return redirect(url_for('index'))

        session['name'] = nome
        return redirect(url_for('index'))

    return render_template('index.html', form=form, name=session.get('name'), known=session.get('known', False))

if __name__ == '__main__':
    app.run(debug=True)
