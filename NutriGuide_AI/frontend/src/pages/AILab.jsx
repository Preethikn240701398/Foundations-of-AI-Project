import { useState } from "react";
import { RotateCcw } from "lucide-react";
import api, { errText } from "../services/api";
import { useUI } from "../context/UIContext";
import { Seg, Spinner } from "../components/ui";

const LINES = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
const winLine = (b) => LINES.find(([a, c, d]) => b[a] && b[a] === b[c] && b[a] === b[d]);

const INFO = {
  alphabeta: ["Minimax + alpha-beta pruning", "Searches the full game tree assuming both players play perfectly. Alpha-beta prunes branches that cannot change the result, so it never loses at tic-tac-toe."],
  mcts: ["Monte Carlo Tree Search", "Runs thousands of random playouts from each move and picks the move with the best win statistics. No hand-written evaluation function is needed."],
};

export default function AILab() {
  const { toast } = useUI();
  const [board, setBoard] = useState(Array(9).fill(null));
  const [engine, setEngine] = useState("alphabeta");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const line = winLine(board);

  const reset = () => { setBoard(Array(9).fill(null)); setResult(null); };
  const play = async (i) => {
    if (board[i] || busy || result) return;
    const next = board.map((c, k) => (k === i ? "X" : c));
    setBoard(next);
    if (winLine(next)) return setResult("You win!");
    if (next.every(Boolean)) return setResult("Draw");
    setBusy(true);
    try {
      const { data } = await api.post("/ai-lab/game-move", { board: next, engine });
      setBoard(data.board);
      if (winLine(data.board)) setResult("AI wins");
      else if (data.board.every(Boolean)) setResult("Draw");
    } catch (e) { toast(errText(e), "err"); } finally { setBusy(false); }
  };

  return (
    <div>
      <div className="page-head"><div><h1>AI Lab</h1><p>Game-playing search algorithms from the AI syllabus, running on the backend.</p></div></div>
      <div className="grid g2">
        <div className="card">
          <div className="row between mb-16"><Seg value={engine} onChange={(e) => { setEngine(e); reset(); }} options={[["alphabeta", "Alpha-beta"], ["mcts", "Monte Carlo"]]} />
            <button className="btn secondary sm" onClick={reset}><RotateCcw size={14} />New game</button></div>
          <div className="board">{board.map((c, i) => <button key={i} className={`cell ${c === "O" ? "o" : ""}`} disabled={!!c || busy || !!result} onClick={() => play(i)} style={line?.includes(i) ? { background: "var(--primary-soft)", borderColor: "var(--primary)" } : null}>{c}</button>)}</div>
          <div className="center mt-16" style={{ minHeight: 28 }}>{busy ? <span className="row gap-6" style={{ justifyContent: "center" }}><Spinner size={16} /> AI is thinking...</span> : result ? <b style={{ fontSize: 18 }}>{result}</b> : <span className="muted small">You are X. Your move.</span>}</div>
        </div>
        <div className="col gap-16">
          <div className="card"><h3>{INFO[engine][0]}</h3><p className="small muted mt-8">{INFO[engine][1]}</p></div>
          <div className="card soft"><h4 className="mb-8">Where else does the project use AI?</h4>
            <ul className="small muted col" style={{ paddingLeft: 18, margin: 0, gap: 6 }}>
              <li><b>Diet plan:</b> CSP backtracking, A*, BFS and simulated annealing</li>
              <li><b>Assistant &amp; Knowledge base:</b> forward and backward chaining</li>
              <li><b>Progress:</b> regression, k-means and preference learning</li>
              <li><b>Food scanner:</b> search under uncertainty</li></ul></div>
        </div>
      </div>
    </div>
  );
}
