// Golf Scorecard Application JavaScript
// =====================================

// Game State
let gameState = {
    courses: {},
    selectedCourse: null,
    holeCount: 0,
    playerCount: 1,
    players: [],
    currentHole: 1,
    scores: {},
    results: null,
    gameId: null
};

// Auth State
let authState = {
    user: null,
    otpType: null,
    otpEmail: null,
    resetToken: null,
    resendTimer: null
};

// Events State
let eventsState = {
    events: [],
    templates: [],
    currentEvent: null,
    currentCategory: 'all'
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    fetchCourses();
    updatePlayerInputs();
    loadHistory();
    loadLandingStats();
    checkAuthStatus();
});

// =====================================
// Authentication Functions
// =====================================

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/me');
        const data = await response.json();
        
        if (data.authenticated) {
            authState.user = data.user;
            updateUIForLoggedInUser();
        }
    } catch (error) {
        console.error('Failed to check auth status:', error);
    }
}

function updateUIForLoggedInUser() {
    if (authState.user) {
        document.getElementById('accountBtnText').textContent = authState.user.name.split(' ')[0];
        document.getElementById('welcomeUserName').textContent = authState.user.name;
        document.getElementById('userWelcomeCard').classList.remove('hidden');
        document.getElementById('quickStatsCard').classList.add('hidden');
    } else {
        document.getElementById('accountBtnText').textContent = 'Login';
        document.getElementById('userWelcomeCard').classList.add('hidden');
        document.getElementById('quickStatsCard').classList.remove('hidden');
    }
}

function showAuthModal() {
    if (authState.user) {
        // Show account menu or logout
        if (confirm('Do you want to logout?')) {
            handleLogout();
        }
        return;
    }
    document.getElementById('authModal').classList.remove('hidden');
    showLoginForm();
}

function hideAuthModal() {
    document.getElementById('authModal').classList.add('hidden');
    clearOtpInputs();
    if (authState.resendTimer) {
        clearInterval(authState.resendTimer);
    }
}

function showLoginForm() {
    document.getElementById('authModalTitle').textContent = 'Login';
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('otpForm').classList.add('hidden');
    document.getElementById('forgotPasswordForm').classList.add('hidden');
    document.getElementById('resetPasswordForm').classList.add('hidden');
}

function showRegisterForm() {
    document.getElementById('authModalTitle').textContent = 'Create Account';
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
    document.getElementById('otpForm').classList.add('hidden');
    document.getElementById('forgotPasswordForm').classList.add('hidden');
    document.getElementById('resetPasswordForm').classList.add('hidden');
}

function showOtpForm(email, type) {
    authState.otpEmail = email;
    authState.otpType = type;
    
    const titles = {
        'verify': 'Verify Email',
        'login': 'Login Verification',
        'reset': 'Reset Password'
    };
    
    document.getElementById('authModalTitle').textContent = titles[type] || 'Verify OTP';
    document.getElementById('otpEmail').textContent = email;
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('otpForm').classList.remove('hidden');
    document.getElementById('forgotPasswordForm').classList.add('hidden');
    document.getElementById('resetPasswordForm').classList.add('hidden');
    
    clearOtpInputs();
    startResendTimer();
    
    // Focus first OTP input
    document.querySelector('.otp-input[data-index="0"]').focus();
}

function showForgotPassword() {
    document.getElementById('authModalTitle').textContent = 'Forgot Password';
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('otpForm').classList.add('hidden');
    document.getElementById('forgotPasswordForm').classList.remove('hidden');
    document.getElementById('resetPasswordForm').classList.add('hidden');
}

function showResetPasswordForm() {
    document.getElementById('authModalTitle').textContent = 'Reset Password';
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.add('hidden');
    document.getElementById('otpForm').classList.add('hidden');
    document.getElementById('forgotPasswordForm').classList.add('hidden');
    document.getElementById('resetPasswordForm').classList.remove('hidden');
}

function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    input.type = input.type === 'password' ? 'text' : 'password';
}

async function handleLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    
    if (!email || !password) {
        showToast('Please fill in all fields');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showOtpForm(email, 'login');
            showToast('OTP sent to your email');
        } else {
            showToast(data.message || 'Login failed');
            if (data.needVerification) {
                showOtpForm(email, 'verify');
            }
        }
    } catch (error) {
        showToast('Login failed. Please try again.');
    }
    
    showLoading(false);
}

async function handleRegister() {
    const name = document.getElementById('registerName').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const phone = document.getElementById('registerPhone').value.trim();
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('registerConfirmPassword').value;
    
    if (!name || !email || !password) {
        showToast('Please fill in all required fields');
        return;
    }
    
    if (password.length < 6) {
        showToast('Password must be at least 6 characters');
        return;
    }
    
    if (password !== confirmPassword) {
        showToast('Passwords do not match');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showOtpForm(email, 'verify');
            showToast('OTP sent to your email');
        } else {
            showToast(data.message || 'Registration failed');
        }
    } catch (error) {
        showToast('Registration failed. Please try again.');
    }
    
    showLoading(false);
}

async function handleForgotPassword() {
    const email = document.getElementById('forgotEmail').value.trim();
    
    if (!email) {
        showToast('Please enter your email');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        showOtpForm(email, 'reset');
        showToast(data.message || 'If email exists, OTP will be sent');
    } catch (error) {
        showToast('Failed to send reset code');
    }
    
    showLoading(false);
}

function getOtpValue() {
    const inputs = document.querySelectorAll('.otp-input');
    return Array.from(inputs).map(input => input.value).join('');
}

function clearOtpInputs() {
    document.querySelectorAll('.otp-input').forEach(input => {
        input.value = '';
    });
}

function handleOtpInput(input) {
    const value = input.value.replace(/\D/g, '');
    input.value = value;
    
    if (value && input.dataset.index < 5) {
        const nextInput = document.querySelector(`.otp-input[data-index="${parseInt(input.dataset.index) + 1}"]`);
        if (nextInput) nextInput.focus();
    }
    
    // Auto-submit when all fields are filled
    if (getOtpValue().length === 6) {
        handleVerifyOtp();
    }
}

function handleOtpKeydown(event, input) {
    if (event.key === 'Backspace' && !input.value && input.dataset.index > 0) {
        const prevInput = document.querySelector(`.otp-input[data-index="${parseInt(input.dataset.index) - 1}"]`);
        if (prevInput) {
            prevInput.focus();
            prevInput.value = '';
        }
    }
}

async function handleVerifyOtp() {
    const otp = getOtpValue();
    
    if (otp.length !== 6) {
        showToast('Please enter the complete OTP');
        return;
    }
    
    showLoading(true);
    
    try {
        let endpoint = '';
        if (authState.otpType === 'verify') {
            endpoint = '/api/auth/verify-register';
        } else if (authState.otpType === 'login') {
            endpoint = '/api/auth/verify-login';
        } else if (authState.otpType === 'reset') {
            endpoint = '/api/auth/verify-reset';
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: authState.otpEmail, otp })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (authState.otpType === 'reset') {
                authState.resetToken = data.resetToken;
                showResetPasswordForm();
                showToast('OTP verified. Create new password.');
            } else {
                authState.user = data.user;
                updateUIForLoggedInUser();
                hideAuthModal();
                showToast('Welcome, ' + data.user.name + '!');
            }
        } else {
            showToast(data.message || 'Invalid OTP');
            clearOtpInputs();
            document.querySelector('.otp-input[data-index="0"]').focus();
        }
    } catch (error) {
        showToast('Verification failed. Please try again.');
    }
    
    showLoading(false);
}

async function handleResetPassword() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmNewPassword').value;
    
    if (!newPassword || !confirmPassword) {
        showToast('Please fill in all fields');
        return;
    }
    
    if (newPassword.length < 6) {
        showToast('Password must be at least 6 characters');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showToast('Passwords do not match');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: authState.otpEmail,
                resetToken: authState.resetToken,
                newPassword
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Password reset successfully');
            showLoginForm();
            document.getElementById('loginEmail').value = authState.otpEmail;
        } else {
            showToast(data.message || 'Reset failed');
        }
    } catch (error) {
        showToast('Reset failed. Please try again.');
    }
    
    showLoading(false);
}

function startResendTimer() {
    let seconds = 60;
    const resendBtn = document.getElementById('resendOtpBtn');
    const timerSpan = document.getElementById('resendTimer');
    
    resendBtn.disabled = true;
    resendBtn.classList.add('opacity-50');
    timerSpan.classList.remove('hidden');
    
    if (authState.resendTimer) {
        clearInterval(authState.resendTimer);
    }
    
    authState.resendTimer = setInterval(() => {
        seconds--;
        timerSpan.textContent = ` (${seconds}s)`;
        
        if (seconds <= 0) {
            clearInterval(authState.resendTimer);
            resendBtn.disabled = false;
            resendBtn.classList.remove('opacity-50');
            timerSpan.classList.add('hidden');
        }
    }, 1000);
}

async function handleResendOtp() {
    showLoading(true);
    
    try {
        const response = await fetch('/api/auth/resend-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: authState.otpEmail,
                type: authState.otpType
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('OTP resent successfully');
            startResendTimer();
        } else {
            showToast(data.message || 'Failed to resend OTP');
        }
    } catch (error) {
        showToast('Failed to resend OTP');
    }
    
    showLoading(false);
}

async function handleLogout() {
    showLoading(true);
    
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        authState.user = null;
        updateUIForLoggedInUser();
        showToast('Logged out successfully');
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    showLoading(false);
}

// =====================================
// Events Functions
// =====================================

function showEvents() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    
    hideAllSteps();
    document.getElementById('courseListSection').classList.add('hidden');
    document.getElementById('forumSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.remove('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    
    const historySection = document.getElementById('historySection');
    if (historySection) historySection.classList.add('hidden');
    
    loadEvents();
    loadEventTemplates();
}

async function loadEvents(category = 'all') {
    eventsState.currentCategory = category;
    const container = document.getElementById('eventsListContainer');
    container.innerHTML = `
        <div class="text-center py-8 text-gray-500">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-amber-500 border-t-transparent mx-auto mb-2"></div>
            <p>Loading events...</p>
        </div>
    `;
    
    try {
        const url = category === 'all' ? '/api/events' : `/api/events?category=${category}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (response.ok) {
            eventsState.events = data;
            renderEvents(data);
        } else {
            throw new Error(data.error || 'Failed to load events');
        }
    } catch (error) {
        console.error('Failed to load events:', error);
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <div class="text-4xl mb-2">😔</div>
                <p>Failed to load events</p>
                <button onclick="loadEvents('${category}')" class="mt-2 text-amber-600 font-medium">Try again</button>
            </div>
        `;
    }
}

async function loadEventTemplates() {
    try {
        const response = await fetch('/api/event-templates');
        const data = await response.json();
        
        if (response.ok) {
            eventsState.templates = data;
            populateTemplateDropdown(data);
        }
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

function populateTemplateDropdown(templates) {
    const select = document.getElementById('eventTemplate');
    if (!select) return;
    
    select.innerHTML = '<option value="">-- Select a template --</option>';
    templates.forEach(template => {
        select.innerHTML += `<option value="${template.id}">${template.name}</option>`;
    });
}

function applyEventTemplate() {
    const templateId = document.getElementById('eventTemplate').value;
    if (!templateId) return;
    
    const template = eventsState.templates.find(t => t.id == templateId);
    if (!template) return;
    
    document.getElementById('eventCategory').value = template.category;
    document.getElementById('eventDescription').value = template.description || '';
    if (template.defaultMaxParticipants) {
        document.getElementById('eventMaxParticipants').value = template.defaultMaxParticipants;
    }
    if (template.defaultFee) {
        document.getElementById('eventFee').value = template.defaultFee;
    }
    
    showToast('Template applied! Customize as needed.');
}

function renderEvents(events) {
    const container = document.getElementById('eventsListContainer');
    
    if (events.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <div class="text-6xl mb-4">📅</div>
                <h3 class="font-semibold text-gray-700 mb-1">No events yet</h3>
                <p class="text-sm">Be the first to create a golf event!</p>
                <button onclick="showCreateEventModal()" class="mt-4 px-6 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full text-sm font-medium">
                    Create Event
                </button>
            </div>
        `;
        return;
    }
    
    const categoryIcons = {
        'tournament': '🏆',
        'monthly-medal': '🎖️',
        'corporate': '🏢',
        'charity': '💝',
        'junior': '👶'
    };
    
    container.innerHTML = events.map(event => {
        const eventDate = new Date(event.eventDate);
        const formattedDate = eventDate.toLocaleDateString('id-ID', { 
            weekday: 'short', 
            day: 'numeric', 
            month: 'short', 
            year: 'numeric' 
        });
        const formattedTime = event.eventTime ? event.eventTime.substring(0, 5) : '';
        const isPast = eventDate < new Date();
        const spotsLeft = event.maxParticipants ? event.maxParticipants - (event.registrationCount || 0) : null;
        
        return `
        <div class="bg-white rounded-xl card-shadow overflow-hidden cursor-pointer hover:shadow-md transition ${isPast ? 'opacity-60' : ''}" 
             onclick="viewEvent(${event.id})">
            <div class="p-4">
                <div class="flex items-start gap-3">
                    <div class="w-12 h-12 bg-gradient-to-br from-amber-100 to-orange-100 rounded-xl flex items-center justify-center flex-shrink-0">
                        <span class="text-2xl">${categoryIcons[event.category] || '📅'}</span>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full font-medium capitalize">
                                ${event.category.replace('-', ' ')}
                            </span>
                            ${isPast ? '<span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">Past</span>' : ''}
                            ${event.status === 'cancelled' ? '<span class="text-xs px-2 py-0.5 bg-red-100 text-red-600 rounded-full">Cancelled</span>' : ''}
                        </div>
                        <h3 class="font-bold text-gray-800 mt-1 truncate">${event.title}</h3>
                        <div class="text-sm text-gray-500 mt-1 space-y-0.5">
                            <p class="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                ${formattedDate}${formattedTime ? ` • ${formattedTime}` : ''}
                            </p>
                            <p class="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                ${event.venue}
                            </p>
                        </div>
                    </div>
                </div>
                ${spotsLeft !== null ? `
                <div class="mt-3 pt-3 border-t flex items-center justify-between text-sm">
                    <span class="text-gray-500">
                        <span class="font-semibold text-gray-700">${event.registrationCount || 0}</span>/${event.maxParticipants} registered
                    </span>
                    ${!isPast && spotsLeft > 0 ? `
                        <span class="text-green-600 font-medium">${spotsLeft} spots left</span>
                    ` : ''}
                    ${!isPast && spotsLeft === 0 ? `
                        <span class="text-red-600 font-medium">Full</span>
                    ` : ''}
                </div>
                ` : ''}
            </div>
        </div>
        `;
    }).join('');
}

function filterEventCategory(category) {
    document.querySelectorAll('.event-category-btn').forEach(btn => {
        if (btn.dataset.category === category) {
            btn.classList.remove('bg-gray-100', 'text-gray-600');
            btn.classList.add('bg-amber-100', 'text-amber-700', 'active');
        } else {
            btn.classList.remove('bg-amber-100', 'text-amber-700', 'active');
            btn.classList.add('bg-gray-100', 'text-gray-600');
        }
    });
    loadEvents(category);
}

async function viewEvent(eventId) {
    try {
        const response = await fetch(`/api/events/${eventId}`);
        const event = await response.json();
        
        if (response.ok) {
            eventsState.currentEvent = event;
            renderEventDetail(event);
            
            document.getElementById('eventsSection').classList.add('hidden');
            document.getElementById('eventDetailSection').classList.remove('hidden');
        } else {
            showToast(event.error || 'Failed to load event');
        }
    } catch (error) {
        console.error('Failed to load event:', error);
        showToast('Failed to load event details');
    }
}

function renderEventDetail(event) {
    const container = document.getElementById('eventDetailContent');
    const eventDate = new Date(event.eventDate);
    const formattedDate = eventDate.toLocaleDateString('id-ID', { 
        weekday: 'long', 
        day: 'numeric', 
        month: 'long', 
        year: 'numeric' 
    });
    const isPast = eventDate < new Date();
    const isRegistered = event.registrations?.some(r => r.email === authState.user?.email);
    const spotsLeft = event.maxParticipants ? event.maxParticipants - (event.registrations?.length || 0) : null;
    const canRegister = !isPast && event.status !== 'cancelled' && (spotsLeft === null || spotsLeft > 0);
    
    const categoryIcons = {
        'tournament': '🏆',
        'monthly-medal': '🎖️',
        'corporate': '🏢',
        'charity': '💝',
        'junior': '👶'
    };
    
    container.innerHTML = `
        <div class="space-y-4">
            <!-- Event Header -->
            <div class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4">
                <div class="flex items-center gap-2 flex-wrap mb-2">
                    <span class="text-2xl">${categoryIcons[event.category] || '📅'}</span>
                    <span class="text-sm px-3 py-1 bg-amber-100 text-amber-700 rounded-full font-medium capitalize">
                        ${event.category.replace('-', ' ')}
                    </span>
                    ${isPast ? '<span class="text-sm px-3 py-1 bg-gray-200 text-gray-600 rounded-full">Past Event</span>' : ''}
                    ${event.status === 'cancelled' ? '<span class="text-sm px-3 py-1 bg-red-100 text-red-600 rounded-full">Cancelled</span>' : ''}
                </div>
                <h2 class="text-xl font-bold text-gray-800">${event.title}</h2>
                <p class="text-sm text-gray-500 mt-1">Organized by ${event.organizer || 'Anonymous'}</p>
            </div>
            
            <!-- Event Details -->
            <div class="bg-white rounded-xl card-shadow p-4 space-y-3">
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800">${formattedDate}</p>
                        <p class="text-sm text-gray-500">${event.eventTime ? event.eventTime.substring(0, 5) + ' WIB' : 'Time TBA'}</p>
                    </div>
                </div>
                
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800">${event.venue}</p>
                        <p class="text-sm text-gray-500">Venue</p>
                    </div>
                </div>
                
                ${event.entryFee ? `
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800">${event.entryFee}</p>
                        <p class="text-sm text-gray-500">Entry Fee</p>
                    </div>
                </div>
                ` : ''}
                
                ${event.contactPerson ? `
                <div class="flex items-start gap-3">
                    <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-semibold text-gray-800">${event.contactPerson}</p>
                        <p class="text-sm text-gray-500">Contact</p>
                    </div>
                </div>
                ` : ''}
            </div>
            
            <!-- Description -->
            ${event.description ? `
            <div class="bg-white rounded-xl card-shadow p-4">
                <h3 class="font-semibold text-gray-800 mb-2">About This Event</h3>
                <p class="text-gray-600 text-sm whitespace-pre-line">${event.description}</p>
            </div>
            ` : ''}
            
            <!-- Registration Status -->
            ${event.maxParticipants ? `
            <div class="bg-white rounded-xl card-shadow p-4">
                <h3 class="font-semibold text-gray-800 mb-3">Registration</h3>
                <div class="flex items-center justify-between mb-2">
                    <span class="text-gray-600">Registered</span>
                    <span class="font-bold text-gray-800">${event.registrations?.length || 0} / ${event.maxParticipants}</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                    <div class="bg-gradient-to-r from-amber-500 to-orange-500 h-2 rounded-full transition-all" 
                         style="width: ${Math.min(100, ((event.registrations?.length || 0) / event.maxParticipants) * 100)}%"></div>
                </div>
                ${event.registrationDeadline ? `
                <p class="text-sm text-gray-500 mt-2">
                    Registration deadline: ${new Date(event.registrationDeadline).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' })}
                </p>
                ` : ''}
            </div>
            ` : ''}
            
            <!-- Participants List -->
            ${event.registrations && event.registrations.length > 0 ? `
            <div class="bg-white rounded-xl card-shadow p-4">
                <h3 class="font-semibold text-gray-800 mb-3">Participants (${event.registrations.length})</h3>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                    ${event.registrations.map((reg, index) => `
                        <div class="flex items-center gap-2 text-sm">
                            <span class="w-6 h-6 bg-amber-100 rounded-full flex items-center justify-center text-xs font-medium text-amber-700">${index + 1}</span>
                            <span class="text-gray-700">${reg.participantName}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
            
            <!-- Action Buttons -->
            <div class="space-y-3 pt-2">
                ${!isPast && event.status !== 'cancelled' ? `
                    ${isRegistered ? `
                        <button onclick="cancelEventRegistration(${event.id})" 
                                class="w-full py-3 bg-red-100 text-red-600 rounded-xl font-semibold hover:bg-red-200 transition">
                            Cancel My Registration
                        </button>
                    ` : `
                        ${canRegister ? `
                            <button onclick="showRegisterEventModal(${event.id})" 
                                    class="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-semibold hover:from-amber-600 hover:to-orange-600 transition">
                                Register for Event
                            </button>
                        ` : `
                            <button disabled 
                                    class="w-full py-3 bg-gray-200 text-gray-500 rounded-xl font-semibold cursor-not-allowed">
                                ${spotsLeft === 0 ? 'Event Full' : 'Registration Closed'}
                            </button>
                        `}
                    `}
                ` : ''}
                
                <button onclick="showEvents()" 
                        class="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition">
                    Back to Events
                </button>
            </div>
        </div>
    `;
}

function showRegisterEventModal(eventId) {
    if (!authState.user) {
        showToast('Please login to register for events');
        showAuthModal('login');
        return;
    }
    
    const event = eventsState.currentEvent;
    const html = `
        <div class="fixed inset-0 bg-black/50 modal-backdrop z-50 flex items-end sm:items-center justify-center" id="registerEventModal">
            <div class="bg-white w-full sm:max-w-md sm:rounded-xl rounded-t-3xl p-6 slide-up">
                <h3 class="text-lg font-bold text-gray-800 mb-4">📝 Register for Event</h3>
                <p class="text-gray-600 mb-4">${event.title}</p>
                
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Your Name *</label>
                        <input type="text" id="regParticipantName" value="${authState.user.name || ''}"
                               class="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-amber-500 focus:ring-0">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                        <input type="email" id="regParticipantEmail" value="${authState.user.email || ''}"
                               class="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-amber-500 focus:ring-0" readonly>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
                        <input type="tel" id="regParticipantPhone" placeholder="e.g., 08123456789"
                               class="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-amber-500 focus:ring-0">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Handicap Index</label>
                        <input type="number" id="regParticipantHandicap" placeholder="e.g., 18" step="0.1"
                               class="w-full p-3 border-2 border-gray-200 rounded-xl focus:border-amber-500 focus:ring-0">
                    </div>
                </div>
                
                <div class="flex gap-3 mt-6">
                    <button onclick="closeRegisterEventModal()" class="flex-1 py-3 bg-gray-200 rounded-xl font-medium">Cancel</button>
                    <button onclick="submitEventRegistration(${eventId})" class="flex-1 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-medium">Register</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', html);
}

function closeRegisterEventModal() {
    const modal = document.getElementById('registerEventModal');
    if (modal) modal.remove();
}

async function submitEventRegistration(eventId) {
    const name = document.getElementById('regParticipantName').value.trim();
    const email = document.getElementById('regParticipantEmail').value.trim();
    const phone = document.getElementById('regParticipantPhone').value.trim();
    const handicap = document.getElementById('regParticipantHandicap').value;
    
    if (!name || !email) {
        showToast('Please fill in required fields');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`/api/events/${eventId}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                participantName: name,
                email: email,
                phone: phone,
                handicap: handicap ? parseFloat(handicap) : null
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Successfully registered! 🎉');
            closeRegisterEventModal();
            viewEvent(eventId); // Refresh event detail
        } else {
            showToast(data.error || 'Registration failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showToast('Failed to register. Please try again.');
    }
    
    showLoading(false);
}

async function cancelEventRegistration(eventId) {
    if (!authState.user) {
        showToast('Please login first');
        return;
    }
    
    if (!confirm('Are you sure you want to cancel your registration?')) {
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`/api/events/${eventId}/cancel-registration`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: authState.user.email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Registration cancelled');
            viewEvent(eventId); // Refresh event detail
        } else {
            showToast(data.error || 'Failed to cancel');
        }
    } catch (error) {
        console.error('Cancel error:', error);
        showToast('Failed to cancel registration');
    }
    
    showLoading(false);
}

function showCreateEventModal() {
    if (!authState.user) {
        showToast('Please login to create events');
        showAuthModal('login');
        return;
    }
    
    // Clear form
    document.getElementById('eventTemplate').value = '';
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventCategory').value = 'tournament';
    document.getElementById('eventDescription').value = '';
    document.getElementById('eventDate').value = '';
    document.getElementById('eventTime').value = '';
    document.getElementById('eventVenue').value = '';
    document.getElementById('eventMaxParticipants').value = '';
    document.getElementById('eventFee').value = '';
    document.getElementById('eventContact').value = '';
    document.getElementById('eventRegDeadline').value = '';
    
    document.getElementById('createEventModal').classList.remove('hidden');
}

function hideCreateEventModal() {
    document.getElementById('createEventModal').classList.add('hidden');
}

async function submitEvent() {
    const title = document.getElementById('eventTitle').value.trim();
    const category = document.getElementById('eventCategory').value;
    const description = document.getElementById('eventDescription').value.trim();
    const eventDate = document.getElementById('eventDate').value;
    const eventTime = document.getElementById('eventTime').value;
    const venue = document.getElementById('eventVenue').value.trim();
    const maxParticipants = document.getElementById('eventMaxParticipants').value;
    const entryFee = document.getElementById('eventFee').value.trim();
    const contactPerson = document.getElementById('eventContact').value.trim();
    const registrationDeadline = document.getElementById('eventRegDeadline').value;
    
    if (!title || !category || !eventDate || !eventTime || !venue) {
        showToast('Please fill in all required fields');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                category,
                description,
                eventDate,
                eventTime,
                venue,
                maxParticipants: maxParticipants ? parseInt(maxParticipants) : null,
                entryFee,
                contactPerson,
                registrationDeadline,
                organizer: authState.user.name || authState.user.email
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Event created successfully! 🎉');
            hideCreateEventModal();
            loadEvents(eventsState.currentCategory);
        } else {
            showToast(data.error || 'Failed to create event');
        }
    } catch (error) {
        console.error('Create event error:', error);
        showToast('Failed to create event');
    }
    
    showLoading(false);
}

// =====================================
// Forum Functions
// =====================================

let forumState = {
    posts: [],
    currentPost: null,
    currentCategory: 'all'
};

function showForum() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    
    hideAllSteps();
    document.getElementById('courseListSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.add('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    document.getElementById('forumSection').classList.remove('hidden');
    
    const historySection = document.getElementById('historySection');
    if (historySection) historySection.classList.add('hidden');
    
    loadForumPosts();
}

async function loadForumPosts(category = 'all') {
    forumState.currentCategory = category;
    const container = document.getElementById('forumPostsContainer');
    container.innerHTML = `
        <div class="text-center py-8 text-gray-500">
            <div class="animate-spin rounded-full h-8 w-8 border-4 border-golf-500 border-t-transparent mx-auto mb-2"></div>
            <p>Loading posts...</p>
        </div>
    `;
    
    try {
        const url = category === 'all' ? '/api/forum/posts' : `/api/forum/posts?category=${category}`;
        const response = await fetch(url);
        const posts = await response.json();
        forumState.posts = posts;
        
        renderForumPosts(posts);
    } catch (error) {
        console.error('Failed to load posts:', error);
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <div class="text-4xl mb-2">😔</div>
                <p>Failed to load posts</p>
                <button onclick="loadForumPosts('${category}')" class="mt-2 text-golf-600 font-medium">Try again</button>
            </div>
        `;
    }
}

function renderForumPosts(posts) {
    const container = document.getElementById('forumPostsContainer');
    
    if (posts.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <div class="text-6xl mb-4">💬</div>
                <h3 class="font-semibold text-gray-700 mb-1">No posts yet</h3>
                <p class="text-sm">Be the first to start a conversation!</p>
                <button onclick="showCreatePostModal()" class="mt-4 px-6 py-2 btn-primary text-white rounded-full text-sm font-medium">
                    Create Post
                </button>
            </div>
        `;
        return;
    }
    
    const categoryIcons = {
        'general': '💬',
        'tips': '🎯',
        'course-review': '⭐',
        'equipment': '🏌️'
    };
    
    container.innerHTML = posts.map(post => `
        <div class="bg-white rounded-xl card-shadow p-4 cursor-pointer hover:shadow-md transition" onclick="viewPost('${post.id}')">
            <div class="flex items-start gap-3">
                <div class="w-10 h-10 bg-golf-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span class="text-lg">${post.userName.charAt(0).toUpperCase()}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="font-medium text-gray-800 text-sm">${post.userName}</span>
                        <span class="text-xs text-gray-400">•</span>
                        <span class="text-xs text-gray-400">${formatTimeAgo(post.createdAt)}</span>
                    </div>
                    <div class="flex items-center gap-2 mb-2">
                        <span class="text-xs bg-golf-50 text-golf-700 px-2 py-0.5 rounded-full">${categoryIcons[post.category] || '💬'} ${formatCategory(post.category)}</span>
                    </div>
                    <h3 class="font-semibold text-gray-800 mb-1 line-clamp-2">${escapeHtml(post.title)}</h3>
                    <p class="text-gray-600 text-sm line-clamp-2">${escapeHtml(post.content)}</p>
                    <div class="flex items-center gap-4 mt-3 text-sm text-gray-500">
                        <span class="flex items-center gap-1 ${post.isLiked ? 'text-red-500' : ''}">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="${post.isLiked ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                            </svg>
                            ${post.likes}
                        </span>
                        <span class="flex items-center gap-1">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            ${post.commentCount}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function filterForumCategory(category) {
    // Update UI
    document.querySelectorAll('.forum-category-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-golf-100', 'text-golf-700');
        btn.classList.add('bg-gray-100', 'text-gray-600');
    });
    
    const activeBtn = document.querySelector(`.forum-category-btn[data-category="${category}"]`);
    if (activeBtn) {
        activeBtn.classList.remove('bg-gray-100', 'text-gray-600');
        activeBtn.classList.add('active', 'bg-golf-100', 'text-golf-700');
    }
    
    loadForumPosts(category);
}

function showCreatePostModal() {
    if (!authState.user) {
        showToast('Please login to create a post');
        showAuthModal();
        return;
    }
    
    document.getElementById('createPostModal').classList.remove('hidden');
    document.getElementById('postTitle').value = '';
    document.getElementById('postContent').value = '';
    document.getElementById('postCategory').value = 'general';
}

function hideCreatePostModal() {
    document.getElementById('createPostModal').classList.add('hidden');
}

async function submitForumPost() {
    const title = document.getElementById('postTitle').value.trim();
    const content = document.getElementById('postContent').value.trim();
    const category = document.getElementById('postCategory').value;
    
    if (!title || !content) {
        showToast('Please fill in all fields');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/forum/posts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, category })
        });
        
        const data = await response.json();
        
        if (data.success) {
            hideCreatePostModal();
            showToast('Post created successfully!');
            loadForumPosts(forumState.currentCategory);
        } else {
            showToast(data.message || 'Failed to create post');
        }
    } catch (error) {
        showToast('Failed to create post');
    }
    
    showLoading(false);
}

async function viewPost(postId) {
    showLoading(true);
    
    try {
        const response = await fetch(`/api/forum/posts/${postId}`);
        const post = await response.json();
        
        if (post.error) {
            showToast('Post not found');
            showLoading(false);
            return;
        }
        
        forumState.currentPost = post;
        renderPostDetail(post);
        document.getElementById('viewPostModal').classList.remove('hidden');
    } catch (error) {
        showToast('Failed to load post');
    }
    
    showLoading(false);
}

function renderPostDetail(post) {
    const categoryIcons = {
        'general': '💬',
        'tips': '🎯',
        'course-review': '⭐',
        'equipment': '🏌️'
    };
    
    const container = document.getElementById('viewPostContent');
    container.innerHTML = `
        <div class="mb-4">
            <div class="flex items-center gap-3 mb-3">
                <div class="w-12 h-12 bg-golf-100 rounded-full flex items-center justify-center">
                    <span class="text-xl">${post.userName.charAt(0).toUpperCase()}</span>
                </div>
                <div>
                    <div class="font-semibold text-gray-800">${post.userName}</div>
                    <div class="text-xs text-gray-400">${formatTimeAgo(post.createdAt)}</div>
                </div>
            </div>
            <span class="inline-block text-xs bg-golf-50 text-golf-700 px-3 py-1 rounded-full mb-3">
                ${categoryIcons[post.category] || '💬'} ${formatCategory(post.category)}
            </span>
            <h2 class="text-xl font-bold text-gray-800 mb-2">${escapeHtml(post.title)}</h2>
            <p class="text-gray-600 whitespace-pre-wrap">${escapeHtml(post.content)}</p>
        </div>
        
        <!-- Like Button -->
        <div class="flex items-center gap-4 py-3 border-y">
            <button onclick="toggleLike('${post.id}')" class="flex items-center gap-2 ${post.isLiked ? 'text-red-500' : 'text-gray-500'} hover:text-red-500 transition">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="${post.isLiked ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span id="postLikeCount">${post.likes}</span> likes
            </button>
            <span class="text-gray-400">•</span>
            <span class="text-gray-500">${post.commentCount} comments</span>
        </div>
        
        <!-- Comments -->
        <div class="mt-4">
            <h3 class="font-semibold text-gray-800 mb-3">Comments</h3>
            <div id="commentsContainer" class="space-y-3">
                ${post.comments && post.comments.length > 0 ? post.comments.map(comment => `
                    <div class="bg-gray-50 rounded-xl p-3">
                        <div class="flex items-center gap-2 mb-1">
                            <div class="w-6 h-6 bg-golf-200 rounded-full flex items-center justify-center text-xs font-medium">
                                ${comment.userName.charAt(0).toUpperCase()}
                            </div>
                            <span class="font-medium text-sm text-gray-800">${comment.userName}</span>
                            <span class="text-xs text-gray-400">${formatTimeAgo(comment.createdAt)}</span>
                        </div>
                        <p class="text-gray-600 text-sm pl-8">${escapeHtml(comment.content)}</p>
                    </div>
                `).join('') : '<p class="text-gray-400 text-sm text-center py-4">No comments yet. Be the first to comment!</p>'}
            </div>
        </div>
    `;
}

function hideViewPostModal() {
    document.getElementById('viewPostModal').classList.add('hidden');
    forumState.currentPost = null;
}

async function toggleLike(postId) {
    if (!authState.user) {
        showToast('Please login to like posts');
        return;
    }
    
    try {
        const response = await fetch(`/api/forum/posts/${postId}/like`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update UI
            forumState.currentPost.isLiked = data.liked;
            forumState.currentPost.likes = data.likes;
            document.getElementById('postLikeCount').textContent = data.likes;
            
            // Update like button appearance
            const likeBtn = document.querySelector(`button[onclick="toggleLike('${postId}')"]`);
            if (likeBtn) {
                likeBtn.classList.toggle('text-red-500', data.liked);
                likeBtn.classList.toggle('text-gray-500', !data.liked);
                const svg = likeBtn.querySelector('svg');
                svg.setAttribute('fill', data.liked ? 'currentColor' : 'none');
            }
            
            // Update post in list
            loadForumPosts(forumState.currentCategory);
        }
    } catch (error) {
        showToast('Failed to update like');
    }
}

async function submitComment() {
    if (!authState.user) {
        showToast('Please login to comment');
        return;
    }
    
    const input = document.getElementById('commentInput');
    const content = input.value.trim();
    
    if (!content) {
        showToast('Please enter a comment');
        return;
    }
    
    if (!forumState.currentPost) return;
    
    try {
        const response = await fetch(`/api/forum/posts/${forumState.currentPost.id}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            input.value = '';
            
            // Add comment to UI
            const commentsContainer = document.getElementById('commentsContainer');
            const noComments = commentsContainer.querySelector('p.text-center');
            if (noComments) noComments.remove();
            
            const commentHtml = `
                <div class="bg-gray-50 rounded-xl p-3 slide-up">
                    <div class="flex items-center gap-2 mb-1">
                        <div class="w-6 h-6 bg-golf-200 rounded-full flex items-center justify-center text-xs font-medium">
                            ${data.comment.userName.charAt(0).toUpperCase()}
                        </div>
                        <span class="font-medium text-sm text-gray-800">${data.comment.userName}</span>
                        <span class="text-xs text-gray-400">just now</span>
                    </div>
                    <p class="text-gray-600 text-sm pl-8">${escapeHtml(data.comment.content)}</p>
                </div>
            `;
            commentsContainer.insertAdjacentHTML('beforeend', commentHtml);
            
            // Update comment count
            forumState.currentPost.commentCount++;
            loadForumPosts(forumState.currentCategory);
            
            showToast('Comment added');
        } else {
            showToast(data.message || 'Failed to add comment');
        }
    } catch (error) {
        showToast('Failed to add comment');
    }
}

function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    
    return date.toLocaleDateString();
}

function formatCategory(category) {
    const names = {
        'general': 'General',
        'tips': 'Tips',
        'course-review': 'Review',
        'equipment': 'Equipment'
    };
    return names[category] || category;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =====================================
// Landing Page Functions
// =====================================

function showLanding() {
    document.getElementById('landingPage').classList.remove('hidden');
    document.getElementById('appHeader').classList.add('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.add('hidden');
    hideAllSteps();
    document.getElementById('courseListSection').classList.add('hidden');
    document.getElementById('forumSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.add('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    loadLandingStats();
}

function showGameSetup() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.remove('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.add('hidden');
    document.getElementById('forumSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.add('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    showStep(1);
}

function showCourseList() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.remove('hidden');
    document.getElementById('forumSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.add('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    hideAllSteps();
    renderCourseList();
}

function hideAllSteps() {
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.add('hidden');
}

async function loadLandingStats() {
    try {
        // Get courses count
        const courseCount = Object.values(gameState.courses).flat().length || 17;
        const regionCount = Object.keys(gameState.courses).length || 6;
        
        document.getElementById('statCourses').textContent = courseCount;
        document.getElementById('statRegions').textContent = regionCount;
        
        // Get games count from history
        const response = await fetch('/api/games/history');
        const history = await response.json();
        document.getElementById('statGames').textContent = history.length || 0;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderCourseList() {
    const container = document.getElementById('courseListContainer');
    container.innerHTML = '';
    
    Object.entries(gameState.courses).forEach(([region, courses]) => {
        const regionDiv = document.createElement('div');
        regionDiv.className = 'mb-6';
        regionDiv.innerHTML = `
            <h3 class="text-sm font-semibold text-golf-600 uppercase tracking-wide mb-3">${region}</h3>
            <div class="space-y-2">
                ${courses.map(course => `
                    <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 hover:border-golf-300 transition cursor-pointer" onclick="selectCourseFromList('${region}', '${course.id}')">
                        <div class="flex justify-between items-start">
                            <div>
                                <h4 class="font-medium text-gray-800">${course.name}</h4>
                                <p class="text-sm text-gray-500">${course.location}</p>
                            </div>
                            <span class="text-xs bg-golf-100 text-golf-700 px-2 py-1 rounded-full">${course.holes} holes</span>
                        </div>
                        <div class="mt-2 flex gap-4 text-xs text-gray-500">
                            <span>Par ${course.par}</span>
                            <span>Rating: ${course.rating?.white || '-'}</span>
                            <span>Slope: ${course.slope?.white || '-'}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        container.appendChild(regionDiv);
    });
}

function selectCourseFromList(region, courseId) {
    document.getElementById('regionSelect').value = region;
    loadCourses();
    setTimeout(() => {
        document.getElementById('courseSelect').value = courseId;
        selectCourse();
        showGameSetup();
    }, 100);
}

// =====================================
// API Functions
// =====================================

async function fetchCourses() {
    try {
        const response = await fetch('/api/courses');
        gameState.courses = await response.json();
        populateRegions();
    } catch (error) {
        showToast('Failed to load courses. Please refresh.');
        console.error(error);
    }
}

async function loadHistory() {
    try {
        const response = await fetch('/api/games/history');
        const history = await response.json();
        renderHistory(history);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// =====================================
// Setup Functions
// =====================================

function populateRegions() {
    const select = document.getElementById('regionSelect');
    select.innerHTML = '<option value="">-- Select Region --</option>';
    
    Object.keys(gameState.courses).forEach(region => {
        const option = document.createElement('option');
        option.value = region;
        option.textContent = region.charAt(0).toUpperCase() + region.slice(1);
        select.appendChild(option);
    });
}

function loadCourses() {
    const region = document.getElementById('regionSelect').value;
    const courseSelect = document.getElementById('courseSelect');
    
    courseSelect.innerHTML = '<option value="">-- Select Course --</option>';
    courseSelect.disabled = !region;
    
    if (region && gameState.courses[region]) {
        gameState.courses[region].forEach(course => {
            const option = document.createElement('option');
            option.value = course.id;
            option.textContent = course.name;
            courseSelect.appendChild(option);
        });
    }
    
    document.getElementById('courseInfo').classList.add('hidden');
    validateSetup();
}

function selectCourse() {
    const courseId = document.getElementById('courseSelect').value;
    const region = document.getElementById('regionSelect').value;
    
    if (courseId && region) {
        gameState.selectedCourse = gameState.courses[region].find(c => c.id === courseId);
        
        document.getElementById('courseInfo').classList.remove('hidden');
        document.getElementById('courseName').textContent = gameState.selectedCourse.name;
        document.getElementById('courseLocation').textContent = gameState.selectedCourse.location;
    } else {
        gameState.selectedCourse = null;
        document.getElementById('courseInfo').classList.add('hidden');
    }
    
    validateSetup();
}

function selectHoles(count) {
    gameState.holeCount = count;
    
    document.querySelectorAll('.hole-btn').forEach(btn => {
        btn.classList.remove('selected', 'border-golf-500', 'bg-golf-50');
    });
    
    event.target.closest('.hole-btn').classList.add('selected', 'border-golf-500', 'bg-golf-50');
    validateSetup();
}

function adjustPlayerCount(delta) {
    gameState.playerCount = Math.max(1, Math.min(10, gameState.playerCount + delta));
    document.getElementById('playerCount').textContent = gameState.playerCount;
    updatePlayerInputs();
    validateSetup();
}

function updatePlayerInputs() {
    const container = document.getElementById('playerInputs');
    container.innerHTML = '';
    
    for (let i = 0; i < gameState.playerCount; i++) {
        const existingPlayer = gameState.players[i] || {};
        
        const div = document.createElement('div');
        div.className = 'bg-gray-50 p-3 rounded-xl';
        div.innerHTML = `
            <div class="flex items-center gap-2 mb-2">
                <span class="w-8 h-8 bg-golf-500 text-white rounded-full flex items-center justify-center text-sm font-bold">${i + 1}</span>
                <input type="text" 
                       class="player-name flex-1 p-2 border border-gray-200 rounded-lg focus:border-golf-500 focus:ring-0" 
                       placeholder="Player ${i + 1} name" 
                       value="${existingPlayer.name || ''}"
                       data-index="${i}"
                       onchange="updatePlayerName(${i}, this.value)">
            </div>
            <div class="mb-2">
                <input type="email" 
                       class="player-email w-full p-2 border border-gray-200 rounded-lg focus:border-golf-500 focus:ring-0 text-sm" 
                       placeholder="Email (optional)" 
                       value="${existingPlayer.email || ''}"
                       onchange="updatePlayerEmail(${i}, this.value)">
            </div>
            <div class="flex items-center gap-2 tee-selector">
                <span class="text-xs text-gray-500">Tee:</span>
                ${['black', 'blue', 'white', 'red'].map(tee => `
                    <input type="radio" name="tee${i}" id="tee${i}${tee}" value="${tee}" class="hidden" ${(existingPlayer.tee || 'white') === tee ? 'checked' : ''} onchange="updatePlayerTee(${i}, '${tee}')">
                    <label for="tee${i}${tee}" class="w-8 h-8 rounded-full cursor-pointer border-2 transition ${getTeeColor(tee)}"></label>
                `).join('')}
                <input type="number" 
                       class="w-16 p-2 border border-gray-200 rounded-lg text-center text-sm" 
                       placeholder="HCP" 
                       min="0" 
                       max="54"
                       value="${existingPlayer.handicap || ''}"
                       onchange="updatePlayerHandicap(${i}, this.value)">
            </div>
        `;
        container.appendChild(div);
    }
}

function getTeeColor(tee) {
    const colors = {
        black: 'bg-gray-900 border-gray-900',
        blue: 'bg-blue-500 border-blue-500',
        white: 'bg-white border-gray-400',
        red: 'bg-red-500 border-red-500'
    };
    return colors[tee] || colors.white;
}

function updatePlayerName(index, value) {
    if (!gameState.players[index]) {
        gameState.players[index] = { tee: 'white', handicap: 0, email: '' };
    }
    gameState.players[index].name = value;
    validateSetup();
}

function updatePlayerEmail(index, value) {
    if (!gameState.players[index]) {
        gameState.players[index] = { name: '', tee: 'white', handicap: 0 };
    }
    gameState.players[index].email = value;
}

function updatePlayerTee(index, value) {
    if (!gameState.players[index]) {
        gameState.players[index] = { name: '', handicap: 0, email: '' };
    }
    gameState.players[index].tee = value;
}

function updatePlayerHandicap(index, value) {
    if (!gameState.players[index]) {
        gameState.players[index] = { name: '', tee: 'white', email: '' };
    }
    gameState.players[index].handicap = parseInt(value) || 0;
}

function validateSetup() {
    const hasRegion = document.getElementById('regionSelect').value;
    const hasCourse = document.getElementById('courseSelect').value;
    const hasHoles = gameState.holeCount > 0;
    
    let allPlayersNamed = true;
    for (let i = 0; i < gameState.playerCount; i++) {
        if (!gameState.players[i] || !gameState.players[i].name?.trim()) {
            allPlayersNamed = false;
            break;
        }
    }
    
    const startBtn = document.getElementById('startBtn');
    startBtn.disabled = !(hasRegion && hasCourse && hasHoles && allPlayersNamed);
}

// =====================================
// Game Functions
// =====================================

async function startGame() {
    // Initialize scores
    gameState.scores = {};
    gameState.players.forEach((player, index) => {
        gameState.scores[index] = Array(gameState.holeCount).fill(0);
    });
    
    gameState.currentHole = 1;
    
    // Create game in database
    try {
        const response = await fetch('/api/games', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: gameState.selectedCourse.id,
                course_name: gameState.selectedCourse.name,
                location: gameState.selectedCourse.location,
                hole_count: gameState.holeCount,
                players: gameState.players.map(p => ({
                    name: p.name,
                    email: p.email || null,
                    tee: p.tee || 'white',
                    handicap: p.handicap || 0
                }))
            })
        });
        
        const data = await response.json();
        gameState.gameId = data.id;
    } catch (error) {
        console.error('Failed to create game:', error);
    }
    
    // Update UI
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.remove('hidden');
    
    updateStepIndicators(2);
    updateHoleDisplay();
    updateScoreEntryCards();
}

function updateStepIndicators(step) {
    document.querySelectorAll('.step-indicator').forEach(indicator => {
        const indicatorStep = parseInt(indicator.dataset.step);
        indicator.classList.remove('active', 'completed');
        
        if (indicatorStep < step) {
            indicator.classList.add('completed');
        } else if (indicatorStep === step) {
            indicator.classList.add('active');
        }
    });
    
    const progress = ((step - 1) / 2) * 100;
    document.getElementById('progressFill').style.width = `${progress}%`;
}

function updateHoleDisplay() {
    document.getElementById('currentHoleNum').textContent = gameState.currentHole;
    document.getElementById('currentHoleTotal').textContent = `/ ${gameState.holeCount}`;
    document.getElementById('currentHolePar').textContent = gameState.selectedCourse.hole_pars[gameState.currentHole - 1];
    
    document.getElementById('prevHoleBtn').disabled = gameState.currentHole === 1;
    
    const nextBtn = document.getElementById('nextHoleBtn');
    if (gameState.currentHole === gameState.holeCount) {
        nextBtn.textContent = 'Finish 🏁';
    } else {
        nextBtn.textContent = 'Next →';
    }
}

function updateScoreEntryCards() {
    const container = document.getElementById('scoreEntryContainer');
    const par = gameState.selectedCourse.hole_pars[gameState.currentHole - 1];
    
    container.innerHTML = gameState.players.map((player, index) => {
        const currentScore = gameState.scores[index][gameState.currentHole - 1] || par;
        
        return `
            <div class="bg-white rounded-xl card-shadow p-4 hole-card">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                        <span class="w-8 h-8 ${getTeeColor(player.tee)} rounded-full flex items-center justify-center text-xs font-bold ${player.tee === 'white' ? 'text-gray-700' : 'text-white'}">${index + 1}</span>
                        <span class="font-semibold text-gray-800">${player.name}</span>
                    </div>
                    <span class="text-xs text-gray-500">HCP: ${player.handicap || 0}</span>
                </div>
                <div class="flex items-center justify-center gap-4">
                    <button onclick="adjustScore(${index}, -1)" class="w-14 h-14 bg-red-100 text-red-600 rounded-xl text-2xl font-bold active:bg-red-200 transition">−</button>
                    <div class="text-center">
                        <input type="number" 
                               id="score${index}" 
                               class="score-input w-20 h-16 text-3xl font-bold text-center border-2 border-gray-200 rounded-xl focus:border-golf-500"
                               value="${currentScore}"
                               min="1"
                               max="15"
                               onchange="setScore(${index}, this.value)">
                        <div id="scoreBadge${index}" class="mt-2 text-xs font-medium px-2 py-1 rounded-full inline-block ${getScoreBadgeClass(currentScore, par)}">
                            ${getScoreName(currentScore, par)}
                        </div>
                    </div>
                    <button onclick="adjustScore(${index}, 1)" class="w-14 h-14 bg-green-100 text-green-600 rounded-xl text-2xl font-bold active:bg-green-200 transition">+</button>
                </div>
            </div>
        `;
    }).join('');
}

function adjustScore(playerIndex, delta) {
    const input = document.getElementById(`score${playerIndex}`);
    let newScore = parseInt(input.value) + delta;
    newScore = Math.max(1, Math.min(15, newScore));
    input.value = newScore;
    setScore(playerIndex, newScore);
}

function setScore(playerIndex, value) {
    const score = parseInt(value) || gameState.selectedCourse.hole_pars[gameState.currentHole - 1];
    gameState.scores[playerIndex][gameState.currentHole - 1] = score;
    
    const par = gameState.selectedCourse.hole_pars[gameState.currentHole - 1];
    const badge = document.getElementById(`scoreBadge${playerIndex}`);
    badge.className = `mt-2 text-xs font-medium px-2 py-1 rounded-full inline-block score-badge ${getScoreBadgeClass(score, par)}`;
    badge.textContent = getScoreName(score, par);
}

function getScoreName(score, par) {
    const diff = score - par;
    if (score === 1) return 'Hole in One!';
    if (diff <= -3) return 'Albatross';
    if (diff === -2) return 'Eagle';
    if (diff === -1) return 'Birdie';
    if (diff === 0) return 'Par';
    if (diff === 1) return 'Bogey';
    if (diff === 2) return 'Double Bogey';
    if (diff === 3) return 'Triple Bogey';
    return `+${diff}`;
}

function getScoreBadgeClass(score, par) {
    const diff = score - par;
    if (score === 1 || diff <= -2) return 'score-eagle';
    if (diff === -1) return 'score-birdie';
    if (diff === 0) return 'score-par';
    if (diff === 1) return 'score-bogey';
    if (diff === 2) return 'score-double';
    return 'score-triple';
}

// =====================================
// Navigation Functions
// =====================================

function prevHole() {
    if (gameState.currentHole > 1) {
        gameState.currentHole--;
        updateHoleDisplay();
        updateScoreEntryCards();
    }
}

function nextHole() {
    // Validate scores
    let allScored = true;
    for (let i = 0; i < gameState.playerCount; i++) {
        if (!gameState.scores[i][gameState.currentHole - 1]) {
            allScored = false;
            break;
        }
    }
    
    if (gameState.currentHole < gameState.holeCount) {
        gameState.currentHole++;
        updateHoleDisplay();
        updateScoreEntryCards();
    } else {
        finishGame();
    }
}

// =====================================
// Finish Game Functions
// =====================================

async function finishGame() {
    showLoading(true);
    
    try {
        const payload = {
            game_id: gameState.gameId,
            course_id: gameState.selectedCourse.id,
            hole_count: gameState.holeCount,
            players: gameState.players.map((player, index) => ({
                name: player.name,
                email: player.email || null,
                tee: player.tee,
                handicap: player.handicap || 0,
                scores: gameState.scores[index]
            }))
        };
        
        const response = await fetch('/api/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        gameState.results = await response.json();
        
        showLoading(false);
        document.getElementById('step2').classList.add('hidden');
        document.getElementById('step3').classList.remove('hidden');
        updateStepIndicators(3);
        
        renderResults();
    } catch (error) {
        showLoading(false);
        showToast('Failed to calculate results. Please try again.');
        console.error(error);
    }
}

// =====================================
// Results Functions
// =====================================

function renderResults() {
    const results = gameState.results;
    
    // Summary
    document.getElementById('resultsSummary').textContent = 
        `${results.course.name} • ${results.hole_count} Holes • ${results.date}`;
    
    // Leaderboard
    const leaderboard = document.getElementById('leaderboard');
    leaderboard.innerHTML = results.results.map((player, index) => {
        const rankIcon = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${player.rank}`;
        const vsParText = player.vs_par > 0 ? `+${player.vs_par}` : player.vs_par;
        
        return `
            <div class="p-4 flex items-center gap-3 ${index === 0 ? 'bg-yellow-50' : ''}">
                <span class="text-2xl w-10 text-center">${rankIcon}</span>
                <div class="flex-1">
                    <div class="font-semibold text-gray-800">${player.name}</div>
                    <div class="text-xs text-gray-500">Tee: ${player.tee.toUpperCase()} • HCP: ${player.course_handicap}</div>
                </div>
                <div class="text-right">
                    <div class="text-lg font-bold ${player.vs_par <= 0 ? 'text-green-600' : 'text-red-600'}">${player.gross_score}</div>
                    <div class="text-xs text-gray-500">Net: ${player.net_score} (${vsParText})</div>
                </div>
            </div>
        `;
    }).join('');
    
    // Scorecard
    renderScorecard();
    
    // Recommendations
    const recsContainer = document.getElementById('recommendations');
    recsContainer.innerHTML = results.recommendations.map(rec => 
        `<p class="text-gray-700">${rec}</p>`
    ).join('');
}

function renderScorecard() {
    const results = gameState.results;
    const holePars = results.course.hole_pars.slice(0, results.hole_count);
    
    let html = '<table class="w-full text-xs">';
    
    // Header row
    html += '<thead class="bg-golf-950 text-white"><tr>';
    html += '<th class="p-2 sticky left-0 bg-golf-950 z-10">Player</th>';
    for (let i = 1; i <= results.hole_count; i++) {
        html += `<th class="p-2 min-w-[2rem]">${i}</th>`;
    }
    html += '<th class="p-2">Tot</th></tr></thead>';
    
    // Par row
    html += '<tbody><tr class="bg-golf-100">';
    html += '<td class="p-2 font-semibold sticky left-0 bg-golf-100 z-10">Par</td>';
    holePars.forEach(par => {
        html += `<td class="p-2 text-center font-medium">${par}</td>`;
    });
    html += `<td class="p-2 text-center font-bold">${results.total_par}</td></tr>`;
    
    // Player rows
    results.results.forEach((player, index) => {
        const bgClass = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';
        html += `<tr class="${bgClass}">`;
        html += `<td class="p-2 font-medium sticky left-0 ${bgClass} z-10 truncate max-w-[80px]">${player.name}</td>`;
        
        player.holes.forEach(hole => {
            const scoreClass = getScoreCellClass(hole.diff);
            html += `<td class="p-2 text-center ${scoreClass}">${hole.score}</td>`;
        });
        
        html += `<td class="p-2 text-center font-bold">${player.gross_score}</td></tr>`;
    });
    
    html += '</tbody></table>';
    document.getElementById('scorecardTable').innerHTML = html;
}

function getScoreCellClass(diff) {
    if (diff <= -2) return 'score-cell-eagle';
    if (diff === -1) return 'score-cell-birdie';
    if (diff === 0) return 'score-cell-par';
    if (diff === 1) return 'score-cell-bogey';
    if (diff >= 2) return 'score-cell-double';
    return '';
}

function toggleScorecard() {
    const table = document.getElementById('scorecardTable');
    table.classList.toggle('hidden');
}

// =====================================
// History Functions
// =====================================

function renderHistory(history) {
    const container = document.getElementById('historyContainer');
    if (!container) return;
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-500 py-8">
                <span class="text-4xl">📋</span>
                <p class="mt-2">No games played yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.map(game => `
        <div class="history-card bg-white rounded-xl card-shadow p-4 mb-3">
            <div class="flex items-center justify-between mb-2">
                <h4 class="font-semibold text-gray-800">${game.course_name}</h4>
                <span class="text-xs text-gray-500">${game.date}</span>
            </div>
            <div class="text-sm text-gray-600 mb-2">${game.location} • ${game.hole_count} Holes</div>
            <div class="flex flex-wrap gap-2">
                ${game.players.map(p => `
                    <span class="text-xs bg-golf-100 text-golf-800 px-2 py-1 rounded-full">
                        ${p.name}: ${p.gross_score}
                    </span>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function showHistory() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.add('hidden');
    document.getElementById('forumSection').classList.add('hidden');
    document.getElementById('eventsSection').classList.add('hidden');
    document.getElementById('eventDetailSection').classList.add('hidden');
    
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.add('hidden');
    document.getElementById('historySection').classList.remove('hidden');
    loadHistory();
}

function hideHistory() {
    document.getElementById('historySection').classList.add('hidden');
    showLanding();
}

function showStep(stepNum) {
    document.getElementById('step1').classList.add('hidden');
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.add('hidden');
    document.getElementById('courseListSection').classList.add('hidden');
    
    const historySection = document.getElementById('historySection');
    if (historySection) {
        historySection.classList.add('hidden');
    }
    
    document.getElementById(`step${stepNum}`).classList.remove('hidden');
    updateStepIndicators(stepNum);
}

// =====================================
// PDF & Email Functions
// =====================================

async function downloadPDF() {
    showLoading(true);
    
    try {
        const response = await fetch('/api/generate-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gameState.results)
        });
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `scorecard_${gameState.results.date}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showLoading(false);
        showToast('PDF downloaded successfully!');
    } catch (error) {
        showLoading(false);
        showToast('Failed to generate PDF.');
        console.error(error);
    }
}

function showEmailModal() {
    document.getElementById('emailModal').classList.remove('hidden');
}

function hideEmailModal() {
    document.getElementById('emailModal').classList.add('hidden');
}

async function sendEmail() {
    const email = document.getElementById('emailInput').value;
    
    if (!email || !email.includes('@')) {
        showToast('Please enter a valid email address.');
        return;
    }
    
    showLoading(true);
    hideEmailModal();
    
    try {
        const response = await fetch('/api/send-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                ...gameState.results
            })
        });
        
        const result = await response.json();
        
        showLoading(false);
        
        if (result.success) {
            showToast('Email sent successfully!');
        } else {
            showToast(result.message || 'Failed to send email. Please download PDF instead.');
        }
    } catch (error) {
        showLoading(false);
        showToast('Failed to send email. Please download PDF instead.');
        console.error(error);
    }
}

// =====================================
// Utility Functions
// =====================================

function resetGame() {
    if (gameState.currentHole > 1 || gameState.results) {
        if (!confirm('Are you sure you want to start a new game? All progress will be lost.')) {
            return;
        }
    }
    
    gameState = {
        courses: gameState.courses,
        selectedCourse: null,
        holeCount: 0,
        playerCount: 1,
        players: [],
        currentHole: 1,
        scores: {},
        results: null,
        gameId: null
    };
    
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.remove('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.add('hidden');
    
    document.getElementById('step1').classList.remove('hidden');
    document.getElementById('step2').classList.add('hidden');
    document.getElementById('step3').classList.add('hidden');
    
    const historySection = document.getElementById('historySection');
    if (historySection) {
        historySection.classList.add('hidden');
    }
    
    document.getElementById('regionSelect').value = '';
    document.getElementById('courseSelect').value = '';
    document.getElementById('courseSelect').disabled = true;
    document.getElementById('courseInfo').classList.add('hidden');
    document.getElementById('playerCount').textContent = '1';
    
    document.querySelectorAll('.hole-btn').forEach(btn => {
        btn.classList.remove('selected', 'border-golf-500', 'bg-golf-50');
    });
    
    updatePlayerInputs();
    updateStepIndicators(1);
    validateSetup();
}

function showLoading(show) {
    document.getElementById('loadingOverlay').classList.toggle('hidden', !show);
}

function showToast(message) {
    const toast = document.getElementById('toast');
    document.getElementById('toastMessage').textContent = message;
    toast.classList.remove('translate-y-20', 'opacity-0');
    
    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
    }, 3000);
}

// Service Worker Registration for PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(reg => console.log('Service Worker registered'))
            .catch(err => console.log('Service Worker not registered', err));
    });
}
