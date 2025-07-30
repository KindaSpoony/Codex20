export default async function handler(req, res) {
  const { report, repository, filepath } = req.body;

  if (!report || !repository || !filepath) {
    return res.status(400).json({ error: "Missing parameters in request body" });
  }

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

  const response = await fetch(`https://api.github.com/repos/${repository}/contents/${filepath}`, {
    method: "PUT",
    headers: {
      "Authorization": `Bearer ${GITHUB_TOKEN}`,
      "Content-Type": "application/json",
      "Accept": "application/vnd.github+json"
    },
    body: JSON.stringify({
      message: "Add daily GPT report",
      content: Buffer.from(JSON.stringify(report, null, 2)).toString('base64'),
    })
  });

  const data = await response.json();

  if (response.status >= 400) {
    res.status(response.status).json({ error: "GitHub API Error", details: data });
  } else {
    res.status(201).json({ fileUrl: data.content.html_url });
  }
}
