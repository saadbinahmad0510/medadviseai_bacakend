from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Consultation
from .serializers import ConsultationSerializer, HealthCheckSerializer, RegisterSerializer


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
        symptoms = serializer.validated_data['symptoms']
        placeholder_response = (
            f"Thanks for sharing your symptoms: \"{symptoms}\". "
            "This is a placeholder response — real AI integration is future work."
        )
        serializer.save(user=self.request.user, ai_response=placeholder_response)
