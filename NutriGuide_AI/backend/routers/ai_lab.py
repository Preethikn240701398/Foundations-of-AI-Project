from fastapi import APIRouter, Depends

from algorithms.games import choose_move, legal_moves, terminal, winner
from auth_utils import get_current_user
from models.schemas import GameMoveIn

router = APIRouter(prefix="/ai-lab", tags=["ai-lab"])


@router.post("/game-move")
async def game_move(body: GameMoveIn, user=Depends(get_current_user)):
    board = [None if c in (None, "", " ") else c for c in body.board]
    if terminal(board):
        return {"board": board, "move": None, "winner": winner(board), "over": True, "engine": body.engine}
    result = choose_move(board, engine=body.engine)
    final = result["board"]
    return {**result, "winner": winner(final), "over": terminal(final), "legal": legal_moves(final)}
