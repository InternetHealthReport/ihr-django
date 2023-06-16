from .test_setup import TestSetUp
from ihr.const import ConfirmationEmail, ChangePasswordEmail, StrErrors, Msg, POOL, std_response
import redis
conn = redis.Redis(connection_pool=POOL)
from rest_framework.authtoken.models import Token
 

class TestViews(TestSetUp):

    def test_usersendemail(self):
        res=self.client.post(self.sendemail_url, self.email_data, format="json")
        code = conn.get(f"Confirmation_{self.email_data['email']}")
        self.assertEqual(res.status_code,200)
        self.assertIsNotNone(code)
        self.assertEqual(res.json()["msg"], Msg.CODE_SENT)

    def test_user_cannot_register_with_invalid_data(self):
        res=self.client.post(self.register_url)
        self.assertEqual(res.status_code,400)
       
    def test_user_can_register(self):
        res=self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(res.status_code,201)
        self.assertEqual(res.json()["msg"], Msg.REGISTER_SUCCEEDED)

    def test_user_cannot_register_with_existing_email(self):
        self.client.post(self.register_url, self.user_data, format="json")
        res=self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()["msg"], Msg.USER_ALREADY_REGISTERED)

    def test_user_cannot_register_with_invalid_code(self):
        self.user_data["code"] = "123456"
        res=self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(res.status_code,202)
        self.assertEqual(res.json()["msg"], Msg.CODE_ERROR)


    def test_user_cannot_confirm_with_invalid_data(self):
        res=self.client.post(self.register_url)
        self.assertEqual(res.status_code,400)
        
        
    def test_user_cannot_login_with_invalid_data(self):
        res=self.client.post(self.login_url)
        self.assertEqual(res.status_code,401)

    def test_user_can_login(self):
        self.client.post(self.register_url, self.user_data, format="json")
        res=self.client.post(self.login_url, self.user_data, format="json")
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()["msg"], Msg.LOGIN_SUCCEEDED)
    
    def test_user_cannot_login_with_unregistered_email(self):
        self.user_data["email"] = "wrongemail@email.com"
        res = self.client.post(self.login_url, self.user_data, format="json")
        self.assertEqual(res.status_code,202)
        self.assertEqual(res.json()["msg"], Msg.USER_NOT_EXIST)
    
    def test_user_can_logout(self):
        self.client.post(self.register_url, self.user_data, format="json")
        login_res = self.client.post(self.login_url, self.user_data, format="json")
        token = login_res.json()["token"]
        
        headers = {"HTTP_AUTHORIZATION":f'{token}'}
        logout_res = self.client.post(self.logout_url, **headers)

        self.assertEqual(logout_res.status_code, 202)
        self.assertEqual(logout_res.json()["msg"], Msg.LOGOUT_SUCCEEDED)

    def test_user_cannot_change_password_with_invalid_data(self):
        res=self.client.post(self.change_password_url)
        self.assertEqual(res.status_code,400)
    
    def test_user_can_change_password(self):
        self.client.post(self.register_url, self.user_data, format="json")
        change_password_res = self.client.post(self.change_password_url, self.change_password_data, format="json")
        self.assertEqual(change_password_res.status_code, 200)
        self.assertEqual(change_password_res.json()["msg"], Msg.CHANGE_PASSWORD_SUCCEEDED)
    
    def test_user_cannot_change_password_with_invalid_password(self):
        self.client.post(self.register_url, self.user_data, format="json")
        self.change_password_data["password"] = "wrongpassword123"
        change_password_res = self.client.post(self.change_password_url, self.change_password_data, format="json")
        self.assertEqual(change_password_res.status_code, 202)
        self.assertEqual(change_password_res.json()["msg"], Msg.LOGIN_FAILED)

    def test_user_cannot_change_password_with_invalid_email(self):
        self.client.post(self.register_url, self.user_data, format="json")
        self.change_password_data["email"] = "invalid@email.com"
        change_password_res = self.client.post(self.change_password_url, self.change_password_data, format="json")
        self.assertEqual(change_password_res.status_code, 202)
        self.assertEqual(change_password_res.json()["msg"], Msg.USER_NOT_EXIST)

    def test_user_send_forget_password_email(self):
        res=self.client.post(self.sendforgetpasswordemail_url, self.email_data, format="json")
        code = conn.get(f"ChangePassword_{self.email_data['email']}")
        self.assertEqual(res.status_code,200)
        self.assertIsNotNone(code)
        self.assertEqual(res.json()["msg"], Msg.CODE_SENT)
    
    def test_user_forget_password_email(self):
        self.client.post(self.register_url, self.user_data, format="json")
        
        forget_password_res = self.client.post(self.forget_password_url, self.forget_password_data, format="json")
        self.assertEqual(forget_password_res.status_code, 200)
        self.assertEqual(forget_password_res.json()["msg"], Msg.CHANGE_PASSWORD_SUCCEEDED)

    def test_user_cannot_forget_password_with_invalid_email(self):
        self.client.post(self.register_url, self.user_data, format="json")
        self.forget_password_data["email"] = "invalid@email.com"
        self.forget_password_data["code"] = "123456"
        conn.set(f"ChangePassword_{self.forget_password_data['email']}", self.forget_password_data["code"])
        res = self.client.post(self.forget_password_url, self.forget_password_data, format="json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.json()["msg"], Msg.USER_NOT_EXIST)

    def test_user_cannot_forget_password_with_invalid_code(self):
        self.client.post(self.register_url, self.user_data, format="json")
        self.forget_password_data["code"] = "123456"
        res = self.client.post(self.forget_password_url, self.forget_password_data, format="json")
        self.assertEqual(res.status_code, 202)
        self.assertEqual(res.json()["msg"], Msg.CODE_ERROR)
