import logging

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
