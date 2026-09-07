from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

class Transcriber(ABC):
    @abstractmethod
    async def transcribe(self, video_path) -> list[TranscriptSegment]:
        """Return timestamped segments grounded in the supplied recording."""
        raise NotImplementedError

class NotConfiguredTranscriber(Transcriber):
    async def transcribe(self, video_path):
        raise RuntimeError("Configure a timestamped transcription provider in ai/transcription.py")
