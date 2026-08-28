/**
 * IaCGenie Unified Auth Wrapper v2 — TEMPLATE
 * 
 * Drop-in template for building multi-backend OIDC-gated dashboards.
 * Customize: SERVICE_BACKENDS, KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
 *            KEYCLOAK_CLIENT_SECRET, DOMAIN_BACKEND_MAP, SERVICE_DISPLAY_NAMES
 * 
 * Env vars:
 *   PORT=9090
 *   KEYCLOAK_URL=https://auth.iacgenie.com
 *   KEYCLOAK_REALM=iacgenie
 *   KEYCLOAK_CLIENT_ID=auth-wrapper
 *   KEYCLOAK_CLIENT_SECRET=*** *   SESSION_SECRET=*** *   SERVICE_BACKENDS=svc1:9091,svc2:9092,svc3:9093
 */
const express = require('express');
const session = require('express-session');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const fetch = require('node-fetch');
const http = require('http');

const app = express();
const PORT = parseInt(process.env.PORT) || 9090;
const KC_URL = process.env.KEYCLOAK_URL || 'https://auth.iacgenie.com';
const KC_REALM = process.env.KEYCLOAK_REALM || 'iacgenie';
const KC_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'auth-wrapper';
const KC_CLIENT_SECRET=proces...CRET || '';
const SESSION_SECRET=proces...CRET || 'change-me-in-production';

// Backend services: "svc1:9091,svc2:9092"
const BACKENDS = {};
const svcBackendsRaw = process.env.SERVICE_BACKENDS || 'default:9090';
svcBackendsRaw.split(',').forEach(function (pair) {
  var parts = pair.split(':');
  if (parts.length === 2) BACKENDS[parts[0]] = parseInt(parts[1]);
});

// Domain → backend name mapping
const DOMAIN_BACKEND_MAP = {
  'service1.example.com': 'svc1',
  'service2.example.com': 'svc2',
  'service3.example.com': 'svc3'
};

const SERVICE_DISPLAY_NAMES = {
  'svc1': 'Service One Dashboard',
  'svc2': 'Service Two Dashboard',
  'svc3': 'Service Three Dashboard'
};

const KC_AUTH_URL=*** + '/realms/' + KC_REALM + '/protocol/openid-connect/auth';
const KC_TOKEN_URL=*** + '/realms/' + KC_REALM + '/protocol/openid-connect/token';
const KC_LOGOUT_URL = KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/logout';

/* -- Token verification -- */
function verifyToken(req, res, next) {
  var token = req.cookies && req.cookies.access_token;
  if (!token) return res.redirect('/login');
  try {
    var decoded = jwt.decode(token);
    if (!decoded || decoded.exp * 1000 < Date.now()) return res.redirect('/login');
    req.user = decoded;
    next();
  } catch (e) { res.redirect('/login'); }
}

/* -- Get backend port from Host header -- */
function getBackendPort(req) {
  var host = req.get('X-Forwarded-Host') || req.hostname;
  var svcName = DOMAIN_BACKEND_MAP[host] || 'default';
  return BACKENDS[svcName] || BACKENDS['default'] || 9090;
}

function getServiceName(req) {
  var host = req.get('X-Forwarded-Host') || req.hostname;
  var svcName = DOMAIN_BACKEND_MAP[host] || 'default';
  return SERVICE_DISPLAY_NAMES[svcName] || 'Dashboard';
}

/* -- Middleware -- */
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
  secret: SESSION_SECRET, resave: false, saveUninitialized: true,
  cookie: { httpOnly: true, secure: false, maxAge: 300000 }
}));

/* -- Login -- */
app.get('/login', function (req, res) {
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  var state = crypto.randomBytes(16).toString('hex');
  var params = new URLSearchParams({
    response_type: 'code', client_id: KC_CLIENT_ID,
    redirect_uri: redirectBase + '/callback',
    scope: 'openid profile email', state: state
  });
  res.cookie('auth_state', state, { httpOnly: true, maxAge: 300000, sameSite: 'lax' });
  res.redirect(KC_AUTH_URL + '?' + params);
});

/* -- Callback -- */
app.get('/callback', async function (req, res) {
  var code = req.query.code, state = req.query.state;
  if (!code || state !== (req.cookies && req.cookies.auth_state))
    return res.status(400).send('Invalid auth state');
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  try {
    var resp = await fetch(KC_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code', code: code,
        redirect_uri: redirectBase + '/callback',
        client_id: KC_CLIENT_ID, client_secret: KC_CLIENT_SECRET
      })
    });
    var tokens = await resp.json();
    if (!tokens.access_token)
      return res.status(400).send('Auth failed: no access token');
    res.cookie('access_token', tokens.access_token, {
      httpOnly: true, secure: false, sameSite: 'lax',
      maxAge: (tokens.expires_in || 3600) * 1000
    });
    res.clearCookie('auth_state');
    res.redirect('/dashboard');
  } catch (e) { console.error('Token error:', e.message); res.status(500).send('Auth failed'); }
});

/* -- Dashboard -- */
app.get('/dashboard', verifyToken, function (req, res) {
  var u = req.user;
  var roles = (u.realm_access && u.realm_access.roles) ? u.realm_access.roles.join(', ') : 'N/A';
  var title = getServiceName(req);
  var html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>' + title + '</title>'
    + '<style>body{font-family:sans-serif;background:#1a1a2e;color:#fff;margin:0}'
    + '.card{background:rgba(255,255,255,.95);border-radius:12px;padding:24px;margin:20px auto;max-width:600px}'
    + 'h1{color:#e94560}</style></head><body>'
    + '<div class="card"><h1>' + title + '</h1><p>User: ' + (u.preferred_username || 'N/A')
    + '</p><p>Email: ' + (u.email || 'N/A') + '</p><p>Roles: ' + roles + '</p>'
    + '<a href="/logout" style="color:#e94560">Logout</a></div></body></html>';
  res.send(html);
});

/* -- Logout -- */
app.get('/logout', function (req, res) {
  var fwdHost = req.get('X-Forwarded-Host') || req.hostname;
  var redirectBase = 'https://' + fwdHost;
  res.clearCookie('access_token');
  res.clearCookie('auth_state');
  res.redirect(KC_LOGOUT_URL + '?post_logout_redirect_uri=' + encodeURIComponent(redirectBase + '/login'));
});

/* -- Health -- */
app.get('/health', function (req, res) {
  res.json({ status: 'ok', service: 'auth-wrapper' });
});

/* -- Root -- */
app.get('/', function (req, res) { res.redirect('/login'); });

/* -- Proxy authenticated requests to backend -- */
app.use('/proxied', verifyToken, function (req, res) {
  var targetPort = getBackendPort(req);
  var options = {
    hostname: '127.0.0.1', port: targetPort,
    path: req.path, method: req.method,
    headers: Object.assign({}, req.headers)
  };
  delete options.host;
  options.host = '127.0.0.1:' + targetPort;
  if (req.user) {
    options.headers['X-User-Name'] = req.user.preferred_username || '';
    options.headers['X-User-Email'] = req.user.email || '';
    options.headers['X-User-Roles'] = JSON.stringify(
      req.user.realm_access && req.user.realm_access.roles || []
    );
  }
  var proxyReq = http.request(options, function (proxyRes) {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });
  proxyReq.on('error', function (err) {
    console.error('Proxy error:', err.message);
    if (!res.headersSent) res.status(502).send('Backend unavailable');
  });
  req.pipe(proxyReq);
});

app.listen(PORT, '0.0.0.0', function () {
  console.log('Auth wrapper v2 listening on port ' + PORT);
  console.log('  Backends: ' + JSON.stringify(BACKENDS));
  console.log('  Domain map: ' + JSON.stringify(DOMAIN_BACKEND_MAP));
});