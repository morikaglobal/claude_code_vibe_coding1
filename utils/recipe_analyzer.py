import os
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class RecipeAnalyzer:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def analyze(self, video_info):
        """Claude APIを使用してレシピを分析"""
        try:
            # 利用可能な情報を優先順位付けして組み立て
            context = self._build_context(video_info)

            if not context:
                logger.error("No useful context found for recipe analysis")
                return None

            # Claude API にプロンプトを送信
            recipe = self._call_claude_api(context, video_info.get('title', ''))

            return recipe

        except Exception as e:
            logger.error(f"Error analyzing recipe: {str(e)}")
            return None

    def _build_context(self, video_info):
        """ビデオ情報からコンテキストを構築"""
        parts = []

        title = video_info.get('title', '')
        description = video_info.get('description', '')
        subtitles = video_info.get('subtitles', '')

        if title:
            parts.append(f"動画タイトル: {title}")

        if description:
            parts.append(f"動画説明: {description[:1000]}")  # 最初の1000文字

        if subtitles:
            parts.append(f"字幕/キャプション:\n{subtitles[:2000]}")  # 最初の2000文字

        return '\n\n'.join(parts)

    def _call_claude_api(self, context, title):
        """Claude APIを呼び出してレシピを抽出"""
        prompt = f"""以下の動画情報からレシピを抽出してください。

{context}

以下のJSONフォーマットで結果を返してください。日本語で、簡潔に記述してください。
{{
    "dish_name": "料理名",
    "ingredients": [
        {{"name": "材料名", "amount": "量"}},
        ...
    ],
    "instructions": [
        "手順1",
        "手順2",
        ...
    ],
    "notes": "その他のメモ（あれば）"
}}

重要：
- 材料は5～10個程度、量は簡潔に
- 手順は5～8段階程度、各段階は20文字以内
- JSONは有効な形式である必要があります
"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-5-5",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if not message.content or len(message.content) == 0:
                logger.error("Empty response from Claude API")
                return None

            # すべてのコンテンツブロックからテキストを抽出
            response_text = None
            for block in message.content:
                if hasattr(block, 'text') and block.text:
                    response_text = block.text
                    break

            if not response_text:
                logger.error(f"No text in Claude response. Blocks: {[type(b).__name__ for b in message.content]}")
                return None

            # JSON部分を抽出
            import json
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                logger.info(f"Extracted JSON: {json_str[:200]}...")  # デバッグ
                try:
                    # JSON を修正（制御文字を削除）
                    json_str = json_str.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                    # 複数の空白を1つにする
                    json_str = ' '.join(json_str.split())

                    # JSON が不完全な場合は修正を試みる
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')

                    if close_braces < open_braces:
                        # 閉じられていない括弧を追加
                        json_str += '}' * (open_braces - close_braces)
                        logger.info(f"Fixed incomplete JSON by adding {open_braces - close_braces} closing braces")

                    recipe = json.loads(json_str)
                    logger.info(f"Recipe parsed: {recipe.keys()}")  # デバッグ
                    recipe['dish_name'] = recipe.get('dish_name', title)

                    # 不足しているキーをデフォルト値で埋める
                    if 'ingredients' not in recipe:
                        recipe['ingredients'] = []
                    if 'instructions' not in recipe:
                        recipe['instructions'] = []
                    if 'notes' not in recipe:
                        recipe['notes'] = ''

                    return recipe
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {str(e)}")
                    logger.error(f"JSON string: {json_str[:500]}")  # デバッグ
                    return None

            logger.error(f"Could not extract JSON from Claude response. Response: {response_text[:300]}")
            return None

        except Exception as e:
            logger.error(f"Claude API error: {str(e)}", exc_info=True)
            return None
