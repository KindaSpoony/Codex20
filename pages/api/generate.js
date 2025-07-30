export default async function handler(req, res) {
  const { prompt } = req.body;

  if (!prompt) {
    return res.status(400).json({ error: "Missing prompt in request body" });
  }

  // Call OpenAI GPT API
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`
    },
    body: JSON.stringify({
      model: "gpt-4",
      messages: [{ role: "user", content: prompt }],
      temperature: 0.3
    })
  });

  const data = await response.json();

  // Assume GPT outputs JSON in message content
  try {
    const report = JSON.parse(data.choices[0].message.content);
    res.status(200).json(report);
  } catch (error) {
    res.status(500).json({ error: "GPT response invalid JSON", details: error.message });
  }
}
