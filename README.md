
# AI スケジュール管理アプリ

自然言語で予定を登録・検索・変更・削除できる AI 搭載スケジュール管理アプリです。
Anthropic Claude を利用して「明日 18 時から会議」「3/4 の会議を 12 時からに変更」といった日本語入力を解析します。
メール/パスワード認証および Google アカウント認証に対応したモバイルフレンドリーな Web アプリです。

---

## 機能概要

| 機能 | 説明 |
|------|------|
| AI 統合コマンド | 追加・検索・変更・削除を 1 つのテキストボックスから自然言語で実行 |
| 音声入力 | 🎤 マイクボタンで日本語音声入力（Web Speech API） |
| 衝突検知 | 新規予定と既存予定の重複を検出し確認を促す |
| 自然言語での変更・削除 | 「〇月〇日の〇〇を変更/削除して」で AI が対象を特定 |
| 複数マッチ選択 | 候補が複数ある場合は一覧から選択して実行 |
| カレンダービュー | 今日 / 月間タブ表示、日付タップでドロワー表示、予定の編集・削除が可能 |
| 個人設定 | デフォルト所要時間・注意喚起レベル・リマインド通知の設定 |
| ユーザー認証 | メール/パスワード + Google アカウントでのログイン |
| パスワード変更・アカウント削除 | 認証済みユーザーによる自己管理 |

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
- Web Speech API による音声入力（Chrome 推奨）

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
| `/home/` | `frontend/home.html` | カレンダー（今日 / 月間タブ） |
| `/input/` | `frontend/input.html` | AI 統合入力（追加/検索/変更/削除 + 音声入力） |
| `/result/` | `frontend/result.html` | AI 検索結果一覧（編集・削除あり） |
| `/account/` | `frontend/account.html` | アカウント管理・個人設定 |

### home.html の主な機能
- **今日タブ**: 当日の予定を時系列カードで表示、近日締切も表示
- **月間タブ**: カレンダー形式で月の予定を表示。日付タップでドロワー表示
- **編集ボタン**: 各イベントカードの ✏️ から開始/終了日時・タイトルを編集
- **削除ボタン**: 各イベントカードの 🗑️ から削除。キャッシュとグリッドを即時更新

### input.html の主な機能
- **AIアシスタント統合カード**: 1 つのテキストボックスで追加・検索・変更・削除をすべて処理
- **音声入力**: 🎤 マイクボタンで話しかけるだけで入力
- **検索結果インライン表示**: 検索結果をページ内に直接表示

### account.html の主な機能
- **個人設定**: デフォルト所要時間（1/2/3 時間）・注意喚起レベル（優しい/標準/厳しめ）
- **通知設定**: 開始前リマインド・1日前通知・締切前通知（DB 保存）
- **パスワード変更**: 旧パスワード確認後に変更
- **ログアウト / アカウント削除**

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

#### パスワード変更
`POST /api/auth/change-password/`  *(要: `Authorization: Bearer <token>`)*

```json
{ "old_password": "...", "new_password": "..." }
```

#### アカウント削除
`DELETE /api/auth/delete/`  *(要: `Authorization: Bearer <token>`)*

```json
{ "password": "..." }
```

---

### スケジュール API

#### 統合コマンド（推奨）
`POST /api/schedule/command/`

追加・検索・変更・削除を 1 つのエンドポイントで処理します。

```json
{ "input": "明日18時から会議", "user_id": "user1" }
```

**intent=add 成功レスポンス:**
```json
{ "status": "success", "action": "add", "event_id": 1, "event": { ... } }
```

**intent=search レスポンス:**
```json
{ "status": "success", "action": "search", "period": "今週", "events": [ ... ] }
```

**intent=update/delete 成功:**
```json
{ "status": "success", "action": "update", "message": "「会議」を更新しました", "event": { ... } }
```

**複数マッチ:**
```json
{ "status": "multiple", "events": [ ... ], "intent": "update", "changes": { ... } }
```

**警告（確認が必要な場合）:** `status: "warning"` → `force_event` を付けて再送で強制追加。

**複数マッチ確定（選択後）:**
```json
{ "user_id": "user1", "confirm_event_id": 3, "intent": "update", "changes": { "start_datetime": "2026-03-04 12:00" } }
```

**警告を無視して強制追加:**
```json
{ "user_id": "user1", "force_event": { <proposed_event オブジェクト> } }
```

---

#### イベント追加（個別）
`POST /api/schedule/add-event/`

```json
{ "input": "明日14時から16時まで会議", "user_id": "user1" }
```

`force: true` を付けると警告を無視して強制追加。

#### イベント取得
`POST /api/schedule/get-events/`

```json
{ "period": "今週", "user_id": "user1" }
```

#### イベント編集
`PATCH /api/schedule/events/{event_id}/`

```json
{ "user_id": "user1", "title": "新タイトル", "start_datetime": "2026-03-10 14:00", "end_datetime": "2026-03-10 15:00" }
```

#### イベント削除
`DELETE /api/schedule/events/{event_id}/`

```json
{ "user_id": "user1" }
```

#### 自然言語での変更・削除
`POST /api/schedule/modify-event/`

```json
{ "input": "3/4の会議を12時からに変更", "user_id": "user1" }
```

#### ユーザー設定
`GET /api/schedule/settings/?user_id=user1`
`PATCH /api/schedule/settings/`

```json
{
  "user_id": "user1",
  "default_duration_hours": 2,
  "warning_level": "strict",
  "remind_minutes_before": 30,
  "remind_day_before": true,
  "remind_days_before_deadline": 3
}
```

---

## イベント種別

| 種別 | 説明 | 例 |
|------|------|-----|
| activity | 時間指定の予定 | 会議、ランチ |
| block | 複数日にまたがる期間 | 合宿、テスト期間 |
| deadline | 締切 | レポート提出 |

---

## 注意喚起レベル

| レベル | 動作 |
|--------|------|
| gentle（優しい） | 時間の完全重複のみ警告。ブロック期間・終日イベントとの重複は無視 |
| standard（標準） | 上記に加え、ブロック期間・終日イベントとの重複も警告 |
| strict（厳しめ） | 上記に加え、締切同士の重複も警告 |

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
│   ├── models.py              # Event / UserSettings モデル
│   ├── views.py               # AddEventView / GetEventsView / EventDetailView
│   │                          # ModifyEventView / CommandView / UserSettingsView
│   ├── serializers.py
│   ├── urls.py                # add-event/ get-events/ events/<id>/ modify-event/ command/ settings/
│   └── services/
│       ├── ai_service.py      # Claude による自然言語解析（統合コマンド対応）
│       └── schedule_service.py # ビジネスロジック・衝突検知・統合コマンド実行
│
├── users/                     # 認証アプリ
│   ├── models.py              # UserProfile（Google ID 紐付け）
│   ├── views.py               # LoginPage / RegisterPage / 各認証 API
│   │                          # ChangePasswordView / DeleteAccountView
│   └── urls.py                # register/ login/ logout/ google/ me/ change-password/ delete/
│
├── frontend/                  # HTML フロントエンド
│   ├── login.html             # ログイン画面
│   ├── register.html          # 新規登録画面
│   ├── home.html              # カレンダー（今日/月間タブ）
│   ├── input.html             # AI 統合入力 + 音声入力
│   ├── result.html            # AI 検索結果（編集・削除あり）
│   └── account.html           # アカウント管理・個人設定
│
├── requirements.txt
├── manage.py
└── .env                       # 環境変数（Git 管理外）
```

---

## 今後の展望

- **リマインダー通知の実装**: 設定済みの通知条件に基づくプッシュ通知・メール送信
- **外部カレンダー連携**: Google Calendar との双方向同期
- **繰り返し予定**: 毎週・毎月などの定期予定登録
- **AI 学習機能**: ユーザーの登録傾向から優先度・カテゴリを自動補正

---

## ライセンス

MIT
