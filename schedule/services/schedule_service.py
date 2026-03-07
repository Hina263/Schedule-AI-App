from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from schedule.models import Event, UserSettings
from schedule.services.ai_service import AIService

class ScheduleService:
    """スケジュール管理のビジネスロジック"""

    def __init__(self):
        self.ai_service = AIService()

    def create_event(self, user_id, natural_input, force=False):
        """
        イベントを作成。

        force=False のとき衝突チェックを行い、
          - 時間重複 (conflict): イベントを作成せずに返す
          - 期間警告 (warning) : フロントに Yes/No を促して返す
        force=True のとき警告を無視して作成する。
        """
        # ユーザー設定を取得
        settings_obj = UserSettings.objects.filter(user_id=user_id).first()
        duration     = settings_obj.default_duration_hours if settings_obj else 1
        warn_level   = settings_obj.warning_level          if settings_obj else 'standard'

        event_data = self.ai_service.parse_natural_language(natural_input, duration)

        start_dt = self._parse_datetime(event_data['start_datetime'])
        end_dt   = self._parse_datetime(event_data['end_datetime']) if event_data.get('end_datetime') else None

        if not force:
            check = self._check_conflicts(user_id, start_dt, end_dt, event_data, warn_level)
            hard  = check['conflicts']
            soft  = check['warnings']

            new_dict = {
                'title'     : event_data['title'],
                'start'     : event_data['start_datetime'],
                'end'       : event_data.get('end_datetime'),
                'type'      : event_data.get('event_type', 'activity'),
                'is_all_day': event_data.get('is_all_day', False),
                'category'  : event_data.get('category'),
            }

            if hard:
                conflict_list = []
                for c in hard:
                    cd = self._event_to_dict(c)
                    cd['warning_message'] = self.ai_service.generate_conflict_message(new_dict, cd)
                    conflict_list.append(cd)
                return {
                    'status'        : 'conflict',
                    'conflicts'     : conflict_list,
                    'proposed_event': event_data,
                }

            if soft:
                warning_list = []
                for w in soft:
                    wd = self._event_to_dict(w)
                    wd['warning_message'] = self.ai_service.generate_conflict_message(new_dict, wd)
                    warning_list.append(wd)
                return {
                    'status'        : 'warning',
                    'warnings'      : warning_list,
                    'proposed_event': event_data,
                }

        event = Event.objects.create(
            user_id        = user_id,
            title          = event_data['title'],
            start_datetime = start_dt,
            end_datetime   = end_dt,
            event_type     = event_data.get('event_type', 'activity'),
            priority       = event_data.get('priority', 3),
            is_all_day     = event_data.get('is_all_day', False),
            category       = event_data.get('category'),
        )

        return {
            'status'  : 'success',
            'event_id': event.id,
            'event'   : self._event_to_dict(event),
        }

    def update_event(self, event_id, user_id, title=None, start_datetime=None, end_datetime=None):
        """タイトル・開始・終了日時を更新する。"""
        try:
            event = Event.objects.get(id=event_id, user_id=user_id)
        except Event.DoesNotExist:
            raise ValueError('イベントが見つかりません')

        if title is not None:
            event.title = title
        if start_datetime is not None:
            event.start_datetime = self._parse_datetime(start_datetime)
        if end_datetime is not None:
            event.end_datetime = self._parse_datetime(end_datetime)

        event.save()
        return self._event_to_dict(event)

    def modify_event_by_natural_language(self, user_id, natural_input):
        """自然言語から予定の変更・削除を実行する。"""
        command = self.ai_service.parse_modify_command(natural_input)
        intent  = command.get('intent')

        if intent == 'unknown':
            return {
                'status' : 'error',
                'message': '変更・削除の内容を読み取れませんでした。'
                           '「〇月〇日の〇〇を削除」「〇月〇日の〇〇を〇時に変更」のように入力してください。',
            }

        search    = command.get('search', {})
        date_str  = search.get('date')
        title_kw  = search.get('title_keyword', '')

        # イベントを検索
        candidates = Event.objects.filter(user_id=user_id)
        if date_str:
            try:
                day        = datetime.strptime(date_str, '%Y-%m-%d').date()
                candidates = candidates.filter(start_datetime__date=day)
            except ValueError:
                pass
        if title_kw:
            candidates = candidates.filter(title__icontains=title_kw)

        events_list = list(candidates.order_by('start_datetime'))
        found_count = len(events_list)

        if found_count == 0:
            action_str  = '変更' if intent == 'update' else '削除'
            search_desc = []
            if date_str:
                search_desc.append(date_str)
            if title_kw:
                search_desc.append(f'「{title_kw}」')
            desc = '・'.join(search_desc) if search_desc else '指定された'
            return {
                'status' : 'not_found',
                'message': f'{desc}の予定が見つかりませんでした。{action_str}する予定を確認してください。',
            }

        # 複数マッチ → フロントに選択を委ねる
        if found_count > 1:
            action_str = '変更' if intent == 'update' else '削除'
            return {
                'status' : 'multiple',
                'message': f'{found_count}件の予定が見つかりました。{action_str}する予定を選んでください。',
                'events' : [self._event_to_dict(e) for e in events_list],
                'intent' : intent,
                'changes': command.get('changes', {}),
            }

        return self._apply_modify(events_list[0], intent, command.get('changes', {}))

    def apply_modify_to_event(self, event_id, user_id, intent, changes):
        """選択確定後に特定イベントへ変更・削除を適用する。"""
        try:
            event = Event.objects.get(id=event_id, user_id=user_id)
        except Event.DoesNotExist:
            raise ValueError('イベントが見つかりません')
        return self._apply_modify(event, intent, changes)

    def _apply_modify(self, event, intent, changes):
        """変更・削除を実際に実行する共通処理。"""
        if intent == 'delete':
            event_dict = self._event_to_dict(event)
            event.delete()
            return {
                'status' : 'success',
                'action' : 'delete',
                'message': f'「{event_dict["title"]}」を削除しました',
                'event'  : event_dict,
            }

        # update
        if changes.get('title'):
            event.title = changes['title']
        if changes.get('start_datetime'):
            event.start_datetime = self._parse_datetime(changes['start_datetime'])
        if changes.get('end_datetime'):
            event.end_datetime = self._parse_datetime(changes['end_datetime'])
        event.save()
        return {
            'status' : 'success',
            'action' : 'update',
            'message': f'「{event.title}」を更新しました',
            'event'  : self._event_to_dict(event),
        }

    def execute_command(self, user_id, natural_input):
        """統合コマンド: 追加/検索/変更/削除を自然言語から判定して実行する。"""
        settings_obj = UserSettings.objects.filter(user_id=user_id).first()
        duration     = settings_obj.default_duration_hours if settings_obj else 1
        warn_level   = settings_obj.warning_level          if settings_obj else 'standard'

        cmd    = self.ai_service.parse_unified_command(natural_input, duration)
        intent = cmd.get('intent', 'unknown')

        if intent == 'add':
            event_data = cmd.get('event_data') or {}
            if not event_data.get('start_datetime'):
                return {'status': 'error', 'message': '予定の日時を読み取れませんでした。日時を含めて入力してください。'}

            start_dt = self._parse_datetime(event_data['start_datetime'])
            end_dt   = self._parse_datetime(event_data['end_datetime']) if event_data.get('end_datetime') else None

            check = self._check_conflicts(user_id, start_dt, end_dt, event_data, warn_level)

            new_dict = {
                'title'     : event_data.get('title', ''),
                'start'     : event_data['start_datetime'],
                'end'       : event_data.get('end_datetime'),
                'type'      : event_data.get('event_type', 'activity'),
                'is_all_day': event_data.get('is_all_day', False),
                'category'  : event_data.get('category'),
            }

            if check['conflicts']:
                conflict_list = []
                for c in check['conflicts']:
                    cd = self._event_to_dict(c)
                    cd['warning_message'] = self.ai_service.generate_conflict_message(new_dict, cd)
                    conflict_list.append(cd)
                return {'status': 'conflict', 'action': 'add', 'conflicts': conflict_list, 'proposed_event': event_data}

            if check['warnings']:
                warning_list = []
                for w in check['warnings']:
                    wd = self._event_to_dict(w)
                    wd['warning_message'] = self.ai_service.generate_conflict_message(new_dict, wd)
                    warning_list.append(wd)
                return {'status': 'warning', 'action': 'add', 'warnings': warning_list, 'proposed_event': event_data}

            return self._create_event_from_data(user_id, event_data, start_dt, end_dt)

        elif intent == 'search':
            period = cmd.get('period') or '今日'
            events = self.get_events(user_id, period)
            return {'status': 'success', 'action': 'search', 'period': period, 'events': events}

        elif intent in ('update', 'delete'):
            search   = cmd.get('search') or {}
            date_str = search.get('date')
            title_kw = search.get('title_keyword', '')
            changes  = cmd.get('changes') or {}

            candidates = Event.objects.filter(user_id=user_id)
            if date_str:
                try:
                    day        = datetime.strptime(date_str, '%Y-%m-%d').date()
                    candidates = candidates.filter(start_datetime__date=day)
                except ValueError:
                    pass
            if title_kw:
                candidates = candidates.filter(title__icontains=title_kw)

            events_list = list(candidates.order_by('start_datetime'))
            found_count = len(events_list)

            if found_count == 0:
                action_str = '変更' if intent == 'update' else '削除'
                return {'status': 'not_found', 'message': f'予定が見つかりませんでした。{action_str}する予定を確認してください。'}

            if found_count > 1:
                action_str = '変更' if intent == 'update' else '削除'
                return {
                    'status' : 'multiple',
                    'action' : intent,
                    'message': f'{found_count}件の予定が見つかりました。{action_str}する予定を選んでください。',
                    'events' : [self._event_to_dict(e) for e in events_list],
                    'intent' : intent,
                    'changes': changes,
                }

            return self._apply_modify(events_list[0], intent, changes)

        else:
            return {
                'status' : 'error',
                'message': '入力の意図を読み取れませんでした。予定の追加・検索・変更・削除のいずれかを入力してください。',
            }

    def force_add_event(self, user_id, event_data):
        """警告を無視してイベントを作成する（proposed_event を直接受け取る）。"""
        start_dt = self._parse_datetime(event_data['start_datetime'])
        end_dt   = self._parse_datetime(event_data['end_datetime']) if event_data.get('end_datetime') else None
        return self._create_event_from_data(user_id, event_data, start_dt, end_dt)

    def _create_event_from_data(self, user_id, event_data, start_dt, end_dt):
        """event_data dict から Event を作成して辞書を返す。"""
        event = Event.objects.create(
            user_id        = user_id,
            title          = event_data.get('title', '予定'),
            start_datetime = start_dt,
            end_datetime   = end_dt,
            event_type     = event_data.get('event_type', 'activity'),
            priority       = event_data.get('priority', 3),
            is_all_day     = event_data.get('is_all_day', False),
            category       = event_data.get('category'),
        )
        return {'status': 'success', 'action': 'add', 'event_id': event.id, 'event': self._event_to_dict(event)}

    def get_events(self, user_id, period_text):
        """期間指定でイベントを取得。"""
        range_data = self.ai_service.parse_period(period_text)
        start_dt   = self._parse_datetime(range_data['start'])
        end_dt     = self._parse_datetime(range_data['end'])

        events = Event.objects.filter(
            user_id            = user_id,
            start_datetime__gte= start_dt,
            start_datetime__lte= end_dt,
        ).order_by('start_datetime')

        return [self._event_to_dict(e) for e in events]

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _check_conflicts(self, user_id, start_dt, end_dt, new_event_data, warning_level='standard'):
        """
        衝突チェック。
        Returns:
            dict: { 'conflicts': [...], 'warnings': [...] }
              conflicts – 時間が完全重複する activity 同士 → 追加不可
              warnings  – block 期間中の追加、終日イベントとの重複 → 確認が必要
        """
        if not end_dt:
            return {'conflicts': [], 'warnings': []}

        new_is_all_day = new_event_data.get('is_all_day', False)
        new_event_type = new_event_data.get('event_type', 'activity')
        new_category   = new_event_data.get('category')

        candidates = Event.objects.filter(user_id=user_id).filter(
            Q(start_datetime__lt=end_dt, end_datetime__gt=start_dt)
            | Q(start_datetime__gte=start_dt, start_datetime__lt=end_dt)
            | Q(start_datetime__lte=start_dt, end_datetime__gte=end_dt)
        )

        hard, soft = [], []
        for existing in candidates:
            kind = self._get_conflict_type(
                new_event_type, new_is_all_day, new_category, existing, warning_level
            )
            if kind == 'conflict':
                hard.append(existing)
            elif kind == 'warning':
                soft.append(existing)

        return {'conflicts': hard, 'warnings': soft}

    def _get_conflict_type(self, new_type, new_all_day, new_category, existing, warning_level='standard'):
        """
        Returns:
            'conflict' – 時間重複 (activity vs activity、両方とも時間指定)
            'warning'  – ブロック期間 / 終日イベントとの重複
            None       – 問題なし (同カテゴリ等)

        warning_level:
            'gentle'   – hard conflict のみ。soft warning は全て無視。
            'standard' – 標準（block/all-day → warning）
            'strict'   – 加えて deadline 同士の重複も warning
        """
        # 同カテゴリ例外
        if new_category and existing.category:
            if set(new_category) & set(existing.category):
                return None

        # 時間指定 activity 同士の完全重複 → conflict (全レベル共通)
        if (new_type == 'activity' and not new_all_day
                and existing.event_type == 'activity' and not existing.is_all_day):
            return 'conflict'

        # gentle: soft warning は全て無視
        if warning_level == 'gentle':
            return None

        # block 期間との重複 → warning
        if existing.event_type == 'block' or new_type == 'block':
            return 'warning'

        # 終日イベントとの重複 → warning
        if new_all_day or existing.is_all_day:
            return 'warning'

        # strict: deadline 絡みも warning
        if warning_level == 'strict':
            if existing.event_type == 'deadline' or new_type == 'deadline':
                return 'warning'

        return None

    def _parse_datetime(self, datetime_str):
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        return timezone.make_aware(dt, timezone.get_current_timezone())

    def _event_to_dict(self, event):
        start_local = timezone.localtime(event.start_datetime)
        end_local   = timezone.localtime(event.end_datetime) if event.end_datetime else None

        return {
            'id'        : event.id,
            'user_id'   : event.user_id,
            'title'     : event.title,
            'start'     : start_local.strftime('%Y-%m-%d %H:%M'),
            'end'       : end_local.strftime('%Y-%m-%d %H:%M') if end_local else None,
            'type'      : event.event_type,
            'priority'  : event.priority,
            'is_all_day': event.is_all_day,
            'category'  : event.category,
            'created_at': timezone.localtime(event.created_at).strftime('%Y-%m-%d %H:%M:%S'),
        }
