var express = require('express');
var app = express();
var bodyParser = require('body-parser');
app.use(bodyParser.json());
app.use(bodyParser.urlencoded());
var mysql = require('mysql');
var connection = mysql.createConnection({
  host: 'localhost',
  port: 3306,
  user: 'root',
  password: 'root',
  database: 'webui'
});

app.options('/*', (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS');
  res.header('Access-Control-Allow-Headers',
    'Content-Type, Authorization, Content-Length, X-Requested-With');
  res.send();
});

var port = 3000;
app.listen(port, function () {
  console.log('Example app listening on port 3000!');
});

app.use('/lib', express.static(__dirname + "/web/lib/"));

app.get('/', function (req, res) {
  res.send('Hello World!');
});

app.get("/login/login", function (req, res) {
  res.sendFile(__dirname + "/login/login.html");
});

app.get("/auth/callbackGoogle", function (req, res) {
  res.sendFile(__dirname + "/login/login.html");
})

app.get("/login/signin", function (req, res) {
  res.sendFile(__dirname + "/login/signin.html");
})

app.post("/adduser", function (req, res) {
  var json2 = req.body.json;
  connection.connect();
  var email = json2.email
  var name = json2.name
  console.log(name)
  console.log(email)
  var sql = `INSERT INTO userinfo (NAME, EMAIL, BALANCE) VALUES ("${name}", "${email}", '3000')` //google계정 닉네임, email로 DB에 추가
  connection.query(sql, function (err, rows, fields) {
    if (err) console.log(err);
    res.send(rows)
  });
  connection.end();
});

app.post("/userlogin", function (req, res) {
  var json2 = req.body.json;
  console.log(json2);
  console.log(json2.email);

  connection.connect();
  var email = json2.email
  var sql = 'SELECT * FROM userinfo WHERE email =' + mysql.escape(email);
  connection.query(sql, function (err, rows, fields) {
    if (err) console.log(err);
    console.log('rows', rows);
    res.send(rows)
  });
  connection.end();
});

app.post("/selectBalance", function (req, res) {
  var json2 = req.body.json;
  console.log(json2);
  console.log(json2.email);
  var email = json2.email
  var sql = 'SELECT * FROM userinfo WHERE email =' + mysql.escape(email);
  connection.query(sql, function (err, rows, fields) {
    if (err) console.log(err);
    console.log('rows', rows);
    console.log("db result : ", rows);
    res.send(rows)

  });
});


app.get('/main', function (req, res) {
  res.sendfile("main.html");
});

app.get('/login/main.html', function (req, res) {
  res.sendfile("login/main.html");
});

app.get('/blockchain/main.html', function (req, res) {
  res.sendfile("blockchain/main.html");
});

app.get('/mypage', function (req, res) {
  res.sendfile("mypage/main.html");
});

app.get('/send', function (req, res) {
  res.sendfile("mypage/send.html");
});

app.get('/blockdata', function (req, res) {
  res.sendfile("blockchain/blockdata.html");
});

app.get('/mine', function (req, res) {
  res.sendfile("blockchain/mine.html");
});

app.get('/balance', function (req, res) {
  res.sendfile("mypage/balance.html");
});
