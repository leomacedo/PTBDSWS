from flask import Flask, request, make_response, redirect, abort

app = Flask(__name__)

# 1. Rota Principal / Home
@app.route('/')
def index():
    return '<h1>Hello World!</h1><h2>Disciplina PTBDSWS</h2>'

# 2. Rota com Parâmetro Dinâmico (Nome do Usuário)
@app.route('/user/<name>')
def user(name):
    return f'<h1>Hello, {name}!</h1>'

# 3. Rota de Contexto da Requisição (Navegador do Usuário)
@app.route('/contextorequisicao')
def contexto_requisicao():
    user_agent = request.headers.get('User-Agent')
    return f'<p>Your browser is {user_agent}</p>'

# 4. Rota com Código de Status HTTP Diferente (400 Bad Request)
@app.route('/codigostatusdiferente')
def codigo_status_diferente():
    return '<h1>Bad request</h1>', 400

# 5. Rota usando Objeto Resposta (make_response com Cookie)
@app.route('/objetoresposta')
def objeto_resposta():
    response = make_response('<h1>This document carries a cookie!</h1>')
    response.set_cookie('answer', '42')
    return response

# 6. Rota de Redirecionamento (Redireciona para o IFSP Pirituba)
@app.route('/redirecionamento')
def redirecionamento():
    return redirect('https://ptb.ifsp.edu.br/')

# 7. Rota de Abortar (Erro 404 simulado)
@app.route('/abortar')
def abortar():
    abort(404)

if __name__ == '__main__':
    app.run()