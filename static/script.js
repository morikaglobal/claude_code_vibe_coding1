document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('recipeForm');
    const submitBtn = document.getElementById('submitBtn');
    const videoUrlInput = document.getElementById('videoUrl');
    const resultContainer = document.getElementById('resultContainer');
    const errorContainer = document.getElementById('errorContainer');
    const errorText = document.getElementById('errorText');
    const spinner = document.querySelector('.spinner');
    const btnText = document.querySelector('.btn-text');

    // PDF プレビュー関連
    const pdfCanvas = document.getElementById('pdfCanvas');
    const downloadBtn = document.getElementById('downloadBtn');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const pageInfo = document.getElementById('pageInfo');

    let pdfDoc = null;
    let currentPage = 1;
    let currentFilename = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const url = videoUrlInput.value.trim();

        if (!url) {
            showError('YouTubeのURLを入力してください');
            return;
        }

        // URL のバリデーション
        if (!isValidYoutubeUrl(url)) {
            showError('有効なYouTubeのURLを入力してください');
            return;
        }

        // UI をリセット
        hideMessages();

        // ボタンを無効化
        submitBtn.disabled = true;
        spinner.style.display = 'inline-block';
        btnText.textContent = '処理中...';

        try {
            const response = await fetch('/api/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'エラーが発生しました');
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'エラーが発生しました');
            }

            // PDFデータを保存
            currentFilename = data.filename;
            const pdfBinary = atob(data.pdf_data);
            const bytes = new Uint8Array(pdfBinary.length);
            for (let i = 0; i < pdfBinary.length; i++) {
                bytes[i] = pdfBinary.charCodeAt(i);
            }

            // PDF.js でプレビュー表示
            await displayPDFPreview(bytes);

            showSuccess();
            videoUrlInput.value = '';

        } catch (error) {
            console.error('Error:', error);
            showError(error.message || 'エラーが発生しました。もう一度試してください');
        } finally {
            submitBtn.disabled = false;
            spinner.style.display = 'none';
            btnText.textContent = 'PDFを生成';
        }
    });

    // PDF プレビュー表示
    async function displayPDFPreview(pdfBytes) {
        try {
            pdfDoc = await pdfjsLib.getDocument({ data: pdfBytes }).promise;
            currentPage = 1;
            await renderPage(currentPage);
            updatePageControls();
        } catch (error) {
            console.error('PDF preview error:', error);
            showError('PDFのプレビュー表示に失敗しました');
        }
    }

    // ページをレンダリング
    async function renderPage(pageNum) {
        try {
            const page = await pdfDoc.getPage(pageNum);
            const viewport = page.getViewport({ scale: 1.5 });

            pdfCanvas.width = viewport.width;
            pdfCanvas.height = viewport.height;

            const context = pdfCanvas.getContext('2d');
            await page.render({
                canvasContext: context,
                viewport: viewport
            }).promise;

            pageInfo.textContent = `ページ ${pageNum} / ${pdfDoc.numPages}`;
        } catch (error) {
            console.error('Render error:', error);
        }
    }

    // ページコントロール更新
    function updatePageControls() {
        prevPageBtn.disabled = currentPage <= 1;
        nextPageBtn.disabled = currentPage >= pdfDoc.numPages;
    }

    // 前のページ
    prevPageBtn.addEventListener('click', async () => {
        if (currentPage > 1) {
            currentPage--;
            await renderPage(currentPage);
            updatePageControls();
        }
    });

    // 次のページ
    nextPageBtn.addEventListener('click', async () => {
        if (currentPage < pdfDoc.numPages) {
            currentPage++;
            await renderPage(currentPage);
            updatePageControls();
        }
    });

    // ダウンロード
    downloadBtn.addEventListener('click', async () => {
        if (!currentFilename) {
            showError('ファイル情報が見つかりません');
            return;
        }

        try {
            downloadBtn.disabled = true;
            downloadBtn.textContent = 'ダウンロード中...';

            const response = await fetch(`/api/download/${currentFilename}`);

            if (!response.ok) {
                throw new Error('ダウンロードに失敗しました');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentFilename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            console.error('Download error:', error);
            showError('ダウンロード中にエラーが発生しました');
        } finally {
            downloadBtn.disabled = false;
            downloadBtn.textContent = '📥 PDFをダウンロード';
        }
    });

    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)\/\S+$/;
        return youtubeRegex.test(url);
    }

    function showSuccess() {
        resultContainer.style.display = 'block';
        errorContainer.style.display = 'none';
    }

    function showError(message) {
        errorText.textContent = message;
        errorContainer.style.display = 'block';
        resultContainer.style.display = 'none';
    }

    function hideMessages() {
        resultContainer.style.display = 'none';
        errorContainer.style.display = 'none';
    }
});
