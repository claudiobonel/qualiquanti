"""
app.py — Chatbot de Análise de Dados
Backend Flask que gerencia sessões, processa uploads e chama o Claude Code CLI.
O LLM faz toda a análise dinamicamente — sem regras hardcoded nem pré-processamento.

Histórico persistente: cada sessão é salva em history/{session_id}.json
e pode ser retomada a qualquer momento.
"""
import hashlib
import io
import json
import re
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

CLAUDE_CMD         = os.getenv("CLAUDE_CMD", "claude").split()
CLAUDE_TIMEOUT     = int(os.getenv("CLAUDE_TIMEOUT", "600"))
WORK_DIR           = os.path.dirname(os.path.abspath(__file__))
MAX_PROMPT_CSV_BYTES = int(os.getenv("MAX_PROMPT_CSV_BYTES", str(400_000)))

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
        "session_id":        sid,
        "title":             sess.get("title", "Nova conversa"),
        "created_at":        sess.get("created_at", _now()),
        "updated_at":        _now(),
        "file":              sess.get("meta"),
        "file_path":         sess.get("file_path"),
        "masked_path":       sess.get("masked_path"),
        "history":           sess.get("history", []),
        "sensitive_columns": sess.get("sensitive_columns", []),
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
        "title":             data.get("title", "Conversa"),
        "created_at":        data.get("created_at", _now()),
        "file_path":         data.get("file_path"),
        "masked_path":       data.get("masked_path"),
        "meta":              data.get("file"),
        "history":           data.get("history", []),
        "sensitive_columns": data.get("sensitive_columns", []),
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
        "title":             "Nova conversa",
        "created_at":        _now(),
        "file_path":         None,
        "masked_path":       None,
        "meta":              None,
        "history":           [],
        "sensitive_columns": [],
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
        "session_id":        sid,
        "title":             sess.get("title", "Conversa"),
        "created_at":        sess.get("created_at"),
        "file":              sess.get("meta"),
        "file_ok":           file_ok,
        "history":           sess.get("history", []),
        "sensitive_columns": sess.get("sensitive_columns", []),
    })


@app.route("/sessions/<sid>", methods=["DELETE"])
def delete_session(sid: str):
    """Remove sessão da memória e do disco."""
    sess = _sessions.pop(sid, None)
    # Remove arquivos gerados pela sessão
    for key in ("file_path", "masked_path"):
        fpath = (sess or {}).get(key)
        if fpath and os.path.exists(fpath):
            try:
                os.unlink(fpath)
            except OSError:
                pass
    path = _history_path(sid)
    if os.path.exists(path):
        os.unlink(path)
    return jsonify({"ok": True})


@app.route("/sessions/<sid>/sensitive-columns", methods=["POST"])
def set_sensitive_columns(sid: str):
    """Define quais colunas serão anonimizadas e gera o CSV mascarado em disco."""
    if sid not in _sessions:
        if not _load_session(sid):
            return jsonify({"error": "Sessão não encontrada."}), 404
    body = request.get_json(silent=True) or {}
    columns = body.get("columns", [])
    _sessions[sid]["sensitive_columns"] = columns

    # Remove masked anterior
    old_masked = _sessions[sid].get("masked_path")
    if old_masked and os.path.exists(old_masked):
        try:
            os.unlink(old_masked)
        except OSError:
            pass

    # Gera novo CSV mascarado (somente se há colunas sensíveis)
    masked_path = _generate_masked_csv(sid, _sessions[sid]) if columns else None
    _sessions[sid]["masked_path"] = masked_path

    _save_session(sid)
    return jsonify({"ok": True, "sensitive_columns": columns})


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
    if not filename.endswith(".xlsx"):
        return jsonify({"error": "Formato inválido — use .xlsx"}), 400

    try:
        raw = f.read()
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")

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

        # Remove arquivo mascarado anterior, se existir
        old_masked = _sessions[sid].get("masked_path")
        if old_masked and os.path.exists(old_masked):
            try:
                os.unlink(old_masked)
            except OSError:
                pass

        _sessions[sid].update({
            "file_path":         csv_path,
            "masked_path":       None,
            "meta":              meta,
            "history":           [],
            "sensitive_columns": [],
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

            # De-mascara localmente: substitui IDs anônimos pelos valores originais
            if sess.get("sensitive_columns"):
                reverse_map = _build_reverse_map(sess)
                reply = _apply_reverse_map(reply, reverse_map)

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

    sensitive_set = set(sess.get("sensitive_columns", []))
    col_lines = []
    for c in meta["columns"]:
        sensitive_tag = " | **[SENSÍVEL — valores anonimizados]**" if c["name"] in sensitive_set else ""
        line = (f"- **{c['name']}** | tipo: {c['dtype']} "
                f"| {c['nunique']} valores únicos | {c['nulls']} nulos{sensitive_tag}")
        if "min" in c:
            line += f" | min={c['min']}, max={c['max']}"
        col_lines.append(line)

    header = (
        f"## Dataset: {meta['filename']}\n"
        f"**Dimensões:** {meta['n_rows']:,} linhas × {meta['n_cols']} colunas\n\n"
        f"**Colunas:**\n" + "\n".join(col_lines)
    )

    # Arquivo a referenciar: versão mascarada (se existir) ou original
    sensitive   = sess.get("sensitive_columns", [])
    masked_path = sess.get("masked_path")
    ref_path    = masked_path if (sensitive and masked_path and os.path.exists(masked_path)) else file_path

    try:
        df = pd.read_csv(ref_path)  # lê já mascarado quando aplicável

        csv_str   = df.to_csv(index=False)
        csv_bytes = csv_str.encode("utf-8")

        if len(csv_bytes) <= MAX_PROMPT_CSV_BYTES:
            # Dataset cabe no prompt — envia completo
            data_block = f"\n\n### Dados completos\n```csv\n{csv_str}```"
        else:
            # Dataset grande — envia amostra + caminho do arquivo (já mascarado)
            sample_csv = df.head(500).to_csv(index=False)
            stats_str  = df.describe(include="all").to_string()
            data_block = (
                f"\n\n### Amostra (primeiras 500 de {meta['n_rows']:,} linhas)\n"
                f"```csv\n{sample_csv}```\n\n"
                f"### Estatísticas descritivas\n```\n{stats_str}\n```\n\n"
                f"> **Arquivo completo disponível:** `{ref_path}`\n"
                f"> Leia o arquivo completo antes de responder para garantir análise sobre todos os dados."
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


def _generate_masked_csv(sid: str, sess: dict) -> str | None:
    """Gera em disco um CSV com as colunas sensíveis anonimizadas. Retorna o caminho."""
    file_path = sess.get("file_path")
    sensitive = sess.get("sensitive_columns", [])
    if not file_path or not os.path.exists(file_path) or not sensitive:
        return None
    try:
        df = pd.read_csv(file_path)
        for col in sensitive:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda v, c=col: _mask_value(str(v), c) if pd.notna(v) else v
                )
        masked_path = os.path.join(UPLOAD_DIR, f"{sid}_masked.csv")
        df.to_csv(masked_path, index=False)
        return masked_path
    except Exception:
        return None


def _mask_value(value: str, col_name: str) -> str:
    """Gera um ID anônimo estável para um valor sensível (determinístico por col+valor)."""
    h = hashlib.md5(f"{col_name}:{value}".encode()).hexdigest()[:6].upper()
    return f"ID_{h}"


def _build_reverse_map(sess: dict) -> dict:
    """Lê o CSV original e constrói mapa ID_XXXXXX → valor_original para cada coluna sensível."""
    file_path = sess.get("file_path")
    sensitive = sess.get("sensitive_columns", [])
    if not file_path or not sensitive or not os.path.exists(file_path):
        return {}
    try:
        df = pd.read_csv(file_path)
        reverse = {}
        for col in sensitive:
            if col not in df.columns:
                continue
            for val in df[col].dropna().unique():
                masked_id = _mask_value(str(val), col)
                reverse[masked_id] = str(val)
        return reverse
    except Exception:
        return {}


def _apply_reverse_map(text: str, reverse_map: dict) -> str:
    """Substitui todos os IDs anônimos no texto pelos valores originais."""
    if not reverse_map:
        return text
    return re.sub(
        r'ID_[A-F0-9]{6}',
        lambda m: reverse_map.get(m.group(0), m.group(0)),
        text
    )


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
