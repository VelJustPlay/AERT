const express = require('express');
const path = require('path');

const app = express();
const port = process.env.PORT || 8000;
const clients = new Set();

function broadcastCount() {
  const count = clients.size;

  for (const client of clients) {
    client.res.write(`data: ${JSON.stringify({ count })}\n\n`);
  }
}

function heartbeat(client) {
  client.timer = setInterval(() => {
    if (!client.res.writableEnded) {
      client.res.write(': ping\n\n');
    }
  }, 20000);
}

app.use(express.static(__dirname));

app.get('/online-count', (req, res) => {
  res.json({ count: clients.size });
});

app.get('/online-events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders?.();

  const client = { res, timer: null };
  clients.add(client);
  res.write(`data: ${JSON.stringify({ count: clients.size })}\n\n`);
  heartbeat(client);

  req.on('close', () => {
    if (client.timer) {
      clearInterval(client.timer);
    }

    clients.delete(client);
    broadcastCount();
  });

  broadcastCount();
});

app.get('/favicon.ico', (req, res) => {
  res.sendFile(path.join(__dirname, 'Axion.png'));
});

app.listen(port, () => {
  console.log(`Axion live counter server running at http://localhost:${port}`);
});
