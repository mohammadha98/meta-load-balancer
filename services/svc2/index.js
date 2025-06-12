const express = require('express');
const app = express();
const PORT = 80;

app.get('/', (req, res) => {
  res.json({
    service: 'svc2',
    time: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`Service svc2 listening on port ${PORT}`);
});