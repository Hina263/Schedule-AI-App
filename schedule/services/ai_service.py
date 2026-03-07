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
    
    def parse_natural_language(self, natural_input, default_duration_hours=1):
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
- end_datetimeが不明な場合はstart_datetimeの{default_duration_hours}時間後にしてください
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

時刻の解釈ルール（重要）:
- 「8時」「9時」など1〜12の時刻で午前/午後が明示されていない場合:
  * その時刻（午前）が現在時刻よりも過去になる場合は、午後（+12時間）として解釈する
  * 例: 現在15:00で「今日8時に会議」→ 午前8時は既に過去 → 20:00（午後8時）として解釈
  * 例: 現在7:00で「今日8時に会議」→ 午前8時はまだ未来 → 08:00（午前8時）として解釈
- 「朝」「午前」「am」が含まれる場合は午前として解釈する
- 「夜」「晩」「夕方」「午後」「pm」が含まれる場合は午後として解釈する
- 明日以降の日付が指定された場合は、上記の「現在時刻より過去」ルールは適用せず、文脈で判断する

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
    
    def parse_modify_command(self, natural_input):
        """
        自然言語から変更・削除の意図を解析する。
        Returns:
            {
                "intent": "update" | "delete" | "unknown",
                "search": {
                    "date": "YYYY-MM-DD" or null,
                    "title_keyword": "..."
                },
                "changes": {   # update の場合のみ
                    "title": null or "新タイトル",
                    "start_datetime": null or "YYYY-MM-DD HH:MM",
                    "end_datetime":   null or "YYYY-MM-DD HH:MM"
                }
            }
        """
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M')

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": f"""以下の入力から予定の変更または削除の意図を解析してください。

入力: {natural_input}
現在時刻: {current_time}

以下の形式でJSONを返してください:
{{
    "intent": "update" または "delete" または "unknown",
    "search": {{
        "date": "YYYY-MM-DD" または null（日付が不明な場合）,
        "title_keyword": "予定を特定するキーワード（例: 会議、英語、合宿）"
    }},
    "changes": {{
        "title": null または "新しいタイトル",
        "start_datetime": null または "YYYY-MM-DD HH:MM",
        "end_datetime":   null または "YYYY-MM-DD HH:MM"
    }}
}}

注意事項:
- intentが"delete"の場合、changesは全てnullでよい
- intentが"update"の場合、変更する項目のみchangesに入れる（変えない項目はnull）
- 変更・削除の意図が読み取れない場合はintent="unknown"
- 「3/4」「明日」「来週火曜」などはYYYY-MM-DD形式に変換する
- title_keywordは予定を特定できる最小限のキーワード
- 例: "変更"/"修正"/"直して"/"ずらして" → intent="update"
- 例: "削除"/"消して"/"キャンセル"/"なくして" → intent="delete"
- 締切・期間予定の変更・削除も同様に扱う

時刻の解釈ルール:
- 1〜12時で午前/午後が不明かつ現在時刻より過去になる場合は午後（+12時間）として解釈
- 「朝」「午前」→ 午前、「夜」「夕方」「午後」→ 午後

JSONのみを返してください。説明文は不要です。"""
            }]
        )

        return self._extract_json(message.content[0].text)

    def parse_unified_command(self, natural_input, default_duration_hours=1):
        """
        自然言語から意図（追加/検索/変更/削除）を判定し、必要なデータを一括抽出する。
        Returns:
            {
                "intent": "add" | "search" | "update" | "delete" | "unknown",
                # intent="add" の場合:
                "event_data": { title, start_datetime, end_datetime, event_type, priority, is_all_day, category },
                # intent="search" の場合:
                "period": "今日" など,
                # intent="update" / "delete" の場合:
                "search": { date, title_keyword },
                "changes": { title, start_datetime, end_datetime }
            }
        """
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M')

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            messages=[{
                "role": "user",
                "content": f"""以下の入力の意図を解析して、JSON形式で返してください。

入力: {natural_input}
現在時刻: {current_time}

意図の判定基準:
- 「追加」「登録」「入れて」「予定がある」「〜がある」「〜する」→ intent="add"
- 「見せて」「教えて」「確認」「今日は?」「今週の予定」→ intent="search"
- 「変更」「修正」「直して」「ずらして」「〜からにして」→ intent="update"
- 「削除」「消して」「キャンセル」「なくして」→ intent="delete"

以下の形式でJSONを返してください:
{{
    "intent": "add" または "search" または "update" または "delete" または "unknown",
    "event_data": {{
        "title": "予定のタイトル",
        "start_datetime": "YYYY-MM-DD HH:MM",
        "end_datetime": "YYYY-MM-DD HH:MM",
        "event_type": "activity",
        "priority": 3,
        "is_all_day": false,
        "category": ["カテゴリ1"]
    }},
    "period": "今日",
    "search": {{
        "date": "YYYY-MM-DD" または null,
        "title_keyword": "キーワード"
    }},
    "changes": {{
        "title": null または "新タイトル",
        "start_datetime": null または "YYYY-MM-DD HH:MM",
        "end_datetime": null または "YYYY-MM-DD HH:MM"
    }}
}}

注意:
- intentに関係するフィールドのみ埋めれば良い（不要フィールドはnullや空で）
- intent="add": event_dataを埋める。end_datetimeが不明なら{default_duration_hours}時間後
- intent="search": periodを埋める（「今日」「今週」「来月」など日本語で）
- intent="update"/"delete": searchとchangesを埋める
- event_typeは activity/block/deadline のいずれか
- 「block」: 複数日にまたがる期間（合宿・テスト期間など）、is_all_day=true、start=開始日00:00、end=終了日23:59
- 「deadline」: 締切

時刻の解釈ルール:
- 1〜12時で午前/午後が不明かつ現在時刻より過去になる場合は午後（+12時間）として解釈
- 「朝」「午前」「am」→ 午前、「夜」「夕方」「午後」「pm」→ 午後
- 明日以降の日付が指定された場合は文脈で判断

JSONのみを返してください。説明文は不要です。"""
            }]
        )

        return self._extract_json(message.content[0].text)

    def _extract_json(self, text):
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"AIのレスポンスをJSONに変換できませんでした: {text}") from e