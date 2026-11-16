from markupsafe import Markup
from flask import (current_app, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .. import db
from ..email import send_password_reset_email
from ..models import User
from . import main
from .forms import (ChangeEmailForm, ChangePasswordForm, LoginForm,
                    RegistrationForm, RequestResetForm, ResetPasswordForm)


@main.route('/')
def index():
    users = []
    if current_user.is_authenticated and current_user.confirmed:
        users = User.query.order_by(User.id).all()
    return render_template('index.html', users=users)


@main.route('/cadastro', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        username = form.username.data.strip()
        if User.query.filter(func.lower(User.email) == email).first():
            flash('Este e-mail já está cadastrado.', 'warning')
        elif User.query.filter_by(username=username).first():
            flash('Este nome de usuário já está cadastrado.', 'warning')
        else:
            user = User(email=email, username=username)
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('Este e-mail ou nome de usuário já está cadastrado.', 'warning')
            else:
                message = Markup('Cadastro realizado! <a href="{}">Clique aqui</a> para confirmar seu e-mail').format(
                    url_for('.confirm_email', token=user.generate_confirmation_token()))
                flash(message, 'warning')
                return redirect(url_for('.login'))
    return render_template('register.html', form=form)


@main.route('/confirmar/<token>')
def confirm_email(token):
    user = User.confirm_token(token)
    if user is None:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
    else:
        flash('E-mail confirmado com sucesso.', 'success')
    return redirect(url_for('.login'))


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('.index'))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        if user is not None and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/') or next_page.startswith('//'):
                next_page = url_for('.index')
            return redirect(next_page)
        flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)


@main.route('/sair')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'warning')
    return redirect(url_for('.index'))


@main.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('A senha atual está incorreta.', 'danger')
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash('Senha alterada com sucesso.', 'success')
            return redirect(url_for('.index'))
    return render_template('change_password.html', form=form)


@main.route('/alterar-email', methods=['GET', 'POST'])
@login_required
def change_email():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if not current_user.check_password(form.password.data):
            flash('A senha atual está incorreta.', 'danger')
        elif User.query.filter(func.lower(User.email) == email, User.id != current_user.id).first():
            flash('Este e-mail já está em uso.', 'warning')
        else:
            current_user.email = email
            current_user.confirmed = False
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('Este e-mail já está em uso.', 'warning')
            else:
                message = Markup('E-mail alterado! <a href="{}">Clique aqui</a> para confirmar o novo endereço.').format(
                    url_for('.confirm_email', token=current_user.generate_confirmation_token()))
                flash(message, 'warning')
                return redirect(url_for('.index'))
    return render_template('change_email.html', form=form)


@main.route('/recuperar-senha', methods=['GET', 'POST'])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for('.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter(func.lower(User.email) == form.email.data.strip().lower()).first()
        if user:
            try:
                send_password_reset_email(user)
            except Exception:
                current_app.logger.exception('Falha ao enviar link de recuperação de senha.')
                flash('Não foi possível enviar o e-mail agora. Tente novamente mais tarde.', 'danger')
                return render_template('request_reset.html', form=form)
        flash('Se o endereço estiver cadastrado, você receberá um link para redefinir sua senha.', 'info')
        return redirect(url_for('.login'))
    return render_template('request_reset.html', form=form)


@main.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.reset_password(token, form.password.data)
        if user is None:
            flash('O link de recuperação é inválido ou expirou.', 'danger')
            return redirect(url_for('.request_password_reset'))
        flash('Sua senha foi redefinida. Faça login com a nova senha.', 'success')
        return redirect(url_for('.login'))
    return render_template('reset_password.html', form=form)
