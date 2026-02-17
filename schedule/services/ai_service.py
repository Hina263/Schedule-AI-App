import anthropic
import json
from django.conf import settings
from django.utils import timezone

class AIService:
    """AI解析サービス"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )
    
    def parse_natural_language(self, natural_input):
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M')
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""以下の自然言語入力を解析して、JSON形式で予定情報を抽出してください。

入力: {natural_input}
現在時刻: {current_time}

以下の形式で返してください:
{{
    "title": "予定のタイトル",
    "start_datetime": "YYYY-MM-DD HH:MM",
    "end_datetime": "YYYY-MM-DD HH:MM",
    "event_type": "activity",
    "priority": 3,
    "is_all_day": false,
    "category": ["カテゴリ1", "カテゴリ2"]
}}

注意事項:
- start_datetimeは必須
- end_datetimeが不明な場合はstart_datetimeの1時間後にしてください
- event_typeは以下のいずれか:
  * "activity": 時間指定の予定(会議、デートなど)
  * "block": 期間予定(合宿、テスト期間など)
  * "deadline": 締切
- priorityは1(最重要)〜5(最低)の整数
- is_all_dayは終日イベントの場合true、時間指定の場合false
- categoryは予定に関連するカテゴリを複数の配列で返してください
  例: "テスト勉強" → ["テスト", "勉強"]
  例: "会議" → ["会議"]
  例: "合宿" → ["合宿", "宿泊"]


判断基準:
- 「終日」「一日中」などのキーワードがあればis_all_day=true
- 「〜期間」「合宿」「〜から〜まで」などの複数日にまたがる予定はevent_type="block"かつis_all_day=true
- event_type="block"の場合、start_datetimeは開始日の00:00、end_datetimeは終了日の23:59にしてください
- 明確な開始・終了時刻があればevent_type="activity"

JSONのみを返してください。説明文は不要です。"""
            }]
        )
        
        response_text = message.content[0].text
        return self._extract_json(response_text)
    
    def parse_period(self, period_text):
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M')
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""「{period_text}」という期間指定を日時範囲に変換してください。
現在: {current_time}

以下の形式で返してください:
{{
    "start": "YYYY-MM-DD 00:00",
    "end": "YYYY-MM-DD 23:59"
}}

例:
- "今日" → 今日の0時から23時59分
- "明日" → 明日の0時から23時59分
- "今週" → 今週月曜0時から日曜23時59分

JSONのみを返してください。"""
            }]
        )
        
        response_text = message.content[0].text
        return self._extract_json(response_text)
    
    def generate_conflict_message(self, new_event, existing_event):
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"""以下の2つの予定が重複しています。適切な警告メッセージを生成してください。

新しい予定:
- タイトル: {new_event['title']}
- 時間: {new_event['start']} 〜 {new_event.get('end', '未定')}
- 種別: {new_event['type']}
- 終日: {new_event.get('is_all_day', False)}
- カテゴリ: {new_event.get('category', 'なし')}

既存の予定:
- タイトル: {existing_event['title']}
- 時間: {existing_event['start']} 〜 {existing_event.get('end', '未定')}
- 種別: {existing_event['type']}
- 終日: {existing_event.get('is_all_day', False)}
- カテゴリ: {existing_event.get('category', 'なし')}

以下のルールに従って警告メッセージを生成してください:
1. 時間指定 vs 時間指定 → 「完全に重複しています」
2. 終日イベント + 時間指定 → 「この日はXXがありますが、時間は問題ありませんか?」
3. 期間予定 + 日付イベント → 「XX期間中ですが問題ありませんか?」
4. 同カテゴリの場合 → 警告を緩和

簡潔で分かりやすい日本語の警告文を1文で返してください。警告文のみを返し、説明は不要です。"""
            }]
        )
        
        return message.content[0].text.strip()
    
    def _extract_json(self, text):
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"AIのレスポンスをJSONに変換できませんでした: {text}") from e