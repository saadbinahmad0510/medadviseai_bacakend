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


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


class ConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = ['id', 'symptoms', 'image', 'ai_response', 'grade',
                  'confidence', 'expected_grade', 'probabilities', 'created_at']
        read_only_fields = ['ai_response', 'grade', 'confidence',
                             'expected_grade', 'probabilities', 'created_at']

    def validate_image(self, image):
        if image.size > MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError(
                f'Image is too large ({image.size // (1024 * 1024)}MB). Max size is '
                f'{MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB.'
            )
        return image


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField()
    consultation_id = serializers.IntegerField(required=False, allow_null=True)
