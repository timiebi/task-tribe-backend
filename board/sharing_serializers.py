from django.contrib.auth.models import User
from rest_framework import serializers

from .models import AppNotification, SharedItem, SpaceConnection


class SpaceConnectionSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source="from_user.username", read_only=True)
    to_username = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = SpaceConnection
        fields = [
            "id",
            "from_username",
            "to_username",
            "invite_email",
            "display_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_to_username(self, obj):
        return obj.to_user.username if obj.to_user else None

    def get_display_name(self, obj):
        if obj.to_user:
            return obj.to_user.username
        return obj.invite_email


class SharedItemSerializer(serializers.ModelSerializer):
    shared_by_username = serializers.CharField(
        source="shared_by.username", read_only=True
    )

    class Meta:
        model = SharedItem
        fields = [
            "id",
            "shared_by_username",
            "item_type",
            "item_id",
            "payload",
            "message",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class AppNotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    action_required = serializers.SerializerMethodField()

    class Meta:
        model = AppNotification
        fields = [
            "id",
            "kind",
            "title",
            "body",
            "payload",
            "is_read",
            "action_required",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_read(self, obj):
        return obj.read_at is not None

    def get_action_required(self, obj):
        return obj.kind == AppNotification.KIND_INVITE and obj.read_at is None


class InviteByEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ShareItemSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    item_type = serializers.ChoiceField(choices=SharedItem.ITEM_CHOICES)
    item_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AcceptTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)


class ImportShareSerializer(serializers.Serializer):
    target = serializers.ChoiceField(choices=SharedItem.ITEM_CHOICES)

    def to_internal_value(self, data):
        payload = dict(data)
        if "as" in payload and "target" not in payload:
            payload["target"] = payload["as"]
        return super().to_internal_value(payload)
