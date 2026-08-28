const express = require('express');
const session = require('express-session');
const jwt = require('jsonwebtoken');
const crypto = require('crypto');
const fetch = require('node-fetch');

const app = express();
const PORT = process.env.PORT || 9091;
const KC_URL = process.env.KEYCLOAK_URL || 'http://127.0.0.1:8083';
const KC_REALM = process.env.KEYCLOAK_REALM || 'iacgenie';
const KC_CLIENT_ID = process.env.KEYCLOAK_CLIENT_ID || 'auth-wrapper';
const KC_CLIENT_SECRET=*** || '';
const SESSION_SECRET=*** || 'dashboard-session-secret';
const DASHBOARD_URL_BASE = process.env.DASHBOARD_URL_BASE || 'https://dashboard.example.com';
const SERVICE_NAME = process.env.SERVICE_NAME || 'Dashboard';
const TITLE = process.env.SERVICE_TITLE || SERVICE_NAME;
const DESCRIPTION = process.env.SERVICE_DESCRIPTION || '';
const LINKS_RAW = process.env.SERVICE_LINKS || '';
const LINKS = LINKS_RAW.split(',').map(function(l){return l.trim();}).filter(Boolean);

const KC_AUTH_URL=*** + '/realms/' + KC_REALM + '/protocol/openid-connect/auth';
const KC_TOKEN_URL=*** + '/realms/' + KC_REALM + '/protocol/openid-connect/token';

function verifyToken(req, res, next) {
  var token = req.cookies && req.cookies.access_token;
  if (!token) return res.redirect('/login');
  try {
    var d = jwt.decode(token);
    if (!d || d.exp * 1000 < Date.now()) return res.redirect('/login');
    req.user = d;
    next();
  } catch (e) { res.redirect('/login'); }
}

app.use(session({
  secret: SESSION_SECRET,
  resave: false,
  saveUninitialized: true,
  cookie: { httpOnly: true, secure: false, maxAge: 300000 }
  // secure=false REQUIRED behind reverse proxy (internal connection is HTTP)
}));

app.get('/login', function(req, res) {
  var state = crypto.randomBytes(16).toString('hex');
  var params = new URLSearchParams({
    response_type: 'code',
    client_id: KC_CLIENT_ID,
    redirect_uri: DASHBOARD_URL_BASE + '/callback',
    scope: 'openid profile email',
    state: state
  });
  res.cookie('auth_state', state, { httpOnly: true, maxAge: 300000 });
  res.redirect(KC_AUTH_URL + '?' + params);
});

app.get('/callback', async function(req, res) {
  var code = req.query.code;
  var state = req.query.state;
  if (!code || state !== (req.cookies && req.cookies.auth_state)) {
    return res.status(400).send('Invalid state');
  }
  try {
    var resp = await fetch(KC_TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: DASHBOARD_URL_BASE + '/callback',
        client_id: KC_CLIENT_ID,
        client_secret: KC_CLIENT_SECRET
      })
    });
    var tokens = await resp.json();
    if (!tokens.access_token) return res.status(400).send('Auth failed');
    res.cookie('access_token', tokens.access_token, {
      httpOnly: true, secure: false, sameSite: 'lax',
      maxAge: (tokens.expires_in || 3600) * 1000
    });
    res.redirect('/dashboard');
  } catch (e) { console.error('Token error:', e.message); res.status(500).send('Auth failed'); }
});

app.get('/dashboard', verifyToken, function(req, res) {
  var u = req.user;
  var roles = (u.realm_access && u.realm_access.roles) ? u.realm_access.roles.join(', ') : 'N/A';
  var linksHtml = LINKS.length ? '<div class="links">' + LINKS.map(function(l){return '<a href="' + l + '">Open</a>';}).join('') + '</div>' : '';

  var html = '<!DOCTYPE html><html><head><title>' + TITLE + '</title>' +
    '<style>body{font-family:sans-serif;margin:0;background:linear-gradient(135deg,#667eea,#764ba2)}' +
    '.header{background:rgba(255,255,255,.95);padding:20px 40px;display:flex;justify-content:space-between;align-items:center}' +
    '.header h1{margin:0;color:#333}.user-info span{color:#666;margin-right:15px}' +
    '.container{max-width:1000px;margin:30px auto;padding:0 20px}' +
    '.card{background:#fff;border-radius:12px;padding:30px;margin-bottom:20px;box-shadow:0 4px 20px rgba(0,0,0,.1)}' +
    '.card h2{margin-top:0;color:#333;border-bottom:2px solid #667eea;padding-bottom:10px}' +
    '.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}' +
    '.item{padding:15px;background:#f8f9fa;border-radius:8px}' +
    '.item label{display:block;font-size:12px;color:#888;text-transform:uppercase;margin-bottom:5px}' +
    '.item .v{font-size:18px;font-weight:600;color:#333}' +
    '.links{display:flex;gap:15px;margin-top:15px}' +
    '.links a{background:#667eea;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none}' +
    'footer{text-align:center;color:rgba(255,255,255,.7);padding:20px}</style></head><body>' +
    '<div class="header"><h1>' + TITLE + '</h1>' +
    '<div class="user-info"><span>' + (u.preferred_username || 'User') + '</span>' +
    '<a href="/logout" style="color:#dc3545">Logout</a></div></div>' +
    '<div class="container">' +
    '<div class="card"><h2>Status</h2><div class="grid">' +
    '<div class="item"><label>Service</label><div class="v">' + TITLE + '</div></div>' +
    '<div class="item"><label>Status</label><div class="v"><span style="color:green">Active</span></div></div>' +
    '<div class="item"><label>User</label><div class="v">' + (u.preferred_username || 'N/A') + '</div></div>' +
    '<div class="item"><label>Roles</label><div class="v">' + roles + '</div></div>' +
    '</div></div>' +
    '<div class="card"><h2>Info</h2><p>' + DESCRIPTION + '</p>' + linksHtml + '</div>' +
    '<div class="card"><h2>Actions</h2><div class="links"><a href="/login">Refresh</a><a href="/logout">Logout</a></div></div>' +
    '</div><footer>' + SERVICE_NAME + ' Dashboard</footer></body></html>';
  res.send(html);
});

app.get('/logout', function(req, res) {
  res.clearCookie('access_token');
  res.clearCookie('auth_state');
  res.redirect(KC_URL + '/realms/' + KC_REALM + '/protocol/openid-connect/logout?post_logout_redirect_uri=' + DASHBOARD_URL_BASE + '/login');
});

app.get('/health', function(req, res) { res.json({ status: 'ok', service: SERVICE_NAME }); });
app.get('/', function(req, res) { res.redirect('/login'); });

app.listen(PORT, '0.0.0.0', function() {
  console.log(SERVICE_NAME + ' listening on port ' + PORT);
});
