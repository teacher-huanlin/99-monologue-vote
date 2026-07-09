// 九十九出独角戏第二季 — 投票后端 (Node.js)
// 阶段 2: 静态资源 + daily_votes 投票机制
import { readFileSync, existsSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..');

// 读取 artists.json
let artistsData = [];
try {
  artistsData = JSON.parse(readFileSync(join(__dirname, 'artists.json'), 'utf-8'));
  console.log('[init] artists.json loaded:', artistsData.length, 'artists');
} catch (e) {
  console.error('[init] artists.json load error:', e.message);
}

const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'admin123';
const DATABASE_URL = process.env.DATABASE_URL || '';

// 动态 import neon (失败也不影响静态资源 serve)
let sql = null;
let neonReady = false;
const neonPromise = import('@neondatabase/serverless')
  .then((mod) => {
    if (DATABASE_URL) {
      sql = mod.neon(DATABASE_URL);
      neonReady = true;
      console.log('[init] neon loaded');
    } else {
      console.warn('[init] DATABASE_URL not set, voting in no-DB mode');
    }
  })
  .catch((e) => {
    console.error('[init] neon failed to load:', e.message);
  });

// 获取当天日期字符串 (YYYY-MM-DD, UTC+8 中国时区)
function getTodayKey() {
  const now = new Date();
  const chinaTime = new Date(now.getTime() + (now.getTimezoneOffset() + 8 * 60) * 60 * 1000);
  return chinaTime.toISOString().slice(0, 10);
}

async function ensureDb() {
  if (!neonReady || !sql) return false;
  try {
    await sql`CREATE TABLE IF NOT EXISTS artists_votes (
      id INTEGER PRIMARY KEY,
      name TEXT NOT NULL,
      cat TEXT DEFAULT '',
      votes INTEGER DEFAULT 0
    )`;
    await sql`CREATE TABLE IF NOT EXISTS daily_votes (
      id SERIAL PRIMARY KEY,
      fingerprint TEXT NOT NULL,
      artist_id INTEGER NOT NULL,
      vote_date TEXT NOT NULL,
      voted_at TIMESTAMP DEFAULT NOW(),
      UNIQUE(fingerprint, artist_id, vote_date)
    )`;
    return true;
  } catch (e) {
    console.error('[ensureDb] error:', e.message);
    return false;
  }
}

function readPageOrNull(relPath) {
  const candidates = [
    join(PROJECT_ROOT, relPath),
    join(__dirname, relPath),
  ];
  for (const p of candidates) {
    if (existsSync(p)) {
      return readFileSync(p);
    }
  }
  return null;
}

function checkAuth(req) {
  const auth = req.headers?.authorization || '';
  if (!auth.startsWith('Basic ')) return false;
  try {
    const decoded = Buffer.from(auth.slice(6), 'base64').toString('utf-8');
    const [u, p] = decoded.split(':');
    return u === ADMIN_USER && p === ADMIN_PASS;
  } catch {
    return false;
  }
}

async function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; });
    req.on('end', () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

export default async function handler(req, res) {
  // 等待 neon 加载 (超时 2s, 失败也不阻塞)
  await Promise.race([
    neonPromise,
    new Promise((r) => setTimeout(r, 2000)),
  ]);

  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const path = url.pathname;

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // 页面
  if (path === '/' || path === '/index.html') {
    const rootIndex = readPageOrNull('index.html');
    if (rootIndex) {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.status(200).send(rootIndex);
    }
    return res.status(404).send('index.html not found');
  }

  if (path === '/artist-vote' || path === '/artist-vote/' || path === '/artist-vote/index.html') {
    const html = readPageOrNull('artist-vote/index.html');
    if (html) {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.status(200).send(html);
    }
    return res.status(404).send('artist-vote/index.html not found');
  }

  // 静态图片
  if (path.startsWith('/images/')) {
    const filename = path.replace('/images/', '');
    const img = readPageOrNull(join('artist-vote/images', filename));
    if (img) {
      const ext = filename.split('.').pop().toLowerCase();
      const mime = ext === 'png' ? 'image/png' : ext === 'webp' ? 'image/webp' : 'image/jpeg';
      res.setHeader('Content-Type', mime);
      res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      return res.status(200).send(img);
    }
    return res.status(404).send('Image not found: ' + filename);
  }

  // API: 艺术家列表
  // 永远以 artists.json 为权威源 (顺序/imageUrl/name/cat/artist/colors)
  // 仅从 DB 合并 votes 数字
  if (path === '/api/artists') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    if (neonReady && sql) {
      try {
        await ensureDb();
        const rows = await sql`SELECT id, votes FROM artists_votes ORDER BY id`;
        const votesMap = {};
        for (const r of rows) votesMap[r.id] = r.votes || 0;
        const merged = artistsData.map((a) => ({
          id: a.id,
          name: a.name,
          artist: a.artist || '',
          cat: a.cat || '',
          votes: votesMap[a.id] || 0,
          colors: a.colors || ['#ccc', '#aaa', '#eee'],
          imageUrl: a.imageUrl || null,
        }));
        return res.status(200).json(merged);
      } catch (e) {
        console.error('[api/artists] DB error:', e.message);
        return res.status(200).json(artistsData);
      }
    }
    return res.status(200).json(artistsData);
  }

  // API: 健康检查
  if (path === '/api/health') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.status(200).json({
      ok: true,
      version: process.version,
      artistsCount: artistsData.length,
      neonReady,
      dbConfigured: !!DATABASE_URL,
    });
  }

  // API: 调试 - 看 artist-vote/images 目录到底有什么
  if (path === '/api/debug-images') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    const imagesDir = join(__dirname, '..', 'artist-vote', 'images');
    let info = {
      imagesDir,
      exists: false,
      files: [],
      error: null,
    };
    try {
      info.exists = existsSync(imagesDir);
      if (info.exists) {
        info.files = readdirSync(imagesDir);
      }
    } catch (e) {
      info.error = e.message;
    }
    return res.status(200).json(info);
  }

  // API: 检查某观众今天已投过哪些艺术家
  if (path === '/api/check-fingerprint' && req.method === 'POST') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    try {
      const { fingerprint } = await readJsonBody(req);
      const today = getTodayKey();
      if (!fingerprint || !neonReady || !sql) {
        return res.status(200).json({ voted: false, voted_today: [], voted_ids: [], today });
      }
      await ensureDb();
      const rows = await sql`SELECT artist_id FROM daily_votes WHERE fingerprint = ${fingerprint} AND vote_date = ${today}`;
      const voted_today = rows.map((r) => r.artist_id);
      return res.status(200).json({ voted: voted_today.length > 0, voted_today, voted_ids: voted_today, today });
    } catch (e) {
      return res.status(200).json({ voted: false, voted_today: [], voted_ids: [], today: getTodayKey(), error: e.message });
    }
  }

  // API: 投票 (支持 voted_ids 数组或单数 artist_id)
  if (path === '/api/vote' && req.method === 'POST') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    try {
      const body = await readJsonBody(req);
      const { artist_id, voted_ids, fingerprint } = body;
      if (!fingerprint) return res.status(400).json({ error: '缺少 fingerprint' });

      // 兼容 voted_ids 数组 (前端实际发的格式)
      const ids = voted_ids ? voted_ids.map(Number) : (artist_id ? [Number(artist_id)] : []);
      if (ids.length === 0) return res.status(400).json({ error: '缺少 artist_id 或 voted_ids' });

      const validIds = new Set(artistsData.map((a) => a.id));
      const invalid = ids.filter((id) => !validIds.has(id));
      if (invalid.length > 0) {
        return res.status(400).json({ error: `无效艺术家 ID: ${invalid.join(', ')}` });
      }

      const today = getTodayKey();

      if (!neonReady || !sql) {
        return res.status(503).json({ error: '数据库未配置, 投票功能不可用' });
      }

      await ensureDb();

      // 找出今天已经投过的 id (跳过, 不重复插入)
      const existingRows = await sql`SELECT artist_id FROM daily_votes WHERE fingerprint = ${fingerprint} AND vote_date = ${today} AND artist_id = ANY(${ids})`;
      const existingSet = new Set(existingRows.map((r) => r.artist_id));
      const newIds = ids.filter((id) => !existingSet.has(id));

      // 插入新投票 (UNIQUE 约束防重)
      for (const id of newIds) {
        try {
          await sql`INSERT INTO daily_votes (fingerprint, artist_id, vote_date) VALUES (${fingerprint}, ${id}, ${today})`;
          await sql`UPDATE artists_votes SET votes = votes + 1 WHERE id = ${id}`;
        } catch (e) {
          if (e.message && e.message.includes('unique')) {
            // 并发重复, 忽略
            continue;
          }
          throw e;
        }
      }

      // 返回完整当天已投列表
      const allRows = await sql`SELECT artist_id FROM daily_votes WHERE fingerprint = ${fingerprint} AND vote_date = ${today}`;
      const voted_today = allRows.map((r) => r.artist_id);

      return res.status(200).json({
        success: true,
        voted_ids: voted_today,
        voted_today,
        inserted: newIds,
        skipped: ids.filter((id) => existingSet.has(id)),
        vote_date: today,
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // API: 管理员统计 (总票数/投票人数/最高票数/Top10)
  if (path === '/api/stats') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    if (!neonReady || !sql) {
      return res.status(200).json({ total_votes: 0, total_voters: 0, today_votes: 0, top10: [] });
    }
    try {
      await ensureDb();
      const totals = await sql`SELECT COALESCE(SUM(votes),0)::int as total FROM artists_votes`;
      const voters = await sql`SELECT COUNT(DISTINCT fingerprint)::int as total FROM daily_votes`;
      const today = getTodayKey();
      const todayTotals = await sql`SELECT COUNT(*)::int as total FROM daily_votes WHERE vote_date = ${today}`;
      // 拿 metaMap 拿到艺术家名字
      const metaMap = {};
      for (const a of artistsData) metaMap[a.id] = a;
      const top = await sql`SELECT id, votes FROM artists_votes ORDER BY votes DESC LIMIT 10`;
      const top10 = top.map((t) => ({
        id: t.id,
        name: metaMap[t.id]?.name || `#${t.id}`,
        votes: t.votes || 0,
      }));
      return res.status(200).json({
        total_votes: totals[0]?.total || 0,
        total_voters: voters[0]?.total || 0,
        today_votes: todayTotals[0]?.total || 0,
        top10,
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // /admin 管理后台 (Basic Auth)
  if (path === '/admin' || path === '/admin/') {
    if (!checkAuth(req)) {
      res.setHeader('WWW-Authenticate', 'Basic realm="Admin Panel"');
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      return res.status(401).send('<h1>401 Unauthorized</h1><p>需要管理员账号密码 (默认 admin / admin123)</p>');
    }
    try {
      const adminHtml = readPageOrNull('admin.html');
      if (adminHtml) {
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        return res.status(200).send(adminHtml);
      }
      return res.status(500).send('admin.html not found');
    } catch (e) {
      return res.status(500).send('Admin page error: ' + e.message);
    }
  }

  // 404
  return res.status(404).json({ error: 'Not found', path });
}
