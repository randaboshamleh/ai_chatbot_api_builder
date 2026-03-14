from rest_framework import serializers


class ChatQuerySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    stream = serializers.BooleanField(default=False, required=False)
    session_id = serializers.UUIDField(required=False, allow_null=True)