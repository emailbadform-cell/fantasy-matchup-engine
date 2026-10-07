from backend.engine.waivers import recommend_waiver_moves


def p(pid,name,pos,pts,elig=None):
    return {'player_id':pid,'name':name,'position':pos,'eligible_positions':elig or [pos],'team':'X','projection':{'median_fantasy_points':pts,'low':max(0,pts-3),'high':pts+3}}


def test_recommends_multiple_sequential_positive_moves():
    roster=[p('q1','QB1','QB',15),p('r1','RB1','RB',8),p('w1','WR1','WR',7)]
    avail=[p('r2','RB2','RB',14),p('w2','WR2','WR',13),p('q2','QB2','QB',14)]
    out=recommend_waiver_moves(roster,avail,['QB','RB','WR'])
    assert out['move_count']==2
    assert [m['pickup']['name'] for m in out['moves']]==['WR2','RB2'] or set(m['pickup']['name'] for m in out['moves'])=={'WR2','RB2'}
    assert all(m['team_points_gain']>0 for m in out['moves'])


def test_does_not_recommend_non_improving_move():
    roster=[p('q1','QB1','QB',15),p('r1','RB1','RB',12)]
    avail=[p('r2','RB2','RB',10)]
    out=recommend_waiver_moves(roster,avail,['QB','RB'])
    assert out['move_count']==0


def test_swap_can_drop_different_position_when_lineup_stays_legal():
    roster=[p('q1','QB1','QB',15),p('r1','RB1','RB',5),p('w1','WR1','WR',6),p('b1','BenchRB','RB',4)]
    avail=[p('w2','WaiverWR','WR',12)]
    out=recommend_waiver_moves(roster,avail,['QB','RB','WR'])
    assert out['move_count']==1
    assert out['moves'][0]['pickup']['name']=='WaiverWR'
