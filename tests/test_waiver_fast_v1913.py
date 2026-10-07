from backend.engine.waivers import recommend_waiver_moves

def p(pid,name,pos,pts):
    return {'player_id':pid,'name':name,'position':pos,'eligible_positions':[pos],'team':'X','projection':{'median_fantasy_points':pts}}

def test_considers_every_candidate_once_per_round_not_cartesian_pairs():
    roster=[p('q','QB','QB',10),p('r','RB','RB',10),p('w','WR','WR',10),p('b1','B1','RB',2),p('b2','B2','WR',3)]
    avail=[p('a1','A1','RB',11),p('a2','A2','WR',12),p('a3','A3','QB',9)]
    seen=[]
    out=recommend_waiver_moves(roster,avail,['QB','RB','WR'],max_moves=1,progress=lambda d,t,m: seen.append((d,t,m)))
    assert out['move_count']==1
    assert out['moves'][0]['pickup']['name']=='A2'
    assert out['moves'][0]['drop']['name']=='B2'
    assert out['lineup_optimizations']==3
    assert seen[-1][1]==3

def test_fast_result_matches_expected_multiple_moves():
    roster=[p('q1','QB1','QB',15),p('r1','RB1','RB',8),p('w1','WR1','WR',7),p('b','Bench','WR',1)]
    avail=[p('r2','RB2','RB',14),p('w2','WR2','WR',13)]
    out=recommend_waiver_moves(roster,avail,['QB','RB','WR'])
    assert {m['pickup']['name'] for m in out['moves']}=={'RB2','WR2'}
    assert all(m['team_points_gain']>0 for m in out['moves'])

def test_no_upgrade_returns_no_move():
    roster=[p('q','QB','QB',15),p('r','RB','RB',12),p('b','Bench','RB',8)]
    out=recommend_waiver_moves(roster,[p('x','X','RB',7)],['QB','RB'])
    assert out['move_count']==0
