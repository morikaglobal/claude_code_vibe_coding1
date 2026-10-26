from flask import Flask, render_template, request, send_file, jsonify
import os
from dotenv import load_dotenv
from utils.youtube_handler import YouTubeHandler
from utils.recipe_analyzer import RecipeAnalyzer
from utils.pdf_generator import PDFGenerator
import logging

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 必要な環境変数確認
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY not set in .env file")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_video():
    try:
        data = request.get_json()
        youtube_url = data.get('url', '').strip()

        if not youtube_url:
            return jsonify({'error': 'URLを入力してください'}), 400

        # YouTube動画情報を取得
        logger.info(f"Processing URL: {youtube_url}")
        yt_handler = YouTubeHandler()
        video_info = yt_handler.extract_info(youtube_url)

        if not video_info:
            return jsonify({'error': 'YouTubeの動画情報を取得できませんでした'}), 400

        # レシピを分析
        logger.info("Analyzing recipe...")
        analyzer = RecipeAnalyzer()
        recipe = analyzer.analyze(video_info)

        if not recipe:
            return jsonify({'error': 'レシピを生成できませんでした'}), 400

        # PDFを生成
        logger.info("Generating PDF...")
        pdf_generator = PDFGenerator()
        pdf_path = pdf_generator.generate(recipe, video_info)

        if not pdf_path:
            return jsonify({'error': 'PDFの生成に失敗しました'}), 500

        # ファイル名を取得
        import os as os_module
        filename = os_module.path.basename(pdf_path)

        # PDFをバイナリで読み込み、base64エンコード
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        import base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

        return jsonify({
            'success': True,
            'filename': filename,
            'pdf_data': pdf_base64,
            'message': 'PDFが生成されました。プレビューを確認してからダウンロードしてください。'
        }), 200

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'error': f'エラー: {str(e)}'}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_pdf(filename):
    try:
        # セキュリティ：ファイル名が安全か確認
        if '..' in filename or '/' in filename:
            return jsonify({'error': '不正なファイル名です'}), 400

        pdf_path = os.path.join('temp', filename)

        if not os.path.exists(pdf_path):
            return jsonify({'error': 'ファイルが見つかりません'}), 404

        return send_file(pdf_path, as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': f'ダウンロード中にエラーが発生しました'}), 500

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    os.makedirs('temp', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
