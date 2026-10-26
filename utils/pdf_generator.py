import os
import logging
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import io
from datetime import datetime

logger = logging.getLogger(__name__)

# 日本語フォントを登録（Windows の MS ゴシック）
try:
    # Windows の場合
    font_path = "C:\\Windows\\Fonts\\msgothic.ttc"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Japanese', font_path))
        _japanese_font = 'Japanese'
    else:
        # フォールバック
        _japanese_font = 'Helvetica'
except Exception as e:
    logger.warning(f"Could not register Japanese font: {str(e)}")
    _japanese_font = 'Helvetica'

class PDFGenerator:
    def __init__(self):
        self.temp_dir = Path('temp')
        self.temp_dir.mkdir(exist_ok=True)
        self.page_width, self.page_height = A4
        self.margin = 0.3 * cm  # さらに狭いマージン

    def generate(self, recipe, video_info):
        """1ページのレシピPDFを生成"""
        try:
            pdf_path = self.temp_dir / f"recipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            # PDFを作成
            c = canvas.Canvas(str(pdf_path), pagesize=A4)

            # 画像を配置
            current_y = self.page_height - self.margin
            logger.info(f"📍 Start Y: {current_y}")
            current_y = self._draw_image(c, video_info, current_y)
            logger.info(f"📍 After image Y: {current_y}")

            # 料理名を配置
            current_y = self._draw_title(c, recipe, current_y)
            logger.info(f"📍 After title Y: {current_y}")

            # 動画タイトルとURLを配置
            current_y = self._draw_video_info(c, video_info, current_y)
            logger.info(f"📍 After URL Y: {current_y}")

            # 材料を配置
            current_y = self._draw_ingredients(c, recipe, current_y)
            logger.info(f"📍 After ingredients Y: {current_y}")

            # 調理手順を配置
            current_y = self._draw_instructions(c, recipe, current_y)
            logger.info(f"📍 After instructions Y: {current_y}")

            c.save()
            logger.info(f"PDF generated: {pdf_path}")
            return str(pdf_path)

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None

    def _draw_image(self, c, video_info, start_y):
        """画像を描画またはショート動画テキストを表示"""
        try:
            # ショート動画でサムネイル取得失敗時は代替テキストを表示
            if video_info.get('show_short_placeholder'):
                max_width = self.page_width - 2 * self.margin
                max_height = 4 * cm

                # グラデーション風の背景色で枠を描く（紫系）
                c.setFillColor(HexColor("#6B5B95"))
                c.rect(self.margin, start_y - max_height, max_width, max_height, fill=True)

                # テキストを描く
                c.setFont(_japanese_font, 11)
                c.setFillColor(HexColor("#FFFFFF"))
                text = "【この動画はショート動画です】"
                text_width = c.stringWidth(text, _japanese_font, 11)
                x = self.margin + (max_width - text_width) / 2
                y = start_y - max_height / 2 - 0.15 * cm
                c.drawString(x, y, text)

                return start_y - max_height - 1.5 * cm

            frame_image = video_info.get('frame_image')
            if not frame_image:
                return start_y

            # 画像を処理
            if isinstance(frame_image, io.BytesIO):
                img = Image.open(frame_image)
            elif isinstance(frame_image, str):
                img = Image.open(frame_image)
            else:
                # OpenCVのフレームの場合
                import cv2
                img = Image.fromarray(cv2.cvtColor(frame_image, cv2.COLOR_BGR2RGB))

            # 画像のサイズを調整
            max_width = self.page_width - 2 * self.margin
            max_height = 5.5 * cm  # より大きく表示

            img_width, img_height = img.size
            ratio = min(max_width / img_width, max_height / img_height)

            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 画像をバイナリに変換
            img_io = io.BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)

            # PDFに画像を追加
            x = self.margin + (max_width - new_width) / 2  # 中央に配置
            y = start_y - new_height

            c.drawImage(ImageReader(img_io), x, y, width=new_width, height=new_height)

            return y - 1.5 * cm  # 画像下のマージンを大きく

        except Exception as e:
            logger.warning(f"Could not draw image: {str(e)}")
            return start_y

    def _draw_title(self, c, recipe, start_y):
        """タイトル（料理名）を描画"""
        try:
            dish_name = recipe.get('dish_name', 'レシピ')

            # フォントサイズと色を設定
            font_size = 22
            c.setFont(_japanese_font, font_size)
            c.setFillColor(HexColor("#2C3E50"))

            # テキストを描画
            text_width = c.stringWidth(dish_name, _japanese_font, font_size)
            x = self.margin + (self.page_width - 2 * self.margin - text_width) / 2
            c.drawString(x, start_y, dish_name)

            return start_y - 1.0 * cm

        except Exception as e:
            logger.warning(f"Could not draw title: {str(e)}")
            return start_y

    def _draw_video_info(self, c, video_info, start_y):
        """動画タイトルとURLを描画"""
        try:
            video_title = video_info.get('title', '')
            video_url = video_info.get('url', '')

            current_y = start_y - 0.4 * cm

            # URL
            if video_url:
                c.setFont(_japanese_font, 14)
                c.setFillColor(HexColor("#555555"))
                c.drawString(self.margin, current_y, "URL:")

                current_y -= 0.75 * cm  # 1行分のスペース
                c.setFont(_japanese_font, 13)
                c.setFillColor(HexColor("#0066CC"))

                # URLを短縮
                short_url = video_url.replace('https://', '').replace('http://', '')
                if len(short_url) > 50:
                    short_url = short_url[:47] + '...'

                c.drawString(1.2 * self.margin, current_y, short_url)
                current_y -= 1.0 * cm

            return current_y

        except Exception as e:
            logger.warning(f"Could not draw video info: {str(e)}")
            return start_y

    def _draw_ingredients(self, c, recipe, start_y):
        """材料を描画"""
        try:
            ingredients = recipe.get('ingredients', [])

            current_y = start_y - 0.8 * cm

            # セクションタイトル
            c.setFont(_japanese_font, 15)
            c.setFillColor(HexColor("#34495E"))
            c.drawString(self.margin, current_y, "【材料】")

            current_y -= 0.75 * cm  # セクションタイトル後に1行分のスペース
            c.setFont(_japanese_font, 13)
            c.setFillColor(black)

            for ingredient in ingredients[:10]:  # 最大10個
                name = ingredient.get('name', '')
                amount = ingredient.get('amount', '')

                text = f"• {name} {amount}"

                # テキストを折り返す
                max_width = self.page_width - 3 * self.margin
                if c.stringWidth(text, _japanese_font, 11) > max_width:
                    # 折り返し処理
                    words = text.split()
                    line = ''
                    for word in words:
                        if c.stringWidth(line + word, _japanese_font, 11) <= max_width:
                            line += word + ' '
                        else:
                            if line:
                                c.drawString(1.5 * self.margin, current_y, line.strip())
                                current_y -= 0.75 * cm
                            line = word + ' '
                    if line:
                        c.drawString(1.5 * self.margin, current_y, line.strip())
                        current_y -= 0.75 * cm
                else:
                    c.drawString(1.5 * self.margin, current_y, text)
                    current_y -= 0.75 * cm

            return current_y

        except Exception as e:
            logger.warning(f"Could not draw ingredients: {str(e)}")
            return start_y

    def _draw_instructions(self, c, recipe, start_y):
        """調理手順を描画"""
        try:
            instructions = recipe.get('instructions', [])

            current_y = start_y - 0.8 * cm

            # セクションタイトル
            c.setFont(_japanese_font, 15)
            c.setFillColor(HexColor("#34495E"))
            c.drawString(self.margin, current_y, "【調理手順】")

            current_y -= 0.75 * cm  # セクションタイトル後に1行分のスペース
            c.setFont(_japanese_font, 13)
            c.setFillColor(black)

            for i, instruction in enumerate(instructions[:8], 1):  # 最大8手順
                text = f"{i}. {instruction}"

                # テキストを折り返す
                max_width = self.page_width - 3 * self.margin
                if c.stringWidth(text, _japanese_font, 11) > max_width:
                    words = text.split()
                    line = ''
                    first_line = True
                    for word in words:
                        if c.stringWidth(line + word, _japanese_font, 11) <= max_width:
                            line += word + ' '
                        else:
                            if first_line:
                                c.drawString(1.5 * self.margin, current_y, line.strip())
                                first_line = False
                            else:
                                c.drawString(2 * self.margin, current_y, line.strip())
                            current_y -= 0.75 * cm
                            line = word + ' '
                    if line:
                        if first_line:
                            c.drawString(1.5 * self.margin, current_y, line.strip())
                        else:
                            c.drawString(2 * self.margin, current_y, line.strip())
                        current_y -= 0.75 * cm
                else:
                    c.drawString(1.5 * self.margin, current_y, text)
                    current_y -= 0.75 * cm

            return current_y

        except Exception as e:
            logger.warning(f"Could not draw instructions: {str(e)}")
            return start_y
