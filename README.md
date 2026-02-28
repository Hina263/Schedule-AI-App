
# AI スケジュール管理アプリ

自然言語で予定を登録・取得・削除できる AI 搭載スケジュール管理アプリです。
Anthropic Claude を利用して「明日 18 時から会議」といった日本語入力から日時・種別を自動解析します。
メール/パスワード認証および Google アカウント認証に対応したモバイルフレンドリーな Web アプリです。

---

## 機能概要

| 機能 | 説明 |
|------|------|
| 自然言語での予定登録 | 日本語テキストからタイトル・日時・種別・優先度・カテゴリを AI が自動抽出 |
| 期間指定での予定取得 | 「今週」「来月」などの期間表現から該当イベントを一覧表示 |
| AI 検索 | 自然言語で期間や条件を指定して予定を検索 |
| 衝突検知 | 新規予定と既存予定の重複を検出し警告 |
| 予定削除 | 各画面からワンタップで予定を削除 |
| ユーザー認証 | メール/パスワード + Google アカウントでのログイン |
| カレンダービュー | 今日 / 週間 / 月間の 3 タブ表示、日タップでドロワー表示 |

---

## 技術スタック

### バックエンド
| ライブラリ | バージョン | 用途 |
|-----------|-----------|------|
| Django | 5.1.6 | Web フレームワーク |
| Django REST Framework | 3.16.1 | REST API |
| djangorestframework-simplejwt | 5.5.1 | JWT 認証 |
| django-cors-headers | 4.9.0 | CORS 設定 |
| anthropic | 0.79.0 | Claude AI による自然言語解析 |
| google-auth | 2.48.0 | Google OAuth トークン検証 |
| psycopg2-binary | 2.9.11 | PostgreSQL 接続 |
| python-dotenv | 1.2.1 | 環境変数管理 |
| requests | 2.32.3 | HTTP クライアント |

### フロントエンド
- 純粋な HTML / CSS / JavaScript（フレームワーク不使用）
- モバイルファースト設計（max-width 480px）
- ボトムナビゲーション、ボトムシートドロワー

### データベース
- PostgreSQL

---

## 必要条件

- Python 3.12
- PostgreSQL

---

## セットアップ

### 1. 仮想環境の作成と有効化

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、以下を設定してください。

```env
# データベース
DB_NAME=todo_app
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# API キー（Anthropic）
ANTHROPIC_API_KEY=your-api-key-here

# Django
SECRET_KEY=your-secret-key
DEBUG=True

# Google OAuth（Google Sign-In を使う場合）
GOOGLE_CLIENT_ID=your-google-client-id
```

### 4. データベースの準備

PostgreSQL でデータベースを作成した後、マイグレーションを実行します。

```bash
python manage.py migrate
```

### 5. サーバーの起動

```bash
python manage.py runserver
```

ブラウザで `http://127.0.0.1:8000` にアクセスするとログイン画面が表示されます。

---

## 画面構成

| URL | ファイル | 説明 |
|-----|---------|------|
| `/` | — | `/login/` へリダイレクト |
| `/login/` | `frontend/login.html` | ログイン画面（メール/パスワード + Google） |
| `/register/` | `frontend/register.html` | 新規登録画面 |
| `/home/` | `frontend/home.html` | カレンダー（今日 / 週間 / 月間タブ） |
| `/input/` | `frontend/input.html` | 予定入力 + AI 検索 |
| `/result/` | `frontend/result.html` | AI 検索結果一覧 |

### home.html の主な機能
- **今日タブ**: 当日の予定を時系列カードで表示
- **週間タブ**: 7 列グリッドで週の予定を俯瞰。日付をタップするとボトムシートドロワーで全予定を表示
- **月間タブ**: カレンダー形式で月の予定を表示。日付タップで同様のドロワー表示
- **削除ボタン**: 各イベントカードに削除ボタンあり。削除後はキャッシュとグリッドを即時更新

---

## API エンドポイント

### 認証 API

#### 新規登録
`POST /api/auth/register/`

```json
{
  "username": "taro",
  "email": "taro@example.com",
  "password": "password123"
}
```

**レスポンス:**
```json
{
  "user": { "id": 1, "username": "taro", "email": "taro@example.com" },
  "tokens": { "access": "...", "refresh": "..." }
}
```

#### ログイン
`POST /api/auth/login/`

```json
{
  "email": "taro@example.com",
  "password": "password123"
}
```

#### Google ログイン
`POST /api/auth/google/`

```json
{ "credential": "<Google ID Token>" }
```

#### ログアウト
`POST /api/auth/logout/`

```json
{ "refresh": "<refresh_token>" }
```

#### ユーザー情報取得
`GET /api/auth/me/`

---

### スケジュール API

#### イベント追加
`POST /api/schedule/add-event/`

```json
{
  "input": "明日14時から16時まで会議",
  "user_id": "user1"
}
```

**成功レスポンス:**
```json
{
  "status": "success",
  "event_id": 1,
  "event": {
    "id": 1,
    "title": "会議",
    "start": "2026-03-01 14:00",
    "end": "2026-03-01 16:00",
    "type": "activity",
    "priority": 3,
    "is_all_day": false,
    "category": ["会議"]
  }
}
```

**衝突レスポンス:**
```json
{
  "status": "conflict",
  "conflicts": [{ "id": 2, "title": "既存の予定", "warning_message": "..." }],
  "proposed_event": { ... }
}
```

#### イベント取得
`POST /api/schedule/get-events/`

```json
{
  "period": "今週",
  "user_id": "user1"
}
```

**レスポンス:**
```json
{
  "status": "success",
  "events": [ { "id": 1, "title": "会議", "start": "...", ... } ]
}
```

#### イベント削除
`DELETE /api/schedule/events/{event_id}/`

```json
{ "user_id": "user1" }
```

**レスポンス:**
```json
{ "status": "success", "message": "削除しました" }
```

---

## イベント種別

| 種別 | 説明 | 例 |
|------|------|-----|
| activity | 時間指定の予定 | 会議、ランチ |
| block | 複数日にまたがる期間 | 合宿、テスト期間 |
| deadline | 締切 | レポート提出 |

---

## プロジェクト構成

```
ai-todo-app/
├── config/                    # Django 設定
│   ├── settings.py            # アプリ設定（JWT, Google OAuth, CORS 等）
│   ├── urls.py                # ルーティング（ページ + API）
│   └── wsgi.py
│
├── schedule/                  # スケジュールアプリ
│   ├── models.py              # Event モデル
│   ├── views.py               # AddEventView / GetEventsView / DeleteEventView
│   ├── serializers.py
│   ├── urls.py                # /add-event/ /get-events/ /events/<id>/
│   └── services/
│       ├── ai_service.py      # Claude による自然言語解析
│       └── schedule_service.py # ビジネスロジック・衝突検知
│
├── users/                     # 認証アプリ
│   ├── models.py              # UserProfile（Google ID 紐付け）
│   ├── views.py               # LoginPage / RegisterPage / 各認証 API
│   └── urls.py                # /register/ /login/ /logout/ /google/ /me/
│
├── frontend/                  # HTML フロントエンド
│   ├── login.html             # ログイン画面
│   ├── register.html          # 新規登録画面
│   ├── home.html              # カレンダー（今日/週/月タブ）
│   ├── input.html             # 予定入力 + AI 検索
│   └── result.html            # AI 検索結果
│
├── requirements.txt
├── manage.py
└── .env                       # 環境変数（Git 管理外）
```

---

## 今後の展望

- **リマインダー・通知機能**: 予定時刻前のプッシュ通知・メール通知
- **ユーザー認証の統合強化**: JWT トークンを API リクエストに自動付与し、各ユーザーのデータを完全に分離
- **外部カレンダー連携**: Google Calendar との双方向同期
- **繰り返し予定**: 毎週・毎月などの定期予定登録
- **AI 学習機能**: ユーザーの登録傾向から優先度・カテゴリを自動補正

---

## ライセンス

MIT
