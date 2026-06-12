# سرور بازی نبرد ناوها - پروژه شبکه

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import websockets

from game_engine import WIN_SCORE, Game, parse_coord

HOST = "0.0.0.0"
PORT = 8765
STATIC = Path(__file__).parent / "static"
LOGS = Path(__file__).parent / "logs"

game = Game()
clients = {}
ws_to_player = {}

LOGS.mkdir(exist_ok=True)
log_file = LOGS / ("game_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def write_log(text):
    logging.info(text)


async def send_msg(ws, data):
    await ws.send(json.dumps(data, ensure_ascii=False))


async def send_all(data, skip=None):
    for ws in list(clients.values()):
        if ws != skip:
            try:
                await send_msg(ws, data)
            except websockets.ConnectionClosed:
                pass


async def send_state():
    for pid, ws in clients.items():
        view = game.make_view(pid)
        await send_msg(ws, {"type": "state", **view})


async def on_connect(ws):
    if len(clients) >= 2:
        await send_msg(ws, {"type": "error", "message": "سرور پر است"})
        await ws.close()
        return None

    pid = 1 if 1 not in clients else 2
    clients[pid] = ws
    ws_to_player[ws] = pid
    write_log("بازیکن %d وصل شد" % pid)

    if pid == 1:
        game.phase = "waiting"
        await send_msg(ws, {
            "type": "status",
            "message": "در انتظار حریف...",
            "player": 1,
        })
    else:
        game.phase = "placement"
        await send_all({"type": "status", "message": "حریف وصل شد. بازی شروع می شود."})
        for p in [1, 2]:
            ship = game.next_ship(p)
            await send_msg(clients[p], {
                "type": "placement_request",
                "ship": ship,
                "message": "مختصات %s را وارد کنید" % ship,
            })
        write_log("هر دو بازیکن در لابی هستند")

    await send_state()
    return pid


async def on_disconnect(ws):
    pid = ws_to_player.pop(ws, None)
    if pid:
        clients.pop(pid, None)
        write_log("بازیکن %d قطع شد" % pid)
        await send_all({"type": "status", "message": "بازیکن %d قطع شد. بازی تمام شد." % pid})
        global game
        game = Game()


async def do_placement(ws, data):
    pid = ws_to_player[ws]
    ship = data.get("ship", "")
    head = data.get("head", "")
    tail = data.get("tail", "")

    expected = game.next_ship(pid)
    if ship != expected:
        await send_msg(ws, {"type": "error", "message": "نوبت کشتی %s است" % expected})
        return

    try:
        game.boards[pid].place_ship(ship, head, tail)
        game.ship_index[pid] += 1
        write_log("بازیکن %d کشتی %s گذاشت: %s تا %s" % (pid, ship, head, tail))
    except ValueError as e:
        await send_msg(ws, {"type": "error", "message": str(e)})
        return

    nxt = game.next_ship(pid)
    if nxt:
        await send_msg(ws, {
            "type": "placement_request",
            "ship": nxt,
            "message": "مختصات %s را وارد کنید" % nxt,
        })
    else:
        await send_msg(ws, {"type": "status", "message": "کشتی ها گذاشته شد. منتظر حریف..."})
        write_log("بازیکن %d تمام کشتی ها را گذاشت" % pid)

    if game.boards[1].all_placed() and game.boards[2].all_placed():
        game.phase = "playing"
        game.turn = 1
        await send_all({
            "type": "game_start",
            "message": "جنگ شروع شد! نوبت بازیکن ۱",
            "currentTurn": 1,
        })
        write_log("بازی شروع شد")

    await send_state()


async def do_fire(ws, data):
    pid = ws_to_player[ws]
    if game.phase != "playing":
        await send_msg(ws, {"type": "error", "message": "هنوز نوبت شلیک نیست"})
        return
    if game.turn != pid:
        await send_msg(ws, {"type": "error", "message": "نوبت شما نیست"})
        return

    target = data.get("target", "")
    try:
        row, col = parse_coord(target)
    except (ValueError, IndexError):
        await send_msg(ws, {"type": "error", "message": "مختصات اشتباه است"})
        return

    opp = 2 if pid == 1 else 1
    try:
        hit, ship_name = game.boards[opp].shot(row, col)
    except ValueError as e:
        await send_msg(ws, {"type": "error", "message": str(e)})
        return

    game.boards[pid].attack(row, col, hit)
    result = "hit" if hit else "miss"

    if hit:
        msg = "بازیکن %d به %s زد - اصابت!" % (pid, target)
    else:
        msg = "بازیکن %d به %s زد - خطا!" % (pid, target)

    write_log(msg)
    await send_all({
        "type": "fire_result",
        "shooter": pid,
        "target": target,
        "result": result,
        "message": msg,
    })

    if game.boards[pid].score >= WIN_SCORE:
        game.phase = "finished"
        game.winner = pid
        await send_all({
            "type": "game_over",
            "winner": pid,
            "message": "بازیکن %d برنده شد!" % pid,
        })
        write_log("بازیکن %d برنده شد" % pid)
    elif hit:
        await send_all({
            "type": "turn",
            "currentTurn": pid,
            "message": "اصابت! دوباره نوبت بازیکن %d" % pid,
        })
    else:
        game.turn = opp
        await send_all({
            "type": "turn",
            "currentTurn": opp,
            "message": "نوبت بازیکن %d" % opp,
        })

    await send_state()


async def handle_ws(ws):
    pid = await on_connect(ws)
    if not pid:
        return
    try:
        async for raw in ws:
            data = json.loads(raw)
            write_log("پیام: " + json.dumps(data, ensure_ascii=False))
            if data.get("type") == "placement":
                await do_placement(ws, data)
            elif data.get("type") == "fire":
                await do_fire(ws, data)
            else:
                await send_msg(ws, {"type": "error", "message": "نوع پیام ناشناخته"})
    except websockets.ConnectionClosed:
        pass
    finally:
        await on_disconnect(ws)


async def serve_http(reader, writer):
    line = await reader.readline()
    if not line:
        writer.close()
        return
    parts = line.decode().strip().split()
    path = parts[1] if len(parts) > 1 else "/"
    if path == "/":
        path = "/index.html"

    fpath = STATIC / path.lstrip("/")
    if not fpath.is_file():
        writer.write(b"HTTP/1.1 404 Not Found\r\n\r\n")
        await writer.drain()
        writer.close()
        return

    body = fpath.read_bytes()
    if path.endswith(".css"):
        ctype = "text/css"
    elif path.endswith(".js"):
        ctype = "application/javascript"
    else:
        ctype = "text/html; charset=utf-8"

    header = "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n\r\n" % (ctype, len(body))
    writer.write(header.encode() + body)
    await writer.drain()
    writer.close()


async def main():
    http = await asyncio.start_server(serve_http, HOST, 8080)
    ws = await websockets.serve(handle_ws, HOST, PORT)
    print("صفحه بازی: http://localhost:8080")
    print("سوکت: ws://localhost:%d" % PORT)
    async with http, ws:
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
