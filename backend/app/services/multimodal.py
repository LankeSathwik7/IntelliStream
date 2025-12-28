"""Multi-modal service for image understanding and audio transcription using Groq."""

import base64
from typing import Optional, Dict, List
from groq import AsyncGroq
from app.config import settings
from functools import lru_cache


@lru_cache
def get_groq_client() -> AsyncGroq:
    """Get cached Groq client."""
    return AsyncGroq(api_key=settings.groq_api_key)


class VisionService:
    """
    Image understanding using Groq's Llama Vision models.

    Models:
    - llama-3.2-11b-vision-preview: DEPRECATED
    - llama-3.2-90b-vision-preview: DEPRECATED
    - meta-llama/llama-4-scout-17b-16e-instruct: Current recommended model
    """

    def __init__(self):
        self.client = get_groq_client()
        # Using Llama 4 Scout for vision tasks
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe this image in detail.",
        image_format: str = "jpeg"
    ) -> Optional[str]:
        """
        Analyze an image and return description.

        Args:
            image_data: Raw image bytes
            prompt: Question or instruction about the image
            image_format: Image format (jpeg, png, gif, webp)

        Returns:
            Text description or analysis
        """
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_data).decode("utf-8")
            image_url = f"data:image/{image_format};base64,{base64_image}"

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=1024,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Vision analysis error: {e}")
            return None

    async def analyze_image_url(
        self,
        image_url: str,
        prompt: str = "Describe this image in detail."
    ) -> Optional[str]:
        """Analyze an image from URL."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=1024,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Vision URL analysis error: {e}")
            return None

    async def extract_text_from_image(self, image_data: bytes) -> Optional[str]:
        """OCR - Extract text from an image."""
        return await self.analyze_image(
            image_data,
            prompt="Extract and transcribe all text visible in this image. Return only the extracted text, nothing else."
        )

    async def analyze_chart(self, image_data: bytes) -> Optional[Dict]:
        """Analyze a chart or graph image."""
        description = await self.analyze_image(
            image_data,
            prompt="""Analyze this chart/graph and provide:
1. Type of chart (bar, line, pie, etc.)
2. Title and labels if visible
3. Key data points and trends
4. Main insights

Format as structured analysis."""
        )

        return {"analysis": description} if description else None


class AudioService:
    """
    Audio transcription using Groq's Whisper models.

    Model: whisper-large-v3-turbo (fast and accurate)
    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm
    Max file size: 25MB
    """

    def __init__(self):
        self.client = get_groq_client()
        self.model = "whisper-large-v3-turbo"

    async def transcribe(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3",
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes
            filename: Filename with extension
            language: Language code (e.g., 'en', 'es')
            prompt: Optional prompt to guide transcription

        Returns:
            Dict with transcription and metadata
        """
        try:
            # Create a file-like object
            from io import BytesIO
            audio_file = BytesIO(audio_data)
            audio_file.name = filename

            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language,
                prompt=prompt,
                response_format="verbose_json"
            )

            return {
                "text": response.text,
                "language": response.language,
                "duration": response.duration,
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text
                    }
                    for seg in (response.segments or [])
                ]
            }

        except Exception as e:
            print(f"Audio transcription error: {e}")
            return None

    async def transcribe_simple(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3"
    ) -> Optional[str]:
        """Simple transcription returning just the text."""
        result = await self.transcribe(audio_data, filename)
        return result.get("text") if result else None

    async def translate_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.mp3"
    ) -> Optional[str]:
        """
        Translate audio from any language to English.

        Uses Whisper's translation capability.
        """
        try:
            from io import BytesIO
            audio_file = BytesIO(audio_data)
            audio_file.name = filename

            response = await self.client.audio.translations.create(
                model=self.model,
                file=audio_file,
                response_format="text"
            )

            return response

        except Exception as e:
            print(f"Audio translation error: {e}")
            return None


# Singleton instances
vision_service = VisionService()
audio_service = AudioService()
