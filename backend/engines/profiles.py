from typing import Dict, Any

def _f(row,k):
    try:return float(row.get(k) or 0)
    except:return 0.0

def qb_profile(rows):
    if not rows:return {'sample_games':0,'pass_attempts':0,'completion_rate':0,'yards_per_attempt':0,'td_rate':0,'int_rate':0,'pressure_proxy':0,'qb_environment':1.0}
    att=sum(_f(r,'attempts') or _f(r,'pass_attempts') for r in rows); comp=sum(_f(r,'completions') for r in rows); y=sum(_f(r,'passing_yards') for r in rows); td=sum(_f(r,'passing_tds') for r in rows); ints=sum(_f(r,'interceptions') for r in rows); sacks=sum(_f(r,'sacks') for r in rows)
    cr=comp/att if att else 0; ypa=y/att if att else 0; tdr=td/att if att else 0; intr=ints/att if att else 0; pressure=sacks/(att+sacks) if att+sacks else 0
    score=1.0 + max(-.12,min(.12,(cr-.65)*.4)) + max(-.10,min(.10,(ypa-7)*.03)) + max(-.08,min(.08,(tdr-.04)*1.2)) - max(0,min(.10,(intr-.02)*1.5)) - pressure*.15
    return {'sample_games':len(rows),'pass_attempts':att,'completion_rate':cr,'yards_per_attempt':ypa,'td_rate':tdr,'int_rate':intr,'pressure_proxy':pressure,'qb_environment':max(.78,min(1.22,score))}

def usage_profile(rows):
    if not rows:return {}
    totals={}
    for k in ['targets','receptions','receiving_yards','carries','rushing_yards','routes','snap_counts','air_yards','receiving_tds','rushing_tds']:
        totals[k]=sum(_f(r,k) for r in rows)
    games=len({r.get('game_id') for r in rows if r.get('game_id')}) or len(rows)
    totals['games']=games
    totals['per_game']={k:v/games for k,v in totals.items() if isinstance(v,(int,float)) and k!='games'}
    return totals
