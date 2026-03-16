"""
app.py — Chatbot de Análise de Dados
Backend Flask que gerencia sessões, processa uploads e chama o Claude Code CLI.
O LLM faz toda a análise dinamicamente — sem regras hardcoded nem pré-processamento.

Histórico persistente: cada sessão é salva em history/{session_id}.json
e pode ser retomada a qualquer momento.
"""
import io
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime

import pandas as pd
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

app = Flask(__name__)

UPLOAD_DIR  = os.path.join(os.path.dirname(__file__), "uploads")
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history")
os.makedirs(UPLOAD_DIR,  exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

CLAUDE_CMD       = os.getenv("CLAUDE_CMD", "claude").split()
CLAUDE_TIMEOUT   = int(os.getenv("CLAUDE_TIMEOUT", "600"))
WORK_DIR         = os.path.dirname(os.path.abspath(__file__))
MAX_FULL_CSV_BYTES = int(os.getenv("MAX_FULL_CSV_BYTES", str(400_000)))

# Cache em memória das sessões ativas: session_id → {file_path, meta, history, title, ...}
_sessions: dict = {}


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def _history_path(sid: str) -> str:
    return os.path.join(HISTORY_DIR, f"{sid}.json")


def _save_session(sid: str) -> None:
    """Persiste a sessão completa em disco."""
    sess = _sessions.get(sid)
    if not sess:
        return
    payload = {
        "session_id":  sid,
        "title":       sess.get("title", "Nova conversa"),
        "created_at":  sess.get("created_at", _now()),
        "updated_at":  _now(),
        "file": sess.get("meta"),          # metadados do arquivo (pode ser None)
        "file_path":   sess.get("file_path"),
        "history":     sess.get("history", []),
    }
    with open(_history_path(sid), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _load_session(sid: str) -> dict | None:
    """Carrega uma sessão do disco para a memória. Retorna None se não existir."""
    path = _history_path(sid)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    sess = {
        "title":      data.get("title", "Conversa"),
        "created_at": data.get("created_at", _now()),
        "file_path":  data.get("file_path"),
        "meta":       data.get("file"),
        "history":    data.get("history", []),
    }
    _sessions[sid] = sess
    return sess


def _list_sessions() -> list[dict]:
    """Lista todas as sessões salvas, ordenadas da mais recente para a mais antiga."""
    result = []
    for fname in os.listdir(HISTORY_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(HISTORY_DIR, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            msg_count = len([m for m in data.get("history", []) if m["role"] == "user"])
            result.append({
                "session_id":  data.get("session_id", fname[:-5]),
                "title":       data.get("title", "Conversa"),
                "updated_at":  data.get("updated_at", ""),
                "created_at":  data.get("created_at", ""),
                "filename":    (data.get("file") or {}).get("filename"),
                "msg_count":   msg_count,
            })
        except Exception:
            continue
    result.sort(key=lambda x: x["updated_at"], reverse=True)
    return result


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _make_title(message: str) -> str:
    """Gera título da conversa a partir da primeira mensagem do usuário."""
    clean = message.strip().replace("\n", " ")
    return clean[:72] + ("…" if len(clean) > 72 else "")


# ---------------------------------------------------------------------------
# Rotas — sessões
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/sessions", methods=["GET"])
def list_sessions():
    """Lista todas as conversas salvas."""
    return jsonify(_list_sessions())


@app.route("/sessions", methods=["POST"])
def new_session():
    """Cria uma nova sessão em branco."""
    sid = str(uuid.uuid4())
    _sessions[sid] = {
        "title":      "Nova conversa",
        "created_at": _now(),
        "file_path":  None,
        "meta":       None,
        "history":    [],
    }
    _save_session(sid)
    return jsonify({"session_id": sid})


@app.route("/sessions/<sid>", methods=["GET"])
def get_session(sid: str):
    """Carrega uma sessão existente (do disco se necessário)."""
    if sid not in _sessions:
        sess = _load_session(sid)
        if not sess:
            return jsonify({"error": "Sessão não encontrada."}), 404

    sess = _sessions[sid]

    # Verifica se o arquivo ainda existe no disco
    file_ok = bool(sess.get("file_path") and os.path.exists(sess["file_path"]))

    return jsonify({
        "session_id": sid,
        "title":      sess.get("title", "Conversa"),
        "created_at": sess.get("created_at"),
        "file":       sess.get("meta"),
        "file_ok":    file_ok,
        "history":    sess.get("history", []),
    })


@app.route("/sessions/<sid>", methods=["DELETE"])
def delete_session(sid: str):
    """Remove sessão da memória e do disco."""
    _sessions.pop(sid, None)
    path = _history_path(sid)
    if os.path.exists(path):
        os.unlink(path)
    return jsonify({"ok": True})


@app.route("/sessions/<sid>/history", methods=["DELETE"])
def clear_history(sid: str):
    """Limpa o histórico mantendo o arquivo carregado."""
    if sid not in _sessions:
        if not _load_session(sid):
            return jsonify({"error": "Sessão não encontrada."}), 404
    _sessions[sid]["history"] = []
    _sessions[sid]["title"] = "Nova conversa"
    _save_session(sid)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Rotas — upload e chat
# ---------------------------------------------------------------------------

@app.route("/upload", methods=["POST"])
def upload():
    sid = request.form.get("session_id", "")
    if not sid:
        return jsonify({"error": "session_id ausente."}), 400

    # Garante que a sessão existe em memória
    if sid not in _sessions:
        if not _load_session(sid):
            return jsonify({"error": "Sessão inválida."}), 400

    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400

    f = request.files["file"]
    filename = (f.filename or "").lower()
    if not any(filename.endswith(ext) for ext in (".xlsx", ".xls", ".csv")):
        return jsonify({"error": "Formato inválido — use .xlsx, .xls ou .csv"}), 400

    try:
        raw = f.read()
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
        else:
            engine = "openpyxl" if filename.endswith(".xlsx") else "xlrd"
            df = pd.read_excel(io.BytesIO(raw), engine=engine)

        csv_path = os.path.join(UPLOAD_DIR, f"{sid}.csv")
        df.to_csv(csv_path, index=False)

        columns_meta = []
        for col in df.columns:
            entry = {
                "name":    col,
                "dtype":   str(df[col].dtype),
                "nunique": int(df[col].nunique()),
                "nulls":   int(df[col].isnull().sum()),
            }
            if pd.api.types.is_numeric_dtype(df[col]) and not df[col].empty:
                entry["min"] = _safe_float(df[col].min())
                entry["max"] = _safe_float(df[col].max())
            columns_meta.append(entry)

        meta = {
            "filename": f.filename,
            "n_rows":   len(df),
            "n_cols":   len(df.columns),
            "columns":  columns_meta,
        }

        _sessions[sid].update({
            "file_path": csv_path,
            "meta":      meta,
            "history":   [],
        })
        _save_session(sid)

        return jsonify({"ok": True, **meta})

    except Exception as exc:
        return jsonify({"error": f"Erro ao processar arquivo: {exc}"}), 500


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    sid     = body.get("session_id", "")
    message = body.get("message", "").strip()

    if not sid:
        return jsonify({"error": "session_id ausente."}), 400
    if not message:
        return jsonify({"error": "Mensagem vazia."}), 400

    # Carrega do disco se necessário
    if sid not in _sessions:
        if not _load_session(sid):
            return jsonify({"error": "Sessão não encontrada."}), 404

    sess = _sessions[sid]

    def generate():
        tmp_path = None
        try:
            prompt = _build_prompt(sess, message)

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as fh:
                fh.write(prompt)
                tmp_path = fh.name

            with open(tmp_path, encoding="utf-8") as fh:
                result = subprocess.run(
                    CLAUDE_CMD + ["-p", "--dangerously-skip-permissions", "-"],
                    stdin=fh,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=CLAUDE_TIMEOUT,
                    encoding="utf-8",
                    errors="replace",
                    cwd=WORK_DIR,
                )

            reply = result.stdout.strip() if result.returncode == 0 \
                else f"⚠️ Erro do Claude: {result.stderr.strip() or 'sem detalhes'}"

            # Atualiza histórico e título
            sess["history"].append({"role": "user",      "content": message})
            sess["history"].append({"role": "assistant", "content": reply})

            if sess.get("title") in ("Nova conversa", ""):
                sess["title"] = _make_title(message)

            _save_session(sid)

            yield f"data: {json.dumps({'text': reply})}\n\n"

        except subprocess.TimeoutExpired:
            yield f"data: {json.dumps({'error': f'Tempo limite de {CLAUDE_TIMEOUT}s excedido.'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_prompt(sess: dict, message: str) -> str:
    data_section    = _build_data_section(sess)
    history_section = _build_history_section(sess["history"])
    return f"""{data_section}

---

## Histórico da conversa

{history_section}

---

## Pergunta do usuário

{message}"""


def _build_data_section(sess: dict) -> str:
    meta      = sess.get("meta")
    file_path = sess.get("file_path")

    if not meta or not file_path:
        return "## Dados\n\nNenhum dataset carregado ainda."

    col_lines = []
    for c in meta["columns"]:
        line = (f"- **{c['name']}** | tipo: {c['dtype']} "
                f"| {c['nunique']} valores únicos | {c['nulls']} nulos")
        if "min" in c:
            line += f" | min={c['min']}, max={c['max']}"
        col_lines.append(line)

    header = (
        f"## Dataset: {meta['filename']}\n"
        f"**Dimensões:** {meta['n_rows']:,} linhas × {meta['n_cols']} colunas\n\n"
        f"**Colunas:**\n" + "\n".join(col_lines)
    )

    try:
        df       = pd.read_csv(file_path)
        csv_str  = df.to_csv(index=False)
        csv_bytes = csv_str.encode("utf-8")

        if len(csv_bytes) <= MAX_FULL_CSV_BYTES:
            data_block = f"\n\n### Dados completos\n```csv\n{csv_str}```"
        else:
            sample_csv = df.head(500).to_csv(index=False)
            stats_str  = df.describe(include="all").to_string()
            data_block = (
                f"\n\n### Amostra (primeiras 500 de {meta['n_rows']:,} linhas)\n"
                f"```csv\n{sample_csv}```\n\n"
                f"### Estatísticas descritivas\n```\n{stats_str}\n```\n\n"
                f"> Arquivo completo: `{file_path}`"
            )
    except Exception as exc:
        data_block = f"\n\n⚠️ Erro ao ler dados: {exc}"

    return header + data_block


def _build_history_section(history: list) -> str:
    if not history:
        return "_Início da conversa._"
    turns = []
    for msg in history:
        role = "**Usuário**" if msg["role"] == "user" else "**Assistente**"
        turns.append(f"{role}: {msg['content']}")
    return "\n\n---\n\n".join(turns)


def _safe_float(value) -> float:
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes"),
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
    )
