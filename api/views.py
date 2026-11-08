import json
import logging
import os
import urllib.request
import urllib.error

from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import chat
from .inference import get_classifier
from .models import Consultation
from .serializers import ChatSerializer, ConsultationSerializer, HealthCheckSerializer, RegisterSerializer

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    def get(self, request):
        serializer = HealthCheckSerializer({'status': 'ok'})
        return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)


class ConsultationViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Consultation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        image = serializer.validated_data.get('image')

        if image is not None:
            try:
                image.seek(0)
                result = get_classifier().predict(image)
            except Exception:
                logger.exception('KOA inference failed for consultation image')
                serializer.save(
                    user=self.request.user,
                    ai_response='Image analysis failed — please try again or contact support.',
                )
                return

            oa_line = (
                'Signs of osteoarthritis detected.' if result['has_osteoarthritis']
                else 'No significant osteoarthritis signs detected.'
            )
            ai_response = (
                f"X-ray analysis: Kellgren-Lawrence Grade {result['grade']} ({result['grade_label']}). "
                f"Confidence: {result['confidence']:.0%}. Expected grade: {result['expected_grade']:.1f}. "
                f"{oa_line} "
                "Research prototype. Not a medical device. Not for clinical decisions. "
                "Please consult a clinician."
            )
            serializer.save(
                user=self.request.user,
                ai_response=ai_response,
                grade=result['grade'],
                confidence=result['confidence'],
                expected_grade=result['expected_grade'],
                probabilities=result['probabilities'],
            )
            return

        symptoms = serializer.validated_data.get('symptoms', '')
        placeholder_response = (
            f"Thanks for sharing your symptoms: \"{symptoms}\". "
            "This is a placeholder response — real AI integration is future work."
        )
        serializer.save(user=self.request.user, ai_response=placeholder_response)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        consultation = None
        consultation_id = serializer.validated_data.get('consultation_id')
        if consultation_id is not None:
            consultation = get_object_or_404(Consultation, id=consultation_id, user=request.user)

        result = chat.reply(serializer.validated_data['message'], consultation)
        return Response(result)


# ---------------------------------------------------------------------------
# Gemini proxy — keeps GEMINI_API_KEY server-side (never exposed to browser)
# ---------------------------------------------------------------------------
_GEMINI_URL = (
    'https://generativelanguage.googleapis.com/v1beta/models/'
    'gemini-1.5-flash:generateContent'
)

_GEMINI_SYSTEM = (
    'You are MedAdvise AI\'s medical assistant for knee osteoarthritis (KOA). '
    'Answer questions about the Kellgren-Lawrence grading scale (0-4), X-ray analysis results, '
    'and general KOA information. Always remind users this is a research prototype only — '
    'not for clinical decisions. Recommend consulting an orthopedic specialist. '
    'Keep responses concise (under 150 words), compassionate, and accurate.'
)


class GeminiChatView(APIView):
    """Server-side proxy to Google Gemini 1.5 Flash.

    Accepts ``{ "message": "...", "history": [...], "context": "..." }``
    and returns ``{ "reply": "..." }``.

    Requires GEMINI_API_KEY in the environment. Returns 503 when the key is
    absent so the frontend can fall back to the rule-based chat endpoint.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        api_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not api_key:
            return Response({'error': 'NO_API_KEY', 'reply': None}, status=503)

        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': 'message is required'}, status=400)

        history = request.data.get('history') or []
        context_note = request.data.get('context') or ''

        system_text = _GEMINI_SYSTEM
        if context_note:
            system_text += f'\n\nCurrent patient context:\n{context_note}'

        contents = [
            {'role': 'user', 'parts': [{'text': system_text}]},
            {'role': 'model', 'parts': [{'text': 'Understood. I am ready to help.'}]},
        ]
        for turn in history:
            if isinstance(turn, dict) and turn.get('role') in ('user', 'model'):
                contents.append(turn)
        contents.append({'role': 'user', 'parts': [{'text': message}]})

        payload = json.dumps({
            'contents': contents,
            'generationConfig': {'maxOutputTokens': 300, 'temperature': 0.3},
        }).encode('utf-8')

        req = urllib.request.Request(
            f'{_GEMINI_URL}?key={api_key}',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')
            logger.warning('Gemini HTTP %s: %s', exc.code, body[:200])
            if exc.code == 429:
                return Response({'error': 'RATE_LIMIT'}, status=429)
            return Response({'error': f'Gemini HTTP {exc.code}'}, status=502)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Gemini request failed: %s', exc)
            return Response({'error': str(exc)}, status=502)

        reply_text = (
            data.get('candidates', [{}])[0]
            .get('content', {})
            .get('parts', [{}])[0]
            .get('text', 'No response generated.')
        )
        return Response({'reply': reply_text})
