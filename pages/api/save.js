import { promises as fs } from 'fs';
import path from 'path';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const { data } = req.body || {};
  if (!data) {
    res.status(400).json({ error: 'Missing data' });
    return;
  }

  const filePath = path.join(process.cwd(), 'saved.json');
  let contents = [];

  try {
    await fs.access(filePath);
    const dataStr = await fs.readFile(filePath, 'utf-8');
    contents = JSON.parse(dataStr);
  } catch (err) {
    if (err.code !== 'ENOENT') {
      console.error('Failed to read existing saved.json:', err);
    }
  }

  contents.push({ data, date: new Date().toISOString() });
  await fs.writeFile(filePath, JSON.stringify(contents, null, 2));

  res.status(200).json({ status: 'saved' });
}
