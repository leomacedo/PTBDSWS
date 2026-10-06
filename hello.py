import os
import requests
from datetime import datetime
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

class EmailEnviado(db.Model):
    __tablename__ = 'emails_enviados'
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(64), nullable=False)
    destinatarios = db.Column(db.String(255), nullable=False)
    assunto = db.Column(db.String(255), nullable=False)
    texto = db.Column(db.Text, nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<EmailEnviado {self.usuario}>'

# Formulário
class NameForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    enviar_professor = BooleanField('Deseja enviar e-mail também para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Enviar')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, EmailEnviado=EmailEnviado)

# Funções
def obter_funcao(nome):
    funcao = Role.query.filter_by(name=nome).first()

    if funcao is None:
        funcao = Role(name=nome)
        db.session.add(funcao)
        db.session.flush()

    return funcao

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

    assunto = '[Flask] Novo usuário'
    texto = f'Novo usuário cadastrado: {usuario.username}'

    resposta = requests.post(
        url,
        auth=('api', chave),
        data={'from': remetente, 'to': destinatarios, 'subject': assunto, 'text': texto},
        timeout=15
    )

    if not resposta.ok:
        app.logger.error('Mailgun HTTP %s: %s', resposta.status_code, resposta.text)
        resposta.raise_for_status()

    email = EmailEnviado(
        usuario=usuario.username,
        destinatarios=', '.join(destinatarios),
        assunto=assunto,
        texto=texto,
        data_hora=datetime.now()
    )

    db.session.add(email)
    db.session.commit()

    return resposta.json()

# Home
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

# Relação de e-mails enviados
@app.route('/emails')
def emails():
    emails_enviados = EmailEnviado.query.order_by(EmailEnviado.id.desc()).all()
    return render_template('emails.html', emails=emails_enviados)

if __name__ == '__main__':
    app.run(debug=True)