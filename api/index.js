// 九十九出独角戏第二季 — 投票后端 (Node.js)
// 阶段 1: 静态资源 (images 路由 + HTML 页面)
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

function getTodayKey() {
  const now = new Date();
  const chinaTime = new Date(now.getTime() + (now.getTimezoneOffset() + 8 * 60) * 60 * 1000);
  return chinaTime.toISOString().slice(0, 10);
}

function readPageOrNull(relPath) {
  // 多个候选路径, 兼容不同部署布局
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

export default async function handler(req, res) {
  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const path = url.pathname;

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,Authorization');
  if (req.method === 'OPTIONS') return res.status(200).end();

  // 页面: 根目录 + artist-vote 入口
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

  // API: 获取艺术家列表
  if (path === '/api/artists') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.status(200).json(artistsData);
  }

  // API: 健康检查
  if (path === '/api/health') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    return res.status(200).json({
      ok: true,
      version: process.version,
      artistsCount: artistsData.length,
      __dirname,
      cwd: process.cwd(),
    });
  }

  // API: 调试
  if (path === '/api/debug') {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    let parent = 'error';
    let apiSelf = 'error';
    try { parent = readdirSync(join(__dirname, '..')); } catch (e) { parent = e.message; }
    try { apiSelf = readdirSync(__dirname); } catch (e) { apiSelf = e.message; }
    return res.status(200).json({
      __dirname,
      cwd: process.cwd(),
      parent,
      apiSelf,
    });
  }

  // 404
  return res.status(404).json({ error: 'Not found', path });
}
