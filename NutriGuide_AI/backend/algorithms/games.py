import math
import random
from copy import deepcopy

WIN_LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


def empty_board():
    return [None] * 9


def legal_moves(board):
    return [i for i, cell in enumerate(board) if cell is None]


def apply(board, move, player):
    nxt = board[:]
    nxt[move] = player
    return nxt


def winner(board):
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def terminal(board):
    return winner(board) is not None or not legal_moves(board)


def evaluate(board, ai="O"):
    w = winner(board)
    if w == ai:
        return 10
    if w and w != ai:
        return -10
    return 0


def minimax(board, depth, maximizing, alpha=-math.inf, beta=math.inf, ai="O"):
    if terminal(board) or depth == 0:
        return evaluate(board, ai)
    player = ai if maximizing else ("X" if ai == "O" else "O")
    if maximizing:
        value = -math.inf
        for move in legal_moves(board):
            value = max(value, minimax(apply(board, move, player), depth - 1, False, alpha, beta, ai))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    value = math.inf
    for move in legal_moves(board):
        value = min(value, minimax(apply(board, move, player), depth - 1, True, alpha, beta, ai))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def best_minimax_move(board, ai="O", depth=9):
    best, chosen = -math.inf, None
    for move in legal_moves(board):
        score = minimax(apply(board, move, ai), depth - 1, False, ai=ai)
        if score > best:
            best, chosen = score, move
    return chosen if chosen is not None else (legal_moves(board)[0] if legal_moves(board) else None)


class MCTSNode:
    def __init__(self, board, player, parent=None, move=None):
        self.board = board
        self.player = player
        self.parent = parent
        self.move = move
        self.children = []
        self.untried = legal_moves(board)
        self.wins = 0.0
        self.visits = 0

    def uct(self, c=1.4):
        if self.visits == 0:
            return math.inf
        return self.wins / self.visits + c * math.sqrt(math.log(self.parent.visits) / self.visits)


def _playout(board, player):
    b, p = board[:], player
    while not terminal(b):
        moves = legal_moves(b)
        if not moves:
            break
        b = apply(b, random.choice(moves), p)
        p = "O" if p == "X" else "X"
    w = winner(b)
    if w is None:
        return 0.5
    return 1.0 if w == "O" else 0.0


def mcts_move(board, ai="O", iterations=200):
    if not legal_moves(board):
        return None
    root = MCTSNode(board, ai)
    for _ in range(iterations):
        node = root
        b = board[:]
        player = ai
        while node.untried == [] and node.children:
            node = max(node.children, key=lambda n: n.uct())
            b = node.board
            player = node.player
        if node.untried:
            mv = node.untried.pop()
            nxt_player = "O" if player == "X" else "X"
            child_board = apply(b, mv, player)
            child = MCTSNode(child_board, nxt_player, parent=node, move=mv)
            node.children.append(child)
            node = child
            b = child_board
            player = nxt_player
        result = _playout(b, player)
        while node:
            node.visits += 1
            if node.player != ai:
                node.wins += result
            else:
                node.wins += 1 - result
            node = node.parent
    if not root.children:
        return legal_moves(board)[0]
    return max(root.children, key=lambda n: n.visits).move


def choose_move(board, engine="alphabeta"):
    board = [None if c in (None, "", " ") else c for c in board]
    if engine == "mcts":
        move = mcts_move(board)
        return {"move": move, "engine": "mcts", "board": apply(board, move, "O") if move is not None else board}
    move = best_minimax_move(board)
    return {
        "move": move,
        "engine": "alphabeta",
        "board": apply(board, move, "O") if move is not None else board,
        "winner": winner(apply(board, move, "O") if move is not None else board),
    }
