"""Text extraction utilities のテスト"""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.application.exceptions import PDFProcessingError, TextExtractionError
from src.infrastructure.utilities.text_extractor import (
    extract_text_from_file,
    extract_text_from_pdf,
)


class TestExtractTextFromPDF:
    """extract_text_from_pdf関数のテスト"""

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_success(self, mock_pdfium):
        """正常なPDFからのテキスト抽出"""
        # PDFドキュメントとページのモック
        mock_textpage = MagicMock()
        mock_textpage.get_text_bounded.return_value = "Page 1 content"

        mock_page = MagicMock()
        mock_page.get_textpage.return_value = mock_textpage

        mock_document = MagicMock()
        mock_document.__len__.return_value = 1
        mock_document.__iter__.return_value = iter([mock_page])

        mock_pdfium.PdfDocument.return_value = mock_document

        # テスト実行
        pdf_content = b"fake pdf content"
        result = extract_text_from_pdf(pdf_content)

        # 検証
        assert result == "Page 1 content"
        mock_pdfium.PdfDocument.assert_called_once()
        mock_page.get_textpage.assert_called_once()
        mock_textpage.close.assert_called_once()
        mock_page.close.assert_called_once()
        mock_document.close.assert_called_once()

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_multiple_pages(self, mock_pdfium):
        """複数ページのPDFからのテキスト抽出"""
        # 複数ページのモック
        mock_textpage1 = MagicMock()
        mock_textpage1.get_text_bounded.return_value = "Page 1"
        mock_textpage2 = MagicMock()
        mock_textpage2.get_text_bounded.return_value = "Page 2"
        mock_textpage3 = MagicMock()
        mock_textpage3.get_text_bounded.return_value = "Page 3"

        mock_page1 = MagicMock()
        mock_page1.get_textpage.return_value = mock_textpage1
        mock_page2 = MagicMock()
        mock_page2.get_textpage.return_value = mock_textpage2
        mock_page3 = MagicMock()
        mock_page3.get_textpage.return_value = mock_textpage3

        mock_document = MagicMock()
        mock_document.__len__.return_value = 3
        mock_document.__iter__.return_value = iter([mock_page1, mock_page2, mock_page3])

        mock_pdfium.PdfDocument.return_value = mock_document

        # テスト実行
        result = extract_text_from_pdf(b"fake pdf")

        # 検証
        assert result == "Page 1\nPage 2\nPage 3"

    def test_extract_text_from_pdf_empty_content(self):
        """空のPDFコンテンツでの例外"""
        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_pdf(b"")

        assert "Empty PDF content provided" in str(exc_info.value)

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_no_pages(self, mock_pdfium):
        """ページのないPDFでの例外"""
        # PdfiumErrorをモック
        mock_pdfium.PdfiumError = Exception

        mock_document = MagicMock()
        mock_document.__len__.return_value = 0

        mock_pdfium.PdfDocument.return_value = mock_document

        with pytest.raises(PDFProcessingError):
            extract_text_from_pdf(b"fake pdf")

        mock_document.close.assert_called_once()

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_extraction_fails_all_pages(self, mock_pdfium):
        """全ページでテキスト抽出が失敗する場合"""
        # PdfiumErrorをモック
        mock_pdfium.PdfiumError = Exception

        mock_page = MagicMock()
        mock_page.get_textpage.side_effect = Exception("Extraction failed")

        mock_document = MagicMock()
        mock_document.__len__.return_value = 2
        mock_document.__iter__.return_value = iter([mock_page, mock_page])

        mock_pdfium.PdfDocument.return_value = mock_document

        # TextExtractionErrorまたはPDFProcessingErrorが発生することを確認
        with pytest.raises((TextExtractionError, PDFProcessingError)):
            extract_text_from_pdf(b"fake pdf")

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_partial_extraction_failure(self, mock_pdfium):
        """一部のページでテキスト抽出が失敗する場合（続行）"""
        # ページ1は成功、ページ2は失敗、ページ3は成功
        mock_textpage1 = MagicMock()
        mock_textpage1.get_text_bounded.return_value = "Page 1"
        mock_textpage3 = MagicMock()
        mock_textpage3.get_text_bounded.return_value = "Page 3"

        mock_page1 = MagicMock()
        mock_page1.get_textpage.return_value = mock_textpage1
        mock_page2 = MagicMock()
        mock_page2.get_textpage.side_effect = Exception("Page 2 extraction failed")
        mock_page3 = MagicMock()
        mock_page3.get_textpage.return_value = mock_textpage3

        mock_document = MagicMock()
        mock_document.__len__.return_value = 3
        mock_document.__iter__.return_value = iter([mock_page1, mock_page2, mock_page3])

        mock_pdfium.PdfDocument.return_value = mock_document

        # テスト実行
        result = extract_text_from_pdf(b"fake pdf")

        # 検証 - ページ2はスキップされるが、ページ1と3は抽出される
        assert result == "Page 1\nPage 3"

    @patch("src.infrastructure.utilities.text_extractor.pdfium")
    def test_extract_text_from_pdf_pdfium_error(self, mock_pdfium):
        """PDFiumエラーが発生した場合"""

        # PdfiumErrorを実際のExceptionクラスとして定義
        class PdfiumError(Exception):
            pass

        mock_pdfium.PdfiumError = PdfiumError
        mock_pdfium.PdfDocument.side_effect = PdfiumError("Invalid PDF")

        with pytest.raises(PDFProcessingError) as exc_info:
            extract_text_from_pdf(b"invalid pdf")

        assert "Failed to process PDF document" in str(exc_info.value)


class TestExtractTextFromFile:
    """extract_text_from_file関数のテスト"""

    @patch("src.infrastructure.utilities.text_extractor.extract_text_from_pdf")
    @patch("builtins.open", new_callable=mock_open, read_data=b"fake pdf content")
    @patch("os.path.exists")
    def test_extract_text_from_file_pdf_success(
        self, mock_exists, mock_file, mock_extract_pdf
    ):
        """PDFファイルからのテキスト抽出成功"""
        mock_exists.return_value = True
        mock_extract_pdf.return_value = "Extracted text"

        result = extract_text_from_file("/path/to/file.pdf")

        assert result == "Extracted text"
        mock_exists.assert_called_once_with("/path/to/file.pdf")
        mock_file.assert_called_once_with("/path/to/file.pdf", "rb")
        mock_extract_pdf.assert_called_once_with(b"fake pdf content")

    @patch("os.path.exists")
    def test_extract_text_from_file_not_found(self, mock_exists):
        """ファイルが見つからない場合"""
        mock_exists.return_value = False

        with pytest.raises(FileNotFoundError) as exc_info:
            extract_text_from_file("/path/to/nonexistent.pdf")

        assert "File not found: /path/to/nonexistent.pdf" in str(exc_info.value)

    @patch("builtins.open", new_callable=mock_open, read_data=b"text content")
    @patch("os.path.exists")
    def test_extract_text_from_file_unsupported_format(self, mock_exists, mock_file):
        """サポートされていないファイル形式"""
        mock_exists.return_value = True

        with pytest.raises(TextExtractionError) as exc_info:
            extract_text_from_file("/path/to/file.txt")

        assert "Unsupported file format" in str(exc_info.value)

    @patch("src.infrastructure.utilities.text_extractor.extract_text_from_pdf")
    @patch("builtins.open", new_callable=mock_open, read_data=b"pdf content")
    @patch("os.path.exists")
    def test_extract_text_from_file_pdf_uppercase_extension(
        self, mock_exists, mock_file, mock_extract_pdf
    ):
        """PDF拡張子が大文字の場合"""
        mock_exists.return_value = True
        mock_extract_pdf.return_value = "Extracted text"

        result = extract_text_from_file("/path/to/FILE.PDF")

        assert result == "Extracted text"
        mock_extract_pdf.assert_called_once()

    @patch("src.infrastructure.utilities.text_extractor.extract_text_from_pdf")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_extract_text_from_file_pdf_processing_error(
        self, mock_exists, mock_file, mock_extract_pdf
    ):
        """PDF処理エラーが発生した場合（再送出）"""
        mock_exists.return_value = True
        mock_extract_pdf.side_effect = PDFProcessingError(
            "PDF error", {"page_count": 0}
        )

        with pytest.raises(PDFProcessingError):
            extract_text_from_file("/path/to/file.pdf")
