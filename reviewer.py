"""Revisión del vídeo terminado (la llama visual.revisar). Todo queda en review_log.jsonl."""
import datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_LOG = os.path.join(HERE, "review_log.jsonl")
MIN_SCORE = float(os.environ.get("REVIEW_MIN_SCORE", "8"))


def log(kind, data):
    try:
        with open(REVIEW_LOG, "a") as f:
            f.write(json.dumps({"date": str(datetime.date.today()), "kind": kind, **data}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def ask_video(parts, temperature=0.3):
    import gemini
    return gemini.ask(parts, temperature)
