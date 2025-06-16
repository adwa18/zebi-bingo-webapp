// Telegram Web App initialization
const tg = window.Telegram.WebApp;
tg.expand();
tg.setViewportHeight(window.innerHeight)
const userId = tg.initDataUnsafe?.user?.id || new URLSearchParams(window.location.search).get('user_id');
const API_URL = 'https://bingo-webapp.vercel.app/api'; // Update with your Heroku URL
const playerInfo = document.getElementById('playerInfo');
let gameId = null;
let selectedNumber = null;
let currentBet = null;

// DOM Elements
const welcomePage = document.getElementById('welcomePage');
const registerPage = document.getElementById('registerPage');
const returnToBotBtn = document.getElementById('returnToBot');
const checkBalanceBtn = document.getElementById('checkBalance');
const withdrawMoneyBtn = document.getElementById('withdrawMoney');
const topLeadersBtn = document.getElementById('topLeaders');
const inviteFriendsBtn = document.getElementById('inviteFriends');
const adminMenuBtn = document.getElementById('adminMenu');
const gameArea = document.getElementById('gameArea');
const bingoCard = document.getElementById('bingoCard');
const gameStatus = document.getElementById('gameStatus');
const callBtn = document.getElementById('callBtn');
const bingoBtn = document.getElementById('bingoBtn');
const contentDiv = document.getElementById('content');
const calledNumbersDiv = document.getElementById('calledNumbers');
const nightModeSwitch = document.getElementById('nightModeSwitch');
const devInfo = document.getElementById('devInfo');

document.getElementById('homeBtn').addEventListener('click', () => {
    showPage(document.getElementById('mainPage'));
});

document.getElementById('checkBalance').addEventListener('click', () => {
    showPage(document.getElementById('profilePage'));
});

async function checkRegistration() {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) {
            showPage(welcomePage);
        } else {
            showPage(document.getElementById('mainPage')); // Changed from gameArea
            updatePlayerInfo();
            checkAdminStatus();
            initGameModeButtons();
        }
    } catch (error) {
        showPage(welcomePage);
    }
}

async function checkAdminStatus() {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        if (data.role === 'admin') {
            adminMenuBtn.style.display = 'block';
        } else {
            adminMenuBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking admin status:', error);
        adminMenuBtn.style.display = 'none';
    }
}

async function updatePlayerInfo() {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        const username = data.username || `User_${userId}`;
        playerInfo.textContent = `👤 ${username} | 💰 ${data.wallet} ETB`;
    } catch (error) {
        playerInfo.textContent = `👤 User_${userId} | 💰 Loading...`;
    }
}

document.getElementById('nightModeSwitch').addEventListener('change', function() {
    if (this.checked) {
        document.body.classList.add('night-mode');
    } else {
        document.body.classList.remove('night-mode');
    }
});

function generateBingoCard(cardNumbers) {
    bingoCard.innerHTML = '';
    const letters = ['B', 'I', 'N', 'G', 'O'];
    for (let i = 0; i < 5; i++) {
        const letter = document.createElement('div');
        letter.className = 'letter';
        letter.textContent = letters[i];
        bingoCard.appendChild(letter);
    }
    for (let i = 0; i < 25; i++) {
        const cell = document.createElement('div');
        cell.className = 'cell';
        cell.textContent = cardNumbers[i];
        if (i === 12) cell.innerHTML = '<span class="star">★</span>';
        cell.onclick = () => cell.classList.toggle('marked');
        bingoCard.appendChild(cell);
    }
    bingoCard.style.gridTemplateColumns = 'repeat(5, 1fr)';
}

function updateCard(calledNumbers) {
    const cells = bingoCard.getElementsByClassName('cell');
    for (let cell of cells) {
        cell.classList.remove('marked');
        if (cell.textContent && calledNumbers.includes(cell.textContent)) {
            cell.classList.add('marked');
        }
    }
}

function updateGameStatus() {
    if (!gameId) return;
    fetch(`${API_URL}/game_status?game_id=${gameId}&user_id=${userId}`)
        .then(response => response.json())
        .then(data => {
            gameStatus.textContent = `Status: ${data.status} | ${data.start_time ? new Date(data.start_time).toLocaleString() : 'Not Started'} - ${data.end_time ? new Date(data.end_time).toLocaleString() : 'Not Ended'} | Prize: ${data.prize_amount} ETB | Called: ${data.numbers_called.length} | Winner: ${data.winner_id || 'None'} | Players: ${data.players.length}`;
            updateCard(data.numbers_called);
            calledNumbersDiv.textContent = `Called Numbers: ${data.numbers_called.join(', ')}`;
            if (data.card_numbers) generateBingoCard(data.card_numbers);
            const inactiveNumbers = document.getElementById('inactiveNumbers');
            if (inactiveNumbers) inactiveNumbers.innerHTML = data.selected_numbers.map(n => `<span class="inactive">${n}</span>`).join(', ');
            if (data.status === 'finished' && data.winner_id) {
                showPostWinOptions(data.bet_amount);
            }
        });
}

returnToBotBtn.addEventListener('click', () => {
    tg.close();
});

checkBalanceBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';
        contentDiv.innerHTML = `
            <h2>💰 የዋሌት ገጽ</h2>
            <p>ዋሌት: ${data.wallet} ETB</p>
            <p>ያሸነፉት ጨዋታ: ${data.wins} ETB</p>
            <p>ከጋበዛቿቸው ጓደኞች: ${data.successful_referrals * 10} ETB</p>
            <p>የተሳሳተ ቢንጎ መጠየቅ: ${data.invalid_bingo_count}</p>
        `;
        updatePlayerInfo();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
});

withdrawMoneyBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';
        contentDiv.innerHTML = `
            <h2>💸 ገንዘብ ለማውጣት</h2>
            <input id="withdrawAmount" type="number" placeholder="መጠን (ETB)" min="100" />
            <select id="withdrawMethod">
                <option value="telebirr">Telebirr</option>
                <option value="cbe">CBE</option>
            </select>
            <button onclick="requestWithdrawal()">📤 ጠይቅ</button>
            <p id="withdrawMessage"></p>
        `;
        updatePlayerInfo();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
});

function requestWithdrawal() {
    const amount = document.getElementById('withdrawAmount').value;
    const method = document.getElementById('withdrawMethod').value;
    if (!amount || amount < 100) {
        document.getElementById('withdrawMessage').textContent = '❌ መጠን 100 ETB መሆን አለበት!';
        return;
    }
    fetch(`${API_URL}/request_withdrawal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, amount: parseInt(amount), method })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('withdrawMessage').textContent = data.status === 'requested' ? `✅ ጠይቅ ተሳክቷል (ID: ${data.withdraw_id})` : `❌ ${data.reason}`;
        updatePlayerInfo();
    })
    .catch(error => {
        document.getElementById('withdrawMessage').textContent = `አንድነት ችግር: ${error.message}`;
    });
}

topLeadersBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_URL}/leaderboard`);
        const data = await response.json();
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';
        let tableHtml = `
            <h2>🏆 የመሪዎች ዝርዝር</h2>
            <table>
                <tr><th>ቦታ</th><th>ስም</th><th>ነጥብ</th></tr>
        `;
        data.forEach((user, index) => {
            tableHtml += `
                <tr><td>${index + 1}</td><td>${user.username}</td><td>${user.score}</td></tr>
            `;
        });
        tableHtml += '</table>';
        contentDiv.innerHTML = tableHtml;
        updatePlayerInfo();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
});

inviteFriendsBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        const botUsername = tg.initDataUnsafe?.botUsername || 'ZebiBingoBot';
        const referralLink = `https://t.me/${botUsername}?start=ref_${userId}`;
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';

        // Check if we can access contacts
        const canAccessContacts = tg.initDataUnsafe?.can_access_contacts || false;
        
        let friendsListHtml = '';
        if (canAccessContacts) {
            try {
                const contactsResponse = await fetch(`${API_URL}/get_contacts?user_id=${userId}`);
                const contactsData = await contactsResponse.json();
                if (contactsData.contacts && contactsData.contacts.length > 0) {
                    friendsListHtml = `
                        <h3>Select Friends to Invite:</h3>
                        <div id="friendsSelection" style="max-height: 200px; overflow-y: auto; margin: 10px 0;">
                            ${contactsData.contacts.map(contact => `
                                <div style="display: flex; align-items: center; margin: 5px 0;">
                                    <input type="checkbox" id="friend_${contact.user_id}" value="${contact.user_id}">
                                    <label for="friend_${contact.user_id}" style="margin-left: 8px;">
                                        ${contact.first_name || 'User'} ${contact.last_name || ''}
                                    </label>
                                </div>
                            `).join('')}
                        </div>
                        <button onclick="sendDirectInvites()">📩 Send Direct Invites</button>
                        <hr>
                    `;
                }
            } catch (error) {
                console.error('Error fetching contacts:', error);
            }
        }

        contentDiv.innerHTML = `
            <h2>👥 ጓደኞችን ጋብዙ</h2>
            <p>ጓደኞችን ጋብዙና እና 10 ETB ለ 20 ግብዣ ያገኙ!</p>

            ${friendsListHtml}

            <p>የመጠቀምያ አገናኝ (መቅዳት ይችላሉ): <br><strong>${referralLink}</strong></p>
            <p>የተሳጭዎ ጓደኞች: ${data.successful_referrals} | የዕርዳታ መጠን: ${Math.floor(data.successful_referrals / 20) * 10} ETB</p>
            <button onclick="navigator.clipboard.writeText('${referralLink}'); alert('አገናኝ ተቅዳ!')">📋 ቅዳ</button>
        `;
    
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
});
// Direct invites function
async function sendDirectInvites() {
    const checkboxes = document.querySelectorAll('#friendsSelection input[type="checkbox"]:checked');
    const selectedFriends = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedFriends.length === 0) {
        alert('እባክዎ ለመጋበዝ የሚፈልጉትን ጓደኞች ይምረጡ');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/send_invites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId,
                friend_ids: selectedFriends
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            alert(`Invites sent to ${data.sent_count} friends successfully!`);
        } else {
            alert(`Error: ${data.message || 'Failed to send invites'}`);
        }
    } catch (error) {
        alert(`አንድነት ችግር: ${error.message}`);
    }
}
updatePlayerInfo();
checkAdminStatus();
adminMenuBtn.addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_URL}/user_data?user_id=${userId}`);
        const data = await response.json();
        if (data.error || data.role !== 'admin') {
            contentDiv.style.display = 'block';
            gameArea.style.display = 'none';
            contentDiv.innerHTML = '<p>አስተዳዳሪነት አልተፈቀደም!</p>';
            return;
        }
        const withdrawalsResponse = await fetch(`${API_URL}/pending_withdrawals?user_id=${userId}`);
        const withdrawalsData = await withdrawalsResponse.json();
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';
        contentDiv.innerHTML = `
            <h2>🛠 አስተዳዳሪ ገጽ</h2>
            <div class="admin-form">
                <h3>አዲስ አስተዳዳሪ ለመጨመር</h3>
                <input id="newAdminId" placeholder="የተጠቃሚ ID" />
                <button onclick="promoteToAdmin()">👑 አስተዳዳሪ አድርግ</button>
                <h3>ጨዋታ አስተዳደር</h3>
                <input id="gameId" placeholder="ጨዋታ ID" />
                <input id="prizeAmount" type="number" placeholder="የዕምቢታ መጠን (ETB)" min="10" />
                <button onclick="adminAction('start_game')">▶ ጨዋታ ለመጀመር</button>
                <button onclick="adminAction('end_game')">⏹ ጨዋታ ለማቆም</button>
                <h3>የፋይናንስ ማረጋገጫ</h3>
                <input id="txId" placeholder="የፋይናንስ መረጃ ID" />
                <button onclick="adminAction('verify_payment')">✅ የፋይናንስ ማረጋገጫጫ</button>
                <h3>ተጠቃሚ አስተዳደር</h3>
                <input id="userIdToKick" placeholder="የሚባረረው ተጠቃሚ ID" />
                <button onclick="adminAction('kick_user')">🚪 ተጠቃሚን አስወጣ</button>
                <h3>Pending Withdrawals</h3>
                ${withdrawalsData.withdrawals.map(w => `
                    <div>
                        ID: ${w.withdraw_id} | User: ${w.user_id} | Amount: ${w.amount} ETB | Method: ${w.method} | Time: ${new Date(w.request_time).toLocaleString()}
                        <input id="note_${w.withdraw_id}" placeholder="Note" />
                        <button onclick="manageWithdrawal('${w.withdraw_id}', 'approve')">✅ Approve</button>
                        <button onclick="manageWithdrawal('${w.withdraw_id}', 'reject')">❌ Reject</button>
                    </div>
                `).join('')}
            </div>
        `;
        updatePlayerInfo();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
});

// Admin promotion function
async function promoteToAdmin() {
    const newAdminId = document.getElementById('newAdminId').value;
    if (!newAdminId) {
        alert('እባክዎ የተጠቃሚ ID ያስገቡ');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/add_admin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, target_user_id: newAdminId })
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert(`User ${newAdminId} promoted to admin successfully!`);
        } else {
            alert(`Error: ${data.reason || 'Failed to promote user'}`);
        }
    } catch (error) {
        alert(`አንድነት ችግር: ${error.message}`);
    }
}

joinGameBtn.addEventListener('click', async () => {
    if (!gameId) {
        contentDiv.style.display = 'block';
        gameArea.style.display = 'none';
        contentDiv.innerHTML = `
            <h2>👥 ጨዋታ ይቀላቀሉ</h2>
            <button onclick="joinGame(10)">10 ETB</button>
            <button onclick="joinGame(50)">50 ETB</button>
            <button onclick="joinGame(100)">100 ETB</button>
            <button onclick="joinGame(200)">200 ETB</button>
        `;
    }
});

async function joinGame(betAmount) {
    try {
        const response = await fetch(`${API_URL}/create_game`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, bet_amount: betAmount })
        });
        const data = await response.json();
        if (data.status === 'failed') throw new Error(data.reason);
        gameId = data.game_id;
        currentBet = data.bet_amount;
        contentDiv.style.display = 'none';
        gameArea.style.display = 'block';
        gameStatus.textContent = `Status: ${data.status} | Bet: ${data.bet_amount} ETB`;
        displayNumberSelector();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
}

function displayNumberSelector() {
    let html = '<div id="numberSelector" class="number-grid">';
    for (let i = 1; i <= 100; i++) {
        html += `<button class="number-btn" onclick="selectCardNumber(${i})">${i}</button>`;
        if (i % 10 === 0 && i < 100) html += '<br>';
    }
    html += '</div>';
    gameArea.innerHTML = html + gameArea.innerHTML;
}

function selectCardNumber(selectedNum) {
    selectedNumber = selectedNum;
    fetch(`${API_URL}/select_number`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, game_id: gameId, selected_number: selectedNum })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'failed') {
            alert(data.reason);
            document.querySelector(`.number-btn[onclick="selectCardNumber(${selectedNum})"]`).disabled = true;
        } else {
            document.getElementById('numberSelector').style.display = 'none';
            const previewCard = document.createElement('div');
            previewCard.id = 'previewCard';
            for (let i = 0; i < 25; i++) {
                const cell = document.createElement('div');
                cell.className = 'cell';
                cell.textContent = data.card_numbers[i];
                if (i === 12) cell.innerHTML = '<span class="star">★</span>';
                previewCard.appendChild(cell);
            }
            previewCard.style.gridTemplateColumns = 'repeat(5, 1fr)';
            gameArea.insertBefore(previewCard, bingoCard);
            const acceptBtn = document.createElement('button');
            acceptBtn.textContent = 'Accept';
            acceptBtn.onclick = acceptCard;
            const cancelBtn = document.createElement('button');
            cancelBtn.textContent = 'Cancel';
            cancelBtn.onclick = cancelCard;
            gameArea.appendChild(acceptBtn);
            gameArea.appendChild(cancelBtn);
        }
    });
}

function acceptCard() {
    fetch(`${API_URL}/accept_card`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, game_id: gameId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'accepted') {
            document.getElementById('previewCard').remove();
            document.querySelectorAll('#gameArea button').forEach(btn => btn.remove());
            generateBingoCard(data.card_numbers);
            updateGameStatus();
            setInterval(updateGameStatus, 5000);
        }
    });
}

function cancelCard() {
    document.getElementById('previewCard').remove();
    document.querySelectorAll('#gameArea button').forEach(btn => btn.remove());
    displayNumberSelector();
}

function showPostWinOptions(betAmount) {
    gameArea.innerHTML = `
        <div id="postWinMessage">${gameStatus.textContent}</div>
        <button onclick="continuePlay(${betAmount})">Continue Play</button>
        <button onclick="backToBetSelection()">Back to Bet Selection</button>
    `;
    gameId = null;
}

function continuePlay(betAmount) {
    gameId = null;
    currentBet = betAmount;
    contentDiv.style.display = 'none';
    gameArea.style.display = 'block';
    gameStatus.textContent = `Status: Waiting | Bet: ${betAmount} ETB`;
    displayNumberSelector();
}

function backToBetSelection() {
    gameId = null;
    currentBet = null;
    contentDiv.style.display = 'block';
    gameArea.style.display = 'none';
    contentDiv.innerHTML = `
        <h2>👥 ጨዋታ ይቀላቀሉ</h2>
        <button onclick="joinGame(10)">10 ETB</button>
        <button onclick="joinGame(50)">50 ETB</button>
        <button onclick="joinGame(100)">100 ETB</button>
        <button onclick="joinGame(200)">200 ETB</button>
    `;
}

callBtn.addEventListener('click', async () => {
    if (!gameId) return;
    try {
        const response = await fetch(`${API_URL}/call_number`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, game_id: gameId })
        });
        const data = await response.json();
        gameStatus.textContent = `Called: ${data.number} | Remaining: ${data.remaining}`;
        updateCard(data.called_numbers);
        updatePlayerInfo();
    } catch (error) {
        gameStatus.textContent = `Error: ${error.message}`;
    }
});

bingoBtn.addEventListener('click', async () => {
    if (!gameId) return;
    try {
        const response = await fetch(`${API_URL}/check_bingo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, game_id: gameId })
        });
        const data = await response.json();
        gameStatus.textContent = data.message;
        if (data.kicked) {
            tg.close();
        } else if (data.won) {
            alert(data.message);
            updateGameStatus(); // Trigger post-win options
        }
        updatePlayerInfo();
    } catch (error) {
        gameStatus.textContent = `Error: ${error.message}`;
    }
});

async function adminAction(action) {
    const gameId = document.getElementById('gameId')?.value;
    const prizeAmount = document.getElementById('prizeAmount')?.value || 0;
    const txId = document.getElementById('txId')?.value;
    const userIdToKick = document.getElementById('userIdToKick')?.value;
    let payload = { user_id: userId, action };
    if (action.includes('game')) {
        payload.game_id = gameId;
        if (action === 'start_game') payload.prize_amount = parseInt(prizeAmount);
    }
    if (action === 'verify_payment') payload.tx_id = txId;
    if (action === 'kick_user') payload.target_user_id = userIdToKick;

    try {
        const response = await fetch(`${API_URL}/admin_actions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        contentDiv.innerHTML = `<p>${data.status === 'verified' ? `✅ ${data.amount} ETB ለ${data.user_id} ተጠበቃ!` : `✅ ${data.status}!`}</p>`;
        if (data.prize_amount) {
            contentDiv.innerHTML += `<p>የጨዋታ ዕምቢታ: ${data.prize_amount} ETB</p>`;
        }
        updatePlayerInfo();
    } catch (error) {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    }
}

function manageWithdrawal(withdrawId, actionType) {
    const adminNote = document.getElementById(`note_${withdrawId}`).value;
    fetch(`${API_URL}/admin_actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, action: 'manage_withdrawal', withdraw_id: withdrawId, action_type: actionType, admin_note: adminNote })
    })
    .then(response => response.json())
    .then(data => {
        contentDiv.innerHTML = `<p>${data.status === 'approved' ? `✅ ${data.amount} ETB withdrawn for User ${data.user_id}` : `❌ ${data.status}`}</p>`;
        adminMenuBtn.click();
        updatePlayerInfo();
    })
    .catch(error => {
        contentDiv.innerHTML = `<p>አንድነት ችግር: ${error.message}</p>`;
    });
}

// Night Mode Toggle
nightModeSwitch.addEventListener('change', () => {
    document.body.classList.toggle('night-mode', nightModeSwitch.checked);
    document.getElementById('app').classList.toggle('night-mode', nightModeSwitch.checked);
});

// Interactive Developer Info
let isHovering = false;
let isClicked = false;

devInfo.addEventListener('mouseover', () => {
    if (!isClicked) {
        devInfo.textContent = '0913252238';
        isHovering = true;
    }
});

devInfo.addEventListener('mouseout', () => {
    if (!isClicked && isHovering) {
        devInfo.textContent = 'Developed by Benzion Creatives 2025';
        isHovering = false;
    }
});

devInfo.addEventListener('click', () => {
    if (!isClicked) {
        devInfo.textContent = '0913252238';
        isClicked = true;
    } else {
        devInfo.textContent = 'Developed by Benzion Creatives 2025';
        isClicked = false;
    }
});

// Initialize with player info
updatePlayerInfo();