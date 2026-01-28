from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import threading
import signal
import sys
import time
from config import Config
from utils.audio_handler import AudioHandler
from utils.openrouter_api import OpenRouterAPI
from utils.text_to_speech import TextToSpeech

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global variables
config = Config()
audio_handler = None
openrouter_api = None
tts = None
conversation_history = []

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Chatbot</title>
    <style>
        body {
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }
        .container {
            background: rgba(255,255,255,0.85);
            border-radius: 24px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.18);
            padding: 48px 36px;
            max-width: 500px;
            width: 100%;
            transition: box-shadow 0.3s;
        }
        .container:hover {
            box-shadow: 0 16px 48px 0 rgba(31, 38, 135, 0.45);
        }
        .header {
            text-align: center;
            margin-bottom: 32px;
        }
        .header h1 {
            color: #3a3a3a;
            font-size: 2.8em;
            font-weight: 800;
            letter-spacing: 1px;
            margin-bottom: 12px;
            text-shadow: 0 2px 8px #c2e9fb;
        }
        .header p {
            color: #5a5a5a;
            font-size: 1.15em;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .chat-container {
            background: rgba(245, 247, 250, 0.85);
            border-radius: 16px;
            padding: 24px 18px;
            margin-bottom: 24px;
            max-height: 320px;
            overflow-y: auto;
            box-shadow: 0 2px 8px rgba(31, 38, 135, 0.07);
            transition: background 0.3s;
        }
        .message {
            margin: 12px 0;
            padding: 12px 18px;
            border-radius: 12px;
            max-width: 85%;
            font-size: 1.08em;
            word-break: break-word;
            animation: fadeIn 0.5s;
        }
        .user-message {
            background: linear-gradient(90deg, #6a89cc 0%, #b8e994 100%);
            color: #fff;
            margin-left: auto;
            text-align: right;
            box-shadow: 0 2px 8px rgba(106,137,204,0.12);
        }
        .ai-message {
            background: linear-gradient(90deg, #f8ffae 0%, #43c6ac 100%);
            color: #333;
            box-shadow: 0 2px 8px rgba(67,198,172,0.10);
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px);}
            to { opacity: 1; transform: translateY(0);}
        }
        .controls {
            display: flex;
            gap: 18px;
            justify-content: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 14px 28px;
            border: none;
            border-radius: 12px;
            font-size: 1.08em;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            min-width: 130px;
            box-shadow: 0 2px 8px rgba(31, 38, 135, 0.10);
        }
        .btn-primary {
            background: linear-gradient(90deg, #43cea2 0%, #185a9d 100%);
            color: white;
        }
        .btn-primary:hover {
            background: linear-gradient(90deg, #185a9d 0%, #43cea2 100%);
            transform: scale(1.04);
        }
        .btn-danger {
            background: linear-gradient(90deg, #ff6a6a 0%, #ffb199 100%);
            color: white;
        }
        .btn-danger:hover {
            background: linear-gradient(90deg, #ffb199 0%, #ff6a6a 100%);
            transform: scale(1.04);
        }
        .btn-success {
            background: linear-gradient(90deg, #56ab2f 0%, #a8e063 100%);
            color: white;
        }
        .btn-success:hover {
            background: linear-gradient(90deg, #a8e063 0%, #56ab2f 100%);
            transform: scale(1.04);
        }
        .btn-secondary {
            background: linear-gradient(90deg, #757f9a 0%, #d7dde8 100%);
            color: #333;
        }
        .btn-secondary:hover {
            background: linear-gradient(90deg, #d7dde8 0%, #757f9a 100%);
            transform: scale(1.04);
        }
        .btn:disabled {
            background: #bdbdbd;
            cursor: not-allowed;
            opacity: 0.7;
            transform: none;
        }
        .status {
            text-align: center;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 24px;
            font-weight: 700;
            font-size: 1.08em;
            box-shadow: 0 2px 8px rgba(31, 38, 135, 0.07);
        }
        .status.recording {
            background: #fff3cd;
            color: #856404;
            border: 2px solid #ffeaa7;
        }
        .status.processing {
            background: #d1ecf1;
            color: #0c5460;
            border: 2px solid #b6d4fe;
        }
        .status.speaking {
            background: #d4edda;
            color: #155724;
            border: 2px solid #c3e6cb;
        }
        .text-input {
            width: 100%;
            padding: 18px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            font-size: 1.08em;
            margin-bottom: 18px;
            resize: vertical;
            min-height: 90px;
            background: rgba(255,255,255,0.95);
            transition: border-color 0.2s;
        }
        .text-input:focus {
            outline: none;
            border-color: #43cea2;
            background: #f8ffae;
        }
        .recording-indicator {
            display: none;
            text-align: center;
            margin: 22px 0;
        }
        .recording-dot {
            width: 18px;
            height: 18px;
            background: #dc3545;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 1s infinite;
            box-shadow: 0 0 8px #dc3545;
        }
        @keyframes pulse {
            0% { opacity: 1; transform: scale(1);}
            50% { opacity: 0.4; transform: scale(1.2);}
            100% { opacity: 1; transform: scale(1);}
        }
        .footer {
            text-align: center;
            margin-top: 36px;
            color: #888;
            font-size: 1em;
            letter-spacing: 0.5px;
            opacity: 0.85;
        }
        /* Add scrollbar styling for chat */
        .chat-container::-webkit-scrollbar {
            width: 8px;
            background: #e9ecef;
            border-radius: 8px;
        }
        .chat-container::-webkit-scrollbar-thumb {
            background: #b8e994;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎤 Voice Chatbot</h1>
            <p>Speak naturally and get AI-powered responses</p>
        </div>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="chat-container" id="chatContainer">
            <div class="message ai-message">
                👋 Hello! I'm your voice assistant. Click "Start Recording" to begin speaking, or type your message below.
            </div>
        </div>
        
        <div class="controls">
            <button id="startRecording" class="btn btn-primary">🎤 Start Recording</button>
            <button id="stopRecording" class="btn btn-danger" disabled>⏹️ Stop Recording</button>
            <button id="stopSpeaking" class="btn btn-success">🔇 Stop Speaking</button>
            <button id="clearChat" class="btn btn-secondary" style="background: #6c757d;">🗑️ Clear Chat</button>
        </div>
        
        <div class="recording-indicator" id="recordingIndicator">
            <div class="recording-dot"></div>
            <span style="margin-left: 10px;">Recording...</span>
        </div>
        
        <textarea id="textInput" class="text-input" placeholder="Or type your message here..."></textarea>
        <button id="sendText" class="btn btn-primary" style="width: 100%;">📝 Send Message</button>
        
        <div class="footer">
            <p>Powered by OpenRouter API | Speech Recognition | Text-to-Speech</p>
        </div>
    </div>

    <script>
        let isRecording = false;
        let isProcessing = false;

        const startRecordingBtn = document.getElementById('startRecording');
        const stopRecordingBtn = document.getElementById('stopRecording');
        const stopSpeakingBtn = document.getElementById('stopSpeaking');
        const clearChatBtn = document.getElementById('clearChat');
        const sendTextBtn = document.getElementById('sendText');
        const textInput = document.getElementById('textInput');
        const chatContainer = document.getElementById('chatContainer');
        const status = document.getElementById('status');
        const recordingIndicator = document.getElementById('recordingIndicator');

        function showStatus(message, type) {
            status.textContent = message;
            status.className = `status ${type}`;
            status.style.display = 'block';
        }

        function hideStatus() {
            status.style.display = 'none';
        }

        function addMessage(content, isUser = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
            messageDiv.textContent = content;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function setRecordingState(recording) {
            isRecording = recording;
            startRecordingBtn.disabled = recording || isProcessing;
            stopRecordingBtn.disabled = !recording;
            recordingIndicator.style.display = recording ? 'block' : 'none';
            
            if (recording) {
                showStatus('🎤 Listening... Speak now!', 'recording');
            }
        }

        function setProcessingState(processing) {
            isProcessing = processing;
            startRecordingBtn.disabled = processing || isRecording;
            sendTextBtn.disabled = processing;
            
            if (processing) {
                showStatus('🤔 Processing your message...', 'processing');
            }
        }

        startRecordingBtn.addEventListener('click', async () => {
            try {
                setRecordingState(true);
                const response = await fetch('/start_recording', { method: 'POST' });
                const data = await response.json();
                
                if (!data.success) {
                    alert('Failed to start recording: ' + data.error);
                    setRecordingState(false);
                    hideStatus();
                }
            } catch (error) {
                console.error('Error starting recording:', error);
                alert('Error starting recording');
                setRecordingState(false);
                hideStatus();
            }
        });

        stopRecordingBtn.addEventListener('click', async () => {
            try {
                setRecordingState(false);
                setProcessingState(true);
                
                const response = await fetch('/stop_recording', { method: 'POST' });
                const data = await response.json();
                
                if (data.success && data.transcribed_text) {
                    addMessage(data.transcribed_text, true);
                    
                    if (data.ai_response) {
                        showStatus('🔊 Speaking response...', 'speaking');
                        addMessage(data.ai_response, false);
                        
                        // Wait for speech to complete
                        setTimeout(() => {
                            hideStatus();
                        }, 3000);
                    }
                } else {
                    alert('Failed to process recording: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error stopping recording:', error);
                alert('Error processing recording');
            } finally {
                setProcessingState(false);
            }
        });

        sendTextBtn.addEventListener('click', async () => {
            const text = textInput.value.trim();
            if (!text) return;
            
            try {
                setProcessingState(true);
                addMessage(text, true);
                textInput.value = '';
                
                const response = await fetch('/send_text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                
                const data = await response.json();
                
                if (data.success && data.ai_response) {
                    showStatus('🔊 Speaking response...', 'speaking');
                    addMessage(data.ai_response, false);
                    
                    // Wait for speech to complete
                    setTimeout(() => {
                        hideStatus();
                    }, 3000);
                } else {
                    alert('Failed to get AI response: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error sending text:', error);
                alert('Error sending message');
            } finally {
                setProcessingState(false);
            }
        });

        stopSpeakingBtn.addEventListener('click', async () => {
            try {
                await fetch('/stop_speaking', { method: 'POST' });
                hideStatus();
            } catch (error) {
                console.error('Error stopping speech:', error);
            }
        });

        clearChatBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the chat history?')) {
                try {
                    await fetch('/clear_history', { method: 'POST' });
                    chatContainer.innerHTML = `
                        <div class="message ai-message">
                            👋 Hello! I'm your voice assistant. Click "Start Recording" to begin speaking, or type your message below.
                        </div>
                    `;
                    hideStatus();
                } catch (error) {
                    console.error('Error clearing chat:', error);
                }
            }
        });

        // Allow Enter key to send text message
        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendTextBtn.click();
            }
        });

        // Initial status
        hideStatus();
    </script>
</body>
</html>
"""

def initialize_components():
    """Initialize all application components."""
    global audio_handler, openrouter_api, tts
    
    try:
        print("Initializing Voice Chatbot...")
        
        # Validate configuration
        config.validate_config()
        
        # Initialize components
        print("Initializing audio handler...")
        audio_handler = AudioHandler()
        
        print("Initializing OpenRouter API...")
        openrouter_api = OpenRouterAPI()
        
        print("Initializing Text-to-Speech...")
        tts = TextToSpeech()
        
        # Test connections
        print("Testing OpenRouter API connection...")
        if openrouter_api.test_connection():
            print("✓ All components initialized successfully!")
        else:
            print("⚠ Warning: OpenRouter API connection test failed")
        
        return True
        
    except Exception as e:
        print(f"✗ Error initializing components: {e}")
        return False

def cleanup_components():
    """Clean up all components on shutdown."""
    global audio_handler, tts
    
    print("Cleaning up components...")
    
    if audio_handler:
        audio_handler.cleanup()
    
    if tts:
        tts.cleanup()
    
    print("Cleanup completed.")

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\nShutting down gracefully...")
    cleanup_components()
    sys.exit(0)

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_recording', methods=['POST'])
def start_recording():
    """Start audio recording."""
    try:
        if audio_handler.start_recording():
            return jsonify({'success': True, 'message': 'Recording started'})
        else:
            return jsonify({'success': False, 'error': 'Already recording'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    """Stop recording and process the audio."""
    global conversation_history
    try:
        # Stop recording and get audio file
        audio_file = audio_handler.stop_recording()
        
        if not audio_file:
            return jsonify({'success': False, 'error': 'No audio recorded'})
        
        # Transcribe audio
        transcribed_text = audio_handler.transcribe_audio(audio_file)
        
        if not transcribed_text:
            return jsonify({'success': False, 'error': 'Could not transcribe audio'})
        
        # Get AI response
        ai_response = openrouter_api.generate_response(transcribed_text, conversation_history=conversation_history)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": transcribed_text})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # Keep conversation history manageable (last 10 exchanges)
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        # Speak the response
        if ai_response:
            tts.speak(ai_response)
        
        return jsonify({
            'success': True,
            'transcribed_text': transcribed_text,
            'ai_response': ai_response
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/send_text', methods=['POST'])
def send_text():
    """Process text input and generate AI response."""
    global conversation_history
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        # Get AI response
        ai_response = openrouter_api.generate_response(text, conversation_history=conversation_history)
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": text})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        # Keep conversation history manageable
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
        
        # Speak the response
        if ai_response:
            tts.speak(ai_response)
        
        return jsonify({
            'success': True,
            'ai_response': ai_response
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop_speaking', methods=['POST'])
def stop_speaking():
    """Stop text-to-speech playback."""
    try:
        tts.stop_speaking()
        return jsonify({'success': True, 'message': 'Speech stopped'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear conversation history."""
    global conversation_history
    try:
        conversation_history = []
        return jsonify({'success': True, 'message': 'History cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/status')
def get_status():
    """Get current application status."""
    return jsonify({
        'recording': audio_handler.is_recording if audio_handler else False,
        'speaking': tts.is_busy() if tts else False,
        'conversation_length': len(conversation_history),
        'components_initialized': all([audio_handler, openrouter_api, tts])
    })

@app.route('/models')
def get_models():
    """Get available AI models."""
    try:
        models = openrouter_api.get_available_models()
        return jsonify({'success': True, 'models': models})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def run_console_mode():
    """Run the application in console mode."""
    print("\n" + "="*50)
    print("VOICE CHATBOT - CONSOLE MODE")
    print("="*50)
    print("Commands:")
    print("  'voice' - Record and send voice message")
    print("  'text' - Send text message")
    print("  'quit' - Exit the application")
    print("="*50 + "\n")
    
    try:
        while True:
            command = input("\nEnter command (voice/text/quit): ").strip().lower();
            
            if command == 'quit':
                break;
            elif command == 'voice':
                print("\nStarting voice recording...")
                transcribed_text = audio_handler.record_and_transcribe();
                
                if transcribed_text:
                    print(f"You said: {transcribed_text}")
                    
                    # Get AI response
                    ai_response = openrouter_api.generate_response(
                        transcribed_text, 
                        conversation_history=conversation_history
                    );
                    
                    if ai_response:
                        print(f"AI: {ai_response}")
                        
                        # Update conversation history
                        conversation_history.append({"role": "user", "content": transcribed_text})
                        conversation_history.append({"role": "assistant", "content": ai_response})
                        
                        # Speak the response
                        tts.speak(ai_response, blocking=True);
                else:
                    print("No speech detected or transcription failed.")
            
            elif command == 'text':
                text = input("Enter your message: ").strip();
                if text:
                    # Get AI response
                    ai_response = openrouter_api.generate_response(
                        text, 
                        conversation_history=conversation_history
                    );
                    
                    if ai_response:
                        print(f"AI: {ai_response}")
                        
                        # Update conversation history
                        conversation_history.append({"role": "user", "content": text})
                        conversation_history.append({"role": "assistant", "content": ai_response})
                        
                        # Speak the response
                        tts.speak(ai_response, blocking=True);
            else:
                print("Invalid command. Use 'voice', 'text', or 'quit'.")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error in console mode: {e}")

if __name__ == '__main__':
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize components
    if not initialize_components():
        print("Failed to initialize components. Exiting.")
        sys.exit(1)
    
    # Check if running in web mode or console mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'console':
        run_console_mode()
    else:
        print(f"\n🚀 Starting Voice Chatbot Web Server...")
        print(f"📱 Open your browser and go to: http://localhost:5000")
        print(f"🎤 You can speak or type messages to interact with the AI")
        print(f"⌨️  Or run 'python app.py console' for console mode")
        print(f"🛑 Press Ctrl+C to stop the server\n")
        
        try:
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=config.DEBUG,
                threaded=True,
                use_reloader=False  # Disable reloader to prevent component re-initialization issues
            )
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            cleanup_components()