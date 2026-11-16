# Avaliação contínua: Aula 090

Aplicação Flask modular com cadastro e login por e-mail, senhas com hash,
confirmação de conta e recuperação de senha por link temporário enviado pelo
Mailgun.

## Executar localmente

Ative o ambiente virtual, instale as dependências e aplique as migrations:

```powershell
venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FLASK_APP = "flasky.py"
flask db upgrade
flask run
```

As configurações locais ficam no `.env` (não versionado). Para recuperação de
senha, configure `API_URL`, `API_KEY`, `API_FROM` do Mailgun e `SECRET_KEY`.

## Atualizar no PythonAnywhere

Faça pull do código no diretório do projeto e, no console Bash do PythonAnywhere,
ative o ambiente virtual usado pela aplicação. Em seguida execute:

```bash
cd ~/PTBDSWS
source ~/PTBDSWS/venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=flasky.py
flask db upgrade
```

Configure no `.env` ou nas variáveis de ambiente do web app a `SECRET_KEY`, as
credenciais do Mailgun e `DATABASE_URL` apontando para o banco já utilizado pelo
site. Por fim, recarregue o web app pelo painel do PythonAnywhere. A migration
adiciona o hash e o estado de confirmação preservando as linhas existentes; as
senhas antigas não são reaproveitadas e usuários legados precisam usar a
recuperação de senha. Não execute `db.drop_all`, `flask db downgrade` ou apague
o banco remoto.

Para aplicar alterações futuras no schema, envie as migrations versionadas e
execute novamente `flask db upgrade` no console do PythonAnywhere.
