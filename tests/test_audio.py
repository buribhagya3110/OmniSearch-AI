import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from extractors.audio_transcriber import AudioTranscriber
from database.database import Database
from pipeline import IngestionPipeline, SearchPipeline
from utils.file_manager import FileManager

class TestAudioPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.wav_path = os.path.join(self.temp_dir, "meeting_recording.wav")
        self._create_dummy_wav(self.wav_path, duration_seconds=4, sample_rate=44100, channels=2)

    def tearDown(self):
        try:
            if os.path.exists(self.wav_path):
                os.remove(self.wav_path)
        except Exception:
            pass

    def _create_dummy_wav(self, file_path: str, duration_seconds: int = 4, sample_rate: int = 44100, channels: int = 2):
        """Generates a valid sine-wave PCM WAV file."""
        n_samples = duration_seconds * sample_rate
        freq = 440.0  # A4 tone
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(n_samples):
                val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
                packed = struct.pack("<h", val)
                for _ in range(channels):
                    frames.extend(packed)
            wf.writeframes(frames)

    def test_audio_validation(self):
        """Test audio validation and property detection."""
        val = AudioTranscriber.validate_audio(self.wav_path)
        self.assertTrue(val["valid"])
        self.assertEqual(val["format"], "wav")
        self.assertEqual(val["channels"], 2)
        self.assertEqual(val["sample_rate"], 44100)
        self.assertAlmostEqual(val["duration"], 4.0, delta=0.2)

    def test_audio_preprocessing_resampling(self):
        """Test resampling audio to standard 16kHz mono PCM WAV."""
        preprocessed_path, is_temp = AudioTranscriber.preprocess_audio(self.wav_path)
        self.assertTrue(os.path.exists(preprocessed_path))

        val = AudioTranscriber.validate_audio(preprocessed_path)
        self.assertTrue(val["valid"])
        self.assertEqual(val["sample_rate"], 16000)
        self.assertEqual(val["channels"], 1)

        if is_temp:
            os.remove(preprocessed_path)

    def test_format_timestamp(self):
        """Test timestamp formatting into MM:SS."""
        self.assertEqual(AudioTranscriber.format_timestamp(0), "00:00")
        self.assertEqual(AudioTranscriber.format_timestamp(65), "01:05")
        self.assertEqual(AudioTranscriber.format_timestamp(3665), "01:01:05")

    def test_full_audio_search_pipeline(self):
        """
        Tests the complete audio search pipeline:
        1. Ingest audio with transcript and timestamps
        2. Verify database records and audio_segments table
        3. Verify BM25 and FAISS vector index
        4. Search for spoken phrase and verify filename, snippet, and exact timestamp retrieval!
        """
        from unittest.mock import MagicMock, patch

        spoken_text = "The quarterly financial report showed substantial revenue growth in cloud computing services."
        pipeline = IngestionPipeline()
        with open(self.wav_path, "rb") as f:
            file_bytes = f.read()

        mock_whisper = MagicMock()
        mock_whisper.transcribe.return_value = {
            "text": spoken_text,
            "language": "en",
            "segments": [
                {
                    "start": 1.2,
                    "end": 3.8,
                    "text": spoken_text
                }
            ]
        }

        with patch.object(AudioTranscriber, "_get_whisper_model", return_value=mock_whisper):
            trace = pipeline.process_file(file_bytes, "financial_briefing.wav")
            self.assertTrue(trace["success"])
            doc_id = trace["doc_id"]

        # Check database
        db = Database()
        doc = db.get_document(doc_id)
        self.assertIsNotNone(doc)
        self.assertEqual(doc["file_type"], "audio")
        self.assertTrue(len(doc["audio_segments"]) > 0)
        self.assertEqual(doc["audio_segments"][0]["text"], spoken_text)
        self.assertEqual(doc["audio_segments"][0]["start_formatted"], "00:01")
        self.assertEqual(doc["audio_segments"][0]["end_formatted"], "00:03")

        # Search for words spoken in the audio
        sp = SearchPipeline()
        search_res = sp.search("revenue growth cloud computing", mode="hybrid")
        self.assertTrue(search_res["total_matches"] > 0)

        # Check top hit
        top_hit = search_res["results"][0]
        self.assertEqual(top_hit["filename"], "financial_briefing.wav")
        self.assertEqual(top_hit["file_type"], "audio")
        self.assertIn("revenue growth", top_hit["snippet"].lower())
        self.assertIsNotNone(top_hit["primary_timestamp"])
        self.assertIsNotNone(top_hit["audio_info"])

if __name__ == "__main__":
    unittest.main()
