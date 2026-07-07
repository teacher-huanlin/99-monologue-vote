from flask import Flask, request, jsonify, render_template_string, make_response
import os
import json
import time
import hashlib
from functools import wraps

# ---- Config ----
DATABASE_URL = os.environ.get('DATABASE_URL', '')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')
IS_PG = bool(DATABASE_URL)

import pg8000.native as pg8000_native

# ---- App ----
app = Flask(__name__)

# ---- Artist Data (synced with frontend) ----
ARTISTS = [
    {'id': 1,  'name': '星辰工作室',     'cat': '数字艺术',   'colors': ['#f8c291','#e55039','#f6b092']},
    {'id': 2,  'name': '水墨丹青',       'cat': '国画',       'colors': ['#82ccdd','#60a3bc','#b8e0ed']},
    {'id': 3,  'name': '光影捕手',       'cat': '摄影',       'colors': ['#fad390','#e1b12c','#f6d775']},
    {'id': 4,  'name': '像素诗人',       'cat': '数字艺术',   'colors': ['#ff6b6b','#feca57','#ff9f80']},
    {'id': 5,  'name': '极简主义',       'cat': '装置艺术',   'colors': ['#a29bfe','#6c5ce7','#c8c2fc']},
    {'id': 6,  'name': '梦幻造物',       'cat': '插画',       'colors': ['#fd79a8','#e84393','#fab8d2']},
    {'id': 7,  'name': '铁锈与玫瑰',     'cat': '雕塑',       'colors': ['#e17055','#d63031','#fab1a0']},
    {'id': 8,  'name': '未来回声',       'cat': '新媒体',     'colors': ['#00cec9','#0984e3','#81ecec']},
    {'id': 9,  'name': '纸间游鱼',       'cat': '综合材料',   'colors': ['#dfe6e9','#b2bec3','#f5f6fa']},
    {'id': 10, 'name': '棱镜实验室',     'cat': '实验艺术',   'colors': ['#ffeaa7','#fdcb6e','#fee9b0']},
    {'id': 11, 'name': '云端画师',       'cat': '数字艺术',   'colors': ['#74b9ff','#0984e3','#a8d8ff']},
    {'id': 12, 'name': '山海经',         'cat': '插画',       'colors': ['#fab1a0','#e17055','#ffcccc']},
    {'id': 13, 'name': '零点共振',       'cat': '声音艺术',   'colors': ['#81ecec','#00cec9','#c8f7f7']},
    {'id': 14, 'name': '燃烧的冰川',     'cat': '装置艺术',   'colors': ['#ff9f43','#ee5a24','#ffc78d']},
    {'id': 15, 'name': '造梦空间',       'cat': '新媒体',     'colors': ['#a29bfe','#6c5ce7','#cec6fd']},
    {'id': 16, 'name': '风之形',         'cat': '雕塑',       'colors': ['#55efc4','#00b894','#9ff5d8']},
    {'id': 17, 'name': '寂静之音',       'cat': '摄影',       'colors': ['#dfe6e9','#b2bec3','#f0f3f5']},
    {'id': 18, 'name': '无限画布',       'cat': '数字艺术',   'colors': ['#ff6b6b','#ee5a24','#ffa3a3']},
    {'id': 19, 'name': '瓷语新说',       'cat': '陶瓷艺术',   'colors': ['#e0c3fc','#8ec5fc','#f0e6ff']},
    {'id': 20, 'name': '数据之花',       'cat': '新媒体',     'colors': ['#fd79a8','#e84393','#ffb8d2']},
    {'id': 21, 'name': '墨迹未干',       'cat': '国画',       'colors': ['#fab1a0','#d63031','#ffe0d9']},
    {'id': 22, 'name': '金属心跳',       'cat': '雕塑',       'colors': ['#fad390','#e1b12c','#fef0c0']},
    {'id': 23, 'name': '透明城市',       'cat': '建筑艺术',   'colors': ['#81ecec','#00cec9','#c0f5f5']},
    {'id': 24, 'name': '星河织造',       'cat': '纤维艺术',   'colors': ['#a29bfe','#4834d4','#d4cefd']},
    {'id': 25, 'name': '暴风雨前',       'cat': '绘画',       'colors': ['#74b9ff','#2d7dd2','#c0dffd']},
    {'id': 26, 'name': '游牧代码',       'cat': '数字艺术',   'colors': ['#ff9f43','#fdcb6e','#ffe0a3']},
    {'id': 27, 'name': '缝隙之间',       'cat': '装置艺术',   'colors': ['#dfe6e9','#bdc3c7','#f0f2f4']},
    {'id': 28, 'name': '霓虹废墟',       'cat': '摄影',       'colors': ['#fd79a8','#ff6b6b','#ffc8d0']},
    {'id': 29, 'name': '重力之外',       'cat': '雕塑',       'colors': ['#f8c291','#e55039','#fcd5b8']},
    {'id': 30, 'name': '感官迷宫',       'cat': '新媒体',     'colors': ['#ffeaa7','#fdcb6e','#fff3c0']},
    {'id': 31, 'name': '纸飞机工厂',     'cat': '综合材料',   'colors': ['#ff6b6b','#c0392b','#ffb3b3']},
    {'id': 32, 'name': '记忆标本',       'cat': '实验艺术',   'colors': ['#55efc4','#27ae60','#b0f8dd']},
    {'id': 33, 'name': '折纸宇宙',       'cat': '综合材料',   'colors': ['#fd79a8','#e84393','#ffccda']},
    {'id': 34, 'name': '声音雕塑',       'cat': '声音艺术',   'colors': ['#74b9ff','#4834d4','#b8c8fd']},
    {'id': 35, 'name': '重影',           'cat': '绘画',       'colors': ['#dfe6e9','#636e72','#f0f2f4']},
]

# ---- DB Helpers ----
def _get_pg_conn():
    return pg8000_native.Connection(DATABASE_URL)

def _ensure_db():
    if IS_PG:
        conn = _get_pg_conn()
        conn.run("""
            CREATE TABLE IF NOT EXISTS artists_votes (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                cat TEXT DEFAULT '',
                votes INTEGER DEFAULT 0
            )
        """)
        conn.run("""
            CREATE TABLE IF NOT EXISTS vote_sessions (
                id SERIAL PRIMARY KEY,
                fingerprint TEXT UNIQUE NOT NULL,
                voted_at TIMESTAMP DEFAULT NOW(),
                voted_ids TEXT NOT NULL
            )
        """)
        # seed artists if empty
        count = conn.run("SELECT COUNT(*) FROM artists_votes")[0][0]
        if count == 0:
            for a in ARTISTS:
                conn.run(
                    "INSERT INTO artists_votes (id, name, cat, votes) VALUES (:id, :name, :cat, 0)",
                    id=a['id'], name=a['name'], cat=a['cat']
                )
        conn.close()
        return True
    else:
        # SQLite fallback for local dev
        import sqlite3
        conn = sqlite3.connect('/tmp/vote.db')
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS artists_votes (
                id INTEGER PRIMARY KEY,
                name TEXT,
                cat TEXT DEFAULT '',
                votes INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS vote_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT UNIQUE,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                voted_ids TEXT NOT NULL
            )
        """)
        c.execute("SELECT COUNT(*) FROM artists_votes")
        if c.fetchone()[0] == 0:
            for a in ARTISTS:
                c.execute("INSERT INTO artists_votes (id, name, cat, votes) VALUES (?, ?, ?, 0)",
                          (a['id'], a['name'], a['cat']))
        conn.commit()
        conn.close()
        return True

# ---- Flask Hooks ----
@app.before_request
def before_request():
    """Ensure DB is initialized before each request that needs it"""
    if request.path.startswith(('/api/', '/admin', '/debug')):
        _ensure_db()
def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return make_response(
                'Unauthorized', 401,
                {'WWW-Authenticate': 'Basic realm="九十九出独角戏 管理后台"'}
            )
        return f(*args, **kwargs)
    return decorated

# ---- API Routes ----
@app.route('/api/artists')
def api_artists():
    """Get all artists with their vote counts"""
    try:
        if IS_PG:
            conn = _get_pg_conn()
            rows = conn.run("SELECT id, name, cat, votes FROM artists_votes ORDER BY id")
            conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            rows = c.execute("SELECT id, name, cat, votes FROM artists_votes ORDER BY id").fetchall()
            conn.close()

        # Merge with ARTISTS metadata (colors)
        artist_map = {a['id']: a for a in ARTISTS}
        result = []
        for r in rows:
            a = artist_map.get(r[0], {})
            result.append({
                'id': r[0],
                'name': r[1],
                'cat': r[2],
                'votes': r[3],
                'colors': a.get('colors', ['#ccc','#aaa','#eee']),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/artists/<int:artist_id>')
def api_artist(artist_id):
    """Get a single artist's vote count"""
    try:
        if IS_PG:
            conn = _get_pg_conn()
            row = conn.run("SELECT id, name, cat, votes FROM artists_votes WHERE id = :id", id=artist_id)
            conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            row = c.execute("SELECT id, name, cat, votes FROM artists_votes WHERE id = ?", (artist_id,)).fetchone()
            conn.close()
            if row:
                row = [row]

        if not row:
            return jsonify({'error': 'Artist not found'}), 404

        r = row[0]
        a = next((a for a in ARTISTS if a['id'] == r[0]), {})
        return jsonify({
            'id': r[0], 'name': r[1], 'cat': r[2], 'votes': r[3],
            'colors': a.get('colors', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/vote', methods=['POST'])
def api_vote():
    """Submit a vote for 5 artists"""
    try:
        data = request.get_json(force=True)
        voted_ids = data.get('voted_ids', [])
        fingerprint = data.get('fingerprint', '')

        # Validate
        if not isinstance(voted_ids, list) or len(voted_ids) != 5:
            return jsonify({'error': '请选择恰好 5 位艺术家'}), 400
        if not fingerprint:
            return jsonify({'error': '缺少指纹标识'}), 400

        valid_ids = [a['id'] for a in ARTISTS]
        for vid in voted_ids:
            if vid not in valid_ids:
                return jsonify({'error': f'无效的艺术家 ID: {vid}'}), 400
        if len(set(voted_ids)) != 5:
            return jsonify({'error': '不能重复投票给同一位艺术家'}), 400

        # Check duplicate
        if IS_PG:
            conn = _get_pg_conn()
            existing = conn.run(
                "SELECT id FROM vote_sessions WHERE fingerprint = :fp",
                fp=fingerprint
            )
            if existing:
                conn.close()
                return jsonify({'error': '该设备已投过票'}), 409
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            existing = c.execute(
                "SELECT id FROM vote_sessions WHERE fingerprint = ?",
                (fingerprint,)
            ).fetchone()
            if existing:
                conn.close()
                return jsonify({'error': '该设备已投过票'}), 409

        # Record session & update votes
        vids_json = json.dumps(voted_ids)
        if IS_PG:
            conn.run(
                "INSERT INTO vote_sessions (fingerprint, voted_ids) VALUES (:fp, :vids)",
                fp=fingerprint, vids=vids_json
            )
            for vid in voted_ids:
                conn.run("UPDATE artists_votes SET votes = votes + 1 WHERE id = :id", id=vid)
            conn.close()
        else:
            c.execute(
                "INSERT INTO vote_sessions (fingerprint, voted_ids) VALUES (?, ?)",
                (fingerprint, vids_json)
            )
            for vid in voted_ids:
                c.execute("UPDATE artists_votes SET votes = votes + 1 WHERE id = ?", (vid,))
            conn.commit()
            conn.close()

        return jsonify({'success': True, 'message': '投票成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-fingerprint', methods=['POST'])
def api_check_fingerprint():
    """Check if a fingerprint already voted"""
    try:
        data = request.get_json(force=True)
        fingerprint = data.get('fingerprint', '')
        if not fingerprint:
            return jsonify({'voted': False})

        if IS_PG:
            conn = _get_pg_conn()
            existing = conn.run(
                "SELECT voted_ids FROM vote_sessions WHERE fingerprint = :fp",
                fp=fingerprint
            )
            conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            existing = c.execute(
                "SELECT voted_ids FROM vote_sessions WHERE fingerprint = ?",
                (fingerprint,)
            ).fetchone()
            conn.close()

        if existing:
            return jsonify({
                'voted': True,
                'voted_ids': json.loads(existing[0]) if not isinstance(existing[0], list) else existing[0]
            })
        return jsonify({'voted': False})
    except Exception as e:
        return jsonify({'error': str(e), 'voted': False}), 500

@app.route('/api/stats')
def api_stats():
    """Get overall voting statistics"""
    try:
        if IS_PG:
            conn = _get_pg_conn()
            total_votes = conn.run("SELECT SUM(votes) FROM artists_votes")[0][0] or 0
            total_sessions = conn.run("SELECT COUNT(*) FROM vote_sessions")[0][0]
            top = conn.run("SELECT id, name, votes FROM artists_votes ORDER BY votes DESC LIMIT 10")
            conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            total_votes = c.execute("SELECT SUM(votes) FROM artists_votes").fetchone()[0] or 0
            total_sessions = c.execute("SELECT COUNT(*) FROM vote_sessions").fetchone()[0]
            top = c.execute("SELECT id, name, votes FROM artists_votes ORDER BY votes DESC LIMIT 10").fetchall()
            conn.close()

        return jsonify({
            'total_votes': total_votes,
            'total_voters': total_sessions,
            'top10': [{'id': t[0], 'name': t[1], 'votes': t[2]} for t in top],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Admin Dashboard ----
ADMIN_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>管理后台 — 九十九出独角戏第二季</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f3ef;color:#2c2c2c;min-height:100vh}
.header{background:linear-gradient(135deg,#e86a58,#d45341);color:#fff;padding:28px 24px;text-align:center}
.header h1{font-size:24px;font-weight:700;letter-spacing:2px}
.header p{font-size:14px;opacity:0.85;margin-top:6px}
.container{max-width:900px;margin:0 auto;padding:24px 16px}
.stats-bar{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.stat-card{flex:1;min-width:180px;background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,0.06);text-align:center}
.stat-card .num{font-size:36px;font-weight:800;color:#e86a58}
.stat-card .label{font-size:13px;color:#8c7b6d;margin-top:4px}
.ranking{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);overflow:hidden}
.ranking h2{padding:18px 24px;font-size:18px;border-bottom:1px solid #ece3d8;background:#fef9f4}
.rank-item{display:flex;align-items:center;padding:12px 24px;gap:14px;border-bottom:1px solid #ece3d8}
.rank-item:hover{background:#fef9f4}
.rank-num{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;flex-shrink:0}
.rank-1{background:linear-gradient(135deg,#f0d78c,#c9a84c);color:#fff}
.rank-2{background:linear-gradient(135deg,#d4d4d4,#a8a8a8);color:#fff}
.rank-3{background:linear-gradient(135deg,#e0b894,#c4956a);color:#fff}
.rank-other{background:#f0ede8;color:#8c7b6d}
.rank-name{flex:1;font-size:15px;font-weight:600}
.rank-cat{font-size:12px;color:#8c7b6d}
.rank-votes{font-size:20px;font-weight:700;color:#e86a58;flex-shrink:0}
.rank-votes small{font-size:12px;color:#8c7b6d;font-weight:400}
.bar-wrap{width:120px;height:6px;background:#f0ede8;border-radius:3px;overflow:hidden;flex-shrink:0}
.bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,#e86a58,#f8a48b);transition:width .6s}
.refresh-hint{text-align:center;margin-top:24px;font-size:12px;color:#bcb5ad}
@media(max-width:600px){.stat-card{min-width:140px}.rank-item{padding:10px 16px;gap:10px}.bar-wrap{width:60px}}
</style>
</head>
<body>
<div class="header">
    <h1>🎭 九十九出独角戏第二季</h1>
    <p>投票数据管理后台</p>
</div>
<div class="container">
    <div class="stats-bar">
        <div class="stat-card">
            <div class="num" id="totalVotes">—</div>
            <div class="label">总票数</div>
        </div>
        <div class="stat-card">
            <div class="num" id="totalVoters">—</div>
            <div class="label">投票人数</div>
        </div>
        <div class="stat-card">
            <div class="num" id="maxVotes">—</div>
            <div class="label">最高票数</div>
        </div>
    </div>
    <div class="ranking">
        <h2>实时票数排行榜</h2>
        <div id="rankingList"></div>
    </div>
    <p class="refresh-hint">页面每 10 秒自动刷新</p>
</div>
<script>
async function loadData() {
    try {
        const [artistsRes, statsRes] = await Promise.all([
            fetch('/api/artists'),
            fetch('/api/stats')
        ]);
        const artists = await artistsRes.json();
        const stats = await statsRes.json();

        document.getElementById('totalVotes').textContent = stats.total_votes?.toLocaleString() || '0';
        document.getElementById('totalVoters').textContent = (stats.total_voters || 0).toLocaleString();
        document.getElementById('maxVotes').textContent = (stats.top10?.[0]?.votes || 0).toLocaleString();

        const sorted = artists.sort((a, b) => b.votes - a.votes);
        const maxV = sorted[0]?.votes || 1;
        document.getElementById('rankingList').innerHTML = sorted.map((a, i) => {
            const r = i + 1;
            const rc = r === 1 ? 'rank-1' : r === 2 ? 'rank-2' : r === 3 ? 'rank-3' : 'rank-other';
            const barW = Math.max((a.votes / maxV) * 100, 1);
            return `<div class="rank-item">
                <div class="rank-num ${rc}">${r}</div>
                <div>
                    <div class="rank-name">${a.name}</div>
                    <div class="rank-cat">${a.cat}</div>
                </div>
                <div class="bar-wrap"><div class="bar-fill" style="width:${barW}%"></div></div>
                <div class="rank-votes">${(a.votes || 0).toLocaleString()} <small>票</small></div>
            </div>`;
        }).join('');
    } catch(e) {
        console.error(e);
    }
}
loadData();
setInterval(loadData, 10000);
</script>
</body>
</html>'''

@app.route('/admin')
@auth_required
def admin():
    _ensure_db()
    return render_template_string(ADMIN_HTML)

@app.route('/debug')
def debug():
    """Debug endpoint (no auth)"""
    try:
        _ensure_db()
        if IS_PG:
            conn = _get_pg_conn()
            total_votes = conn.run("SELECT SUM(votes) FROM artists_votes")[0][0] or 0
            total_sessions = conn.run("SELECT COUNT(*) FROM vote_sessions")[0][0]
            artists_count = conn.run("SELECT COUNT(*) FROM artists_votes")[0][0]
            conn.close()
        else:
            import sqlite3
            conn = sqlite3.connect('/tmp/vote.db')
            c = conn.cursor()
            total_votes = c.execute("SELECT SUM(votes) FROM artists_votes").fetchone()[0] or 0
            total_sessions = c.execute("SELECT COUNT(*) FROM vote_sessions").fetchone()[0]
            artists_count = c.execute("SELECT COUNT(*) FROM artists_votes").fetchone()[0]
            conn.close()

        return jsonify({
            'DATABASE_URL_set': bool(DATABASE_URL),
            'DATABASE_URL_prefix': DATABASE_URL[:25] + '...' if DATABASE_URL else 'N/A',
            'ADMIN_USER': ADMIN_USER,
            'artists_count': artists_count,
            'total_votes': total_votes,
            'total_sessions': total_sessions,
            'IS_PG': IS_PG,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---- Vercel entry point ----
def handler(request, context=None):
    """Vercel serverless function handler"""
    _ensure_db()
    return app(request.environ, lambda s, h: None)

# Allow running locally
if __name__ == '__main__':
    _ensure_db()
    app.run(debug=True, port=5000)
