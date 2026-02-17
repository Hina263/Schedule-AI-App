from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.ModelSerializer):
    """イベントシリアライザー"""
    
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    type = serializers.CharField(source='event_type', read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id',
            'user_id',
            'title',
            'start',
            'end',
            'type',
            'priority',
            'is_all_day',
            'category',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_start(self, obj):
        """開始日時をフォーマット"""
        return obj.start_datetime.strftime('%Y-%m-%d %H:%M')
    
    def get_end(self, obj):
        """終了日時をフォーマット"""
        if obj.end_datetime:
            return obj.end_datetime.strftime('%Y-%m-%d %H:%M')
        return None


class EventCreateSerializer(serializers.Serializer):
    """イベント作成用シリアライザー"""
    
    input = serializers.CharField(
        max_length=500,
        help_text="自然言語での予定入力（例: 明日18時から会議）"
    )
    user_id = serializers.CharField(
        max_length=100,
        default='default_user',
        required=False
    )


class EventListSerializer(serializers.Serializer):
    """イベント取得用シリアライザー"""
    
    period = serializers.CharField(
        max_length=100,
        default='今日',
        help_text="期間指定（例: 今日、明日、今週）"
    )
    user_id = serializers.CharField(
        max_length=100,
        default='default_user',
        required=False
    )