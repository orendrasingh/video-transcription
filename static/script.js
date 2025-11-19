// Socket.IO connection
const socket = io();

let currentTranscriptionId = null;
let currentUser = null;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
});

// Check if user is logged in
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/user');
        const data = await response.json();
        
        if (data.user) {
            currentUser = data.user;
            showApp();
        } else {
            showAuth();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showAuth();
    }
}

// Show authentication section
function showAuth() {
    document.getElementById('authSection').style.display = 'flex';
    document.getElementById('appSection').style.display = 'none';
}

// Show main app section
function showApp() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('appSection').style.display = 'block';
    document.getElementById('userEmail').textContent = currentUser.email;
    loadAPIKeys();
}

// Switch between login and signup tabs
function switchAuthTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const otpForm = document.getElementById('otpForm');
    const buttons = document.querySelectorAll('.auth-tab-button');
    
    buttons.forEach(btn => btn.classList.remove('active'));
    
    if (tab === 'login') {
        loginForm.style.display = 'block';
        signupForm.style.display = 'none';
        otpForm.style.display = 'none';
        buttons[0].classList.add('active');
    } else {
        loginForm.style.display = 'none';
        signupForm.style.display = 'block';
        otpForm.style.display = 'none';
        buttons[1].classList.add('active');
    }
}

// Show OTP verification form
let pendingUserId = null;
function showOTPForm(userId) {
    pendingUserId = userId;
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('signupForm').style.display = 'none';
    document.getElementById('otpForm').style.display = 'block';
    document.querySelectorAll('.auth-tab-button').forEach(btn => btn.classList.remove('active'));
}

// Cancel verification and go back to login
function cancelVerification() {
    pendingUserId = null;
    document.getElementById('otpForm').reset();
    switchAuthTab('login');
}

// Resend OTP
async function resendOTP() {
    if (!pendingUserId) {
        showNotification('No pending verification', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/resend-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: pendingUserId })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('New OTP sent to your email!', 'success');
        } else {
            showNotification(data.error || 'Failed to resend OTP', 'error');
        }
    } catch (error) {
        console.error('Resend OTP failed:', error);
        showNotification('Failed to resend OTP', 'error');
    }
}

// Handle login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser = data.user;
            showNotification('Login successful!', 'success');
            showApp();
            document.getElementById('loginForm').reset();
        } else if (response.status === 403 && data.requires_verification) {
            // Email not verified
            showNotification('Please verify your email first', 'warning');
            showOTPForm(data.user_id);
        } else {
            showNotification(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login failed:', error);
        showNotification('Login failed', 'error');
    }
});

// Handle signup
document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('signupName').value;
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    
    if (password.length < 8) {
        showNotification('Password must be at least 8 characters long', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Verification email sent! Check your inbox.', 'success');
            document.getElementById('signupForm').reset();
            showOTPForm(data.user_id);
        } else {
            showNotification(data.error || 'Signup failed', 'error');
        }
    } catch (error) {
        console.error('Signup failed:', error);
        showNotification('Signup failed', 'error');
    }
});

// Handle OTP verification
document.getElementById('otpForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const otp = document.getElementById('otpCode').value;
    
    if (!pendingUserId) {
        showNotification('No pending verification', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: pendingUserId, otp })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentUser = data.user;
            showNotification('Email verified successfully!', 'success');
            document.getElementById('otpForm').reset();
            pendingUserId = null;
            showApp();
        } else {
            showNotification(data.error || 'Verification failed', 'error');
        }
    } catch (error) {
        console.error('Verification failed:', error);
        showNotification('Verification failed', 'error');
    }
});

// Handle logout
async function handleLogout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });
        
        if (response.ok) {
            currentUser = null;
            showNotification('Logged out successfully', 'success');
            showAuth();
        }
    } catch (error) {
        console.error('Logout failed:', error);
        showNotification('Logout failed', 'error');
    }
}

// Tab switching
function openTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-button');
    
    tabs.forEach(tab => tab.classList.remove('active'));
    buttons.forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
    
    // Load data when switching tabs
    if (tabName === 'keys') {
        loadAPIKeys();
    } else if (tabName === 'history') {
        loadHistory();
    }
}

// Load API keys
async function loadAPIKeys() {
    try {
        const response = await fetch('/api/keys');
        if (await handleAPIError(response)) return;
        const keys = await response.json();
        
        const keysList = document.getElementById('keysList');
        
        if (keys.length === 0) {
            keysList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔑</div>
                    <p>No API keys saved yet. Add one above to get started!</p>
                </div>
            `;
            return;
        }
        
        keysList.innerHTML = keys.map(key => `
            <div class="key-item">
                <div class="key-info">
                    <span class="key-provider">${key.provider === 'gemini' ? '🤖 Gemini' : '🔷 OpenAI'}</span>
                    <span class="key-preview">${key.key_preview}</span>
                </div>
                <button class="btn btn-danger" onclick="deleteAPIKey('${key.provider}')">Delete</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load API keys:', error);
        showNotification('Failed to load API keys', 'error');
    }
}

// Save API key
document.getElementById('keyForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const provider = document.getElementById('keyProvider').value;
    const keyValue = document.getElementById('keyValue').value;
    
    try {
        const response = await fetch('/api/keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, key_value: keyValue })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('API key saved successfully!', 'success');
            document.getElementById('keyValue').value = '';
            loadAPIKeys();
        } else {
            showNotification(data.error || 'Failed to save API key', 'error');
        }
    } catch (error) {
        console.error('Failed to save API key:', error);
        showNotification('Failed to save API key', 'error');
    }
});

// Delete API key
async function deleteAPIKey(provider) {
    if (!confirm(`Are you sure you want to delete the ${provider} API key?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/keys?provider=${provider}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('API key deleted successfully!', 'success');
            loadAPIKeys();
        } else {
            showNotification(data.error || 'Failed to delete API key', 'error');
        }
    } catch (error) {
        console.error('Failed to delete API key:', error);
        showNotification('Failed to delete API key', 'error');
    }
}

// Upload form submission
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    const videoFile = document.getElementById('videoFile').files[0];
    const provider = document.getElementById('provider').value;
    
    if (!videoFile) {
        showNotification('Please select a video file', 'error');
        return;
    }
    
    formData.append('video', videoFile);
    formData.append('provider', provider);
    
    // Show status section
    document.getElementById('statusSection').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('statusMessage').textContent = 'Preparing upload...';
    document.getElementById('progressFill').style.width = '5%';
    
    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentTranscriptionId = data.transcription_id;
            document.getElementById('statusMessage').textContent = 'Queued for transcription...';
            document.getElementById('progressFill').style.width = '10%';
            showNotification('Video uploaded! Transcription will start shortly.', 'success');
        } else {
            showNotification(data.error || 'Failed to start transcription', 'error');
            document.getElementById('statusSection').style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to start transcription:', error);
        showNotification('Failed to start transcription', 'error');
        document.getElementById('statusSection').style.display = 'none';
    }
});

// Socket.IO status updates
socket.on('status_update', (data) => {
    console.log('Status update:', data);
    
    // Handle updates for current transcription
    if (data.id === currentTranscriptionId || data.transcription_id === currentTranscriptionId) {
        const transcriptionId = data.id || data.transcription_id;
        const progress = data.progress || 0;
        const message = data.message || 'Processing...';
        const status = data.status;
        
        // Update progress bar and message
        document.getElementById('statusMessage').textContent = message;
        document.getElementById('progressFill').style.width = progress + '%';
        
        if (status === 'uploading') {
            // Upload in progress
            document.getElementById('progressFill').style.width = '5%';
        } else if (status === 'queued') {
            // Queued for processing
            document.getElementById('progressFill').style.width = '10%';
        } else if (status === 'processing') {
            // Processing - use provided progress
            document.getElementById('progressFill').style.width = progress + '%';
        } else if (status === 'completed') {
            document.getElementById('progressFill').style.width = '100%';
            
            // Fetch the complete transcription
            fetch(`/api/transcriptions/${transcriptionId}`)
                .then(response => response.json())
                .then(result => {
                    document.getElementById('statusSection').style.display = 'none';
                    
                    // Show result with full text
                    document.getElementById('resultSection').style.display = 'block';
                    document.getElementById('resultFilename').textContent = result.filename || 'Transcription Result';
                    document.getElementById('transcriptionText').textContent = result.text || 'No transcription available';
                    
                    showNotification('Transcription completed!', 'success');
                    
                    // Reset form and allow new uploads
                    document.getElementById('uploadForm').reset();
                    currentTranscriptionId = null;
                })
                .catch(error => {
                    console.error('Error fetching transcription:', error);
                    showNotification('Transcription completed but failed to fetch result', 'error');
                    document.getElementById('statusSection').style.display = 'none';
                    currentTranscriptionId = null;
                });
        } else if (status === 'failed') {
            document.getElementById('statusSection').style.display = 'none';
            showNotification(message || 'Transcription failed', 'error');
            currentTranscriptionId = null;
            // Allow new uploads
            document.getElementById('uploadForm').reset();
        }
    }
});

// Copy transcription
function copyTranscription() {
    const text = document.getElementById('transcriptionText').textContent;
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Transcription copied to clipboard!', 'success');
    }).catch(() => {
        showNotification('Failed to copy transcription', 'error');
    });
}

// Load history
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        if (await handleAPIError(response)) return;
        const history = await response.json();
        
        const historyList = document.getElementById('historyList');
        
        if (history.length === 0) {
            historyList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📜</div>
                    <p>No transcription history yet. Upload a video to get started!</p>
                </div>
            `;
            return;
        }
        
        historyList.innerHTML = history.map(item => {
            const statusClass = item.status === 'completed' ? 'badge-completed' : 
                               item.status === 'processing' ? 'badge-processing' : 
                               'badge-failed';
            
            return `
                <div class="history-item">
                    <div class="history-header">
                        <div class="history-info">
                            <strong>${item.filename}</strong>
                            <span class="history-badge ${statusClass}">${item.status}</span>
                            <span>${item.provider === 'gemini' ? '🤖 Gemini' : '🔷 OpenAI'}</span>
                        </div>
                        <div class="history-actions">
                            ${item.status === 'completed' ? `
                                <button class="btn btn-secondary" onclick="viewTranscription('${item.id}')">View Full</button>
                            ` : ''}
                            <button class="btn btn-danger" onclick="deleteHistory('${item.id}')">Delete</button>
                        </div>
                    </div>
                    ${item.text ? `
                        <div class="history-text" onclick="viewTranscription('${item.id}')">
                            ${item.text}
                        </div>
                    ` : ''}
                    <div class="history-meta">
                        Created: ${new Date(item.created_at).toLocaleString()}
                        ${item.completed_at ? ` | Completed: ${new Date(item.completed_at).toLocaleString()}` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
        showNotification('Failed to load history', 'error');
    }
}

// View full transcription
async function viewTranscription(id) {
    try {
        const response = await fetch(`/api/transcriptions/${id}`);
        if (await handleAPIError(response)) return;
        const data = await response.json();
        
        if (response.ok && data.text) {
            // Switch to upload tab and show result
            const uploadButton = document.querySelector('.tab-button[onclick*="upload"]');
            if (uploadButton) {
                uploadButton.click();
            }
            
            document.getElementById('statusSection').style.display = 'none';
            document.getElementById('resultSection').style.display = 'block';
            document.getElementById('resultFilename').textContent = data.filename || 'Transcription';
            document.getElementById('transcriptionText').textContent = data.text;
            
            // Scroll to result section
            document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else if (response.ok && !data.text) {
            showNotification('Transcription is empty or still processing', 'warning');
        } else {
            showNotification('Failed to load transcription', 'error');
        }
    } catch (error) {
        console.error('Failed to load transcription:', error);
        showNotification('Failed to load transcription', 'error');
    }
}

// Delete history item
async function deleteHistory(id) {
    if (!confirm('Are you sure you want to delete this transcription?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/history/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Transcription deleted successfully!', 'success');
            loadHistory();
        } else {
            showNotification('Failed to delete transcription', 'error');
        }
    } catch (error) {
        console.error('Failed to delete transcription:', error);
        showNotification('Failed to delete transcription', 'error');
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#6366f1'};
        color: white;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// API error handler
async function handleAPIError(response) {
    if (response.status === 401) {
        showNotification('Session expired. Please login again.', 'error');
        currentUser = null;
        showAuth();
        return true;
    }
    return false;
}
