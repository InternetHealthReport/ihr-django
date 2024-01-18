# Import necessary modules and classes
from rest_framework.test import APITestCase
from django.urls import reverse
from ihr import const

from ihr.const import ConfirmationEmail, ChangePasswordEmail, StrErrors, Msg, POOL, std_response
import redis

# Establish a connection to Redis using a connection pool
conn = redis.Redis(connection_pool=POOL)

# Define a test setup class
class TestSetUp(APITestCase, const.ConfirmationEmail):
    
    # Method to send a registration email for testing
    def post_emailForRegistration(self):
        self.sendemail_url= reverse('ihr:UserSendEmailListView')

        # Sample email data
        self.email_data={
            "email":"email@gmail.com"
        }

        # Send a POST request to the email endpoint
        self.client.post(self.sendemail_url, self.email_data, format="json")
    
    # Method to retrieve the confirmation code from Redis
    def get_code(self):
        code = conn.get(f"Confirmation_{self.email_data['email']}")
        return code

    # Method to retrieve the forget password code from Redis
    def get_forget_code(self):
        code = conn.get(f"ChangePassword_{self.email_data['email']}")
        return code

    # Method to set up data and parameters before each test case
    def setUp(self):
        # URLs for various user-related actions
        self.register_url= reverse('ihr:UserRegisterListView')
        self.login_url= reverse('ihr:UserLoginListView')
        self.sendemail_url= reverse('ihr:UserSendEmailListView')
        self.logout_url= reverse('ihr:UserLogoutListView')
        self.change_password_url = reverse('ihr:UserChangePasswordListView')
        self.sendforgetpasswordemail_url = reverse('ihr:UserSendForgetPasswordEmailListView')
        self.forget_password_url = reverse('ihr:UserForgetPasswordListView')

        # Sample email data for testing
        self.email_data={
            "email":"email@gmail.com"
        }
        
        # Sample user data for registration and login
        self.user_data={
            "email":"email@gmail.com",
            "password":"password123",
            "code": self.get_code(),
        }

        # Sample data for changing password
        self.change_password_data={
            "email":"email@gmail.com",
            "password":"password123",
            "new_password":"password1234",
        }

        # Sample data for forgetting password
        self.forget_password_data={
            "email":"email@gmail.com",
            "new_password":"password1234",
            "code": self.get_forget_code(),
        }
        
        return super().setUp()
    # Method to clean up resources after each test case
    def tearDown(self):
        return super().tearDown()
    
