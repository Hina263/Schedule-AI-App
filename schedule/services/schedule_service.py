from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from schedule.models import Event
from schedule.services.ai_service import AIService

class ScheduleService:
    """スケジュール管理のビジネスロジック"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    def create_event(self, user_id, natural_input):
        """
        イベントを作成
        
        Args:
            user_id (str): ユーザーID
            natural_input (str): 自然言語の予定入力
            
        Returns:
            dict: 作成結果
        """
        # AIで自然言語を解析
        event_data = self.ai_service.parse_natural_language(natural_input)
        
        # 日時文字列をdatetimeオブジェクトに変換
        start_dt = self._parse_datetime(event_data['start_datetime'])
        end_dt = self._parse_datetime(event_data['end_datetime']) if event_data.get('end_datetime') else None
        
        # 衝突チェック
        conflicts = self._check_conflicts(user_id, start_dt, end_dt, event_data)
        
        if conflicts:
            # AIで警告メッセージを生成
            new_event_dict = {
                'title': event_data['title'],
                'start': event_data['start_datetime'],
                'end': event_data.get('end_datetime'),
                'type': event_data.get('event_type', 'activity'),
                'is_all_day': event_data.get('is_all_day', False),
                'category': event_data.get('category')
            }
            
            conflict_list = []
            for conflict in conflicts:
                conflict_dict = self._event_to_dict(conflict)
                warning_message = self.ai_service.generate_conflict_message(
                    new_event_dict,
                    conflict_dict
                )
                conflict_dict['warning_message'] = warning_message
                conflict_list.append(conflict_dict)
            
            return {
                'status': 'conflict',
                'conflicts': conflict_list,
                'proposed_event': event_data
            }
        
        # イベントを作成
        event = Event.objects.create(
            user_id=user_id,
            title=event_data['title'],
            start_datetime=start_dt,
            end_datetime=end_dt,
            event_type=event_data.get('event_type', 'activity'),
            priority=event_data.get('priority', 3),
            is_all_day=event_data.get('is_all_day', False),
            category=event_data.get('category')
        )
        
        return {
            'status': 'success',
            'event_id': event.id,
            'event': self._event_to_dict(event)
        }
    
    def get_events(self, user_id, period_text):
        """
        期間指定でイベントを取得
        
        Args:
            user_id (str): ユーザーID
            period_text (str): 期間表現（例: 今日、明日、今週）
            
        Returns:
            list: イベントリスト
        """
        # AIで期間を解析
        range_data = self.ai_service.parse_period(period_text)
        
        # 日時文字列をdatetimeオブジェクトに変換
        start_dt = self._parse_datetime(range_data['start'])
        end_dt = self._parse_datetime(range_data['end'])
        
        # イベントを取得
        events = Event.objects.filter(
            user_id=user_id,
            start_datetime__gte=start_dt,
            start_datetime__lte=end_dt
        ).order_by('start_datetime')
        
        return [self._event_to_dict(event) for event in events]
    
    def _check_conflicts(self, user_id, start_dt, end_dt, new_event_data):
        """
        高度な衝突チェック
        
        Args:
            user_id (str): ユーザーID
            start_dt (datetime): 開始日時
            end_dt (datetime): 終了日時
            new_event_data (dict): 新しいイベントのデータ
            
        Returns:
            QuerySet: 衝突するイベント
        """
        if not end_dt:
            return Event.objects.none()
        
        new_is_all_day = new_event_data.get('is_all_day', False)
        new_event_type = new_event_data.get('event_type', 'activity')
        new_category = new_event_data.get('category')
        
        # 時間が重複する可能性のあるイベントを全て取得
        potentially_conflicting = Event.objects.filter(
            user_id=user_id
        ).filter(
            Q(start_datetime__lt=end_dt, end_datetime__gt=start_dt) |
            Q(start_datetime__gte=start_dt, start_datetime__lt=end_dt) |
            Q(start_datetime__lte=start_dt, end_datetime__gte=end_dt)
        )
        
        conflicts = []
        
        for existing in potentially_conflicting:
            should_warn = self._should_warn_about_conflict(
                new_event_type=new_event_type,
                new_is_all_day=new_is_all_day,
                new_category=new_category,
                existing_event=existing
            )
            
            if should_warn:
                conflicts.append(existing)
        
        return conflicts
    
    def  _should_warn_about_conflict(self, new_event_type, new_is_all_day, new_category, existing_event):
        # ルール5: 同カテゴリ例外(カテゴリが一つでも一致する場合は警告しない)
        if new_category and existing_event.category:
            # どちらかのカテゴリが一つでも被ってれば例外
            if set(new_category) & set(existing_event.category):
                return False
    
        # ルール1: 時間指定 vs 時間指定
        if (new_event_type == 'activity' and not new_is_all_day and
            existing_event.event_type == 'activity' and not existing_event.is_all_day):
                return True
    
        # ルール2: 終日イベント + 時間指定
        if ((new_is_all_day and existing_event.event_type == 'activity' and not existing_event.is_all_day) or
            (not new_is_all_day and existing_event.is_all_day)):
                return True
    
        # ルール3 & 4: 期間予定が絡む場合
        if new_event_type == 'block' or existing_event.event_type == 'block':
            return True
    
        return False
    
    def _parse_datetime(self, datetime_str):
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        # タイムゾーンを設定(UTCではなく日本時間として扱う)
        return timezone.make_aware(dt, timezone.get_current_timezone())
    
    def _event_to_dict(self, event):
        start_local = timezone.localtime(event.start_datetime)
        end_local = timezone.localtime(event.end_datetime) if event.end_datetime else None
    
        return {
            'id': event.id,
            'user_id': event.user_id,
            'title': event.title,
            'start': start_local.strftime('%Y-%m-%d %H:%M'),
            'end': end_local.strftime('%Y-%m-%d %H:%M') if end_local else None,
            'type': event.event_type,
            'priority': event.priority,
            'is_all_day': event.is_all_day,
            'category': event.category,  # 配列のままそのまま返す
            'created_at': timezone.localtime(event.created_at).strftime('%Y-%m-%d %H:%M:%S')
        }