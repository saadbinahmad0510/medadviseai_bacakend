from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

SAMPLE_IMAGE_PATH = Path(settings.BASE_DIR).parent / 'asset' / 'samples' / 'grade4_0.png'


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

    def test_create_consultation_with_xray_returns_grade(self):
        self.client.force_authenticate(user=self.alice)

        with open(SAMPLE_IMAGE_PATH, 'rb') as f:
            image = SimpleUploadedFile('grade4_0.png', f.read(), content_type='image/png')

        response = self.client.post('/api/consultations/', {'image': image}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsInstance(response.data['grade'], int)
        self.assertIn(response.data['grade'], range(5))
        self.assertIn('Grade', response.data['ai_response'])


class ChatTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='pass-123')
        self.bob = User.objects.create_user(username='bob', password='pass-123')
        self.client.force_authenticate(user=self.alice)

    def ask(self, message, consultation_id=None):
        payload = {'message': message}
        if consultation_id is not None:
            payload['consultation_id'] = consultation_id
        return self.client.post('/api/chat/', payload)

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.ask('hello')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_accuracy_intent(self):
        response = self.ask('How accurate and reliable is this model?')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['intent'], 'accuracy')
        self.assertIn('QWK', response.data['reply'])

    def test_grade1_intent(self):
        response = self.ask('Why is grade 1 doubtful and unreliable?')
        self.assertEqual(response.data['intent'], 'grade1')
        self.assertIn('0.39', response.data['reply'])

    def test_kellgren_intent(self):
        response = self.ask('What is the Kellgren-Lawrence grading system?')
        self.assertEqual(response.data['intent'], 'kellgren')
        self.assertIn('Grade 4', response.data['reply'])

    def test_architecture_intent(self):
        response = self.ask('How does the model architecture work?')
        self.assertEqual(response.data['intent'], 'architecture')
        self.assertIn('MobileNetV2', response.data['reply'])

    def test_dataset_intent(self):
        response = self.ask('Where does the training dataset come from?')
        self.assertEqual(response.data['intent'], 'dataset')
        self.assertIn('Mendeley', response.data['reply'])

    def test_advice_intent_for_direct_question(self):
        response = self.ask('What treatment should I do, should I see a doctor?')
        self.assertEqual(response.data['intent'], 'advice')
        self.assertIn('clinician', response.data['reply'])

    def test_advice_intent_for_symptom_message(self):
        response = self.ask('My knee hurts a lot, should I take painkillers?')
        self.assertEqual(response.data['intent'], 'advice')

    def test_result_intent_without_consultation(self):
        response = self.ask('What does this result mean?')
        self.assertEqual(response.data['intent'], 'result')
        self.assertIn("don't have a graded X-ray", response.data['reply'])

    def test_result_intent_with_consultation(self):
        create_response = self.client.post('/api/consultations/', {'symptoms': 'knee pain'})
        consultation_id = create_response.data['id']

        response = self.ask('Can you explain the grade?', consultation_id=consultation_id)
        self.assertEqual(response.data['intent'], 'result')

    def test_cannot_reference_another_users_consultation(self):
        self.client.force_authenticate(user=self.bob)
        bob_consultation = self.client.post('/api/consultations/', {'symptoms': 'fever'}).data['id']

        self.client.force_authenticate(user=self.alice)
        response = self.ask('Explain the result', consultation_id=bob_consultation)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_fallback_intent(self):
        response = self.ask('what is the weather today')
        self.assertEqual(response.data['intent'], 'fallback')
        self.assertIn('What does this result mean?', response.data['reply'])
