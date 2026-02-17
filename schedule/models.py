from django.db import models

class Event(models.Model):
    
    EVENT_TYPE_CHOICES = [
        ('activity', 'アクティビティ'),
        ('block', 'ブロック期間'),
        ('deadline', '締切'),
    ]
    
    PRIORITY_CHOICES = [
        (1, '最重要'),
        (2, '重要'),
        (3, '普通'),
        (4, '低'),
        (5, '最低'),
    ]
    
    user_id = models.CharField(max_length=100, default='default_user')
    title = models.CharField(max_length=200, verbose_name='タイトル')
    start_datetime = models.DateTimeField(verbose_name='開始日時')
    end_datetime = models.DateTimeField(null=True, blank=True, verbose_name='終了日時')
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        default='activity',
        verbose_name='種別'
    )
    priority = models.IntegerField(
        choices=PRIORITY_CHOICES,
        default=3,
        verbose_name='優先度'
    )
    is_all_day = models.BooleanField(default=False, verbose_name='終日イベント')
    
    # 複数カテゴリに変更
    category = models.JSONField(default=list, blank=True, verbose_name='カテゴリ')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    
    class Meta:
        db_table = 'events'
        ordering = ['start_datetime']
        verbose_name = 'イベント'
        verbose_name_plural = 'イベント'
    
    def __str__(self):
        return f"{self.title} ({self.start_datetime})"