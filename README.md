# Video Transcription Web App

A modern web application for transcribing videos using Google Gemini or OpenAI Whisper APIs.

## Features

- 👤 **User Authentication**: Secure signup/login system with session management
- 🔐 **Multi-User Support**: Each user has their own API keys and transcription history
- 🎬 **Video Upload & Transcription**: Upload videos in various formats (MP4, AVI, MOV, etc.)
- 🔑 **API Key Management**: Securely store and manage your Gemini and OpenAI API keys
- ⚡ **Real-time Status Updates**: Track transcription progress with live WebSocket updates
- 📜 **Transcription History**: View and manage all your past transcriptions
- 🎨 **Modern UI**: Beautiful, responsive dark-themed interface
- 💾 **Local Storage**: SQLite database for storing user accounts, API keys, and transcription history

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio extraction from videos)

### Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Configuration

1. **Get API Keys:**
   - **Google Gemini**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Add API keys through the web interface** (recommended) or directly in the app

## Usage

1. **Start the application:**
```bash
python app.py
```

Or with Flask CLI:
```bash
FLASK_APP=app.py flask run --port 5001
```

2. **Open your browser and navigate to:**
```
http://localhost:5001
```

3. **Create an Account:**
   - Click "Sign Up" on the login page
   - Enter your email and create a password
   - Optionally add your name
   - Click "Create Account"

4. **Setup API Keys:**
   - Go to the "🔑 API Keys" tab
   - Add your Gemini and/or OpenAI API keys
   - Keys are stored securely per user

5. **Transcribe Videos:**
   - Go to "📤 Upload" tab
   - Select your video file
   - Choose transcription provider (Gemini or OpenAI)
   - Click "Start Transcription"
   - Watch real-time progress updates
   - View and copy your transcription

6. **View History:**
   - Go to "📜 History" tab
   - See all your past transcriptions
   - View full transcriptions
   - Delete old entries

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create a new user account
- `POST /api/auth/login` - Login with email and password
- `POST /api/auth/logout` - Logout current user
- `GET /api/auth/user` - Get current logged-in user

### API Keys (requires authentication)
- `GET /api/keys` - List all saved API keys
- `POST /api/keys` - Add/update an API key
- `DELETE /api/keys?provider={provider}` - Delete an API key

### Transcriptions (requires authentication)
- `POST /api/transcribe` - Start video transcription
- `GET /api/transcriptions/{id}` - Get specific transcription
- `GET /api/history` - Get user's transcription history
- `DELETE /api/history/{id}` - Delete a transcription

### WebSocket Events
- `status_update` - Real-time transcription status updates

## Project Structure

```
video transcription/
├── app.py                    # Main Flask application
├── models.py                 # Database models
├── transcription_service.py  # Transcription logic
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Main HTML template
├── static/
│   ├── style.css            # Styles
│   └── script.js            # Frontend JavaScript
└── uploads/                 # Temporary video storage
```

## Features in Detail

### Supported Video Formats
- MP4, AVI, MOV, MKV, WMV, FLV, WebM
- Maximum file size: 500MB

### Transcription Providers

**Google Gemini:**
- Uses Gemini 1.5 Flash model
- Supports longer audio files
- Good for various languages

**OpenAI Whisper:**
- High accuracy transcription
- Automatic chunking for large files
- Supports 99+ languages

### Security
- Password hashing using Werkzeug's security functions
- Session-based authentication
- User data isolation - each user can only access their own data
- API keys stored securely in SQLite database per user
- Keys never sent to external servers except provider APIs
- Temporary files cleaned up after processing

## Troubleshooting

### FFmpeg not found
Make sure FFmpeg is installed and available in your PATH:
```bash
ffmpeg -version
```

### Port already in use
Change the port in `app.py` or when running:
```bash
python app.py  # Edit app.py to change port
```

### API Key errors
- Verify your API keys are valid
- Check your API quota/credits
- Ensure proper API permissions

## Contributing

Feel free to open issues or submit pull requests for improvements!

## License

MIT License - feel free to use this project for personal or commercial purposes.
