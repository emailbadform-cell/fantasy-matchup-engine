"""Regression coverage for combined bye-safe waivers and Sleeper multi-flex optimizer."""
from backend.engine.optimizer import optimize_lineup
from backend.engine.waivers import recommend_waiver_moves

SLOTS = ['QB','RB','WR','TE','FLEX','FLEX','SUPER_FLEX']

def p(name, pos, pts, bye=False):
    return {'player_id':name,'name':name,'position':pos,'on_bye':bye,'projection':{'median_fantasy_points':pts}}

def test_optimizer_all_three_flex_slots_and_best_total():
    players=[p('q1','QB',20),p('q2','QB',24),p('q3','QB',8),p('r1','RB',15),p('r2','RB',14),p('w1','WR',13),p('w2','WR',12),p('t1','TE',11),p('w3','WR',10)]
    o=optimize_lineup(players,SLOTS)
    assert o['filled_slots']==7
    assert len(o['assignment'])==7
    assert sum(a['slot']=='FLEX' for a in o['assignment'])==2
    assert sum(a['slot']=='SUPER_FLEX' for a in o['assignment'])==1
    assert all(a['position']!='QB' for a in o['assignment'] if a['slot']=='FLEX')
    assert {a['player_id'] for a in o['assignment']}=={'q1','q2','r1','r2','w1','w2','t1'}
    assert o['median_points']==109

def test_superflex_falls_back_to_non_qb_and_fills_both_flex():
    players=[p('q1','QB',20),p('r1','RB',15),p('r2','RB',14),p('w1','WR',13),p('w2','WR',12),p('t1','TE',11),p('w3','WR',10)]
    o=optimize_lineup(players,SLOTS)
    assert o['filled_slots']==7
    assert next(a for a in o['assignment'] if a['slot']=='SUPER_FLEX')['position']!='QB'

def test_bye_qb_not_dropped_for_weekly_streamer():
    roster=[p('starter','QB',14),p('bye_qb','QB',0,True),p('rb','RB',15),p('wr','WR',12),p('te','TE',10),p('rb2','RB',8),p('wr2','WR',7)]
    out=recommend_waiver_moves(roster,[p('pickup','QB',25)],SLOTS,max_moves=1)
    assert all(m['drop']['player_id']!='bye_qb' for m in out['moves'])
    assert out['lineup_slot_audit']['standard_flex']==2
    assert out['lineup_slot_audit']['superflex']==1

def test_waiver_gain_recomputed_across_three_flex_slots():
    roster=[p('q1','QB',20),p('q2','QB',19),p('r1','RB',18),p('w1','WR',17),p('t1','TE',16),p('r2','RB',15),p('w2','WR',14),p('bench','WR',1)]
    baseline=optimize_lineup(roster,SLOTS)['median_points']
    out=recommend_waiver_moves(roster,[p('upgrade','WR',23)],SLOTS,max_moves=1)
    assert len(out['moves'])==1
    m=out['moves'][0]
    assert m['team_points_gain']>0
    final=[x for x in roster if x['player_id']!=m['drop']['player_id']]+[p('upgrade','WR',23)]
    expected=optimize_lineup(final,SLOTS)['median_points']
    assert abs(out['final_optimal_team_points']-expected)<0.011
    assert abs(out['final_optimal_team_points']-baseline-m['team_points_gain'])<0.011
