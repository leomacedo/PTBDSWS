import re
import unittest
from html import unescape
from unittest.mock import patch

from app import create_app, db
from app.models import Role, User


class UserManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.admin_role = Role(name='Admin')
        self.user_role = Role(name='User')
        db.session.add_all([self.admin_role, self.user_role])
        db.session.flush()
        self.admin = User(username='admin', role=self.admin_role)
        self.user = User(username='usuario', role=self.user_role)
        db.session.add_all([self.admin, self.user])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def csrf_token(self, field_name):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        match = re.search(
            rf'name="{re.escape(field_name)}"[^>]*value="([^"]+)"',
            response.get_data(as_text=True),
        )
        self.assertIsNotNone(match, f'Campo CSRF {field_name} não foi renderizado')
        return match.group(1)

    def test_editar_usuario_persiste_sem_alterar_funcao_ou_enviar_email(self):
        csrf = self.csrf_token(f'edit-{self.user.id}-csrf_token')
        with patch('app.main.views.send_simple_message') as send_email:
            response = self.client.post(
                f'/usuarios/{self.user.id}/editar',
                data={f'edit-{self.user.id}-csrf_token': csrf,
                      f'edit-{self.user.id}-username': 'nome_atualizado'},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Nome do usuário atualizado com sucesso.'.encode(), response.data)
        send_email.assert_not_called()
        db.session.expire_all()
        self.assertEqual(db.session.get(User, self.user.id).username, 'nome_atualizado')
        self.assertEqual(db.session.get(User, self.user.id).role.name, 'User')
        self.assertEqual(db.session.get(User, self.admin.id).role.name, 'Admin')
        self.assertIn(b'nome_atualizado', self.client.get('/').data)

    def test_edicao_vazia_ou_duplicada_nao_altera_usuario(self):
        for username in ('', self.admin.username):
            with self.subTest(username=username):
                csrf = self.csrf_token(f'edit-{self.user.id}-csrf_token')
                response = self.client.post(
                    f'/usuarios/{self.user.id}/editar',
                    data={f'edit-{self.user.id}-csrf_token': csrf,
                          f'edit-{self.user.id}-username': username},
                    follow_redirects=True,
                )
                self.assertEqual(response.status_code, 200)
                page_text = unescape(response.get_data(as_text=True))
                if username == '':
                    self.assertIn('Informe o nome do usuário.', page_text)
                else:
                    self.assertIn('Já existe outro usuário cadastrado com esse nome.', page_text)
                db.session.expire_all()
                self.assertEqual(db.session.get(User, self.user.id).username, 'usuario')

    def test_edicao_com_nome_maior_que_64_caracteres_e_rejeitada(self):
        csrf = self.csrf_token(f'edit-{self.user.id}-csrf_token')
        response = self.client.post(
            f'/usuarios/{self.user.id}/editar',
            data={f'edit-{self.user.id}-csrf_token': csrf,
                  f'edit-{self.user.id}-username': 'x' * 65},
            follow_redirects=True,
        )
        self.assertIn('Use até 64 caracteres.'.encode(), response.data)
        db.session.expire_all()
        self.assertEqual(db.session.get(User, self.user.id).username, 'usuario')

    def test_excluir_usuario_remove_apenas_o_registro_e_nao_envia_email(self):
        user_id = self.user.id
        csrf = self.csrf_token(f'delete-{user_id}-csrf_token')
        with patch('app.main.views.send_simple_message') as send_email:
            response = self.client.post(
                f'/usuarios/{user_id}/excluir',
                data={f'delete-{user_id}-csrf_token': csrf},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Usuário "usuario" excluído com sucesso.',
                      unescape(response.get_data(as_text=True)))
        send_email.assert_not_called()
        self.assertIsNone(db.session.get(User, user_id))
        self.assertIsNotNone(db.session.get(User, self.admin.id))
        self.assertEqual(Role.query.count(), 2)

    def test_exclusao_nao_aceita_get_e_formulario_tem_csrf(self):
        response = self.client.get(f'/usuarios/{self.user.id}/excluir')
        self.assertEqual(response.status_code, 405)
        page = self.client.get('/').get_data(as_text=True)
        self.assertIn(f'name="delete-{self.user.id}-csrf_token"', page)
        self.assertIsNotNone(db.session.get(User, self.user.id))

    def test_cancelar_sem_enviar_post_nao_altera_o_banco(self):
        # Cancelar na interface fecha a edição/confirmacao sem submeter um POST.
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'cancelarEdicao(this)', response.data)
        self.assertIn(b'window.confirm' if b'window.confirm' in response.data else b'confirm(', response.data)
        db.session.expire_all()
        self.assertEqual(User.query.count(), 2)
        self.assertEqual(db.session.get(User, self.user.id).username, 'usuario')

    def test_cadastro_novo_usuario_continua_ativo_com_papel_e_email(self):
        response = self.client.get('/')
        match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        with patch('app.main.views.send_simple_message') as send_email:
            result = self.client.post(
                '/',
                data={'csrf_token': match.group(1).decode(),
                      'name': 'novo_usuario', 'email': 'novo@example.com'},
                follow_redirects=True,
            )

        self.assertEqual(result.status_code, 200)
        new_user = User.query.filter_by(username='novo_usuario').one()
        self.assertEqual(new_user.role.name, 'User')
        send_email.assert_called_once()
        self.assertIn('novo@example.com', send_email.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
