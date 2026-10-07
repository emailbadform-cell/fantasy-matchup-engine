from backend.engine.waivers import recommend_waiver_moves

def p(i,pos,points):
    return {'player_id':i,'name':i,'position':pos,'team':'X','projection':{'median_fantasy_points':points}}

def test_reject_third_qb_for_rb():
    r=[p('Brissett','QB',12),p('Young','QB',0),p('Walker','RB',0),p('RB2','RB',10),p('Dicker','K',7)]
    out=recommend_waiver_moves(r,[p('Cousins','QB',18)],['QB','RB','K'])
    assert not any(m['drop']['name']=='Walker' for m in out['moves'])

def test_reject_second_kicker_for_qb():
    r=[p('Brissett','QB',12),p('Young','QB',0),p('Walker','RB',10),p('Dicker','K',7)]
    out=recommend_waiver_moves(r,[p('McLaughlin','K',9)],['QB','RB','K'])
    assert not any(m['drop']['name']=='Young' for m in out['moves'])

def test_lineup_changes_are_explained():
    r=[p('QB','QB',12),p('RB','RB',10),p('bench','RB',1)]
    out=recommend_waiver_moves(r,[p('upgrade','RB',15)],['QB','RB'])
    assert out['moves'][0]['lineup_changes'][0]['new_starter']=='upgrade'
    assert out['moves'][0]['rest_of_season_assessed'] is False
