// کلاینت بازی نبرد ناوها

var ROWS = "ABCDEFGHIJ";
var SHIPS = { Carrier: 5, Battleship: 4, Cruiser: 3, Submarine: 3, Destroyer: 2 };
var SHIP_FA = {
  Carrier: "ناو هواپیمابر",
  Battleship: "نبردناو",
  Cruiser: "رزمناو",
  Submarine: "زیردریایی",
  Destroyer: "ناوشکن"
};

var ws = null;
var myId = null;
var placing = false;
var curShip = null;
var startCell = null;
var horizontal = true;

function $(id) { return document.getElementById(id); }

function toCoord(r, c) {
  return ROWS[r] + (c + 1);
}

function makeGrid(el) {
  el.innerHTML = "";
  for (var r = 0; r < 10; r++) {
    for (var c = 0; c < 10; c++) {
      var d = document.createElement("div");
      d.className = "cell";
      d.setAttribute("data-r", r);
      d.setAttribute("data-c", c);
      el.appendChild(d);
    }
  }
}

function cell(el, r, c) {
  return el.querySelector('[data-r="' + r + '"][data-c="' + c + '"]');
}

function setMsg(text) {
  $("msgBox").textContent = text;
}

function showLobby() {
  $("lobby").classList.remove("hide");
  $("game").classList.add("hide");
  $("endBox").classList.add("hide");
}

function showGame() {
  $("lobby").classList.add("hide");
  $("game").classList.remove("hide");
}

function drawOwn(grid) {
  var el = $("ownGrid");
  for (var r = 0; r < 10; r++) {
    for (var c = 0; c < 10; c++) {
      var d = cell(el, r, c);
      d.className = "cell";
      d.textContent = "";
      var ch = grid[r][c];
      if (ch === "&") { d.classList.add("ship"); d.textContent = "&"; }
      if (ch === "*") { d.classList.add("hit"); d.textContent = "*"; }

      if (placing) {
        d.classList.add("can-fire");
        d.onclick = (function(rr, cc) {
          return function() { clickPlace(rr, cc); };
        })(r, c);
        d.onmouseenter = (function(rr, cc) {
          return function() { hoverPlace(rr, cc); };
        })(r, c);
      } else {
        d.onclick = null;
        d.onmouseenter = null;
      }
    }
  }
}

function drawAtk(grid, canFire) {
  var el = $("atkGrid");
  for (var r = 0; r < 10; r++) {
    for (var c = 0; c < 10; c++) {
      var d = cell(el, r, c);
      d.className = "cell";
      d.textContent = "";
      if (grid[r][c] === "#") {
        d.classList.add("shot");
        d.textContent = "#";
      } else if (canFire) {
        d.classList.add("can-fire");
        d.onclick = (function(rr, cc) {
          return function() { fire(rr, cc); };
        })(r, c);
      }
    }
  }
}

function updateState(s) {
  if (s.player) {
    myId = s.player;
    $("playerNum").textContent = myId;
  }
  $("myScore").textContent = s.yourScore || 0;
  $("oppScore").textContent = s.opponentScore || 0;

  if (s.phase === "playing") {
    if (s.isYourTurn) $("turnText").textContent = "نوبت شماست";
    else $("turnText").textContent = "نوبت حریف";
  } else if (s.phase === "placement") {
    $("turnText").textContent = "مرحله چیدمان";
  } else {
    $("turnText").textContent = "منتظر...";
  }

  placing = s.phase === "placement" && s.nextShip;
  if (placing) {
    curShip = s.nextShip;
    $("placeBar").classList.remove("hide");
    $("shipName").textContent = (SHIP_FA[curShip] || curShip) + " (" + SHIPS[curShip] + " خانه)";
  } else {
    $("placeBar").classList.add("hide");
  }

  drawOwn(s.ownGrid);
  drawAtk(s.attackGrid, s.phase === "playing" && s.isYourTurn);

  var list = "";
  for (var name in SHIPS) {
    var ok = s.shipsPlaced.indexOf(name) >= 0;
    list += (ok ? "[✓] " : "[ ] ") + (SHIP_FA[name] || name) + "  ";
  }
  $("shipList").textContent = list;

  if (s.winner) {
    $("endBox").classList.remove("hide");
    if (s.winner === myId) {
      $("endTitle").textContent = "بردید!";
      $("endMsg").textContent = "شما به ۱۷ امتیاز رسیدید.";
    } else {
      $("endTitle").textContent = "باختید!";
      $("endMsg").textContent = "بازیکن " + s.winner + " برنده شد.";
    }
  }
}

function clearPreview() {
  var cells = $("ownGrid").querySelectorAll(".preview, .start, .bad");
  for (var i = 0; i < cells.length; i++) {
    cells[i].classList.remove("preview", "start", "bad");
  }
}

function clickPlace(r, c) {
  if (!placing || !curShip) return;

  if (!startCell) {
    startCell = { r: r, c: c };
    clearPreview();
    cell($("ownGrid"), r, c).classList.add("start");
    return;
  }

  send({
    type: "placement",
    ship: curShip,
    head: toCoord(startCell.r, startCell.c),
    tail: toCoord(r, c)
  });
  startCell = null;
  clearPreview();
}

function hoverPlace(r, c) {
  if (!placing || !curShip) return;
  clearPreview();
  var size = SHIPS[curShip];
  var sr = startCell ? startCell.r : r;
  var sc = startCell ? startCell.c : c;
  if (startCell) cell($("ownGrid"), sr, sc).classList.add("start");

  var horiz = horizontal;
  if (startCell && (r !== sr || c !== sc)) {
    horiz = (r === sr);
  }

  for (var i = 0; i < size; i++) {
    var rr = horiz ? sr : sr + i;
    var cc = horiz ? sc + i : sc;
    if (rr < 0 || rr > 9 || cc < 0 || cc > 9) continue;
    var d = cell($("ownGrid"), rr, cc);
    d.classList.add("preview");
    if (rr > 9 || cc > 9 || (horiz && sc + size - 1 > 9) || (!horiz && sr + size - 1 > 9)) {
      d.classList.add("bad");
    }
  }
}

function fire(r, c) {
  send({ type: "fire", target: toCoord(r, c) });
}

function send(data) {
  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify(data));
  }
}

function connect() {
  var url = $("serverUrl").value;
  if (ws) ws.close();

  ws = new WebSocket(url);

  ws.onopen = function() {
    $("connText").textContent = "وصل";
    $("connText").classList.add("on");
    showGame();
    setMsg("به سرور وصل شدید");
  };

  ws.onclose = function() {
    $("connText").textContent = "قطع";
    $("connText").classList.remove("on");
    $("endBox").classList.add("hide");
    showLobby();
  };

  ws.onerror = function() {
    setMsg("خطا در اتصال - سرور روشن است؟");
  };

  ws.onmessage = function(e) {
    var data = JSON.parse(e.data);
    if (data.type === "status" || data.type === "placement_request" ||
        data.type === "game_start" || data.type === "turn" ||
        data.type === "fire_result" || data.type === "game_over") {
      setMsg(data.message);
    }
    if (data.type === "placement_request") {
      curShip = data.ship;
      startCell = null;
    }
    if (data.type === "error") {
      setMsg("خطا: " + data.message);
    }
    if (data.type === "state") {
      updateState(data);
    }
  };
}

$("connectBtn").onclick = connect;
$("rotateBtn").onclick = function() {
  horizontal = !horizontal;
  clearPreview();
  setMsg(horizontal ? "افقی" : "عمودی");
};
$("clearBtn").onclick = function() {
  startCell = null;
  clearPreview();
};
$("backBtn").onclick = function() {
  if (ws) ws.close();
  showLobby();
};

// برچسب سطر و ستون
$("ownLabels").textContent = "A-J  |  1-10";
$("atkLabels").textContent = "A-J  |  1-10";
makeGrid($("ownGrid"));
makeGrid($("atkGrid"));
