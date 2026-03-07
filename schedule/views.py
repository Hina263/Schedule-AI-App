from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EventCreateSerializer, EventListSerializer
from .services.schedule_service import ScheduleService
from .models import Event, UserSettings
import anthropic

schedule_service = ScheduleService()


class AddEventView(APIView):
    """イベント追加 API"""

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            force = bool(request.data.get('force', False))
            result = schedule_service.create_event(
                user_id       = serializer.validated_data.get('user_id', 'default_user'),
                natural_input = serializer.validated_data['input'],
                force         = force,
            )
            return Response(result, status=status.HTTP_200_OK)

        except anthropic.APIConnectionError:
            return Response(
                {'status': 'error', 'message': 'AI APIへの接続に失敗しました。ネットワークを確認してください。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except anthropic.AuthenticationError:
            return Response(
                {'status': 'error', 'message': 'APIキーが無効です。'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except ValueError as e:
            return Response(
                {'status': 'error', 'message': f'AIのレスポンスの解析に失敗しました: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'予期しないエラーが発生しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetEventsView(APIView):
    """イベント取得 API"""

    def post(self, request):
        serializer = EventListSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            events = schedule_service.get_events(
                user_id     = serializer.validated_data.get('user_id', 'default_user'),
                period_text = serializer.validated_data.get('period', '今日'),
            )
            return Response(
                {'status': 'success', 'events': events},
                status=status.HTTP_200_OK
            )

        except anthropic.APIConnectionError:
            return Response(
                {'status': 'error', 'message': 'AI APIへの接続に失敗しました。ネットワークを確認してください。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except anthropic.AuthenticationError:
            return Response(
                {'status': 'error', 'message': 'APIキーが無効です。'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except ValueError as e:
            return Response(
                {'status': 'error', 'message': f'AIのレスポンスの解析に失敗しました: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'予期しないエラーが発生しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EventDetailView(APIView):
    """イベント詳細 API（削除・編集）"""

    def delete(self, request, event_id):
        """イベント削除"""
        user_id = request.data.get('user_id', 'default_user')
        try:
            event = Event.objects.get(id=event_id, user_id=user_id)
            event.delete()
            return Response({'status': 'success', 'message': '削除しました'})
        except Event.DoesNotExist:
            return Response(
                {'status': 'error', 'message': 'イベントが見つかりません'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, event_id):
        """イベント編集（タイトル・開始・終了日時）"""
        user_id        = request.data.get('user_id', 'default_user')
        title          = request.data.get('title')
        start_datetime = request.data.get('start_datetime')
        end_datetime   = request.data.get('end_datetime')

        try:
            updated = schedule_service.update_event(
                event_id       = event_id,
                user_id        = user_id,
                title          = title,
                start_datetime = start_datetime,
                end_datetime   = end_datetime,
            )
            return Response({'status': 'success', 'event': updated})

        except ValueError as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'更新に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSettingsView(APIView):
    """ユーザー設定 API"""

    def get(self, request):
        user_id = request.query_params.get('user_id', 'default_user')
        obj, _ = UserSettings.objects.get_or_create(user_id=user_id)
        return Response({'status': 'success', 'settings': obj.to_dict()})

    def patch(self, request):
        user_id = request.data.get('user_id', 'default_user')
        obj, _ = UserSettings.objects.get_or_create(user_id=user_id)

        fields = [
            'default_duration_hours',
            'warning_level',
            'remind_minutes_before',
            'remind_day_before',
            'remind_days_before_deadline',
        ]
        for field in fields:
            if field in request.data:
                setattr(obj, field, request.data[field])
        obj.save()

        return Response({'status': 'success', 'settings': obj.to_dict()})


class CommandView(APIView):
    """統合コマンド API（追加/検索/変更/削除を一つのエンドポイントで処理）"""

    def post(self, request):
        user_id = request.data.get('user_id', 'default_user')

        # 強制追加（warning 確認後）
        force_event = request.data.get('force_event')
        if force_event is not None:
            try:
                result = schedule_service.force_add_event(user_id, force_event)
                return Response(result, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {'status': 'error', 'message': f'追加に失敗しました: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # 複数マッチ確定（update/delete 選択後）
        confirm_event_id = request.data.get('confirm_event_id')
        if confirm_event_id is not None:
            intent  = request.data.get('intent', 'update')
            changes = request.data.get('changes', {})
            try:
                result = schedule_service.apply_modify_to_event(
                    event_id=int(confirm_event_id),
                    user_id=user_id,
                    intent=intent,
                    changes=changes,
                )
                return Response(result, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(
                    {'status': 'error', 'message': str(e)},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'status': 'error', 'message': f'操作に失敗しました: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # 通常フロー
        natural_input = request.data.get('input', '').strip()
        if not natural_input:
            return Response(
                {'status': 'error', 'message': '入力内容を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = schedule_service.execute_command(
                user_id       = user_id,
                natural_input = natural_input,
            )
            return Response(result, status=status.HTTP_200_OK)

        except anthropic.APIConnectionError:
            return Response(
                {'status': 'error', 'message': 'AI APIへの接続に失敗しました。ネットワークを確認してください。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except anthropic.AuthenticationError:
            return Response(
                {'status': 'error', 'message': 'APIキーが無効です。'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except ValueError as e:
            return Response(
                {'status': 'error', 'message': f'AIのレスポンスの解析に失敗しました: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'予期しないエラーが発生しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModifyEventView(APIView):
    """自然言語での予定変更・削除 API"""

    def post(self, request):
        user_id          = request.data.get('user_id', 'default_user')
        confirm_event_id = request.data.get('confirm_event_id')

        # 選択確定リクエスト: AI解析をスキップして直接実行
        if confirm_event_id is not None:
            intent  = request.data.get('intent', 'update')
            changes = request.data.get('changes', {})
            try:
                result = schedule_service.apply_modify_to_event(
                    event_id = int(confirm_event_id),
                    user_id  = user_id,
                    intent   = intent,
                    changes  = changes,
                )
                return Response(result, status=status.HTTP_200_OK)
            except ValueError as e:
                return Response(
                    {'status': 'error', 'message': str(e)},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'status': 'error', 'message': f'操作に失敗しました: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # 通常フロー: 自然言語解析
        natural_input = request.data.get('input', '').strip()
        if not natural_input:
            return Response(
                {'status': 'error', 'message': '入力内容を指定してください'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = schedule_service.modify_event_by_natural_language(
                user_id       = user_id,
                natural_input = natural_input,
            )
            return Response(result, status=status.HTTP_200_OK)

        except anthropic.APIConnectionError:
            return Response(
                {'status': 'error', 'message': 'AI APIへの接続に失敗しました。ネットワークを確認してください。'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except anthropic.AuthenticationError:
            return Response(
                {'status': 'error', 'message': 'APIキーが無効です。'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except ValueError as e:
            return Response(
                {'status': 'error', 'message': f'AIのレスポンスの解析に失敗しました: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'予期しないエラーが発生しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
