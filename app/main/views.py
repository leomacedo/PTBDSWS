from flask import render_template, session, redirect, url_for, current_app, flash
from sqlalchemy.exc import IntegrityError
from .. import db
from ..models import Role, User
from ..email import send_simple_message
from . import main
from .forms import DeleteUserForm, EditUserForm, NameForm
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
                           known=session.get('known', False), users=users,
                           edit_forms={user.id: EditUserForm(prefix=f'edit-{user.id}') for user in users},
                           delete_forms={user.id: DeleteUserForm(prefix=f'delete-{user.id}') for user in users})


@main.route('/usuarios/<int:user_id>/editar', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = EditUserForm(prefix=f'edit-{user.id}')
    if not form.validate_on_submit():
        message = next(iter(form.username.errors), 'Não foi possível validar o nome do usuário.')
        flash(message, 'danger')
        return redirect(url_for('.index'))

    username = form.username.data.strip()
    if not username:
        flash('O nome do usuário não pode ficar vazio.', 'danger')
        return redirect(url_for('.index'))
    if len(username) > 64:
        flash('O nome do usuário deve ter no máximo 64 caracteres.', 'danger')
        return redirect(url_for('.index'))
    duplicate = User.query.filter(User.username == username, User.id != user.id).first()
    if duplicate:
        flash('Já existe outro usuário cadastrado com esse nome.', 'warning')
        return redirect(url_for('.index'))

    user.username = username
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Já existe outro usuário cadastrado com esse nome.', 'warning')
        return redirect(url_for('.index'))

    flash('Nome do usuário atualizado com sucesso.', 'success')
    return redirect(url_for('.index'))


@main.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    form = DeleteUserForm(prefix=f'delete-{user.id}')
    if not form.validate_on_submit():
        flash('Não foi possível validar a solicitação. Atualize a página e tente novamente.', 'danger')
        return redirect(url_for('.index'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário "{username}" excluído com sucesso.', 'success')
    return redirect(url_for('.index'))
