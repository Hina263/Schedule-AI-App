# AI Todo App

自然言語で予定を登録・取得できるAI搭載スケジュール管理APIです。Anthropic Claudeを利用して、「明日18時から会議」といった日本語の入力から日時や種別を自動解析し、重複チェックやカテゴリ分類を行います。

## 機能概要

- **自然言語での予定登録**: 「明日14時から16時まで会議」「来週月曜の締め切り」といった日本語の入力から、タイトル・日時・種別・優先度・カテゴリを自動抽出
- **期間指定での予定取得**: 「今日」「今週」などの期間表現から該当イベントを取得
- **衝突検知**: 新規予定と既存予定の重複を検出し、AIによる警告メッセージを生成
- **イベント種別**: アクティビティ（時間指定）、ブロック期間、締切の3種類に対応

## 技術スタック

- **バックエンド**: Django 5.1
- **API**: Django REST Framework
- **データベース**: PostgreSQL
- **AI**: Anthropic Claude (claude-sonnet-4-20250514)

## 必要条件

- Python 3.12
- PostgreSQL

## セットアップ

### 1. 仮想環境の作成と有効化

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存パッケージのインストール

```bash
pip install django djangorestframework django-cors-headers anthropic python-dotenv psycopg2-binary
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

# APIキー（Anthropic）
ANTHROPIC_API_KEY=your-api-key-here

# Django
SECRET_KEY=your-secret-key
DEBUG=True
```

### 4. データベースの準備

PostgreSQLでデータベースを作成した後、マイグレーションを実行します。

```bash
python manage.py migrate
```

### 5. サーバーの起動

```bash
python manage.py runserver
```

APIは `http://127.0.0.1:8000` で起動します。

## API エンドポイント

### イベント追加

`POST /api/schedule/add-event/`

自然言語で予定を登録します。

**リクエストBody:**

```json
{
  "input": "明日14時から16時まで会議",
  "user_id": "default_user"
}
```

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| input | ○ | 自然言語での予定入力（最大500文字） |
| user_id | - | ユーザーID（省略時: default_user） |

**成功時レスポンス:**

```json
{
  "status": "success",
  "event_id": 1,
  "event": {
    "id": 1,
    "user_id": "default_user",
    "title": "会議",
    "start": "2025-02-21 14:00",
    "end": "2025-02-21 16:00",
    "type": "activity",
    "priority": 3,
    "is_all_day": false,
    "category": ["会議"]
  }
}
```

**衝突時レスポンス:**

```json
{
  "status": "conflict",
  "conflicts": [
    {
      "id": 1,
      "title": "既存の予定",
      "start": "...",
      "end": "...",
      "warning_message": "この日はXXがありますが、時間は問題ありませんか?"
    }
  ],
  "proposed_event": { ... }
}
```

### イベント取得

`POST /api/schedule/get-events/`

期間指定で予定を取得します。

**リクエストBody:**

```json
{
  "period": "今週",
  "user_id": "default_user"
}
```

| パラメータ | 必須 | 説明 |
|-----------|------|------|
| period | - | 期間（例: 今日、明日、今週、デフォルト: 今日） |
| user_id | - | ユーザーID（省略時: default_user） |

**レスポンス:**

```json
{
  "status": "success",
  "events": [
    {
      "id": 1,
      "user_id": "default_user",
      "title": "会議",
      "start": "2025-02-21 14:00",
      "end": "2025-02-21 16:00",
      "type": "activity",
      "priority": 3,
      "is_all_day": false,
      "category": ["会議"]
    }
  ]
}
```

## イベント種別

| 種別 | 説明 | 例 |
|------|------|------|
| activity | 時間指定の予定 | 会議、デート |
| block | 複数日にまたがる期間 | 合宿、テスト期間 |
| deadline | 締切 | レポート提出 |

## プロジェクト構成

```
ai-todo-app/
├── config/           # Django設定
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── schedule/         # スケジュールアプリ
│   ├── models.py     # Eventモデル
│   ├── views.py      # APIビュー
│   ├── serializers.py
│   ├── services/
│   │   ├── ai_service.py      # AI解析（Claude）
│   │   └── schedule_service.py # ビジネスロジック
│   └── migrations/
├── manage.py
└── .env
```

## 今後の展望

本プロジェクトはAPIとしての基盤実装を中心に開発していますが、今後は以下のような機能拡張を検討しています。

- **フロントエンドの実装**
  WebまたはモバイルアプリとしてのUIを実装し、より直感的に操作できるインターフェースを提供予定です。音声入力との連携も強化し、「話すだけで予定が登録できる体験」を実現します。
- **リマインダー・通知機能の追加**
  指定時間前の通知や、重要度に応じたリマインド機能を実装し、実用性をさらに向上させます。
- **学習機能の強化**
  ユーザーの登録傾向や行動パターンをもとに、優先度やカテゴリの自動補正、予定時間の提案などを行う「より秘書らしい」支援機能の実装を目指します。
- **メモ機能との統合**
  スケジュールとは別に、自然言語で保存できるメモ機能を追加し、タスク・予定・メモを横断的に扱える設計への拡張を検討しています。
- **外部カレンダーとの連携**
  Google Calendarなどの外部サービスとの同期機能を実装し、既存のスケジュール管理環境との統合を目指します。
- **パフォーマンスと精度の最適化**
  データ量増加に伴う検索・解析の最適化、プロンプト設計の改善による解析精度向上を継続的に行います。

## ライセンス

MIT
