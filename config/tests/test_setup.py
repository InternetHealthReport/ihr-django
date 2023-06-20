from rest_framework.test import APITestCase
from django.urls import reverse
from ihr import const

from ihr.const import ConfirmationEmail, ChangePasswordEmail, StrErrors, Msg, POOL, std_response
import redis
conn = redis.Redis(connection_pool=POOL)

class TestSetUp(APITestCase, const.ConfirmationEmail):

    def post_emailForRegistration(self):
        self.sendemail_url= reverse('ihr:UserSendEmailListView')


        self.email_data={
            "email":"email@gmail.com"
        }

        self.client.post(self.sendemail_url, self.email_data, format="json")
    
    def get_code(self):
        code = conn.get(f"Confirmation_{self.email_data['email']}")
        return code
    def get_forget_code(self):
        code = conn.get(f"ChangePassword_{self.email_data['email']}")
        return code


    def setUp(self):
        
        self.register_url= reverse('ihr:UserRegisterListView')
        self.login_url= reverse('ihr:UserLoginListView')
        self.sendemail_url= reverse('ihr:UserSendEmailListView')
        self.logout_url= reverse('ihr:UserLogoutListView')
        self.change_password_url = reverse('ihr:UserChangePasswordListView')
        self.sendforgetpasswordemail_url = reverse('ihr:UserSendForgetPasswordEmailListView')
        self.forget_password_url = reverse('ihr:UserForgetPasswordListView')


        self.email_data={
            "email":"email@gmail.com"
        }

        self.user_data={
            "email":"email@gmail.com",
            "password":"password123",
            "code": self.get_code(),
        }
        self.change_password_data={
            "email":"email@gmail.com",
            "password":"password123",
            "new_password":"password1234",
        }
        self.forget_password_data={
            "email":"email@gmail.com",
            "new_password":"password1234",
            "code": self.get_forget_code(),
        }
        
        return super().setUp()
    
    def tearDown(self):
        return super().tearDown()
    