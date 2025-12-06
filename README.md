# 介護業務DX - 帳票自動転記・AI分析Webアプリ

介護業務のDXを目的とした、PDF/音声ファイルから情報を自動抽出し、Googleスプレッドシートに転記するStreamlitアプリケーションです。

## 機能

### 1. PDFから転記（アセスメント）
- PDFや画像ファイルから介護記録データを自動抽出
- Gemini AIで手書き文字やチェックボックスも認識
- 定義されたマッピングに基づいてGoogleスプレッドシートに自動転記

### 2. 音声から会議録作成
- 会議の音声ファイルを文字起こし
- 決定事項、課題、アクション項目を自動要約
- 会議録シートに転記

## セットアップ

### 1. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定（推奨）

`.env.example`をコピーして`.env`ファイルを作成し、設定を記述します：

```bash
# .env.exampleをコピー
cp .env.example .env
```

`.env`ファイルを編集して、実際の値を設定：

```bash
# Gemini API設定
GEMINI_API_KEY=AIzaSy...（実際のAPIキー）
GEMINI_MODEL=gemini-2.0-flash-exp

# Google Sheets設定
SERVICE_ACCOUNT_PATH=./service_account.json

# デフォルトのスプレッドシートID
ASSESSMENT_SHEET_ID=1abc...（実際のスプレッドシートID）
CASE_MEETING_SHEET_ID=1def...
MANAGEMENT_MEETING_SHEET_ID=1ghi...
```

### 3. Google Cloud設定

#### Gemini API
1. [Google AI Studio](https://makersuite.google.com/app/apikey)でAPIキーを取得
2. `.env`ファイルの`GEMINI_API_KEY`に設定（または起動後にアプリのサイドバーで入力）

#### Google Sheets API
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Sheets APIを有効化
3. サービスアカウントを作成してJSONキーをダウンロード
4. `service_account.json`として保存し、`.env`で`SERVICE_ACCOUNT_PATH`に指定

### 4. スプレッドシートの共有
- サービスアカウントのメールアドレスに対してスプレッドシートの編集権限を付与

## 使い方

### アプリの起動

```bash
streamlit run app.py
```

### PDFからの転記手順

1. **設定を確認**
   - サイドバーで設定を確認（`.env`で設定済みの場合は自動入力されています）
   - 必要に応じてGemini APIキーやモデルを変更
   - 処理モードを「PDFから転記」に設定

2. **ファイルをアップロード**
   - `mapping.txt`をアップロード（項目とセル座標の対応ファイル）
   - 処理対象のPDF/画像ファイルをアップロード

3. **AI処理を実行**
   - 「AI処理を実行」ボタンをクリック
   - 抽出結果を確認

4. **スプレッドシートに転記**
   - `.env`で`SERVICE_ACCOUNT_PATH`を設定していない場合は`service_account.json`をアップロード
   - スプレッドシートID（`.env`で設定済みの場合は自動入力）を確認
   - 「スプレッドシートに転記」ボタンをクリック

### 音声からの会議録作成

1. **設定を入力**
   - 処理モードを「音声会議録作成」に設定

2. **音声ファイルをアップロード**
   - mp3, m4a, wav形式に対応

3. **AI処理を実行**
   - 会議録が自動で作成されます

4. **転記**
   - 同様にスプレッドシートに転記可能

## マッピングファイルの形式

`mapping.txt`は以下の形式で記述します：

```
項目名：セル番地
項目名：セル番地（選択肢1、選択肢2、選択肢3）
```

例：
```
作成日：J11
性別：P18（男、女）
アセスメント理由：F15（初回、更新、区分変更（改善）、退院）
```

## 技術スタック

- **フロントエンド**: Streamlit
- **AI**: Google Gemini API (2.0-flash, 1.5-pro)
- **スプレッドシート連携**: gspread, oauth2client
- **ファイル処理**: Python標準ライブラリ

## トラブルシューティング

### APIエラー
- APIキーが正しく入力されているか確認
- Gemini APIの利用制限を確認

### スプレッドシート転記エラー
- `service_account.json`が正しくアップロードされているか確認
- サービスアカウントにスプレッドシートの編集権限があるか確認
- スプレッドシートIDが正しいか確認

### ファイル読み込みエラー
- ファイル形式が対応しているか確認
- ファイルサイズが大きすぎないか確認（推奨: 50MB以下）

## ライセンス

MIT License

## 作成者

介護DXプロジェクト
