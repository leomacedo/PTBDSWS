import unittest
from unittest.mock import patch

from app import create_app, db
from app.models import User
from app.email import send_password_reset_email


class AuthenticationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False,
                               SERVER_NAME='aula090.example',
                               API_URL='https://mail.example/messages',
                               API_KEY='test-key', API_FROM='test@example.com')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_user(self, email='pessoa@example.com', username='pessoa', confirmed=False):
        user = User(email=email, username=username, confirmed=confirmed)
        user.set_password('senha-correta-123')
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, email='pessoa@example.com', password='senha-correta-123'):
        return self.client.post('/login', data={'email': email, 'password': password},
                                follow_redirects=True)

    def test_cadastro_guarda_hash_e_oferece_confirmacao_direta(self):
        response = self.client.post('/cadastro', data={
            'email': ' NOVA@example.com ', 'username': 'nova',
            'password': 'senha-nova-123', 'password2': 'senha-nova-123',
        }, follow_redirects=True)
        user = User.query.filter_by(username='nova').one()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Cadastro realizado!', response.get_data(as_text=True))
        self.assertIn('Clique aqui', response.get_data(as_text=True))
        self.assertEqual(user.email, 'nova@example.com')
        self.assertTrue(user.password_hash != 'senha-nova-123')
        self.assertTrue(user.check_password('senha-nova-123'))
        self.assertFalse(user.confirmed)

    def test_login_email_persistencia_e_acesso_condicional_a_relacao(self):
        user = self.create_user(confirmed=False)
        logged_out = self.client.get('/')
        self.assertIn('Olá, Desconhecido!', logged_out.get_data(as_text=True))
        self.assertNotIn('Relação de usuários cadastrados', logged_out.get_data(as_text=True))
        response = self.login()
        self.assertIn('Olá, pessoa!', response.get_data(as_text=True))
        self.assertNotIn('Relação de usuários cadastrados', response.get_data(as_text=True))
        self.assertIn('Seu e-mail ainda não foi confirmado.', response.get_data(as_text=True))
        self.assertIn('Você não pode ver a relação de usuários por conta disso.', response.get_data(as_text=True))
        self.client.get(f'/confirmar/{user.generate_confirmation_token()}')
        confirmed_page = self.client.get('/').get_data(as_text=True)
        self.assertIn('Relação de usuários cadastrados', confirmed_page)
        self.assertIn('pessoa@example.com', confirmed_page)
        self.assertIn('Sim', confirmed_page)

    def test_login_recusa_senha_incorreta(self):
        self.create_user()
        response = self.login(password='incorreta')
        self.assertIn('E-mail ou senha inválidos.', response.get_data(as_text=True))
        self.assertIn('Entrar', response.get_data(as_text=True))

    def test_login_exibe_manter_conectado(self):
        page = self.client.get('/login').get_data(as_text=True)
        self.assertIn('Manter conectado', page)
        self.assertIn('name="remember_me"', page)

    def test_alterar_senha_valida_atualiza_hash(self):
        user = self.create_user(confirmed=True)
        self.login()
        response = self.client.post('/alterar-senha', data={
            'old_password': 'senha-correta-123', 'password': 'senha-nova-456',
            'password2': 'senha-nova-456',
        }, follow_redirects=True)
        db.session.refresh(user)
        self.assertIn('Senha alterada com sucesso.', response.get_data(as_text=True))
        self.assertTrue(user.check_password('senha-nova-456'))

    def test_alterar_email_exige_senha_e_remove_confirmacao(self):
        user = self.create_user(confirmed=True)
        stale_confirmation = user.generate_confirmation_token()
        self.login()
        response = self.client.post('/alterar-email', data={
            'email': 'novo@example.com', 'password': 'senha-correta-123',
        }, follow_redirects=True)
        db.session.refresh(user)
        self.assertIn('confirmar o novo endereço', response.get_data(as_text=True))
        self.assertEqual(user.email, 'novo@example.com')
        self.assertFalse(user.confirmed)
        self.assertIsNone(User.confirm_token(stale_confirmation))
        self.assertIsNotNone(User.confirm_token(user.generate_confirmation_token()))

    def test_recuperacao_envia_email_com_token_e_redefine_senha(self):
        user = self.create_user()
        with patch('app.main.views.send_password_reset_email') as send_email:
            response = self.client.post('/recuperar-senha', data={'email': user.email},
                                        follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        send_email.assert_called_once_with(user)
        with patch('app.main.views.send_password_reset_email') as send_email:
            self.client.post('/recuperar-senha', data={'email': 'naoexiste@example.com'})
        send_email.assert_not_called()
        token = user.generate_reset_token()
        response = self.client.post(f'/redefinir-senha/{token}', data={
            'password': 'senha-recuperada-789', 'password2': 'senha-recuperada-789',
        }, follow_redirects=True)
        db.session.refresh(user)
        self.assertTrue(user.check_password('senha-recuperada-789'))
        self.assertIn('Sua senha foi redefinida.', response.get_data(as_text=True))

    def test_email_de_recuperacao_usa_mailgun_e_link_com_token(self):
        user = self.create_user()
        with patch('app.email.requests.post') as post:
            post.return_value.raise_for_status.return_value = None
            send_password_reset_email(user)
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://mail.example/messages')
        self.assertEqual(kwargs['auth'], ('api', 'test-key'))
        self.assertEqual(kwargs['data']['to'], [user.email])
        self.assertIn('/redefinir-senha/', kwargs['data']['text'])

    def test_menu_conta_tem_opcoes_e_sair_desloga(self):
        self.create_user(confirmed=True)
        page = self.login().get_data(as_text=True)
        self.assertIn('Alterar senha', page)
        self.assertIn('Alterar e-mail', page)
        self.assertIn('Sair', page)
        response = self.client.get('/sair', follow_redirects=True)
        self.assertIn('Olá, Desconhecido!', response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
