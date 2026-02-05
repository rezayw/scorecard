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
// Landing Page Functions
// =====================================

function showLanding() {
    document.getElementById('landingPage').classList.remove('hidden');
    document.getElementById('appHeader').classList.add('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.add('hidden');
    hideAllSteps();
    document.getElementById('courseListSection').classList.add('hidden');
    loadLandingStats();
}

function showGameSetup() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.remove('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.add('hidden');
    showStep(1);
}

function showCourseList() {
    document.getElementById('landingPage').classList.add('hidden');
    document.getElementById('appHeader').classList.remove('hidden');
    document.getElementById('progressBar').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');
    document.getElementById('courseListSection').classList.remove('hidden');
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
