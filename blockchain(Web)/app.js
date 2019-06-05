var express = require('express');
var http = require('http');
var app = express();
var server = http.createServer(app).listen(80);
var mysql = require('mysql')
var bodyParser = require('body-parser')
app.use(bodyParser.urlencoded({
  extended: true
}))
app.use(bodyParser.json())
var connection = mysql.createConnection({
  host: '192.168.110.111',
  port: 3306,
  user: 'kopo',
  password: 'kopo',
  database: 'kopo'
})
app.get('/', function(req, res) {
  res.sendfile("index.html");
});
app.get('/getBlockData', function(req, res) {
  res.sendfile("getBlockData.html");
});
app.get('/getTxdata', function(req, res) {
  res.sendfile("getTxdata.html");
});
app.get('/getNodelist', function(req, res) {
  res.sendfile("getNodelist.html");
});

app.get('/blockList', function(req, res) {
  var selectQuery = `select * from blockchain`;
  connection.query(selectQuery,
    function(err, rows, fields) {
      if (err) throw err;
      res.send(rows)
    }
  )
});
app.get('/txList', function(req, res) {
  var selectQuery = `select * from txdata where commityn = 0 order by fee DESC`;
  connection.query(selectQuery,
    function(err, rows, fields) {
      if (err) throw err;
      // console.log(rows);
      res.send(rows)
    }
  )
});
app.get('/nodeList', function(req, res) {
  var selectQuery = `select * from nodelist`;
  connection.query(selectQuery,
    function(err, rows, fields) {
      if (err) throw err;
      // console.log(rows);
      res.send(rows)
    }
  )
});
app.post('/searchBlock', function(req, res) {
  var start = Number(req.body.start) - 1
  var end = Number(req.body.end) - 1
  var selectQuery = `select * from blockchain where NO between ${start} and ${end}`;
  connection.query(selectQuery,
    function(err, rows, fields) {
      if (err) throw err;
      res.send(rows)
    }
  )
});
app.post('/searchTx', function(req, res) {
  var count = Number(req.body.count)
  var selectQuery = `select * from txdata order by fee desc limit ${count}`;
  connection.query(selectQuery,
    function(err, rows, fields) {
      if (err) throw err;
      res.send(rows)
    }
  )
});
app.get('/insertNode', function(req, res) {
  res.sendfile('insertNode.html')
});
app.post('/addNode', function(req, res) {
  var IP = req.body.IP
  var PORT = req.body.PORT
  var insertQuery = `insert into nodelist (IP, PORT) values ('${IP}', '${PORT}')`;
  connection.query(insertQuery,
    function(err, rows, fields) {
      if (err) throw err;
      res.send(rows)
    }
  )
});
