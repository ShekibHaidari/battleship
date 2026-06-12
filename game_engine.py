# موتور بازی نبرد ناوها

ROWS = "ABCDEFGHIJ"
SIZE = 10

SHIPS = {
    "Carrier": 5,
    "Battleship": 4,
    "Cruiser": 3,
    "Submarine": 3,
    "Destroyer": 2,
}

WIN_SCORE = 17
SHIP_ORDER = list(SHIPS.keys())


def parse_coord(text):
    text = text.strip().upper()
    row = ROWS.index(text[0])
    col = int(text[1:]) - 1
    if col < 0 or col >= SIZE:
        raise ValueError("مختصات اشتباه است")
    return row, col


def get_cells(head, tail):
    r1, c1 = parse_coord(head)
    r2, c2 = parse_coord(tail)
    if r1 != r2 and c1 != c2:
        raise ValueError("کشتی باید افقی یا عمودی باشد")

    cells = []
    if r1 == r2:
        if c2 < c1:
            c1, c2 = c2, c1
        for c in range(c1, c2 + 1):
            cells.append((r1, c))
    else:
        if r2 < r1:
            r1, r2 = r2, r1
        for r in range(r1, r2 + 1):
            cells.append((r, c1))
    return cells


class Board:
    def __init__(self):
        self.ships = {}
        self.occupied = set()
        self.enemy_shots = set()
        self.my_shots = set()
        self.my_hits = set()
        self.score = 0

    def place_ship(self, name, head, tail):
        if name in self.ships:
            raise ValueError("این کشتی قبلا گذاشته شده")
        cells = get_cells(head, tail)
        if len(cells) != SHIPS[name]:
            raise ValueError("اندازه کشتی درست نیست")
        for cell in cells:
            if cell in self.occupied:
                raise ValueError("کشتی ها روی هم افتاده")
        self.ships[name] = cells
        for cell in cells:
            self.occupied.add(cell)

    def all_placed(self):
        return len(self.ships) == len(SHIPS)

    def shot(self, row, col):
        pos = (row, col)
        if pos in self.enemy_shots:
            raise ValueError("قبلا به این خانه شلیک شده")
        self.enemy_shots.add(pos)
        for name, cells in self.ships.items():
            if pos in cells:
                return True, name
        return False, None

    def attack(self, row, col, hit):
        pos = (row, col)
        self.my_shots.add(pos)
        if hit:
            self.my_hits.add(pos)
            self.score += 1


class Game:
    def __init__(self):
        self.phase = "waiting"
        self.turn = 1
        self.winner = None
        self.boards = {1: Board(), 2: Board()}
        self.ship_index = {1: 0, 2: 0}

    def next_ship(self, player):
        i = self.ship_index[player]
        if i >= len(SHIP_ORDER):
            return None
        return SHIP_ORDER[i]

    def make_view(self, player):
        b = self.boards[player]
        opp = 2 if player == 1 else 1

        own = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                p = (r, c)
                if p in b.occupied:
                    row.append("&")
                elif p in b.enemy_shots:
                    row.append("*")
                else:
                    row.append(".")
            own.append(row)

        attack = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                p = (r, c)
                if p in b.my_shots:
                    row.append("#")
                else:
                    row.append(".")
            attack.append(row)

        return {
            "player": player,
            "phase": self.phase,
            "yourScore": b.score,
            "opponentScore": self.boards[opp].score,
            "currentTurn": self.turn,
            "isYourTurn": self.phase == "playing" and self.turn == player,
            "ownGrid": own,
            "attackGrid": attack,
            "nextShip": self.next_ship(player),
            "shipsPlaced": list(b.ships.keys()),
            "winner": self.winner,
        }
