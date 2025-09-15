#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, csv, ast, math, random, sys, hashlib
from statistics import median, mean
from collections import defaultdict
from pathlib import Path
from config import GENRE_TO_MACROGENRE

# Path
TRACKS_PATH = Path("output/tracks_by_genre.json")
PERSONAS_PATH = Path("profiles/personas.json")
FEATURE_RANGES_CSV = Path("Feature_Ranges_Espansi.csv")
OUTPUT_PATH = Path("output/ranking_class.json")
FULL_VOTES_PATH = Path("output/individual_ratings.json")

# Parametri
TOPK_EXPORT = 50

# Segmenti e corridoi
SEGMENTS = [
    {"name":"warmup",   "len":1, "bpm_bias":-0.02, "dance_bias": 0.00, "target_bpm_shift":-6},
    {"name":"flat",     "len":2, "bpm_bias": 0.02, "dance_bias": 0.01, "target_bpm_shift":+2},
    {"name":"climb",    "len":2, "bpm_bias": 0.05, "dance_bias": 0.00, "target_bpm_shift":+6},
    {"name":"sprint",   "len":2, "bpm_bias": 0.12, "dance_bias": 0.03, "target_bpm_shift":+12},
    {"name":"cooldown", "len":1, "bpm_bias":-0.06, "dance_bias":-0.02, "target_bpm_shift":-10},
]
def bpm_corridor_mult_for(seg):  # ampiezza corridoio BPM per segmento
    return {"warmup":2.3,"flat":2.2,"climb":2.0,"sprint":1.9,"cooldown":2.3}.get(seg,2.2)

# AWM “a maggioranza” (paper)
AWM_TAU        = 0.35   # soglia minima di ammissibilità
AWM_QUORUM     = 0.60   # maggioranza qualificata
AWM_RELAX_STEP = 0.05   # rilassamento τ se non si copre la quota
AWM_MAX_RELAX  = 5

# Pesi feature per rating
WEIGHTS_BASE = {"genre": 0.22, "bpm": 0.40, "dance": 0.28, "valence": 0.10}
LAMBDA_DECAY = 0.22
def pos_weights(n=10, lam=LAMBDA_DECAY): return [math.exp(-lam*i) for i in range(n)]
POS_W = pos_weights()

# Anchor di coerenza + normalizzazione
ANCHOR_BPM      = 0.06
ANCHOR_DANCE    = 0.03
ANCHOR_VALENCE  = 0.015
MAX_THEORETICAL = 1.0 + ANCHOR_BPM + ANCHOR_DANCE + ANCHOR_VALENCE  # = 1.105

# Tolleranze
FALLBACK_TOL = {"bpm":18.0, "dance":0.18, "valence":0.18}
TOL_MULT     = {"bpm":1.35, "dance":1.25, "valence":1.2}
GEN_TOL      = {}

# Mappe qualitative (target)
RITMO_MAP  = {"lento":70, "moderato":105, "veloce":130}
BALLO_MAP  = {"scarso":0.2, "medio":0.5, "alto":0.8}
UMORE_MAP  = {"introspettivo":0.2, "equilibrato":0.5, "solare":0.8}

# IO / util
def jload(p: Path):
    return json.load(p.open("r", encoding="utf-8"))

def jsave(p: Path, obj):
    json.dump(obj, p.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)

def get_macros(g):
    v = GENRE_TO_MACROGENRE.get(g, [])
    return [v] if isinstance(v,str) else list(v)

def _pair_tuple(s):
    try:
        a,b = ast.literal_eval(str(s)); a,b = float(a),float(b)
        return (a,b) if a<=b else (b,a)
    except:
        return (None,None)

def load_genre_tolerances(csv_path: Path):
    global GEN_TOL
    GEN_TOL = defaultdict(lambda: FALLBACK_TOL.copy())
    if not csv_path.exists():
        print(f"⚠️  CSV non trovato: {csv_path}. Uso fallback.")
        return
    loaded = 0
    with csv_path.open(newline="",encoding="utf-8") as f:
        rdr = csv.DictReader(f, delimiter=",")
        for row in rdr:
            g = (row.get("Genere") or row.get("genere") or row.get("genre") or "").strip()
            if not g: continue
            if row.get("BPM") and row.get("Danceability") and row.get("Valence"):
                bpm_min,bpm_max = _pair_tuple(row.get("BPM"))
                d_min,d_max     = _pair_tuple(row.get("Danceability"))
                v_min,v_max     = _pair_tuple(row.get("Valence"))
            else:
                def pick(x):
                    try: return float(x) if x not in (None,"") else None
                    except: return None
                bpm_min,bpm_max = pick(row.get("bpm_min")), pick(row.get("bpm_max"))
                d_min,d_max     = pick(row.get("dance_min")), pick(row.get("dance_max"))
                v_min,v_max     = pick(row.get("valence_min")), pick(row.get("valence_max"))
            def tol(mn,mx,k): return None if (mn is None or mx is None or mx<mn) else k*(mx-mn)/2.0
            GEN_TOL[g] = {
                "bpm":   (tol(bpm_min,bpm_max,0.85) or FALLBACK_TOL["bpm"])   * TOL_MULT["bpm"],
                "dance": (tol(d_min,d_max,0.95)    or FALLBACK_TOL["dance"]) * TOL_MULT["dance"],
                "valence":(tol(v_min,v_max,0.90)   or FALLBACK_TOL["valence"])* TOL_MULT["valence"],
            }
            loaded += 1
    print(f"✅ Tolleranze caricate: {loaded} righe valide (delim=',')")

# micro-epsilon deterministico
def _hash_float(key: str, scale: float) -> float:
    h = hashlib.blake2b(key.encode('utf-8'), digest_size=8).digest()
    x = int.from_bytes(h,'big') / float(1<<64)  # [0,1)
    return (x*2.0 - 1.0) * scale

# Estrae il nome dalla nota '## BRANO PREFERITO DI <Nome>'.
def favorite_owner_from_note(note: str) -> str | None:
    if not isinstance(note, str): return None
    prefix = "## BRANO PREFERITO DI "
    if note.startswith(prefix):
        name = note[len(prefix):].strip()
        return name if name else None
    return None

# Similarità continue
def genre_similarity(track_genre, persona_genres, persona_name):
    # exact match
    for i, g in enumerate(persona_genres[:10]):
        if g == track_genre:
            sim = 0.88 + 0.10*math.exp(-0.42*i)
            sim += _hash_float(f"g|{track_genre}|{persona_name}|{i}", 0.004)
            return max(0.0, min(1.0, sim))
    # macro match
    tmac = set(get_macros(track_genre))
    best = 0.0
    for i, g in enumerate(persona_genres[:10]):
        if tmac & set(get_macros(g)):
            cand = 0.52 + 0.36*math.exp(-0.38*i)
            if cand > best: best = cand
    if best > 0.0:
        best += _hash_float(f"gm|{track_genre}|{persona_name}", 0.0035)
        return max(0.0, min(1.0, best))
    # nessuna affinità
    base = 0.28 + _hash_float(f"g0|{track_genre}|{persona_name}", 0.005)
    return max(0.0, min(1.0, base))

def fuzzy(value, target, tol):
    if value is None or target is None or tol is None:
        return 0.5
    d = abs(value - target) / max(1e-6, 1.6*tol)
    score = 0.30 + 0.65*math.exp(-(d*d))
    return max(0.0, min(1.0, score))

def impute_bpm_for_genre(genre, all_tracks):
    m=set(get_macros(genre)); s=n=0
    for tr in all_tracks:
        if set(get_macros(tr.get("genre",""))) & m:
            b=tr.get("bpm")
            if isinstance(b,(int,float)): s+=b; n+=1
    return (s/n) if n else 110.0

def segment_bias_weights(seg):
    w = WEIGHTS_BASE.copy()
    w["bpm"]   = max(0.0, min(0.60, w["bpm"]   + seg.get("bpm_bias",0.0)))
    w["dance"] = max(0.0, min(0.60, w["dance"] + seg.get("dance_bias",0.0)))
    s = sum(w.values())
    for k in w: w[k] /= s
    return w

def class_targets(personas):
    bpm_t = median([RITMO_MAP.get(p.get("ritmo_preferito"),105) for p in personas])
    d_t   = median([BALLO_MAP.get(p.get("ballabilità"),0.5) for p in personas])
    v_t   = median([UMORE_MAP.get(p.get("umore_musicale"),0.5) for p in personas])
    return bpm_t,d_t,v_t

#  Voto 0–1 per persona x brano, normalizzato e con micro-epsilon.
def component_score_for(persona, track, tol, seg_w, seg_targets):
    # Override per brano preferito
    fav_owner = favorite_owner_from_note(track.get("note"))
    if fav_owner and persona.get("nome") and persona["nome"].strip() == fav_owner:
        return 1.0

    g   = track.get("genre")
    bpm = track.get("bpm")
    if bpm is None: bpm = impute_bpm_for_genre(g, ALL_TRACKS)
    d   = track.get("danceability")
    v   = track.get("valence")

    gsc = genre_similarity(g, persona.get("generi_preferiti",[]), persona.get("nome","?")) if g else 0.5
    bsc = fuzzy(bpm, RITMO_MAP.get(persona.get("ritmo_preferito")), GEN_TOL.get(g,FALLBACK_TOL)["bpm"])
    dsc = fuzzy(d,   BALLO_MAP.get(persona.get("ballabilità")),     GEN_TOL.get(g,FALLBACK_TOL)["dance"]) if d is not None else 0.5
    vsc = fuzzy(v,   UMORE_MAP.get(persona.get("umore_musicale")),  GEN_TOL.get(g,FALLBACK_TOL)["valence"]) if v is not None else 0.5

    base = seg_w["genre"]*gsc + seg_w["bpm"]*bsc + seg_w["dance"]*dsc + seg_w["valence"]*vsc
    cbpm, cd, cv = seg_targets
    base += (ANCHOR_BPM    * fuzzy(bpm, cbpm, GEN_TOL.get(g,FALLBACK_TOL)["bpm"])
           + ANCHOR_DANCE  * fuzzy(d,   cd,   GEN_TOL.get(g,FALLBACK_TOL)["dance"])
           + ANCHOR_VALENCE* fuzzy(v,   cv,   GEN_TOL.get(g,FALLBACK_TOL)["valence"]))

    base += _hash_float(f"t|{track.get('id','?')}|{persona.get('nome','?')}", 0.004)
    norm = base / MAX_THEORETICAL
    return max(0.0, min(1.0, norm))

# AWM-majority
def awm_majority_pass(ratings, tau=AWM_TAU, quorum=AWM_QUORUM):
    if not ratings: return False
    ok = sum(1 for v in ratings if v >= tau)
    return (ok / len(ratings)) >= quorum

def awm_mean(ratings, tau=AWM_TAU):
    vals = [v for v in ratings if v >= tau]
    return (sum(vals)/len(vals)) if vals else 0.0

# Segment runner
def run_segment(seg, tracks, personas, cls_targets):
    base_bpm, base_d, base_v = cls_targets
    seg_targets = (base_bpm + seg.get("target_bpm_shift",0), base_d, base_v)
    seg_w = segment_bias_weights(seg)

    # Prefiltro strutturale: corridoio BPM del segmento (niente preferenze hard)
    kept=[]
    for t in tracks:
        g=t.get("genre")
        if not g: continue
        tol_bpm=GEN_TOL.get(g,FALLBACK_TOL)["bpm"]
        bpm=t.get("bpm") or impute_bpm_for_genre(g, tracks)
        if abs(bpm-seg_targets[0])>bpm_corridor_mult_for(seg["name"])*tol_bpm:
            continue
        kept.append(t)

    # Voti individuali (SOLO partecipanti)
    scores_by_track={}
    for t in kept:
        tid=t.get("id"); g=t.get("genre")
        ratings=[component_score_for(p,t,GEN_TOL.get(g,FALLBACK_TOL),seg_w,seg_targets) for p in personas]
        scores_by_track[tid]={"info":t,"ratings":ratings}

    # AWM-majority: filtro + ordinamento
    total_len=sum(s["len"] for s in SEGMENTS)
    quota=max(1, round(TOPK_EXPORT*seg["len"]/total_len))

    def eligible_ids(tau):
        ids=[]
        for tid, s in scores_by_track.items():
            if awm_majority_pass(s["ratings"], tau=tau, quorum=AWM_QUORUM):
                ids.append(tid)
        return ids

    tau=AWM_TAU; relax=0
    elig=eligible_ids(tau)
    while len(elig)<quota and relax<AWM_MAX_RELAX:
        relax+=1; tau=max(0.0, tau-AWM_RELAX_STEP)
        elig=eligible_ids(tau)

    # Ordinamento: AWM-mean + epsilon deterministico (tie-break)
    pool=[]
    for tid in elig:
        r=scores_by_track[tid]["ratings"]
        score = awm_mean(r, tau=tau) + _hash_float(f"awm|{tid}", 0.001)
        pool.append((tid, score, r))
    random.shuffle(pool)  # varietà minima
    pool.sort(key=lambda x: x[1], reverse=True)

    picked = pool[:quota]
    print(f"[{seg['name']}] quota={quota} inclusi={len(picked)} awm_tau_finale={tau:.2f} relax={relax}")

    ranked={tid:round(sc,6) for (tid,sc,_) in picked}

    # Dump leggibile
    for tid, sc, r in pool:
        s=scores_by_track[tid]
        s["group_score"]=round(sc,4)
        s["ratings"]=[round(v,4) for v in r]
        s["final_score"]=round(sc,4)  # AWM-mean
    return scores_by_track, ranked

# Pipeline
def run_full(ALL_TRACKS, personas):
    valid = set(GENRE_TO_MACROGENRE)
    tracks = [t for t in ALL_TRACKS if t.get("genre") in valid]
    load_genre_tolerances(FEATURE_RANGES_CSV)
    cls_t = class_targets(personas)

    seg_scores, seg_ranked = {}, {}
    for seg in SEGMENTS:
        s, r = run_segment(seg, tracks, personas, cls_t)
        seg_scores[seg["name"]]=s; seg_ranked[seg["name"]]=r

    # Quote per segmento → lista unica
    total_len = sum(s["len"] for s in SEGMENTS)
    final_items=[]
    for seg in SEGMENTS:
        q=max(1, round(TOPK_EXPORT*seg["len"]/total_len))
        final_items.extend(list(seg_ranked[seg["name"]].items())[:q])

    # Dedup sul migliore
    agg={}
    for tid,sc in final_items: agg[tid]=max(agg.get(tid,0.0), sc)

    # Medie sui selezionati (classe)
    final_ids={tid for tid,_ in final_items}
    all_ratings=[]
    for _, sd in seg_scores.items():
        for tid in final_ids:
            if tid in sd: all_ratings.extend(sd[tid]["ratings"])
    mean_global = (sum(all_ratings)/len(all_ratings)) if all_ratings else 0.0

    return agg, mean_global, seg_ranked, seg_scores

# Main
if __name__ == "__main__":
    seed = None
    if "--seed" in sys.argv:
        try:
            seed = int(sys.argv[sys.argv.index("--seed")+1])
        except Exception:
            seed = 42
    if seed is None:
        random.seed()
    else:
        random.seed(seed)
        print(f"🔁 Seed riproducibile: {seed}")

    ALL_TRACKS = jload(TRACKS_PATH)
    ALL_PERSONAS = jload(PERSONAS_PATH)
    if len(ALL_PERSONAS) < 10:
        raise SystemExit(" Servono almeno 10 persone in profiles/personas.json")

    # 10 partecipanti casuali (niente coach in questa modalità)
    personas = [dict(p, _is_instructor=False) for p in random.sample(ALL_PERSONAS, 10)]
    partecipanti = [p.get("nome", f"p{i}") for i,p in enumerate(personas)]
    print(f"\n🧑‍🤝‍🧑 Partecipanti (10): {', '.join(partecipanti)}")

    blended, mean_global, seg_ranked, seg_scores = run_full(ALL_TRACKS, personas)

    # Formatter semplice
    def format_list(agg, seg_scores):
        out=[]
        for tid,score in list(sorted(agg.items(), key=lambda x:x[1], reverse=True))[:TOPK_EXPORT]:
            info=None
            for sname, sdict in seg_scores.items():
                if tid in sdict: info=sdict[tid]["info"]; break
            if info:
                out.append({"title":info.get("title"),"artist":info.get("artist"),
                            "genre":info.get("genre"),"score":round(score,3)})
        return out

    total_len=sum(s["len"] for s in SEGMENTS)
    segments_out={}
    for seg in SEGMENTS:
        q=max(1, round(TOPK_EXPORT*seg["len"]/total_len))
        ranked=seg_ranked[seg["name"]]
        items=[]
        for tid, sc in list(ranked.items())[:q]:
            info=None
            for sname, sdict in seg_scores.items():
                if tid in sdict: info=sdict[tid]["info"]; break
            if info:
                items.append({"title":info.get("title"),"artist":info.get("artist"),
                              "genre":info.get("genre"),"score":round(sc,3)})
        segments_out[seg["name"]]=items

    results={
        "partecipanti": partecipanti,
        "Metodo": "AWM-majority (filtro+ranking) — puro articolo",
        "Segments": segments_out,
        "TopK_globale_AWM": format_list(blended, seg_scores),
        "Voto_medio_generale": round(mean_global,3),
        "Parametri": {
            "SEGMENTS": SEGMENTS,
            "AWM_TAU": AWM_TAU, "AWM_QUORUM": AWM_QUORUM,
            "AWM_RELAX_STEP": AWM_RELAX_STEP, "AWM_MAX_RELAX": AWM_MAX_RELAX,
            "WEIGHTS_BASE": WEIGHTS_BASE, "LAMBDA_DECAY": LAMBDA_DECAY,
            "ANCHORS": {
                "BPM": ANCHOR_BPM, "DANCE": ANCHOR_DANCE, "VALENCE": ANCHOR_VALENCE,
                "MAX_THEORETICAL": MAX_THEORETICAL
            }
        }
    }
    jsave(OUTPUT_PATH, results)

    votes = {"mode": "group-AWM-majority", "participants": partecipanti, "items": {}}
    for sname, sdict in seg_scores.items():
        for tid, s in sdict.items():
            info = s.get("info", {})
            note = info.get("note")
            fav_owner = favorite_owner_from_note(note)
            if fav_owner and fav_owner in partecipanti:
                key = f"{tid} ## BRANO PREFERITO DI {fav_owner}"
            else:
                key = tid

            votes["items"][key] = {
                "ratings": s.get("ratings", []),
                "group_score": s.get("group_score"),
                "final_score": s.get("final_score"),
            }
    jsave(FULL_VOTES_PATH, votes)

    # Log finale
    print("\n🎼 Playlist generata (AWM-majority — puro articolo).")
    print(f"   • Voto medio CLASSE (tutti): {results['Voto_medio_generale']}")
    print(f"✅ Salvato: {OUTPUT_PATH}")
    print(f"✅ Salvato: {FULL_VOTES_PATH}")
