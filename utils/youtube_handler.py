import yt_dlp
import os
import logging
from pathlib import Path
from PIL import Image
import io

logger = logging.getLogger(__name__)

class YouTubeHandler:
    def __init__(self):
        self.temp_dir = Path('temp')
        self.temp_dir.mkdir(exist_ok=True)

    def extract_info(self, url):
        """YouTube動画から情報を抽出"""
        try:
            import re

            # ビデオ ID を抽出
            video_id = None

            # YouTube ショート形式: youtube.com/shorts/[ID]
            if 'youtube.com/shorts/' in url:
                match = re.search(r'youtube\.com/shorts/([^/?&]+)', url)
                if match:
                    video_id = match.group(1)
            # 通常の YouTube 動画: youtube.com/watch?v=[ID]
            elif 'youtube.com' in url or 'www.youtube.com' in url:
                match = re.search(r'v=([^&]+)', url)
                if match:
                    video_id = match.group(1)
            # YouTube ショートリンク: youtu.be/[ID]
            elif 'youtu.be' in url:
                match = re.search(r'youtu\.be/([^?&]+)', url)
                if match:
                    video_id = match.group(1)

            if not video_id:
                return None

            # ショート動画かどうかを判定
            is_short = 'youtube.com/shorts/' in url

            # 最小限のオプションで情報取得を試みる
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'no_color': True,
            }

            title = f'YouTube Video {video_id}'
            description = ''

            try:
                import requests
                # YouTube のページからメタデータを取得
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=5)
                response.encoding = 'utf-8'
                html = response.text

                # og:title を抽出
                title_match = re.search(r'<meta name="title" content="([^"]+)"', html)
                if title_match:
                    title = title_match.group(1)
                else:
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
                    if title_match:
                        title = title_match.group(1)

                # og:description を抽出
                desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
                if desc_match:
                    description = desc_match.group(1)
                else:
                    desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                    if desc_match:
                        description = desc_match.group(1)

                logger.info(f"Extracted metadata - Title: {title}, Desc length: {len(description)}")
            except Exception as e:
                logger.warning(f"Could not extract metadata from HTML: {str(e)}")

            # サムネイル画像を取得
            frame_image = self._extract_thumbnail_image(url)

            # サムネイル取得失敗時は、ショート動画でもフォールバック表示
            show_short_placeholder = is_short and frame_image is None

            return {
                'title': title,
                'description': description,
                'subtitles': '',
                'duration': 0,
                'url': url,
                'frame_image': frame_image,
                'video_id': video_id,
                'is_short': is_short,
                'show_short_placeholder': show_short_placeholder,
            }

        except Exception as e:
            logger.error(f"Error extracting YouTube info: {str(e)}")
            return None

    def _get_subtitles(self, url):
        """字幕を取得"""
        try:
            ydl_opts = {
                'skip_download': True,
                'quiet': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})

            # 字幕テキストを結合
            subtitle_text = ''
            for lang, subs in subtitles.items():
                if subs:
                    for sub in subs:
                        if isinstance(sub, dict) and sub.get('data'):
                            subtitle_text += sub.get('data', '')

            return subtitle_text

        except Exception as e:
            logger.warning(f"Could not get subtitles: {str(e)}")
            return ''

    def _extract_thumbnail_image(self, url):
        """YouTubeのサムネイル画像を取得"""
        try:
            import requests

            # YouTubeのビデオIDを抽出
            video_id = None
            if 'youtube.com' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif 'youtu.be' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]

            if not video_id:
                return None

            # サムネイル URL（高品質版）
            thumbnail_url = f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg'
            response = requests.get(thumbnail_url, timeout=10)

            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                # 画像をバイナリに変換
                img_io = io.BytesIO()
                image.save(img_io, format='JPEG')
                img_io.seek(0)
                return img_io

            return None

        except Exception as e:
            logger.warning(f"Could not get thumbnail: {str(e)}")
            return None
