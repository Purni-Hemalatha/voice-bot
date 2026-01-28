import pyttsx3
import threading
import queue
import time
from config import Config

class TextToSpeech:
    """Handles text-to-speech conversion and audio playback."""
    
    def __init__(self):
        self.config = Config()
        self.engine = None
        self.is_speaking = False
        self.speech_queue = queue.Queue()
        self.speech_thread = None
        self.should_stop = False
        
        self._initialize_engine()
        self._start_speech_thread()
    
    def _initialize_engine(self):
        """Initialize the TTS engine with configuration."""
        try:
            self.engine = pyttsx3.init()
            
            # Set speech rate
            self.engine.setProperty('rate', self.config.TTS_RATE)
            
            # Set volume
            self.engine.setProperty('volume', self.config.TTS_VOLUME)
            
            # Get available voices and set a preferred one
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to find a female voice or use the first available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                else:
                    # Use the first voice if no preferred voice found
                    self.engine.setProperty('voice', voices[0].id)
                
                print(f"✓ TTS engine initialized with voice: {self.engine.getProperty('voice')}")
            else:
                print("⚠ No voices available for TTS engine")
                
        except Exception as e:
            print(f"✗ Error initializing TTS engine: {e}")
            self.engine = None
    
    def _start_speech_thread(self):
        """Start the background thread for handling speech queue."""
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()
    
    def _speech_worker(self):
        """Background worker thread for processing speech queue."""
        while not self.should_stop:
            try:
                # Get text from queue with timeout
                text = self.speech_queue.get(timeout=1)
                if text is None:  # Signal to stop
                    break
                
                self._speak_text(text)
                self.speech_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in speech worker: {e}")
    
    def _speak_text(self, text):
        """Internal method to speak text."""
        if not self.engine or not text.strip():
            return
        
        try:
            self.is_speaking = True
            print(f"🔊 Speaking: {text[:50]}...")
            
            self.engine.say(text)
            self.engine.runAndWait()
            
        except Exception as e:
            print(f"Error during speech: {e}")
        finally:
            self.is_speaking = False
    
    def speak(self, text, blocking=False):
        """
        Convert text to speech.
        
        Args:
            text (str): Text to speak
            blocking (bool): If True, wait for speech to complete
        """
        if not text or not text.strip():
            return
        
        if blocking:
            self._speak_text(text)
        else:
            # Add to queue for background processing
            self.speech_queue.put(text)
    
    def speak_streaming(self, text_generator):
        """
        Speak text as it's generated from a generator.
        
        Args:
            text_generator: Generator that yields text chunks
        """
        accumulated_text = ""
        sentence_endings = ['.', '!', '?', '\n']
        
        try:
            for chunk in text_generator:
                accumulated_text += chunk
                
                # Check if we have a complete sentence
                for ending in sentence_endings:
                    if ending in accumulated_text:
                        sentences = accumulated_text.split(ending)
                        # Speak all complete sentences except the last part
                        for sentence in sentences[:-1]:
                            if sentence.strip():
                                self.speak(sentence.strip() + ending)
                        # Keep the remaining text
                        accumulated_text = sentences[-1]
                        break
            
            # Speak any remaining text
            if accumulated_text.strip():
                self.speak(accumulated_text.strip())
                
        except Exception as e:
            print(f"Error in streaming speech: {e}")
    
    def stop_speaking(self):
        """Stop current speech and clear the queue."""
        try:
            if self.engine and self.is_speaking:
                self.engine.stop()
            
            # Clear the speech queue
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except queue.Empty:
                    break
            
            self.is_speaking = False
            print("🔇 Speech stopped")
            
        except Exception as e:
            print(f"Error stopping speech: {e}")
    
    def set_rate(self, rate):
        """Set the speech rate."""
        if self.engine:
            try:
                self.engine.setProperty('rate', rate)
                print(f"Speech rate set to: {rate}")
            except Exception as e:
                print(f"Error setting speech rate: {e}")
    
    def set_volume(self, volume):
        """Set the speech volume (0.0 to 1.0)."""
        if self.engine:
            try:
                volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
                self.engine.setProperty('volume', volume)
                print(f"Speech volume set to: {volume}")
            except Exception as e:
                print(f"Error setting speech volume: {e}")
    
    def get_voices(self):
        """Get list of available voices."""
        if self.engine:
            try:
                voices = self.engine.getProperty('voices')
                return [(voice.id, voice.name) for voice in voices] if voices else []
            except Exception as e:
                print(f"Error getting voices: {e}")
        return []
    
    def set_voice(self, voice_id):
        """Set the voice by ID."""
        if self.engine:
            try:
                self.engine.setProperty('voice', voice_id)
                print(f"Voice set to: {voice_id}")
            except Exception as e:
                print(f"Error setting voice: {e}")
    
    def is_busy(self):
        """Check if TTS is currently speaking."""
        return self.is_speaking or not self.speech_queue.empty()
    
    def wait_until_done(self, timeout=None):
        """Wait until all speech is completed."""
        start_time = time.time()
        while self.is_busy():
            if timeout and (time.time() - start_time) > timeout:
                break
            time.sleep(0.1)
    
    def test_speech(self):
        """Test the TTS functionality."""
        test_text = "Hello! This is a test of the text to speech system."
        print("Testing TTS...")
        self.speak(test_text, blocking=True)
        print("TTS test completed.")
    
    def cleanup(self):
        """Clean up TTS resources."""
        self.should_stop = True
        
        # Signal speech thread to stop
        self.speech_queue.put(None)
        
        # Wait for thread to finish
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2)
        
        # Stop any ongoing speech
        self.stop_speaking()
        
        print("TTS cleanup completed.")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass