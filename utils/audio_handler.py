try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    print("Warning: PyAudio not available. Voice recording will be disabled.")
    PYAUDIO_AVAILABLE = False

import wave
import speech_recognition as sr
import threading
import time
import numpy as np
import tempfile
import os
from config import Config

class AudioHandler:
    """Handles audio recording and speech-to-text conversion."""
    
    def __init__(self):
        self.config = Config()
        self.recognizer = sr.Recognizer()
        self.is_recording = False
        self.audio_data = []
        self.recording_thread = None
        
        if PYAUDIO_AVAILABLE:
            self.audio = pyaudio.PyAudio()
            self.microphone = sr.Microphone()
            # Adjust for ambient noise
            self._adjust_for_noise()
        else:
            self.audio = None
            self.microphone = None
            print("Audio recording disabled - PyAudio not available")
    
    def _adjust_for_noise(self):
        """Adjust the recognizer sensitivity to ambient noise."""
        print("Adjusting for ambient noise... Please wait.")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Noise adjustment complete.")
    
    def start_recording(self):
        """Start recording audio in a separate thread."""
        if self.is_recording:
            return False
        
        self.is_recording = True
        self.audio_data = []
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.start()
        return True
    
    def stop_recording(self):
        """Stop recording audio."""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()
        
        if self.audio_data:
            return self._save_audio_to_file()
        return None
    
    def _record_audio(self):
        """Internal method to record audio."""
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.config.AUDIO_CHANNELS,
            rate=self.config.AUDIO_SAMPLE_RATE,
            input=True,
            frames_per_buffer=self.config.AUDIO_CHUNK_SIZE
        )
        
        print("Recording started...")
        start_time = time.time()
        silence_start = None
        
        try:
            while self.is_recording:
                data = stream.read(self.config.AUDIO_CHUNK_SIZE)
                self.audio_data.append(data)
                
                # Check for silence
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                volume = np.sqrt(np.mean(audio_chunk**2))
                
                if volume < self.config.SILENCE_THRESHOLD:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > self.config.SILENCE_DURATION:
                        print("Silence detected, stopping recording...")
                        break
                else:
                    silence_start = None
                
                # Check max duration
                if time.time() - start_time > self.config.MAX_RECORDING_DURATION:
                    print("Maximum recording duration reached.")
                    break
        
        except Exception as e:
            print(f"Error during recording: {e}")
        
        finally:
            stream.stop_stream()
            stream.close()
            self.is_recording = False
            print("Recording stopped.")
    
    def _save_audio_to_file(self):
        """Save recorded audio data to a temporary file."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        
        try:
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.config.AUDIO_CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.config.AUDIO_SAMPLE_RATE)
                wf.writeframes(b''.join(self.audio_data))
            
            return temp_file.name
        except Exception as e:
            print(f"Error saving audio file: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path=None):
        """Convert audio to text using speech recognition."""
        if audio_file_path:
            # Transcribe from file
            try:
                with sr.AudioFile(audio_file_path) as source:
                    audio = self.recognizer.record(source)
                return self._perform_recognition(audio)
            except Exception as e:
                print(f"Error transcribing audio file: {e}")
                return None
        else:
            # Record and transcribe in real-time
            try:
                with self.microphone as source:
                    print("Say something...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                return self._perform_recognition(audio)
            except sr.WaitTimeoutError:
                print("No speech detected within timeout period.")
                return None
            except Exception as e:
                print(f"Error during real-time transcription: {e}")
                return None
    
    def _perform_recognition(self, audio):
        """Perform speech recognition on audio data."""
        try:
            # Try Google Speech Recognition first
            text = self.recognizer.recognize_google(audio)
            print(f"Transcribed text: {text}")
            return text
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Error with speech recognition service: {e}")
            # Fallback to offline recognition if available
            try:
                text = self.recognizer.recognize_sphinx(audio)
                print(f"Transcribed text (offline): {text}")
                return text
            except:
                print("Offline recognition also failed")
                return None
    
    def record_and_transcribe(self):
        """Record audio and return transcribed text."""
        print("Starting voice recording... Speak now!")
        
        # Start recording
        if not self.start_recording():
            return None
        
        # Wait for user to speak or recording to stop automatically
        input("Press Enter to stop recording manually, or wait for automatic stop...")
        
        # Stop recording and get audio file
        audio_file = self.stop_recording()
        
        if not audio_file:
            print("No audio recorded.")
            return None
        
        # Transcribe the audio
        try:
            text = self.transcribe_audio(audio_file)
            return text
        finally:
            # Clean up temporary file
            if audio_file and os.path.exists(audio_file):
                os.unlink(audio_file)
    
    def cleanup(self):
        """Clean up audio resources."""
        if self.is_recording:
            self.stop_recording()
        self.audio.terminate()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass