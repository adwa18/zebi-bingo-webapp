from flask import Flask, request, jsonify, send_from_directory
import psycopg2
import random
from datetime import datetime, timedelta
import os

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, '../public')

TOKEN = os.environ.get('TOKEN', '8119390210:AAFjN2YTSaPEyae9N9otMZ6kaNoo4-gns18')  # Fallback to hardcoded value
WEB_APP_URL = os.environ.get('WEB_APP_URL', 'http://bingo-webapp.vercel.app')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '5380773431').split(',')]
DATABASE_URL = os.environ.get('DATABASE_URL')

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')

# --- Static File Serving ---
@app.route('/')
def serve_index():
    print(f"Serving index.html from {os.path.join(STATIC_FOLDER, 'index.html')}")
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    print(f"Serving {path} from {os.path.join(STATIC_FOLDER, path)}")
    return send_from_directory(app.static_folder, path)

@app.route('/favicon.ico')
def serve_favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

# Constants
INSUFFICIENT_WALLET = "Insufficient wallet"
SELECT_WALLET_QUERY = "SELECT wallet FROM users WHERE user_id = ?"
UPDATE_WALLET_DEBIT_QUERY = "UPDATE users SET wallet = wallet - ? WHERE user_id = ?"
SELECT_CARD_NUMBERS_QUERY = "SELECT card_numbers FROM player_cards WHERE game_id = ? AND user_id = ?"
SELECT_ROLE_QUERY = "SELECT role FROM users WHERE user_id = ?"
UPDATE_ROLE_QUERY = "UPDATE users SET role = 'admin' WHERE user_id = ? AND role != 'admin'"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            username TEXT UNIQUE,
            name TEXT,
            wallet INTEGER DEFAULT 10,
            score INTEGER DEFAULT 0,
            referral_code TEXT UNIQUE,
            referred_by TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT 'user',
            invalid_bingo_count INTEGER DEFAULT 0
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS referrals (
            referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referee_id INTEGER,
            bonus_credited BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
            tx_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount INTEGER,
            method TEXT,
            status TEXT DEFAULT 'pending',
            verification_code TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            players TEXT DEFAULT '',  -- Comma-separated list of user_ids
            selected_numbers TEXT DEFAULT '',  -- Comma-separated list of selected numbers
            status TEXT DEFAULT 'waiting',
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            numbers_called TEXT DEFAULT '',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            prize_amount INTEGER DEFAULT 0,
            winner_id INTEGER DEFAULT NULL,
            bet_amount INTEGER DEFAULT 0,
            countdown_start TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS player_cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            user_id INTEGER,
            card_numbers TEXT,  -- Comma-separated 25 numbers
            FOREIGN KEY (game_id) REFERENCES games(game_id)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
            withdraw_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            method TEXT,
            admin_note TEXT
        )''')
        conn.commit()

init_db()

@app.route('/api/register_user', methods=['POST'])
def register_user():
    user_id = request.json.get('user_id')
    phone = request.json.get('phone')
    name = request.json.get('name')
    username = request.json.get('username')
    referral_code = request.json.get('referral_code')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Username already taken'}), 400
    cursor.execute("INSERT INTO users (user_id, phone, username, name, referral_code) VALUES (?, ?, ?, ?, ?)",
                   (user_id, phone, username, name, f"REF{user_id}{int(datetime.now().timestamp())}"))
    if referral_code:
        cursor.execute("SELECT user_id FROM users WHERE referral_code = ?", (referral_code,))
        referrer = cursor.fetchone()
        if referrer:
            cursor.execute("INSERT INTO referrals (referrer_id, referee_id) VALUES (?, ?)", (referrer[0], user_id))
            cursor.execute("UPDATE users SET wallet = wallet + 10 WHERE user_id = ?", (referrer[0],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'registered', 'wallet': 10, 'username': username})

@app.route('/api/user_data', methods=['GET'])
def user_data():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT wallet, score, (SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND bonus_credited), role, invalid_bingo_count, username FROM users WHERE user_id = ?", (user_id, user_id))
    data = cursor.fetchone()
    conn.close()
    if data:
        wallet, wins, successful_referrals, role, invalid_count, username = data
        return jsonify({
            'wallet': wallet,
            'wins': wins or 0,
            'successful_referrals': successful_referrals or 0,
            'role': role or 'user',
            'is_admin' : role =='admin',
            'invalid_bingo_count': invalid_count or 0,
            'username': username
        })
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/add_admin', methods=['POST'])
def add_admin():
    user_id = request.json.get('user_id')  # Admin performing the action
    target_user_id = request.json.get('target_user_id')  # User to promote
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(SELECT_ROLE_QUERY, (user_id,))
    role = cursor.fetchone()
    if not role or role[0] != 'admin':
        conn.close()
        return jsonify({'status': 'unauthorized'}), 403

    cursor.execute(UPDATE_ROLE_QUERY, (target_user_id,))
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': f'User {target_user_id} promoted to admin'})
    conn.close()
    return jsonify({'status': 'failed', 'reason': 'User not found or already admin'}), 400

@app.route('/api/get_contacts', methods=['GET'])
def get_contacts():
    
    return jsonify({
        
            'contacts': [
        {'user_id': 123456, 'first_name': 'Friend1', 'last_name': 'Last1'},
        {'user_id': 789012, 'first_name': 'Friend2', 'last_name': 'Last2'}
    ]
})
            

@app.route('/api/send_invites', methods=['POST'])
def send_invites():
    
    friend_ids = request.json.get('friend_ids', [])
    
    # In a real implementation, you would send invites via Telegram API
    # This is a simplified mock implementation
    sent_count = len(friend_ids)
    
    return jsonify({
        'status': 'success',
        'sent_count': sent_count,
        'message': f'Invites sent to {sent_count} friends'
    })

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, score FROM users ORDER BY score DESC LIMIT 10")
    leaderboard = [{'username': row[0] or 'Anonymous', 'score': row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaderboard)

def start_game_action(cursor, game_id, bet_amount):
    cursor.execute("SELECT players FROM games WHERE game_id = ? AND status = 'waiting'", (game_id,))
    game = cursor.fetchone()
    if game and len(game[0].split(',')) < 2:
        return jsonify({'status': 'failed', 'reason': 'At least 2 players required'}), 400
    cursor.execute("UPDATE games SET status = 'started', start_time = ?, last_updated = ?, prize_amount = ? WHERE game_id = ? AND status = 'waiting'",
                   (datetime.now(), datetime.now(), bet_amount, game_id))
    if cursor.rowcount > 0:
        return jsonify({'status': 'started', 'prize_amount': bet_amount})
    return None

def end_game_action(cursor, game_id):
    cursor.execute("UPDATE games SET status = 'finished', end_time = ?, last_updated = ? WHERE game_id = ? AND status = 'started'",
                   (datetime.now(), datetime.now(), game_id))
    if cursor.rowcount > 0:
        return jsonify({'status': 'ended'})
    return None

def verify_payment_action(cursor, tx_id):
    cursor.execute("SELECT user_id, amount FROM transactions WHERE tx_id = ? AND status = 'pending'", (tx_id,))
    tx = cursor.fetchone()
    if tx:
        user_id, amount = tx
        cursor.execute("UPDATE transactions SET status = 'verified' WHERE tx_id = ?", (tx_id,))
        cursor.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("SELECT referrer_id FROM referrals WHERE referee_id = ? AND NOT bonus_credited", (user_id,))
        referrer = cursor.fetchone()
        if referrer:
            cursor.execute("UPDATE users SET wallet = wallet + 20 WHERE user_id = ?", (referrer[0],))
            cursor.execute("UPDATE referrals SET bonus_credited = TRUE WHERE referee_id = ?", (user_id,))
        return jsonify({'status': 'verified', 'user_id': user_id, 'amount': amount})
    return None

def kick_user_action(cursor, target_user_id):
    cursor.execute("DELETE FROM users WHERE user_id = ?", (target_user_id,))
    if cursor.rowcount > 0:
        return jsonify({'status': 'kicked'})
    return None

def manage_withdrawal_action(cursor, withdraw_id, action_type, admin_note, user_id):
    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE withdraw_id = ? AND status = 'pending'", (withdraw_id,))
    withdrawal = cursor.fetchone()
    if withdrawal:
        withdrawal_user_id, amount = withdrawal
        cursor.execute(SELECT_WALLET_QUERY, (withdrawal_user_id,))
        wallet = cursor.fetchone()[0]
        if action_type == 'approve' and wallet >= amount:
            cursor.execute(UPDATE_WALLET_DEBIT_QUERY, (amount, withdrawal_user_id))
            cursor.execute("UPDATE withdrawals SET status = 'approved', admin_note = ? WHERE withdraw_id = ?", (admin_note, withdraw_id))
            return jsonify({'status': 'approved', 'user_id': withdrawal_user_id, 'amount': amount})
        elif action_type == 'reject':
            cursor.execute("UPDATE withdrawals SET status = 'rejected', admin_note = ? WHERE withdraw_id = ?", (admin_note, withdraw_id))
            return jsonify({'status': 'rejected', 'user_id': withdrawal_user_id, 'amount': amount})
    return None

@app.route('/api/admin_actions', methods=['POST'])
def admin_actions():
    user_id = request.json.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()
    if not role or role[0] != 'admin':
        conn.close()
        return jsonify({'status': 'unauthorized'}), 403

    action = request.json.get('action')
    game_id = request.json.get('game_id')
    tx_id = request.json.get('tx_id')
    target_user_id = request.json.get('target_user_id')
    withdraw_id = request.json.get('withdraw_id')
    action_type = request.json.get('action_type')
    admin_note = request.json.get('admin_note', '')
    bet_amount = request.json.get('bet_amount')

    actions = {
        'start_game': lambda: start_game_action(cursor, game_id, bet_amount),
        'end_game': lambda: end_game_action(cursor, game_id),
        'verify_payment': lambda: verify_payment_action(cursor, tx_id),
        'kick_user': lambda: kick_user_action(cursor, target_user_id),
        'manage_withdrawal': lambda: manage_withdrawal_action(cursor, withdraw_id, action_type, admin_note, user_id)
    }

    result = actions.get(action, lambda: None)()
    if result:
        conn.commit()
        conn.close()
        return result
    conn.close()
    return jsonify({'status': 'failed'}), 400

@app.route('/api/create_game', methods=['POST'])
def create_game():
    user_id = request.json.get('user_id')
    bet_amount = request.json.get('bet_amount')  # 10, 50, 100, or 200 ETB
    if bet_amount not in [10, 50, 100, 200]:
        return jsonify({'status': 'failed', 'reason': 'Invalid bet amount'}), 400
    game_id = f"MP{user_id}{int(datetime.now().timestamp())}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(SELECT_WALLET_QUERY, (user_id,))
    wallet = cursor.fetchone()[0]
    if wallet < bet_amount:
        conn.close()
        return jsonify({'status': 'failed', 'reason': INSUFFICIENT_WALLET}), 400
    cursor.execute(UPDATE_WALLET_DEBIT_QUERY, (bet_amount, user_id))
    cursor.execute(
        "INSERT INTO games (game_id, players, selected_numbers, status, bet_amount, countdown_start) VALUES (?, ?, ?, 'waiting', ?, NULL)",
        (game_id, str(user_id), '', bet_amount)
    )
    conn.commit()
    conn.close()
    return jsonify({'game_id': game_id, 'status': 'waiting', 'bet_amount': bet_amount})

@app.route('/api/join_game', methods=['POST'])
def join_game():
    user_id = request.json.get('user_id')
    game_id = request.json.get('game_id')
    bet_amount = request.json.get('bet_amount')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT players, selected_numbers, bet_amount FROM games WHERE game_id = ? AND status = 'waiting'", (game_id,))
    game = cursor.fetchone()
    if not game:
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Game not found'}), 400
    players, selected_numbers, game_bet = game
    players = players.split(',')
    selected_numbers = selected_numbers.split(',') if selected_numbers else []
    if str(user_id) in players:
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Already joined'}), 400
    if bet_amount != game_bet:
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Bet amount must match game'}), 400
    cursor.execute(SELECT_WALLET_QUERY, (user_id,))
    wallet = cursor.fetchone()[0]
    if wallet < bet_amount:
        conn.close()
        return jsonify({'status': 'failed', 'reason': INSUFFICIENT_WALLET}), 400
    cursor.execute(UPDATE_WALLET_DEBIT_QUERY, (bet_amount, user_id))
    players.append(str(user_id))
    cursor.execute("UPDATE games SET players = ? WHERE game_id = ?", (','.join(players), game_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'joined', 'players': len(players), 'bet_amount': bet_amount})

@app.route('/api/select_number', methods=['POST'])
def select_number():
    user_id = request.json.get('user_id')
    game_id = request.json.get('game_id')
    selected_number = request.json.get('selected_number')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT players, selected_numbers, status FROM games WHERE game_id = ? AND status = 'waiting'", (game_id,))
    game = cursor.fetchone()
    if not game or str(user_id) not in game[0].split(','):
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Invalid game or user'}), 400
    selected_numbers = game[1].split(',') if game[1] else []
    if str(selected_number) != '':
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Number already selected'}), 400
    if not (0 <= selected_number <= 100):
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Number must be 0-100'}), 400
    selected_numbers.append(str(selected_number))
    cursor.execute("UPDATE games SET selected_numbers = ? WHERE game_id = ?", (','.join(selected_numbers), game_id))
    if game[2] != 'waiting' or game[0].split(',').index(str(user_id)) != 0:
        cursor.execute("UPDATE games SET countdown_start = ? WHERE game_id = ?", (datetime.now(), game_id))
    random.seed(selected_number)
    card_numbers = sorted(random.sample(range(0, 101), 25))
    cursor.execute("INSERT INTO player_cards (game_id, user_id, card_numbers) VALUES (?, ?, ?)",
                   (game_id, user_id, ','.join(map(str, card_numbers))))
    conn.commit()
    conn.close()
    return jsonify({'status': 'card_generated', 'card_numbers': card_numbers, 'selected_number': selected_number})

@app.route('/api/accept_card', methods=['POST'])
def accept_card():
    user_id = request.json.get('user_id')
    game_id = request.json.get('game_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(SELECT_CARD_NUMBERS_QUERY, (game_id, user_id))
    card = cursor.fetchone()
    if card:
        conn.close()
        return jsonify({'status': 'accepted', 'card_numbers': card[0].split(',')})
    conn.close()
    return jsonify({'status': 'failed'}), 400

@app.route('/api/game_status', methods=['GET'])
def game_status():
    game_id = request.args.get('game_id')
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, start_time, end_time, numbers_called, prize_amount, winner_id, players, selected_numbers, bet_amount, countdown_start FROM games WHERE game_id = ?", (game_id,))
    game = cursor.fetchone()
    if not game:
        conn.close()
        return jsonify({'status': 'not_found'}), 404
    status, start_time, end_time, numbers_called, prize_amount, winner_id, players_str, selected_numbers, bet_amount, countdown_start = game
    players = players_str.split(',') if players_str else []
    cursor.execute(SELECT_CARD_NUMBERS_QUERY, (game_id, user_id))
    card = cursor.fetchone()
    auto_start = countdown_start and len(players) > 2 and (datetime.now() - countdown_start).total_seconds() > 120
    if auto_start and status == 'waiting':
        cursor.execute("UPDATE games SET status = 'started', start_time = ?, last_updated = ?, prize_amount = ?, selected_numbers = '' WHERE game_id = ?",
                       (datetime.now(), datetime.now(), bet_amount, game_id))
        conn.commit()
    conn.close()
    return jsonify({
        'status': status,
        'start_time': start_time.isoformat() if start_time else None,
        'end_time': end_time.isoformat() if end_time else None,
        'numbers_called': numbers_called.split(',') if numbers_called else [],
        'prize_amount': prize_amount,
        'winner_id': winner_id,
        'players': players,
        'selected_numbers': selected_numbers.split(',') if selected_numbers else [],
        'bet_amount': bet_amount,
        'card_numbers': card[0].split(',') if card else []
    })

@app.route('/api/call_number', methods=['POST'])
def call_number():
    game_id = request.json.get('game_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, numbers_called, end_time FROM games WHERE game_id = ?", (game_id,))
    game = cursor.fetchone()
    if not game or game[0] != 'started' or (game[2] and datetime.now() > game[2]):
        conn.close()
        return jsonify({'status': 'invalid'}), 400
    numbers = game[1].split(',') if game[1] else []
    if len(numbers) >= 100 or game[0] == 'finished':
        conn.close()
        return jsonify({'status': 'complete'}), 400
    new_number = random.randint(0, 100)
    while str(new_number) in numbers:
        new_number = random.randint(0, 100)
    numbers.append(str(new_number))
    cursor.execute("UPDATE games SET numbers_called = ?, last_updated = ? WHERE game_id = ?",
                   (','.join(numbers), datetime.now(), game_id))
    conn.commit()
    import time
    time.sleep(5)  # 5-second interval
    conn.close()
    return jsonify({'number': new_number, 'called_numbers': numbers, 'remaining': 100 - len(numbers)})

@app.route('/api/check_bingo', methods=['POST'])
def check_bingo():
    user_id = request.json.get('user_id')
    game_id = request.json.get('game_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT numbers_called, winner_id, players, bet_amount FROM games WHERE game_id = ?", (game_id,))
    game = cursor.fetchone()
    if not game or game[1] is not None:
        conn.close()
        return jsonify({'message': 'Game already has a winner or not started', 'won': False})
    numbers_called = game[0].split(',') if game[0] else []
    players = game[2].split(',')
    bet_amount = game[3]
    cursor.execute(SELECT_CARD_NUMBERS_QUERY, (game_id, user_id))
    card = cursor.fetchone()
    if not card:
        conn.close()
        return jsonify({'message': 'Card not found', 'won': False})
    card_numbers = set(card[0].split(','))
    marked = [num for num in card_numbers if num in numbers_called]
    card_grid = [marked[i:i+5] for i in range(0, 25, 5)]
    won = any(all(row) for row in card_grid) or \
          any(all(str(i*5 + col) in marked for i in range(5)) for col in range(5)) or \
          all(str(i*5 + i) in marked for i in range(5)) or \
          all(str(i*5 + (4-i)) in marked for i in range(5))
    if not won:
        cursor.execute("UPDATE users SET invalid_bingo_count = invalid_bingo_count + 1 WHERE user_id = ?", (user_id,))
        invalid_count = cursor.execute("SELECT invalid_bingo_count FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
        if invalid_count >= 1:
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return jsonify({'message': '🚫 You were kicked for repeated invalid Bingo claims!', 'kicked': True})
        conn.commit()
        conn.close()
        return jsonify({'message': '❌ Invalid Bingo claim! Try again. (You are kicked out of the game!)', 'won': False})
    total_bet = bet_amount * len(players)
    prize_amount = int(total_bet * 0.98)  # 2% deduction
    cursor.execute("UPDATE games SET winner_id = ?, prize_amount = ?, status = 'finished', end_time = ? WHERE game_id = ?", (user_id, prize_amount, datetime.now(), game_id))
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    winner_username = cursor.fetchone()[0]
    cursor.execute(UPDATE_WALLET_DEBIT_QUERY, (bet_amount, user_id))  # Corrected to credit winner
    cursor.execute("UPDATE users SET wallet = wallet + ? WHERE user_id = ?", (prize_amount, user_id))
    for player in players:
        if player != str(user_id):
            cursor.execute(UPDATE_WALLET_DEBIT_QUERY, (bet_amount, player))
    conn.commit()
    conn.close()
    return jsonify({'message': f'🎉 Bingo! {winner_username} won {prize_amount} ETB! You are the first winner!', 'won': True})

@app.route('/api/pending_withdrawals', methods=['GET'])
def pending_withdrawals():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()
    if not role or role[0] != 'admin':
        conn.close()
        return jsonify({'status': 'unauthorized'}), 403
    cursor.execute("SELECT withdraw_id, user_id, amount, method, request_time FROM withdrawals WHERE status = 'pending'")
    withdrawals = [{'withdraw_id': row[0], 'user_id': row[1], 'amount': row[2], 'method': row[3], 'request_time': row[4].isoformat()} for row in cursor.fetchall()]
    conn.close()
    return jsonify({'withdrawals': withdrawals})

@app.route('/api/request_withdrawal', methods=['POST'])
def request_withdrawal():
    user_id = request.json.get('user_id')
    amount = request.json.get('amount')
    method = request.json.get('method', 'telebirr')
    withdraw_id = f"W{user_id}{int(datetime.now().timestamp())}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(SELECT_WALLET_QUERY, (user_id,))
    wallet = cursor.fetchone()[0]
    if wallet < 100:
        conn.close()
        return jsonify({'status': 'failed', 'reason': 'Wallet must be at least 100 ETB to request withdrawal'}), 400
    if wallet < amount:
        conn.close()
        return jsonify({'status': 'failed', 'reason': INSUFFICIENT_WALLET}), 400
    cursor.execute(
        "INSERT INTO withdrawals (withdraw_id, user_id, amount, method) VALUES (?, ?, ?, ?)",
        (withdraw_id, user_id, amount, method)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'requested', 'withdraw_id': withdraw_id, 'amount': amount})

if __name__ == '__main__':
    print(f"Static folder: {STATIC_FOLDER}")  # Debug
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))