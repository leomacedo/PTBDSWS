from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class NameForm(FlaskForm):
    name = StringField(
        'Qual é o seu nome?',
        validators=[
            DataRequired(message='Informe o nome do usuário.'),
            Length(max=64, message='Use até 64 caracteres.'),
        ],
    )
    email = StringField(
        'Qual é o seu e-mail (envio de notificação do novo usuário)?',
        validators=[
            DataRequired(message='Informe seu e-mail.'),
            Email(message='Informe um endereço de e-mail válido.'),
            Length(max=254, message='Use até 254 caracteres.'),
        ],
    )
    submit = SubmitField('Cadastrar')
