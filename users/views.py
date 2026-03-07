from django.shortcuts import render
from django.views import View
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import UserProfile


# ------------------------------------------------------------------ #
#  ページビュー（Django テンプレートとして HTML を配信）               #
# ------------------------------------------------------------------ #

class LoginPage(View):
    def get(self, request):
        return render(request, 'login.html', {
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })


class RegisterPage(View):
    def get(self, request):
        return render(request, 'register.html')


# ------------------------------------------------------------------ #
#  共通ヘルパー                                                        #
# ------------------------------------------------------------------ #

def _get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def _user_data(user):
    return {'id': user.id, 'username': user.username, 'email': user.email}


# ------------------------------------------------------------------ #
#  認証 API                                                            #
# ------------------------------------------------------------------ #

class RegisterView(APIView):
    """メールアドレスで新規登録"""

    def post(self, request):
        username = request.data.get('username', '').strip()
        email    = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not username or not email or not password:
            return Response({'error': '全ての項目を入力してください'}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'このユーザー名は既に使用されています'}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'このメールアドレスは既に登録されています'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user)

        return Response({
            'user': _user_data(user),
            'tokens': _get_tokens(user),
        }, status=201)


class LoginView(APIView):
    """メールアドレス + パスワードでログイン"""

    def post(self, request):
        email    = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response({'error': 'メールアドレスとパスワードを入力してください'}, status=400)

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'メールアドレスまたはパスワードが正しくありません'}, status=401)

        user = authenticate(username=user_obj.username, password=password)
        if not user:
            return Response({'error': 'メールアドレスまたはパスワードが正しくありません'}, status=401)

        return Response({
            'user': _user_data(user),
            'tokens': _get_tokens(user),
        })


class LogoutView(APIView):
    """ログアウト（クライアント側でトークンを削除）"""

    def post(self, request):
        return Response({'message': 'ログアウトしました'})


class GoogleLoginView(APIView):
    """Google ID トークンを検証してログイン / 新規登録"""

    def post(self, request):
        credential = request.data.get('credential')
        if not credential:
            return Response({'error': 'Google 認証情報が必要です'}, status=400)

        if not settings.GOOGLE_CLIENT_ID:
            return Response({'error': 'Google OAuth が設定されていません'}, status=503)

        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as e:
            return Response({'error': f'Google 認証に失敗しました: {str(e)}'}, status=401)

        google_id = idinfo['sub']
        email     = idinfo.get('email', '')
        name      = idinfo.get('name', email.split('@')[0])

        # 既存プロフィール → そのユーザー
        try:
            profile = UserProfile.objects.get(google_id=google_id)
            user = profile.user
        except UserProfile.DoesNotExist:
            # 同メールのユーザーがあれば紐付け、なければ新規作成
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                base = email.split('@')[0]
                uname, n = base, 1
                while User.objects.filter(username=uname).exists():
                    uname = f'{base}{n}'; n += 1

                user = User.objects.create_user(username=uname, email=email)
                user.first_name = name
                user.set_unusable_password()
                user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.google_id = google_id
            profile.save()

        return Response({
            'user': _user_data(user),
            'tokens': _get_tokens(user),
        })


class MeView(APIView):
    """ログイン中のユーザー情報を返す"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_data(request.user))


class ChangePasswordView(APIView):
    """パスワード変更"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')

        if not old_password or not new_password:
            return Response({'error': '現在のパスワードと新しいパスワードを入力してください'}, status=400)

        if len(new_password) < 8:
            return Response({'error': '新しいパスワードは8文字以上にしてください'}, status=400)

        user = authenticate(username=request.user.username, password=old_password)
        if not user:
            return Response({'error': '現在のパスワードが正しくありません'}, status=401)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'パスワードを変更しました'})


class DeleteAccountView(APIView):
    """アカウント削除"""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password', '')

        if not password:
            return Response({'error': 'パスワードを入力してください'}, status=400)

        user = authenticate(username=request.user.username, password=password)
        if not user:
            return Response({'error': 'パスワードが正しくありません'}, status=401)

        user.delete()
        return Response({'message': 'アカウントを削除しました'})
