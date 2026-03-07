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


class UserSettings(models.Model):

    WARN_CHOICES = [
        ('gentle',   '優しい'),
        ('standard', '標準'),
        ('strict',   '厳しめ'),
    ]

    user_id                     = models.CharField(max_length=100, unique=True, default='default_user')
    default_duration_hours      = models.IntegerField(default=1)
    warning_level               = models.CharField(max_length=20, choices=WARN_CHOICES, default='standard')
    remind_minutes_before       = models.IntegerField(null=True, blank=True)
    remind_day_before           = models.BooleanField(default=False)
    remind_days_before_deadline = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'user_settings'

    def __str__(self):
        return f"UserSettings({self.user_id})"

    def to_dict(self):
        return {
            'user_id'                    : self.user_id,
            'default_duration_hours'     : self.default_duration_hours,
            'warning_level'              : self.warning_level,
            'remind_minutes_before'      : self.remind_minutes_before,
            'remind_day_before'          : self.remind_day_before,
            'remind_days_before_deadline': self.remind_days_before_deadline,
        }