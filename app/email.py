from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

import requests

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_simple_message(recipients, subject, username, email, prontuario, student_name):
    app = current_app._get_current_object()
    text = (
        'Novo usuário cadastrado.\n\n'
        f'Prontuário: {prontuario}\n'
        f'Nome do aluno: {student_name}\n'
        f'Novo usuário cadastrado: {username}\n'
        f'E-mail informado: {email}\n'
    )
    response = requests.post(
        app.config['API_URL'],
        auth=('api', app.config['API_KEY']),
        data={
            'from': app.config['API_FROM'],
            'to': recipients,
            'subject': f"{app.config['FLASKY_MAIL_SUBJECT_PREFIX']} {subject}",
            'text': text,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response
