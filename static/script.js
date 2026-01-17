const API_URL = '';  // Use relative URLs to avoid cross-origin issues
let cooldownInterval = null;
let lastRollResult = null;
let autoRollEnabled = false;
let autoRollTimeout = null;

// Check session on load
window.onload = async () => {
    try {
        const response = await fetch(`${API_URL}/check_session`, {
            credentials: 'include'
        });
        const data = await response.json();
        
        if (data.logged_in) {
            showGame(data.username);
            loadInventory();
            checkCooldown();
        }
    } catch (error) {
        console.error('Error checking session:', error);
    }
};

// Update when returning to tab
window.addEventListener('visibilitychange', async () => {
    if (!document.hidden && document.getElementById('game-container').style.display !== 'none') {
        // User returned to tab and is logged in
        loadInventory();
        checkCooldown();
    }
});

// Also update when window gains focus
window.addEventListener('focus', async () => {
    if (document.getElementById('game-container').style.display !== 'none') {
        loadInventory();
        checkCooldown();
    }
});

function showLogin() {
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
    document.getElementById('auth-message').textContent = '';
}

function showRegister() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
    document.getElementById('auth-message').textContent = '';
}

async function register() {
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    
    if (!username || !password) {
        showMessage('Please enter username and password', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage('Registration successful! Please login.', 'success');
            setTimeout(showLogin, 1500);
        } else {
            showMessage(data.error, 'error');
        }
    } catch (error) {
        showMessage('Error connecting to server', 'error');
    }
}

async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    if (!username || !password) {
        showMessage('Please enter username and password', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showGame(username);
            loadInventory();
            checkCooldown();
        } else {
            showMessage(data.error, 'error');
        }
    } catch (error) {
        showMessage('Error connecting to server', 'error');
    }
}

async function logout() {
    try {
        await fetch(`${API_URL}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        
        showAuth();
        lastRollResult = null;
        autoRollEnabled = false;
        document.getElementById('auto-roll-toggle').checked = false;
        if (cooldownInterval) {
            clearInterval(cooldownInterval);
        }
        if (autoRollTimeout) {
            clearTimeout(autoRollTimeout);
        }
    } catch (error) {
        console.error('Error logging out:', error);
    }
}

function showMessage(message, type) {
    const messageDiv = document.getElementById('auth-message');
    messageDiv.textContent = message;
    messageDiv.className = type;
}

function showAuth() {
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('game-container').style.display = 'none';
    document.getElementById('login-username').value = '';
    document.getElementById('login-password').value = '';
    document.getElementById('register-username').value = '';
    document.getElementById('register-password').value = '';
    showLogin();
}

function showGame(username) {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('game-container').style.display = 'flex';
    document.getElementById('username-display').textContent = username;
}

async function roll() {
    const button = document.getElementById('roll-btn');
    button.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/roll`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            lastRollResult = data.rarity;
            displayLastRoll(data.rarity, data.modifier, data.gradient);
            loadInventory();
            startCooldown(10);
        } else if (response.status === 429) {
            // Cooldown active
            startCooldown(data.remaining);
        } else {
            alert(data.error || 'Error rolling RNG');
            button.disabled = false;
        }
    } catch (error) {
        console.error('Error rolling:', error);
        alert('Error connecting to server');
        button.disabled = false;
    }
}

function toggleAutoRoll() {
    autoRollEnabled = document.getElementById('auto-roll-toggle').checked;
    
    if (autoRollEnabled) {
        // Try to roll immediately if not on cooldown
        const button = document.getElementById('roll-btn');
        if (!button.disabled) {
            roll();
        }
    } else {
        // Cancel any pending auto roll
        if (autoRollTimeout) {
            clearTimeout(autoRollTimeout);
            autoRollTimeout = null;
        }
    }
}

function displayLastRoll(rarity, modifier, gradient) {
    const lastRollDiv = document.getElementById('last-roll');
    const modifierText = modifier ? `${modifier} ` : '';
    lastRollDiv.textContent = `Last Roll: ${modifierText}1 in ${rarity}`;
    
    // Apply gradient if modifier exists
    if (gradient) {
        lastRollDiv.style.background = gradient;
    } else {
        lastRollDiv.style.background = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
    }
    
    // Add animation
    lastRollDiv.style.animation = 'none';
    setTimeout(() => {
        lastRollDiv.style.animation = 'pulse 0.5s ease-in-out';
    }, 10);
}

async function loadInventory() {
    try {
        const response = await fetch(`${API_URL}/inventory`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayInventory(data.inventory);
        }
    } catch (error) {
        console.error('Error loading inventory:', error);
    }
}

function displayInventory(inventory) {
    const inventoryList = document.getElementById('inventory-list');
    
    if (inventory.length === 0) {
        inventoryList.innerHTML = '<div class="empty-inventory">No items yet. Start rolling!</div>';
        return;
    }
    
    inventoryList.innerHTML = '';
    
    inventory.forEach(item => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'inventory-item';
        
        const rarityBadge = document.createElement('span');
        rarityBadge.className = 'rarity-badge';
        
        if (item.modifier) {
            rarityBadge.classList.add(`modifier-${item.modifier.name.toLowerCase()}`);
            rarityBadge.textContent = `${item.modifier.name} 1 in ${item.rarity}`;
        } else {
            rarityBadge.textContent = `1 in ${item.rarity}`;
        }
        
        const countBadge = document.createElement('span');
        countBadge.className = 'count-badge';
        countBadge.textContent = `x ${item.count}`;
        
        itemDiv.appendChild(rarityBadge);
        itemDiv.appendChild(countBadge);
        
        inventoryList.appendChild(itemDiv);
    });
}

async function checkCooldown() {
    try {
        const response = await fetch(`${API_URL}/cooldown`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.on_cooldown) {
            startCooldown(data.remaining);
        }
    } catch (error) {
        console.error('Error checking cooldown:', error);
    }
}

function startCooldown(seconds) {
    const button = document.getElementById('roll-btn');
    const cooldownDisplay = document.getElementById('cooldown-display');
    
    button.disabled = true;
    
    if (cooldownInterval) {
        clearInterval(cooldownInterval);
    }
    
    // If seconds > 10 (clock skew), apply modulo to wrap it. If it's 0 after modulo, use 10.
    if (seconds > 10) {
        seconds = seconds % 10 || 10;
    }
    // Clamp to max 10
    seconds = Math.min(Math.max(seconds, 0), 10);
    
    if (seconds <= 0) {
        button.disabled = false;
        cooldownDisplay.textContent = '';
        return;
    }
    
    const endTime = Date.now() + (seconds * 1000);
    
    const updateCooldown = () => {
        const remaining = (endTime - Date.now()) / 1000;
        
        if (remaining <= 0) {
            clearInterval(cooldownInterval);
            button.disabled = false;
            cooldownDisplay.textContent = '';
            
            // If auto-roll is enabled, schedule next roll
            if (autoRollEnabled) {
                autoRollTimeout = setTimeout(() => {
                    roll();
                }, 100);
            }
        } else {
            // Clamp display to max 10s
            const displayRemaining = Math.min(remaining, 10);
            cooldownDisplay.textContent = `Cooldown: ${displayRemaining.toFixed(1)}s`;
        }
    };
    
    updateCooldown();
    cooldownInterval = setInterval(updateCooldown, 100);
}

// Add CSS animation for pulse effect
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
`;
document.head.appendChild(style);
