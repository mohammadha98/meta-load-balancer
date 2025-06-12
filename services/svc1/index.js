const express = require('express');
const app = express();
const PORT = 80;

app.get('/', (req, res) => {
  res.json({
    service: 'svc1',
    time: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`Service svc1 listening on port ${PORT}`);
});