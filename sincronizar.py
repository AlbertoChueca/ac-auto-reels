"""Guarda en el repositorio los archivos de estado SIN perder nada aunque otro workflow haya guardado a la vez.

    python sincronizar.py "mensaje del commit" archivo1 archivo2 carpeta/ ...

Problema que evita: "Reels diarios" y "Comunidad" guardan a veces el mismo archivo
(p. ej. log.jsonl o el banco). Con git normal, el segundo en guardar choca con el primero y su trabajo se pierde.
Aquí se descarga la última versión del repositorio y se FUSIONA el contenido (verificaciones, preguntas usadas,
registros...) antes de subirlo, con reintentos.
"""
import json, os, shutil, subprocess, sys, tempfile, time

MERGE_DICT = {"banco/verificacion.json", "performance.json"}
MERGE_LINES = {"log.jsonl", "review_log.jsonl", "image_log.jsonl", "errores_reels.log", "tiempos.log"}


def sh(*a, check=True):
    r = subprocess.run(list(a), capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(a)}: {r.stderr.strip()[:300]}")
    return r


def load(path, default):
    try:
        if path.endswith(".jsonl"):
            return open(path).read().splitlines()
        return json.load(open(path))
    except Exception:
        return default


def merge(path, mine, theirs):
    """mine = versión de este workflow, theirs = la que hay ahora en el repositorio."""
    if path in MERGE_DICT:
        out = dict(theirs or {})
        for k, v in (mine or {}).items():
            t = out.get(k)
            if not isinstance(t, dict) or not isinstance(v, dict) or str(v.get("fecha", "")) >= str(t.get("fecha", "")):
                out[k] = v
        return out
    if path in MERGE_LINES:
        seen, out = set(), []
        for line in (theirs or []) + (mine or []):
            if line.strip() and line not in seen:
                seen.add(line); out.append(line)
        return out
    if path == "banco/piezas.json":                # unión por id (las piezas nuevas de otro workflow no se pierden)
        out, seen = [], set()
        for e in (theirs or []) + (mine or []):
            if e.get("id") not in seen:
                seen.add(e.get("id")); out.append(e)
        return out
    if path == "banco/generado.json":
        t, m = theirs or {"chunks": {}, "temas": {}}, mine or {"chunks": {}, "temas": {}}
        return {"chunks": {**t.get("chunks", {}), **m.get("chunks", {})},
                "temas": {k: max(t.get("temas", {}).get(k, ""), m.get("temas", {}).get(k, ""))
                          for k in set(t.get("temas", {})) | set(m.get("temas", {}))}}
    if path == "fuentes/visual.json":              # banco: unión de listas, nunca se pierde nada
        t, m = theirs or {}, mine or {}
        out = dict(t)
        for k, v in m.items():
            if isinstance(v, list):
                seen = {json.dumps(e, sort_keys=True) for e in out.get(k, [])}
                out[k] = list(out.get(k, [])) + [e for e in v if json.dumps(e, sort_keys=True) not in seen]
            else:
                out.setdefault(k, v)
        return out
    if path in ("used.json", "carruseles.json"):
        seen, out = set(), []
        for e in (theirs or []) + (mine or []):
            k = json.dumps(e, sort_keys=True)
            if k not in seen:
                seen.add(k); out.append(e)
        return out
    if path == "handled_comments.json":
        t, m = theirs or {"comments": [], "dm": {}}, mine or {"comments": [], "dm": {}}
        dm = dict(t.get("dm", {}))
        for u, d in m.get("dm", {}).items():
            dm[u] = max(d, dm.get(u, ""))
        return {"comments": sorted(set(t.get("comments", [])) | set(m.get("comments", [])))[-5000:], "dm": dm}
    return mine                                    # informes, cuadernos, estrategia: gana la versión nueva


def write(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if path.endswith(".jsonl"):
        open(path, "w").write("\n".join(data) + ("\n" if data else ""))
    else:
        json.dump(data, open(path, "w"), ensure_ascii=False, indent=0)


def expand(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                out += [os.path.join(root, f) for f in files]
        elif os.path.exists(p):
            out.append(p)
    return out


def main(msg, paths):
    files = expand(paths)
    if not files:
        print("nada que guardar"); return
    tmp = tempfile.mkdtemp()
    for f in files:                                # copia de lo que ha producido este workflow
        os.makedirs(os.path.join(tmp, os.path.dirname(f)), exist_ok=True)
        shutil.copy2(f, os.path.join(tmp, f))
    sh("git", "config", "user.name", "reels-bot")
    sh("git", "config", "user.email", "reels-bot@users.noreply.github.com")
    branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    for attempt in range(5):
        sh("git", "fetch", "origin", branch)
        sh("git", "reset", "--hard", f"origin/{branch}")          # última versión del repositorio
        for f in files:
            mine_path = os.path.join(tmp, f)
            if f.endswith((".json", ".jsonl")):
                mine = load(mine_path, None)
                theirs = load(f, None) if os.path.exists(f) else None
                write(f, merge(f, mine, theirs))
            else:
                os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
                shutil.copy2(mine_path, f)
            sh("git", "add", f)
        if sh("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
            print("sin cambios que guardar"); return
        sh("git", "commit", "-m", msg)
        if sh("git", "push", "origin", f"HEAD:{branch}", check=False).returncode == 0:
            print(f"guardado: {len(files)} archivos"); return
        print(f"otro workflow guardó a la vez; fusiono y reintento ({attempt + 1}/5)", flush=True)
        time.sleep(5 + 5 * attempt)
    raise SystemExit("no se pudo guardar el estado tras 5 intentos")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
