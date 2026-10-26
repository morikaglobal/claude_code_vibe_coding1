# CLAUDE.md - Recipe Card Maker Project

このプロジェクトの Claude Code ガイドラインです。

## Python 仮想環境

**重要: Python/Flask アプリの仮想環境について**

このプロジェクトおよび、今後 Claude が Python や Flask アプリを作成する際：

- **仮想環境は `python -m venv .venv` 方式で統一する**
- 他の仮想環境管理ツール（poetry, pipenv, conda など）は指定されない限り使用しない
- セットアップは標準的な手順：
  1. `python -m venv .venv`
  2. `.venv\Scripts\activate.bat` (Windows CMD)
  3. `pip install -r requirements.txt`

## プロジェクト構成

- **フロントエンド**: HTML/CSS/JavaScript (Flask テンプレート)
- **バックエンド**: Python + Flask
- **依存管理**: `requirements.txt`

## テスト・実行方法

- 仮想環境を有効化後、`python app.py` でサーバーを起動
- ブラウザで `http://localhost:5000` にアクセス

