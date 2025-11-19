# Video Transcription Web App

A production-ready web application for transcribing videos using AI-powered speech recognition with Google Gemini or OpenAI Whisper APIs.

## Features

- 👤 **User Authentication**: Secure signup/login with email OTP verification
- 🔐 **Multi-User Support**: Isolated user data with encrypted API key storage
- 🎬 **Video Upload & Transcription**: Support for multiple formats (MP4, AVI, MOV, etc.)
- 🗣️ **Speaker Diarization**: AI-powered speaker detection and labeling
- ✨ **Content Enhancement**: Automatic filler word removal and profanity filtering
- 🔑 **Encrypted API Keys**: Fernet encryption for secure API key storage
- 📧 **Email Verification**: OTP-based email verification system
- ⚡ **Real-time Updates**: WebSocket-based live transcription progress
- 📜 **Transcription History**: Complete history with search and management
- 🛡️ **Security Features**: Rate limiting, XSS protection, CSRF prevention
- 🐳 **Docker Ready**: Complete containerization with Docker Compose
- 💾 **PostgreSQL Database**: Production-grade database with Redis caching

## Prerequisites

### For Docker Deployment (Recommended)
- Docker & Docker Compose
- Git

### For Local Development
- Python 3.13 or higher
- PostgreSQL 15+
- Redis 7+
- FFmpeg (for audio extraction)

## Quick Start with Docker 🐳

The easiest way to run the application is using Docker Compose:

1. **Clone the repository:**
```bash
git clone git@github.com:orendrasingh/video-transcription.git
cd video-transcription
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your settings (SMTP credentials, secret key, etc.)
```

3. **Start all services:**
```bash
docker-compose up --build
```

4. **Access the application:**
```
http://localhost:5001
```

That's it! PostgreSQL, Redis, and the Flask app are all running in containers.

### Docker Commands

```bash
# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# View running containers
docker-compose ps
```

## Local Development Setup

### 1. Install Dependencies

**macOS:**
```bash
brew install ffmpeg postgresql redis
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg postgresql redis-server libpq-dev
```

### 2. Setup Database

```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Create database and user
psql postgres
CREATE DATABASE transcription_db;
CREATE USER transcription_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE transcription_db TO transcription_user;
\q
```

### 3. Setup Redis

```bash
# Start Redis
sudo systemctl start redis  # Linux
brew services start redis   # macOS
```

### 4. Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials and SMTP settings
```

### 6. Run Application

```bash
python app.py
```

Open browser to `http://localhost:5001`

## Configuration

### Required Environment Variables

Create a `.env` file with the following:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/transcription_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Email (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-fernet-key-here
```

### Get API Keys

Users add their own API keys through the web interface:
- **Google Gemini**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **OpenAI**: [OpenAI Platform](https://platform.openai.com/api-keys)

## Usage Guide

1. **Sign Up:**
   - Enter email, password, and name
   - Verify email with OTP sent to your inbox
   - Login with verified credentials

2. **Add API Keys:**
   - Navigate to "🔑 API Keys" tab
   - Add your Gemini and/or OpenAI API keys
   - Keys are encrypted and stored securely

3. **Transcribe Videos:**
   - Go to "📤 Upload" tab
   - Select video file (supports MP4, AVI, MOV, MKV, etc.)
   - Choose AI provider (Gemini or OpenAI)
   - Click "Start Transcription"
   - Monitor real-time progress
   - Get enhanced transcription with:
     - Speaker labels (Speaker 1, Speaker 2, etc.)
     - Clean formatting with natural conversation flow
     - Filler words removed
     - Profanity filtered

4. **Manage History:**
   - View all transcriptions in "📜 History" tab
   - Search and filter results
   - Copy or download transcriptions
   - Delete old entries

## Technology Stack

- **Backend**: Flask 3.0, Flask-SocketIO, Flask-SQLAlchemy
- **Database**: PostgreSQL 15 with encrypted storage
- **Cache/Sessions**: Redis 7
- **AI APIs**: Google Gemini 1.5 Flash, OpenAI Whisper + GPT-4o-mini
- **Security**: Flask-Limiter, Fernet encryption, Bleach XSS protection
- **Email**: Flask-Mail with SMTP
- **Containerization**: Docker & Docker Compose
- **Video Processing**: FFmpeg

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create user account
- `POST /api/auth/verify-otp` - Verify email with OTP
- `POST /api/auth/login` - Login with credentials
- `POST /api/auth/logout` - Logout current session
- `GET /api/auth/user` - Get current user info

### API Keys (authenticated)
- `GET /api/keys` - List encrypted API keys
- `POST /api/keys` - Add/update API key
- `DELETE /api/keys?provider={provider}` - Delete API key

### Transcriptions (authenticated)
- `POST /api/transcribe` - Start transcription job
- `GET /api/transcriptions/{id}` - Get transcription details
- `GET /api/history` - Get user's history
- `DELETE /api/history/{id}` - Delete transcription

### WebSocket Events
- `status_update` - Real-time progress updates

## Project Structure

```
video-transcription/
├── app.py                      # Main Flask application
├── models.py                   # SQLAlchemy database models
├── transcription_service.py    # AI transcription logic
├── email_service.py            # OTP email service
├── encryption_service.py       # API key encryption
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Multi-container orchestration
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
├── templates/
│   └── index.html             # Single-page application
├── static/
│   ├── style.css              # Dark theme styles
│   └── script.js              # Frontend logic
└── uploads/                   # Temporary video storage
```

## Features in Detail

### AI-Enhanced Transcription
- **Speaker Diarization**: Automatically detects and labels different speakers
- **Content Filtering**: Removes filler words (um, uh, like) and profanity
- **Natural Flow**: Formats transcriptions with proper paragraphs and punctuation
- **Multi-Provider**: Choose between Gemini (fast, cost-effective) or OpenAI (highly accurate)

### Supported Formats
- **Video**: MP4, AVI, MOV, MKV, WMV, FLV, WebM
- **Maximum Size**: 500MB per file
- **Languages**: 99+ languages supported

### Security Features
- **Email Verification**: OTP-based email verification for new accounts
- **Encrypted Storage**: Fernet encryption for API keys at rest
- **Password Hashing**: Werkzeug security for password storage
- **Rate Limiting**: Redis-backed rate limiting on all endpoints
- **XSS Protection**: Bleach sanitization for user inputs
- **CSRF Protection**: Built-in Flask CSRF protection
- **Session Security**: Secure cookie-based sessions
- **Data Isolation**: Users can only access their own data

## Troubleshooting

### Docker Issues

**Port conflicts:**
```bash
# Check if ports are in use
lsof -i :5001  # App
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Change ports in docker-compose.yml if needed
```

**Database connection errors:**
```bash
# Restart services
docker-compose down
docker-compose up --build
```

**View container logs:**
```bash
docker-compose logs app
docker-compose logs postgres
docker-compose logs redis
```

### Local Development Issues

**FFmpeg not found:**
```bash
ffmpeg -version  # Verify installation
```

**Database connection failed:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Verify credentials in .env match database
```

**Email OTP not sending:**
- Check SMTP credentials in `.env`
- For Gmail, use App Password (not regular password)
- Verify `MAIL_USE_TLS=True` for port 587

**API Key errors:**
- Verify API keys are valid and have credits
- Check provider status pages
- Ensure proper API permissions

### Common Errors

**ModuleNotFoundError:**
```bash
pip install -r requirements.txt
```

**Permission denied:**
```bash
chmod +x uploads/  # Ensure uploads directory is writable
```

## Production Deployment

### Using Docker in Production

1. **Update environment variables:**
   - Set `FLASK_ENV=production`
   - Use strong `SECRET_KEY` and `ENCRYPTION_KEY`
   - Configure production SMTP server

2. **Use production WSGI server:**
   - Replace development server with Gunicorn
   - Add to `requirements.txt`: `gunicorn`
   - Update Dockerfile CMD: `gunicorn -k gevent -w 1 app:app`

3. **Enable HTTPS:**
   - Use nginx reverse proxy
   - Configure SSL certificates (Let's Encrypt)

4. **Backups:**
   - Regular PostgreSQL backups
   - Volume backup for uploads (if persisted)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - free to use for personal or commercial projects.

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing issues for solutions
