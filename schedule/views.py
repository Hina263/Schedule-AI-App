from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import EventCreateSerializer, EventListSerializer
from .services.schedule_service import ScheduleService
from .models import Event
import anthropic

schedule_service = ScheduleService()

class AddEventView(APIView):
    """イベント追加API"""

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = schedule_service.create_event(
                user_id=serializer.validated_data.get('user_id', 'default_user'),
                natural_input=serializer.validated_data['input']
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
    """イベント取得API"""

    def post(self, request):
        serializer = EventListSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'status': 'error', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            events = schedule_service.get_events(
                user_id=serializer.validated_data.get('user_id', 'default_user'),
                period_text=serializer.validated_data.get('period', '今日')
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


class DeleteEventView(APIView):
    """イベント削除API"""

    def delete(self, request, event_id):
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
