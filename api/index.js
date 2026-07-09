// 最小测试版 — 验证 Vercel Node.js runtime 能否启动
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// 读取 artists.json 测试
let artistsData = [];
try {
  artistsData = JSON.parse(readFileSync(join(__dirname, 'artists.json'), 'utf-8'));
} catch (e) {
  console.error('artists.json load error:', e.message);
}

export default async function handler(req, res) {
  const url = new URL(req.url || '/', `http://${req.headers.host}`);
  const path = url.pathname;

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (path === '/api/artists') {
    return res.status(200).json({
      ok: true,
      runtime: 'node',
      nodeVersion: process.version,
      artistsCount: artistsData.length,
      firstArtist: artistsData[0] || null,
    });
  }

  if (path === '/api/health') {
    return res.status(200).json({ ok: true, runtime: 'node', version: process.version });
  }

  return res.status(200).json({
    ok: true,
    msg: 'hello from api/index.js (minimal test)',
    nodeVersion: process.version,
    artistsLoaded: artistsData.length,
  });
}
