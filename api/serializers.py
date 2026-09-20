from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Consultation


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ['id', 'symptoms', 'ai_response', 'created_at']
        read_only_fields = ['ai_response', 'created_at']
