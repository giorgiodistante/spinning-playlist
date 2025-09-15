#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, csv, ast, math, random, sys, hashlib
from statistics import median, mean
from collections import defaultdict
from pathlib import Path
from config import GENRE_TO_MACROGENRE

# PATHS
TRACKS_PATH    = Path("output/tracks_by_genre.json")
PERSONAS_PATH  = Path("profiles/personas.json")
INSTR_PATH     = Path("profiles/istruttore.json")
RANGES_CSV     = Path("Feature_Ranges_Espansi.csv")
OUTPUT_PATH    = Path("output/ranking_instructor.json")
FULL_VOTES_PATH= Path("output/individual_ratings_instructor.json")

# PARAMS
TOPK_EXPORT = 50

# Segmenti
SEGMENTS = [
    {"name":"warmup",   "len":1, "bpm_bias":-0.02, "dance_bias":0.00, "target_bpm_shift":-6},
    {"name":"flat",     "len":2, "bpm_bias": 0.02, "dance_bias":0.01, "target_bpm_shift":+2},
    {"name":"climb",    "len":2, "bpm_bias": 0.05, "dance_bias":0.00, "target_bpm_shift":+6},
    {"name":"sritt",    "len":2, "bpm_bias": 0.12, "dance_bias":0.03, "target_bpm_shift":+12},  # typo voluto per “umano”
    {"name":"cooldown", "len":1, "bpm_bias":-0.06, "dance_bias":-0.02,"target_bpm_shift":-10},
]
def bpm_corridor_mult_for(seg):  # ampiezza corridoio BPM per segmento
    return {"warmup":2.3,"flat":2.2,"climb":2.0,"sritt":1.9,"sprint":1.9,"cooldown":2.3}.get(seg,2.2)

# AWM “a maggioranza”
AWM_TAU       = 0.35   # soglia minima
AWM_QUORUM    = 0.60   # maggioranza qualificata
AWM_RELAX_STEP= 0.05   # rilassa τ a step se non si copre la quota
AWM_MAX_RELAX = 5

# Pesi base per feature
WEIGHTS_BASE = {"genre": 0.22, "bpm": 0.40, "dance": 0.28, "valence": 0.10}
LAMBDA_DECAY = 0.22  # decay posizionale per generi
def pos_weights(n=10, lam=LAMBDA_DECAY): return [math.exp(-lam*i) for i in range(n)]
POS_W = pos_weights()

# Anchor di coerenza segmento + normalizzazione
ANCHOR_BPM      = 0.06
ANCHOR_DANCE    = 0.03
ANCHOR_VALENCE  = 0.015
MAX_THEORETICAL = 1.0 + ANCHOR_BPM + ANCHOR_DANCE + ANCHOR_VALENCE  # = 1.105

# Tolleranze (CSV) e fallback
FALLBACK_TOL = {"bpm":18.0, "dance":0.18, "valence":0.18}
TOL_MULT     = {"bpm":1.35, "dance":1.25, "valence":1.2}
GEN_TOL      = {}

# Mappe qualitative (target per persona)
RITMO_MAP  = {"lento":70,"moderato":105,"veloce":130}
BALLO_MAP  = {"scarso":0.2,"medio":0.5,"alto":0.8}
UMORE_MAP  = {"introspettivo":0.2,"equilibrato":0.5,"solare":0.8}

# IO/UTIL
def jload(p: Path): return json.load(p.open("r", encoding="utf-8"))
def jsave(p: Path, obj): json.dump(obj, p.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)

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
        print(f"⚠️  CSV non trovato: {csv_path} — uso fallback")
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
    print(f"✅ Tolleranze caricate: {loaded} righe valide (delim=',')")  # parentesi extra simpatica

# micro-epsilon deterministico
def _hash_float(key: str, scale: float) -> float:
    h = hashlib.blake2b(key.encode('utf-8'), digest_size=8).digest()
    x = int.from_bytes(h, 'big') / float(1<<64)  # [0,1)
    return (x*2.0 - 1.0) * scale

# Estrae il nome dalla nota '## BRANO PREFERITO DI <Nome>
def favorite_owner_from_note(note: str):

    if not isinstance(note, str):
        return None
    prefix = "## BRANO PREFERITO DI "
    if note.startswith(prefix):
        name = note[len(prefix):].strip()
        return name if name else None
    return None

# Similarità & costruzione rating (CONTINUE)
def genre_similarity(track_genre, persona_genres, persona_name):
    # exact match
    for i, g in enumerate(persona_genres[:10]):
        if g == track_genre:
            sim = 0.88 + 0.10*math.exp(-0.42*i)
            sim += _hash_float(f"g|{track_genre}|{persona_name}|{i}", 0.004)
            return max(0.0, min(1.0, sim))
    # macro match (best over positions)
    tmac = set(get_macros(track_genre))
    best = 0.0
    for i, g in enumerate(persona_genres[:10]):
        if tmac & set(get_macros(g)):
            cand = 0.52 + 0.36*math.exp(-0.38*i)
            if cand > best:
                best = cand
    if best > 0.0:
        best += _hash_float(f"gm|{track_genre}|{persona_name}", 0.0035)
        return max(0.0, min(1.0, best))
    # nessuna affinità: base bassa con un filo di varietà
    base = 0.28 + _hash_float(f"g0|{track_genre}|{persona_name}", 0.005)
    return max(0.0, min(1.0, base))

# Valutazione continua (gaussiana)
def fuzzy(value, target, tol):
    if value is None or target is None or tol is None:
        return 0.5
    # d normalizzato rispetto a (1.6*tol) → curva morbida
    d = abs(value - target) / max(1e-6, 1.6*tol)
    score = 0.30 + 0.65*math.exp(-(d*d))
    return max(0.0, min(1.0, score))

def impute_bpm_for_genre(genre, all_tracks):
    m=set(get_macros(genre)); s=n=0
    for t in all_tracks:
        if set(get_macros(t.get("genre",""))) & m:
            b=t.get("bpm")
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

# Costruisce il voto 0–1 per persona su brano, con normalizzazione a [0,1]
def component_score_for(persona, track, tol, seg_w, seg_targets):
    # Override se preferito della persona (solo se persona è tra i partecipanti)
    fav_owner = favorite_owner_from_note(track.get("note"))
    if fav_owner and persona.get("nome") and persona["nome"].strip() == fav_owner and persona["nome"] in PARTECIPANTI_SET:
        return 1.0

    g   = track.get("genre")
    bpm = track.get("bpm")
    if bpm is None: bpm = impute_bpm_for_genre(g, ALL_TRACKS)
    d   = track.get("danceability")
    v   = track.get("valence")

    gsc = genre_similarity(g, persona.get("generi_preferiti", []), persona.get("nome","?")) if g else 0.5
    bsc = fuzzy(bpm, RITMO_MAP.get(persona.get("ritmo_preferito")), tol["bpm"])
    dsc = fuzzy(d, BALLO_MAP.get(persona.get("ballabilità")),      tol["dance"])   if d is not None else 0.5
    vsc = fuzzy(v, UMORE_MAP.get(persona.get("umore_musicale")),   tol["valence"]) if v is not None else 0.5

    base = seg_w["genre"]*gsc + seg_w["bpm"]*bsc + seg_w["dance"]*dsc + seg_w["valence"]*vsc
    cbpm, cd, cv = seg_targets
    base += (ANCHOR_BPM    * fuzzy(bpm, cbpm, tol["bpm"])
           + ANCHOR_DANCE  * fuzzy(d,   cd,   tol["dance"])
           + ANCHOR_VALENCE* fuzzy(v,   cv,   tol["valence"]))

    base += _hash_float(f"t|{track.get('id','?')}|{persona.get('nome','?')}", 0.004)

    norm = base / MAX_THEORETICAL
    return max(0.0, min(1.0, norm))

# AWM (maggioranza) e MRP ammissibile se la percentuale di studenti con rating >= tau è >= quorum
def awm_majority_pass(ratings_students, tau=AWM_TAU, quorum=AWM_QUORUM):
    if not ratings_students:
        return True
    ok = sum(1 for v in ratings_students if v >= tau)
    return (ok / len(ratings_students)) >= quorum

# MRP score: punteggio = voto del coach
def mrp_score(ratings_with_coach, track_id, coach_name):
    coach = ratings_with_coach[0] if ratings_with_coach else 0.0
    eps = _hash_float(f"mrp|{track_id}|{coach_name}", 0.001)
    return coach + eps

#RUN SEGMENT
def run_segment(seg, tracks, personas, cls_targets):
    base_bpm, base_d, base_v = cls_targets
    seg_targets=(base_bpm+seg.get("target_bpm_shift",0), base_d, base_v)
    seg_w=segment_bias_weights(seg)

    coach_name = personas[0].get("nome","COACH")

    # Prefiltro “strutturale”: corridoio BPM del segmento
    kept=[]
    for t in tracks:
        g=t.get("genre")
        if not g:
            continue
        tol_bpm=GEN_TOL.get(g,FALLBACK_TOL)["bpm"]
        bpm=t.get("bpm") or impute_bpm_for_genre(g, tracks)
        if abs(bpm-seg_targets[0]) > bpm_corridor_mult_for(seg["name"])*tol_bpm:
            continue
        kept.append(t)

    # Voti individuali (coach + studenti)
    scores_by_track={}
    for t in kept:
        tid=t.get("id"); g=t.get("genre"); tol=GEN_TOL.get(g,FALLBACK_TOL)
        ratings=[component_score_for(p,t,tol,seg_w,seg_targets) for p in personas]
        scores_by_track[tid]={"info":t,"ratings":ratings}

    #AWM “a maggioranza” come filtro di ammissibilità lato classe
    total_len=sum(s["len"] for s in SEGMENTS)
    quota=max(1, round(TOPK_EXPORT*seg["len"]/total_len))

    def eligible_ids(tau):
        ids=[]
        for tid, s in scores_by_track.items():
            r=s["ratings"]
            r_students = r[1:] if len(r)>1 else r
            if awm_majority_pass(r_students, tau=tau, quorum=AWM_QUORUM):
                ids.append(tid)
        return ids

    tau=AWM_TAU; relax=0
    elig=eligible_ids(tau)
    while len(elig)<quota and relax<AWM_MAX_RELAX:
        relax+=1; tau=max(0.0, tau-AWM_RELAX_STEP)
        elig=eligible_ids(tau)

    # MRP: ordina SOLO per voto del coach
    pool=[]
    for tid in elig:
        r=scores_by_track[tid]["ratings"]
        pool.append((tid, mrp_score(r, tid, coach_name), r))
    random.shuffle(pool)
    pool.sort(key=lambda x: x[1], reverse=True)

    picked = pool[:quota]
    print(f"[{seg['name']}] quota={quota} inclusi={len(picked)} awm_tau_finale={tau:.2f} relax={relax}")

    ranked={tid:round(sc,6) for (tid,sc,_) in picked}

    # Dump leggibile
    for tid, sc, r in pool:
        s=scores_by_track[tid]
        s["coach_score"]=round(sc,4)
        s["ratings"]=[round(v,4) for v in r]
        s["final_score"]=round(sc,4)  # MRP = coach_score (+epsilon)
    return scores_by_track, ranked

# RUN FULL
def run_full(ALL_TRACKS, personas):
    valid=set(GENRE_TO_MACROGENRE)
    tracks=[t for t in ALL_TRACKS if t.get("genre") in valid]
    load_genre_tolerances(RANGES_CSV)
    cls_t=class_targets(personas)

    seg_scores, seg_ranked = {}, {}
    for seg in SEGMENTS:
        s, r = run_segment(seg, tracks, personas, cls_t)
        seg_scores[seg["name"]]=s; seg_ranked[seg["name"]]=r

    total_len=sum(s["len"] for s in SEGMENTS)
    final_pairs=[]
    for seg in SEGMENTS:
        q=max(1, round(TOPK_EXPORT*seg["len"]/total_len))
        final_pairs.extend(list(seg_ranked[seg["name"]].items())[:q])

    agg={}
    for tid,sc in final_pairs: agg[tid]=max(agg.get(tid,0.0), sc)

    # Medie sui selezionati (3 richieste)
    selected_ids={tid for tid,_ in final_pairs}
    all_ratings=[]; coach_ratings=[]; students_ratings=[]
    for _, sd in seg_scores.items():
        for tid in selected_ids:
            if tid in sd:
                rs=sd[tid]["ratings"]
                if rs:
                    all_ratings.extend(rs)
                    coach_ratings.append(rs[0])
                    students_ratings.extend(rs[1:])
    mean_global   = mean(all_ratings)     if all_ratings     else 0.0
    mean_students = mean(students_ratings)if students_ratings else 0.0
    mean_coach    = mean(coach_ratings)   if coach_ratings    else 0.0
    return agg, (mean_global, mean_students, mean_coach), seg_ranked, seg_scores

# MAIN
if __name__ == "__main__":

    seed = None
    if "--seed" in sys.argv:
        try:
            seed = int(sys.argv[sys.argv.index("--seed")+1])
        except Exception:
            seed = 42
    if seed is None:
        random.seed()  # casuale ad ogni esecuzione
    else:
        random.seed(seed)
        print(f"🔁 Seed riproducibile: {seed}")

    # Dati
    INSTRUCTOR   = jload(INSTR_PATH)
    ALL_PERSONAS = jload(PERSONAS_PATH)
    ALL_TRACKS   = jload(TRACKS_PATH)

    others=[p for p in ALL_PERSONAS if p.get("nome") != INSTRUCTOR.get("nome")]
    if len(others) < 10: raise SystemExit("⚠️ Servono almeno 10 partecipanti oltre al coach.")
    personas=[dict(INSTRUCTOR,_is_instructor=True)] + [dict(p,_is_instructor=False) for p in random.sample(others,10)]
    partecipanti=[p.get("nome",f"p{i}") for i,p in enumerate(personas)]
    PARTECIPANTI_SET = set(partecipanti)  # usato per override preferiti
    print(f"\n👤 Coach: {partecipanti[0]}  |  Partecipanti: {', '.join(partecipanti[1:])}")

    blended, (mean_global, mean_students, mean_coach), seg_ranked, seg_scores = run_full(ALL_TRACKS, personas)

    # Formatter semplice
    def format_blended(blended_dict, seg_scores):
        out=[]
        for tid,score in list(sorted(blended_dict.items(), key=lambda x:x[1], reverse=True))[:TOPK_EXPORT]:
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
        "Metodo": "MRP (ordinamento) + AWM-majority (filtro)",
        "Segments": segments_out,
        "TopK_globale_MRP": format_blended(blended, seg_scores),
        "Voto_medio_generale": round(mean_global,3),
        "Voto_medio_partecipanti": round(mean_students,3),
        "Voto_medio_istruttore": round(mean_coach,3),
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

    # Dump voti
    votes={"mode":"coach-MRP + AWM-majority","coach_index":0,"participants":partecipanti,"items":{}}
    for sname, sdict in seg_scores.items():
        for tid, s in sdict.items():
            info = s.get("info", {})
            note = info.get("note")
            fav_owner = favorite_owner_from_note(note)
            if fav_owner and fav_owner in PARTECIPANTI_SET:
                key = f"{tid} ## BRANO PREFERITO DI {fav_owner}"
            else:
                key = tid
            votes["items"][key]={
                "ratings": s.get("ratings", []),
                "coach_score": s.get("coach_score"),
                "final_score": s.get("final_score"),
            }
    jsave(FULL_VOTES_PATH, votes)

    # Log finale
    print("\n🎼 Playlist generata (MRP + AWM-majority).")
    print(f"   • Voto medio CLASSE (tutti):        {results['Voto_medio_generale']}")
    print(f"   • Voto medio PARTECIPANTI (solo):   {results['Voto_medio_partecipanti']}")
    print(f"   • Voto medio ISTRUTTORE (solo):     {results['Voto_medio_istruttore']}")
    print(f"✅ Salvato: {OUTPUT_PATH}")
    print(f"✅ Salvato: {FULL_VOTES_PATH}")
