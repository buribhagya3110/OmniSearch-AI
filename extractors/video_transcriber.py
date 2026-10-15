import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
from config import FFMPEG_CMD
from extractors.audio_transcriber import AudioTranscriber
from utils.logger import setup_logger

logger = setup_logger("VideoTranscriber")

class VideoTranscriber:
    """Extracts audio from video files and transcribes using Whisper speech-to-text."""

    @classmethod
    def _extract_audio_ffmpeg(cls, video_path: str, output_audio_path: str) -> bool:
        """Extracts audio track from video using ffmpeg CLI."""
        try:
            cmd = [
                FFMPEG_CMD, "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                output_audio_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            return res.returncode == 0 and os.path.exists(output_audio_path)
        except Exception as e:
            logger.debug(f"ffmpeg extraction failed: {e}")
            return False

    @classmethod
    def _extract_audio_moviepy(cls, video_path: str, output_audio_path: str) -> bool:
        """Extracts audio track using moviepy."""
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(video_path)
            if clip.audio is not None:
                clip.audio.write_audiofile(output_audio_path, logger=None)
                clip.close()
                return os.path.exists(output_audio_path)
        except Exception as e:
            logger.debug(f"moviepy extraction failed: {e}")
        return False

    @classmethod
    def parse(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Attempt direct Whisper parsing first (Whisper supports video files natively if ffmpeg is available)
        try:
            res = AudioTranscriber.parse(file_path)
            if res.get("text"):
                res["metadata"]["source"] = "video_direct"
                return res
        except Exception:
            pass

        # If direct failed, extract audio to a temporary .wav file
        temp_audio = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_audio = f.name

            extracted = cls._extract_audio_ffmpeg(str(path), temp_audio)
            if not extracted:
                extracted = cls._extract_audio_moviepy(str(path), temp_audio)

            if extracted and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                result = AudioTranscriber.parse(temp_audio)
                result["metadata"]["source"] = "video_extracted_audio"
                return result
            else:
                return {
                    "text": "",
                    "segments": [],
                    "metadata": {"warning": "Could not extract audio from video. Ensure ffmpeg or moviepy is installed."}
                }
        finally:
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except Exception:
                    pass
