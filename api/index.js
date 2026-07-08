// 九十九出独角戏第二季 — 投票后端 (Node.js)
import { neon } from '@neondatabase/serverless';
import artistsData from './artists.json' with { type: 'json' };
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const DATABASE_URL = process.env.DATABASE_URL || '';
const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'admin123';

let sql = null;
if (DATABASE_URL) {
  sql = neon(DATABASE_URL);
}

// 获取当天日期字符串 (YYYY-MM-DD, UTC+8 中国时区)
function getTodayKey() {
  const now = new Date();
  // 中国时区 UTC+8
  const chinaTime = new Date(now.getTime() + (now.getTimezoneOffset() + 8 * 60) * 60 * 1000);
  return chinaTime.toISOString().slice(0, 10);
}

async function ensureDb() {
  if (!sql) return;
  // 艺术家主表
  await sql`CREATE TABLE IF NOT EXISTS artists_votes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cat TEXT DEFAULT '',
    votes INTEGER DEFAULT 0
  )`;
  // 每日投票记录表：fingerprint + artist_id + vote_date 唯一
  await sql`CREATE TABLE IF NOT EXISTS daily_votes (
    id SERIAL PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    artist_id INTEGER NOT NULL,
    vote_date TEXT NOT NULL,
    voted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(fingerprint, artist_id, vote_date)
  )`;
  // 创建索引
  await sql`CREATE INDEX IF NOT EXISTS idx_daily_fingerprint_date ON daily_votes(fingerprint, vote_date)`;
  await sql`CREATE INDEX IF NOT EXISTS idx_daily_artist ON daily_votes(artist_id)`;

  const validIds = artistsData.map(a => a.id);
  // 1) 插入任何缺失的艺术家
  for (const a of artistsData) {
    const existing = await sql`SELECT id FROM artists_votes WHERE id = ${a.id}`;
    if (existing.length === 0) {
      await sql`INSERT INTO artists_votes (id, name, cat, votes) VALUES (${a.id}, ${a.name}, ${a.cat}, 0)`;
    } else {
      // 同步 name/cat (避免旧的元数据覆盖新的)
      await sql`UPDATE artists_votes SET name = ${a.name}, cat = ${a.cat} WHERE id = ${a.id}`;
    }
  }
  // 2) 删除当前 artistsData 中不存在的旧 ID（如旧的 34, 35）
  if (validIds.length > 0) {
    const minId = Math.min(...validIds);
    const maxId = Math.max(...validIds);
    await sql`DELETE FROM artists_votes WHERE id < ${minId} OR id > ${maxId}`;
    // 清理关联的 daily_votes 孤立记录
    await sql`DELETE FROM daily_votes WHERE artist_id < ${minId} OR artist_id > ${maxId}`;
  }
}

function checkAuth(req) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Basic ')) return false;
  const decoded = Buffer.from(auth.slice(6), 'base64').toString();
  const [user, pass] = decoded.split(':');
  return user === ADMIN_USER && pass === ADMIN_PASS;
}

// 读取 POST 请求体：兼容 Vercel Node.js 的 IncomingMessage 与 Web Request
async function readJsonBody(req) {
  // Web Request (Vercel Edge / 较新 runtime)
  if (typeof req.json === 'function') {
    try { return await req.json(); } catch (_) { return {}; }
  }
  // Node IncomingMessage (Vercel Node 默认)
  return new Promise((resolve) => {
    try {
      const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => {
        const raw = Buffer.concat(chunks).toString('utf8') || '';
        if (!raw) return resolve({});
        try { resolve(JSON.parse(raw)); } catch (_) { resolve({}); }
      });
      req.on('error', () => resolve({}));
    } catch (_) {
      resolve({});
    }
  });
}

function getArtistsWithVotes(rows) {
  const metaMap = {};
  for (const a of artistsData) metaMap[a.id] = a;
  return rows.map(r => {
    const meta = metaMap[r.id] || {};
    return {
      id: r.id,
      name: meta.name || r.name,
      artist: meta.artist || '',
      cat: meta.cat || r.cat,
      votes: r.votes || 0,
      colors: meta.colors || ['#ccc', '#aaa', '#eee'],
      imageUrl: meta.imageUrl || null,
    };
  });
}

export default async function handler(req, res) {
  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const path = url.pathname;

  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // Pages
  if (path === '/' || path === '/index.html' || path === '/artist-vote' || path === '/artist-vote/' || path === '/artist-vote/index.html') {
    try {
      const html = readFileSync(join(__dirname, '..', 'artist-vote', 'index.html'));
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.status(200).send(html);
    } catch (e) {
      return res.status(500).send('Page not found');
    }
  }

  // Image route
  if (path.startsWith('/images/')) {
    try {
      const filename = path.replace('/images/', '');
      const img = readFileSync(join(__dirname, '..', 'artist-vote', 'images', filename));
      const ext = filename.split('.').pop().toLowerCase();
      const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
      res.setHeader('Content-Type', mime);
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      return res.status(200).send(img);
    } catch (e) {
      return res.status(404).send('Image not found');
    }
  }

  // API: 获取艺术家列表 + 票数
  if (path === '/api/artists') {
    try {
      await ensureDb();
      if (!sql) {
        return res.status(200).json(artistsData);
      }
      const rows = await sql`SELECT id, name, cat, votes FROM artists_votes ORDER BY id`;
      return res.status(200).json(getArtistsWithVotes(rows));
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // API: 查询指定观众今天已投过哪些艺术家
  if (path === '/api/check-fingerprint' && req.method === 'POST') {
    try {
      const { fingerprint } = await readJsonBody(req);
      if (!fingerprint || !sql) return res.status(200).json({ voted: false, voted_today: [], today: getTodayKey() });
      const today = getTodayKey();
      const rows = await sql`SELECT artist_id FROM daily_votes WHERE fingerprint = ${fingerprint} AND vote_date = ${today}`;
      const voted_today = rows.map(r => r.artist_id);
      return res.status(200).json({ voted: voted_today.length > 0, voted_today, today });
    } catch (e) {
      return res.status(200).json({ voted: false, voted_today: [], today: getTodayKey(), error: e.message });
    }
  }

  // API: 给单艺术家投票
  if (path === '/api/vote' && req.method === 'POST') {
    try {
      const body = await readJsonBody(req);
      const { artist_id, fingerprint } = body;
      if (!artist_id) return res.status(400).json({ error: '缺少 artist_id' });
      if (!fingerprint) return res.status(400).json({ error: '缺少指纹标识' });

      const validIds = new Set(artistsData.map(a => a.id));
      if (!validIds.has(Number(artist_id))) {
        return res.status(400).json({ error: `无效艺术家 ID: ${artist_id}` });
      }

      const today = getTodayKey();

      if (sql) {
        // 检查今天是否已投过该艺术家
        const existing = await sql`SELECT id FROM daily_votes WHERE fingerprint = ${fingerprint} AND artist_id = ${artist_id} AND vote_date = ${today}`;
        if (existing.length > 0) {
          return res.status(409).json({ error: '今天已经给这位艺术家投过票了，明天再来吧', voted_today: [Number(artist_id)] });
        }
        // 插入每日投票记录（唯一约束防重）
        try {
          await sql`INSERT INTO daily_votes (fingerprint, artist_id, vote_date) VALUES (${fingerprint}, ${artist_id}, ${today})`;
        } catch (e) {
          if (e.message && e.message.includes('unique')) {
            return res.status(409).json({ error: '今天已经给这位艺术家投过票了' });
          }
          throw e;
        }
        // 艺术家总票数 +1
        await sql`UPDATE artists_votes SET votes = votes + 1 WHERE id = ${artist_id}`;
      }
      return res.status(200).json({ success: true, artist_id: Number(artist_id), vote_date: today });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // API: 管理员统计
  if (path === '/api/stats') {
    try {
      await ensureDb();
      if (!sql) {
        return res.status(200).json({ total_votes: 0, total_voters: 0, today_votes: 0, top10: [] });
      }
      const totals = await sql`SELECT SUM(votes)::int as total FROM artists_votes`;
      const voters = await sql`SELECT COUNT(DISTINCT fingerprint)::int as total FROM daily_votes`;
      const today = getTodayKey();
      const todayTotals = await sql`SELECT COUNT(*)::int as total FROM daily_votes WHERE vote_date = ${today}`;
      const top = await sql`SELECT id, name, votes FROM artists_votes ORDER BY votes DESC LIMIT 10`;
      return res.status(200).json({
        total_votes: totals[0]?.total || 0,
        total_voters: voters[0]?.total || 0,
        today_votes: todayTotals[0]?.total || 0,
        top10: top.map(t => ({ id: t.id, name: t.name, votes: t.votes })),
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  if (path === '/admin') {
    if (!checkAuth(req)) {
      res.setHeader('WWW-Authenticate', 'Basic realm="Admin Panel"');
      return res.status(401).send('Unauthorized');
    }
    try {
      await ensureDb();
      const adminHtml = readFileSync(join(__dirname, 'admin.html'), 'utf-8');
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.status(200).send(adminHtml);
    } catch (e) {
      return res.status(500).send('Admin page error: ' + e.message);
    }
  }

  if (path === '/debug') {
    try {
      await ensureDb();
      if (!sql) return res.status(200).json({ DATABASE_URL_set: false, mode: 'fallback' });
      const artists = await sql`SELECT COUNT(*)::int as count FROM artists_votes`;
      const votes = await sql`SELECT SUM(votes)::int as total FROM artists_votes`;
      const dailyTotal = await sql`SELECT COUNT(*)::int as total FROM daily_votes`;
      const today = getTodayKey();
      const todayTotal = await sql`SELECT COUNT(*)::int as total FROM daily_votes WHERE vote_date = ${today}`;
      return res.status(200).json({
        DATABASE_URL_set: true,
        today,
        artists_count: artists[0].count,
        total_votes: votes[0].total,
        total_daily_records: dailyTotal[0].total,
        today_votes: todayTotal[0].total,
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  return res.status(404).json({ error: 'Not found' });
}
