from datetime import datetime
from flask import Flask, render_template, request
from flask_moment import Moment

app = Flask(__name__)
moment = Moment(app)

@app.route('/')
def index():
    return render_template('index.html', current_time=datetime.utcnow())

@app.route('/identificacao/<nome>/<prontuario>/<instituicao>')
def identificacao(nome, prontuario, instituicao):
    return render_template('identificacao.html', nome=nome, prontuario=prontuario, instituicao=instituicao)

@app.route('/contextorequisicao')
def contexto_requisicao():
    nome = "Leonardo Macêdo Aurieni"
    user_agent = request.user_agent.string
    
    # Pega o IP correto sem quebrar no PythonAnywhere
    ip_remoto = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_remoto and ',' in ip_remoto:
        ip_remoto = ip_remoto.split(',')[0]
        
    host = request.host
    return render_template('contexto.html', nome=nome, user_agent=user_agent, ip_remoto=ip_remoto, host=host)

if __name__ == '__main__':
    app.run()