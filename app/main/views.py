from flask import render_template, session, redirect, url_for, current_app, flash
from .. import db
from ..models import Role, User
from ..email import send_simple_message
from . import main
from .forms import NameForm
import requests


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        username = form.name.data.strip()
        user = User.query.filter_by(username=username).first()
        if user is None:
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role is None:
                admin_role = Role(name='Admin')
                db.session.add(admin_role)
            user_role = Role.query.filter_by(name='User').first()
            if user_role is None:
                user_role = Role(name='User')
                db.session.add(user_role)
            is_first_user = User.query.count() == 0
            user = User(
                username=username,
                prontuario=current_app.config['STUDENT_PRONTUARIO'],
                student_name=current_app.config['STUDENT_NAME'],
                email=form.email.data.strip(),
                role=admin_role if is_first_user else user_role,
            )
            db.session.add(user)
            db.session.commit()
            session['known'] = False
            recipients = list(dict.fromkeys([
                'flaskaulasweb@zohomail.com',
                current_app.config.get('PROFESSOR_EMAIL'),
                current_app.config.get('FLASKY_ADMIN'),
                user.email,
            ]))
            recipients = [address for address in recipients if address]
            try:
                send_simple_message(
                    recipients,
                    'Novo usuário cadastrado',
                    user.username,
                    user.email,
                    user.prontuario,
                    user.student_name,
                )
                flash('Cadastro realizado e notificações enviadas por e-mail.', 'success')
            except requests.RequestException:
                current_app.logger.exception('Falha ao enviar a notificação de novo usuário.')
                flash('Cadastro realizado, mas não foi possível enviar as notificações por e-mail.', 'warning')
        else:
            session['known'] = True
            flash('Este usuário já está cadastrado.', 'warning')
        session['name'] = form.name.data
        return redirect(url_for('.index'))
    users = User.query.order_by(User.id).all()
    return render_template('index.html',
                           form=form, name=session.get('name'),
                           known=session.get('known', False), users=users)
