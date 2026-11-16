from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    email = StringField('E-mail', filters=[lambda value: value.strip() if value else value], validators=[DataRequired(), Email(), Length(max=254)])
    username = StringField('Nome de usuário', validators=[DataRequired(), Length(min=1, max=64)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Confirme a senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Cadastrar')


class LoginForm(FlaskForm):
    email = StringField('E-mail', filters=[lambda value: value.strip() if value else value], validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Manter conectado')
    submit = SubmitField('Entrar')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Senha atual', validators=[DataRequired()])
    password = PasswordField('Nova senha', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Confirme a nova senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Alterar senha')


class ChangeEmailForm(FlaskForm):
    email = StringField('Novo e-mail', filters=[lambda value: value.strip() if value else value], validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField('Senha atual', validators=[DataRequired()])
    submit = SubmitField('Alterar e-mail')


class RequestResetForm(FlaskForm):
    email = StringField('E-mail', filters=[lambda value: value.strip() if value else value], validators=[DataRequired(), Email(), Length(max=254)])
    submit = SubmitField('Enviar link de recuperação')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova senha', validators=[DataRequired(), Length(min=8, max=128)])
    password2 = PasswordField('Confirme a nova senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Salvar nova senha')
