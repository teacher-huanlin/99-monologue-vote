"""九十九出独角戏第二季 — 投票后端"""
from flask import Flask, request, jsonify, render_template_string, make_response, send_from_directory
import json, os
from pathlib import Path
from urllib.parse import urlparse
from functools import wraps
from datetime import datetime
import uuid

try:
    import ssl
except ImportError:
    ssl = None

# Vercel 入口
app = Flask(__name__)
handler = app

# ── 环境变量 ──
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'admin123')

# 条件导入 pg8000（匹配 find-passion-tool 模式，避免本地无 pg8000 时导入失败）
try:
    if DATABASE_URL:
        import pg8000
except ImportError:
    pass

# 项目根目录
HERE = Path(__file__).parent
ROOT = HERE.parent

# ── Artist Data (synced with frontend) ──
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

# ── 数据库 ──
_DB_INITED = False


def get_db():
    """返回 (conn, is_pg) 元组，调用方负责 close"""
    if DATABASE_URL:
        parsed = urlparse(DATABASE_URL)
        pg_kwargs = {
            'user': parsed.username,
            'password': parsed.password or '',
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/').split('?')[0],
        }
        if ssl is not None:
            pg_kwargs['ssl_context'] = ssl.create_default_context()
        conn = pg8000.connect(**pg_kwargs)
        conn.autocommit = False
        return conn, True
    else:
        import sqlite3
        db_dir = Path('/tmp/monologue-vote') if os.environ.get('VERCEL') else (ROOT / 'data')
        db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_dir / 'votes.db'))
        conn.row_factory = sqlite3.Row
        return conn, False


def _ensure_db():
    global _DB_INITED
    if _DB_INITED:
        return
    conn, is_pg = get_db()
    try:
        cur = conn.cursor()
        if is_pg:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS artists_votes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    cat TEXT DEFAULT '',
                    votes INTEGER DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vote_sessions (
                    id SERIAL PRIMARY KEY,
                    fingerprint TEXT UNIQUE NOT NULL,
                    voted_at TIMESTAMP DEFAULT NOW(),
                    voted_ids TEXT NOT NULL
                )
            """)
            cur.execute("SELECT COUNT(*) FROM artists_votes")
            if cur.fetchone()[0] == 0:
                for a in ARTISTS:
                    cur.execute(
                        "INSERT INTO artists_votes (id, name, cat, votes) VALUES (%s, %s, %s, 0)",
                        (a['id'], a['name'], a['cat'])
                    )
            conn.commit()
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS artists_votes (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    cat TEXT DEFAULT '',
                    votes INTEGER DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vote_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT UNIQUE,
                    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    voted_ids TEXT NOT NULL
                )
            """)
            cur.execute("SELECT COUNT(*) FROM artists_votes")
            if cur.fetchone()[0] == 0:
                for a in ARTISTS:
                    cur.execute(
                        "INSERT INTO artists_votes (id, name, cat, votes) VALUES (?, ?, ?, 0)",
                        (a['id'], a['name'], a['cat'])
                    )
            conn.commit()
    finally:
        cur.close()
        conn.close()
    _DB_INITED = True


# ── 查询辅助 ──
def query_all(sql, params=None, is_pg=None):
    conn, is_pg = get_db() if is_pg is None else (None, is_pg)
    if conn is None:
        conn, is_pg = get_db()
    try:
        cur = conn.cursor()
        if is_pg:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in rows]
        else:
            cur.execute(sql.replace('%s', '?'), params or ())
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def query_one(sql, params=None, is_pg=None):
    rows = query_all(sql, params, is_pg)
    return rows[0] if rows else None


def execute(sql, params=None, is_pg=None):
    conn, is_pg = get_db() if is_pg is None else (None, is_pg)
    if conn is None:
        conn, is_pg = get_db()
    try:
        cur = conn.cursor()
        if is_pg:
            cur.execute(sql, params or ())
        else:
            cur.execute(sql.replace('%s', '?'), params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()


# ── Basic Auth ──
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not (auth.username == ADMIN_USER and auth.password == ADMIN_PASS):
            return make_response(
                'Unauthorized', 401,
                {'WWW-Authenticate': 'Basic realm="Admin Panel"'}
            )
        return f(*args, **kwargs)
    return decorated


# ── 页面路由 ──
@app.route('/')
@app.route('/index.html')
@app.route('/artist-vote/')
@app.route('/artist-vote/index.html')
def vote_page():
    """投票页面"""
    return send_from_directory(ROOT / 'artist-vote', 'index.html')


# ── API 路由 ──
@app.route('/api/artists')
def api_artists():
    """获取所有艺术家及票数"""
    try:
        _ensure_db()
        rows = query_all("SELECT id, name, cat, votes FROM artists_votes ORDER BY id")
        artist_map = {a['id']: a for a in ARTISTS}
        result = []
        for r in rows:
            meta = artist_map.get(r['id'], {})
            result.append({
                'id': r['id'],
                'name': r['name'],
                'cat': r['cat'],
                'votes': r['votes'] or 0,
                'colors': meta.get('colors', ['#ccc','#aaa','#eee']),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/artists/<int:artist_id>')
def api_artist(artist_id):
    """获取单个艺术家票数"""
    try:
        _ensure_db()
        row = query_one("SELECT id, name, cat, votes FROM artists_votes WHERE id = %s", (artist_id,))
        if not row:
            return jsonify({'error': 'Artist not found'}), 404
        meta = next((a for a in ARTISTS if a['id'] == row['id']), {})
        return jsonify({
            'id': row['id'], 'name': row['name'], 'cat': row['cat'], 'votes': row['votes'] or 0,
            'colors': meta.get('colors', [])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/vote', methods=['POST'])
def api_vote():
    """提交 5 票"""
    try:
        _ensure_db()
        data = request.get_json(force=True)
        voted_ids = data.get('voted_ids', [])
        fingerprint = data.get('fingerprint', '')

        if not isinstance(voted_ids, list) or len(voted_ids) != 5:
            return jsonify({'error': '请选择恰好 5 位艺术家'}), 400
        if not fingerprint:
            return jsonify({'error': '缺少指纹标识'}), 400

        valid_ids = {a['id'] for a in ARTISTS}
        for vid in voted_ids:
            if vid not in valid_ids:
                return jsonify({'error': f'无效的艺术家 ID: {vid}'}), 400
        if len(set(voted_ids)) != 5:
            return jsonify({'error': '不能重复投票给同一位艺术家'}), 400

        existing = query_one("SELECT id FROM vote_sessions WHERE fingerprint = %s", (fingerprint,))
        if existing:
            return jsonify({'error': '该设备已投过票'}), 409

        execute(
            "INSERT INTO vote_sessions (fingerprint, voted_ids) VALUES (%s, %s)",
            (fingerprint, json.dumps(voted_ids))
        )
        for vid in voted_ids:
            execute("UPDATE artists_votes SET votes = votes + 1 WHERE id = %s", (vid,))

        return jsonify({'success': True, 'message': '投票成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-fingerprint', methods=['POST'])
def api_check_fingerprint():
    """检查是否已投票"""
    try:
        _ensure_db()
        data = request.get_json(force=True)
        fingerprint = data.get('fingerprint', '')
        if not fingerprint:
            return jsonify({'voted': False})

        row = query_one("SELECT voted_ids FROM vote_sessions WHERE fingerprint = %s", (fingerprint,))
        if row:
            return jsonify({'voted': True, 'voted_ids': json.loads(row['voted_ids'])})
        return jsonify({'voted': False})
    except Exception as e:
        return jsonify({'error': str(e), 'voted': False}), 500


@app.route('/api/stats')
def api_stats():
    """统计信息"""
    try:
        _ensure_db()
        total_votes = query_all("SELECT SUM(votes) AS total FROM artists_votes")[0]['total'] or 0
        total_sessions = query_all("SELECT COUNT(*) AS total FROM vote_sessions")[0]['total'] or 0
        top = query_all("SELECT id, name, votes FROM artists_votes ORDER BY votes DESC LIMIT 10")
        return jsonify({
            'total_votes': total_votes,
            'total_voters': total_sessions,
            'top10': [{'id': t['id'], 'name': t['name'], 'votes': t['votes'] or 0} for t in top],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── 管理后台 ──
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
.header p{font-size:14px;opacity:.85;margin-top:6px}
.container{max-width:900px;margin:0 auto;padding:24px 16px}
.stats-bar{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.stat-card{flex:1;min-width:180px;background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);text-align:center}
.stat-card .num{font-size:36px;font-weight:800;color:#e86a58}
.stat-card .label{font-size:13px;color:#8c7b6d;margin-top:4px}
.ranking{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.06);overflow:hidden}
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
        <div class="stat-card"><div class="num" id="totalVotes">—</div><div class="label">总票数</div></div>
        <div class="stat-card"><div class="num" id="totalVoters">—</div><div class="label">投票人数</div></div>
        <div class="stat-card"><div class="num" id="maxVotes">—</div><div class="label">最高票数</div></div>
    </div>
    <div class="ranking">
        <h2>实时票数排行榜</h2>
        <div id="rankingList"></div>
    </div>
    <p class="refresh-hint">页面每 10 秒自动刷新</p>
</div>
<script>
async function loadData(){
    try{
        const [artistsRes,statsRes]=await Promise.all([fetch('/api/artists'),fetch('/api/stats')]);
        const artists=await artistsRes.json();
        const stats=await statsRes.json();
        document.getElementById('totalVotes').textContent=(stats.total_votes||0).toLocaleString();
        document.getElementById('totalVoters').textContent=(stats.total_voters||0).toLocaleString();
        document.getElementById('maxVotes').textContent=(stats.top10?.[0]?.votes||0).toLocaleString();
        const sorted=artists.sort((a,b)=>b.votes-a.votes);
        const maxV=sorted[0]?.votes||1;
        document.getElementById('rankingList').innerHTML=sorted.map((a,i)=>{
            const r=i+1;
            const rc=r===1?'rank-1':r===2?'rank-2':r===3?'rank-3':'rank-other';
            const barW=Math.max((a.votes/maxV)*100,1);
            return `<div class="rank-item">
                <div class="rank-num ${rc}">${r}</div>
                <div><div class="rank-name">${a.name}</div><div class="rank-cat">${a.cat}</div></div>
                <div class="bar-wrap"><div class="bar-fill" style="width:${barW}%"></div></div>
                <div class="rank-votes">${(a.votes||0).toLocaleString()} <small>票</small></div>
            </div>`;
        }).join('');
    }catch(e){console.error(e)}
}
loadData();
setInterval(loadData,10000);
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
    """调试端点"""
    try:
        _ensure_db()
        artists_count = query_all("SELECT COUNT(*) AS total FROM artists_votes")[0]['total'] or 0
        total_votes = query_all("SELECT SUM(votes) AS total FROM artists_votes")[0]['total'] or 0
        total_sessions = query_all("SELECT COUNT(*) AS total FROM vote_sessions")[0]['total'] or 0
        return jsonify({
            'DATABASE_URL_set': bool(DATABASE_URL),
            'DATABASE_URL_prefix': DATABASE_URL[:25] + '...' if DATABASE_URL else 'N/A',
            'ADMIN_USER': ADMIN_USER,
            'artists_count': artists_count,
            'total_votes': total_votes,
            'total_sessions': total_sessions,
            'IS_PG': bool(DATABASE_URL),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
