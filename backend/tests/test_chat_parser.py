"""Unit tests for the WhatsApp chat parser logic."""
import pytest

from app.tasks.ocr import _parse_whatsapp_chat, _extract_ocr_blocks, _parse_timestamp


class TestParseTimestamp:
    def test_12h_format(self):
        assert _parse_timestamp("2:30 PM") is not None

    def test_24h_format(self):
        assert _parse_timestamp("14:30") is not None

    def test_date_time_format(self):
        result = _parse_timestamp("3/19/26, 2:30 PM")
        assert result is not None

    def test_invalid_format(self):
        assert _parse_timestamp("not a time") is None

    def test_dot_separator(self):
        assert _parse_timestamp("2.30 PM") is not None


class TestParseWhatsAppChat:
    def _make_block(self, text, x_center, y_center, x_min=0, x_max=100, y_min=0, y_max=20):
        return {
            "text": text,
            "confidence": 0.95,
            "x_center": x_center,
            "y_center": y_center,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "width": x_max - x_min,
            "height": y_max - y_min,
        }

    def test_empty_blocks(self):
        assert _parse_whatsapp_chat([]) == []

    def test_simple_left_right_classification(self):
        blocks = [
            self._make_block("Hello", x_center=100, y_center=50, x_min=20, x_max=180),
            self._make_block("Hi there", x_center=400, y_center=100, x_min=300, x_max=500),
        ]
        messages = _parse_whatsapp_chat(blocks)
        assert len(messages) == 2
        assert messages[0]["is_sent"] is False  # left side
        assert messages[1]["is_sent"] is True   # right side

    def test_sender_extraction(self):
        blocks = [
            self._make_block("Alice: How are you?", x_center=100, y_center=50, x_min=20, x_max=250),
        ]
        messages = _parse_whatsapp_chat(blocks)
        assert len(messages) == 1
        assert messages[0]["sender"] == "Alice"
        assert messages[0]["message"] == "How are you?"

    def test_timestamp_extraction(self):
        blocks = [
            self._make_block("Hello 2:30 PM", x_center=100, y_center=50, x_min=20, x_max=200),
        ]
        messages = _parse_whatsapp_chat(blocks)
        assert len(messages) == 1
        assert messages[0]["timestamp_raw"] is not None
        assert "Hello" in messages[0]["message"]

    def test_vertical_grouping(self):
        """Nearby blocks on the same side should be grouped into one message."""
        blocks = [
            self._make_block("This is a", x_center=100, y_center=50, x_min=20, x_max=200, y_min=40, y_max=60),
            self._make_block("long message", x_center=100, y_center=70, x_min=20, x_max=200, y_min=62, y_max=80),
        ]
        messages = _parse_whatsapp_chat(blocks)
        assert len(messages) == 1
        assert "This is a" in messages[0]["message"]
        assert "long message" in messages[0]["message"]


class TestExtractOcrBlocks:
    def test_empty_result(self):
        assert _extract_ocr_blocks(None) == []
        assert _extract_ocr_blocks([]) == []

    def test_valid_blocks(self):
        result = [[
            [
                [[10, 20], [100, 20], [100, 40], [10, 40]],
                ("Hello world", 0.95),
            ],
        ]]
        blocks = _extract_ocr_blocks(result)
        assert len(blocks) == 1
        assert blocks[0]["text"] == "Hello world"
        assert blocks[0]["confidence"] == 0.95
        assert blocks[0]["x_min"] == 10
        assert blocks[0]["y_min"] == 20

    def test_low_confidence_filtered(self):
        result = [[
            [
                [[10, 20], [100, 20], [100, 40], [10, 40]],
                ("noise", 0.3),
            ],
        ]]
        blocks = _extract_ocr_blocks(result)
        assert len(blocks) == 0
