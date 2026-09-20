from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_check(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')


class AuthFlowTests(APITestCase):
    def test_register_and_obtain_token(self):
        register_response = self.client.post('/api/auth/register/', {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'strong-pass-123',
        })
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        token_response = self.client.post('/api/token/', {
            'username': 'alice',
            'password': 'strong-pass-123',
        })
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', token_response.data)
        self.assertIn('refresh', token_response.data)


class ConsultationTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='pass-123')
        self.bob = User.objects.create_user(username='bob', password='pass-123')

    def test_requires_authentication(self):
        response = self.client.get('/api/consultations/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_own_consultations(self):
        self.client.force_authenticate(user=self.alice)

        create_response = self.client.post('/api/consultations/', {'symptoms': 'headache'})
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertIn('headache', create_response.data['ai_response'])

        list_response = self.client.get('/api/consultations/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

    def test_cannot_see_another_users_consultations(self):
        self.client.force_authenticate(user=self.bob)
        self.client.post('/api/consultations/', {'symptoms': 'fever'})

        self.client.force_authenticate(user=self.alice)
        response = self.client.get('/api/consultations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
