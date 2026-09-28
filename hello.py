
import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_wtf import FlaskForm
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from wtforms import StringField, BooleanField, SubmitField
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
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    enviar_professor = BooleanField('Deseja enviar e-mail também para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Enviar')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)

# Cadastro das funções
def obter_funcao(nome):
    funcao = Role.query.filter_by(name=nome).first()

    if funcao is None:
        funcao = Role(name=nome)
        db.session.add(funcao)
        db.session.flush()

    return funcao

# Envio de e-mail pelo Mailgun
def enviar_email(usuario, enviar_professor=False):
    url = app.config['API_URL']
    chave = app.config['API_KEY']
    remetente = app.config['API_FROM']
    admin = app.config['FLASKY_ADMIN']

    if not all([url, chave, remetente, admin]):
        raise RuntimeError('Configuração do Mailgun incompleta no .env')

    destinatarios = [admin]

    if enviar_professor:
        destinatarios.append('flaskaulasweb@zohomail.com')

    mensagem = (
        'Novo usuário cadastrado no Flask.\n\n'
        'Prontuário: PT3035867\n'
        'Nome do aluno: Leonardo Macedo Aurieni\n'
        f'Usuário cadastrado: {usuario.username}\n'
        f'Função: {usuario.role.name}'
    )

    resposta = requests.post(
        url,
        auth=('api', chave),
        data={'from': remetente, 'to': destinatarios, 'subject': '[Flask] Novo usuário cadastrado', 'text': mensagem},
        timeout=15
    )

    if not resposta.ok:
        app.logger.error('Mailgun HTTP %s: %s', resposta.status_code, resposta.text)
        resposta.raise_for_status()

    return resposta.json()

# Página principal
@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()

    if form.validate_on_submit():
        nome = form.name.data.strip()

        if not nome:
            flash('Digite um nome válido.', 'warning')
            return redirect(url_for('index'))

        usuario = User.query.filter_by(username=nome).first()
        session['name'] = nome

        if usuario is None:
            nome_funcao = 'Administrador' if User.query.count() == 0 else 'Usuário'
            funcao = obter_funcao(nome_funcao)

            usuario = User(username=nome, role=funcao)
            db.session.add(usuario)
            db.session.commit()

            session['known'] = False

            try:
                enviar_email(usuario, form.enviar_professor.data)
                session['email_enviado'] = True
                flash('Novo usuário cadastrado! E-mail aceito pelo Mailgun.', 'success')
            except (requests.RequestException, RuntimeError, ValueError):
                session['email_enviado'] = False
                app.logger.exception('Falha ao enviar e-mail de novo usuário')
                flash('Usuário cadastrado, mas não foi possível confirmar o envio do e-mail.', 'warning')
        else:
            session['known'] = True
            session['email_enviado'] = False

        return redirect(url_for('index'))

    usuarios = User.query.order_by(User.id.asc()).all()

    return render_template(
        'index.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        email_enviado=session.pop('email_enviado', False),
        usuarios=usuarios
    )

if __name__ == '__main__':
    app.run(debug=True)
