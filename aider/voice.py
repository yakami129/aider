import os
import queue
import tempfile
import time

import numpy as np

from aider.litellm import litellm

try:
    import soundfile as sf
except (OSError, ModuleNotFoundError):
    sf = None

from prompt_toolkit.shortcuts import prompt

from .dump import dump  # noqa: F401


class SoundDeviceError(Exception):
    """Custom exception for sound device errors."""
    pass


class Voice:
    """Class to handle voice recording and transcription."""
    def __init__(self):
        self.max_rms = 0
        self.min_rms = 1e5
        self.pct = 0
        self.threshold = 0.15
        self.q = queue.Queue()

        self._initialize_sound_device()

    def _initialize_sound_device(self):
        """Initialize the sound device and handle errors."""
        if sf is None:
            raise SoundDeviceError("Soundfile library is not available.")
        try:
            print("Initializing sound device...")
            import sounddevice as sd
            self.sd = sd
        except (OSError, ModuleNotFoundError) as e:
            raise SoundDeviceError(f"Failed to initialize sound device: {e}")

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        rms = np.sqrt(np.mean(indata**2))
        self.max_rms = max(self.max_rms, rms)
        self.min_rms = min(self.min_rms, rms)

        rng = self.max_rms - self.min_rms
        self.pct = (rms - self.min_rms) / rng if rng > 0.001 else 0.5

        self.q.put(indata.copy())

    def get_prompt(self):
        """Generate a recording prompt with a visual progress bar."""
        num = 10
        cnt = int(self.pct * 10) if not np.isnan(self.pct) and self.pct >= self.threshold else 0

        bar = "░" * cnt + "█" * (num - cnt)
        dur = time.time() - self.start_time
        return f"Recording, press ENTER when done... {dur:.1f}sec {bar[:num]}"

    def record_and_transcribe(self, history=None, language=None):
        """Record audio and transcribe it using the specified model."""
        try:
            return self.raw_record_and_transcribe(history, language)
        except KeyboardInterrupt:
            print("Recording interrupted.")
            return None

    def raw_record_and_transcribe(self, history, language):
        """Handle the raw recording and transcription process."""
        filename = tempfile.mktemp(suffix=".wav")
        sample_rate = 16000  # 16kHz
        self.start_time = time.time()

        with self.sd.InputStream(samplerate=sample_rate, channels=1, callback=self.callback):
            prompt(self.get_prompt, refresh_interval=0.1)

        self._write_audio_to_file(filename)

        return self._transcribe_audio(filename, history, language)

    def _write_audio_to_file(self, filename):
        """Write recorded audio data to a WAV file."""
        try:
            with sf.SoundFile(filename, mode="x", samplerate=16000, channels=1) as file:
                while not self.q.empty():
                    file.write(self.q.get())
        except Exception as e:
            raise SoundDeviceError(f"Error writing audio to file: {e}")

    def _transcribe_audio(self, filename, history, language):
        """Transcribe the audio file using the litellm model."""
        try:
            with open(filename, "rb") as fh:
                transcript = litellm.transcription(
                    model="whisper-1", file=fh, prompt=history, language=language
                )
            return transcript.text
        except Exception as e:
            raise SoundDeviceError(f"Error during transcription: {e}")
        
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")
    print(Voice().record_and_transcribe())
