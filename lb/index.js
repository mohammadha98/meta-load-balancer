const express = require('express');
const httpProxy = require('http-proxy');
const promClient = require('prom-client');

const app = express();
const proxy = httpProxy.createProxyServer();

let algorithm = 'roundrobin';
let backends = ['svc1:80', 'svc2:80', 'svc3:80'];
let currentIndex = 0;
const connections = {};

const lbRequestsTotal = new promClient.Counter({
  name: 'lb_requests_total',
  help: 'Total number of requests handled by the load balancer'
});

app.use((req, res) => {
  lbRequestsTotal.inc();
  const target = selectBackend(req);
  proxy.web(req, res, { target: `http://${target}` });
});

app.post('/config', express.json(), (req, res) => {
  algorithm = req.body.algorithm;
  backends = req.body.backends;
  res.send('Configuration updated');
});

app.get('/metrics', (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(promClient.register.metrics());
});

function selectBackend(req) {
  switch (algorithm) {
    case 'roundrobin':
      return roundrobin();
    case 'leastconn':
      return leastconn();
    case 'iphash':
      return iphash(req.ip);
    default:
      return roundrobin();
  }
}

function roundrobin() {
  const target = backends[currentIndex];
  currentIndex = (currentIndex + 1) % backends.length;
  return target;
}

function leastconn() {
  let minConn = Infinity;
  let target = backends[0];
  backends.forEach(backend => {
    const conn = connections[backend] || 0;
    if (conn < minConn) {
      minConn = conn;
      target = backend;
    }
  });
  connections[target] = (connections[target] || 0) + 1;
  return target;
}

function iphash(ip) {
  const hash = ip.split('.').reduce((hash, octet) => hash * 256 + parseInt(octet), 0);
  return backends[hash % backends.length];
}

app.listen(80, () => console.log('Load balancer listening on port 80'));
app.listen(7000, () => console.log('Config API listening on port 7000'));
app.listen(9102, () => console.log('Metrics available on port 9102'));