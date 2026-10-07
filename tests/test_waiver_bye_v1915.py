from backend.engine.waivers import recommend_waiver_moves, _lineup_changes

def p(name, pos, pts, bye=False):
    return {'player_id':name,'name':name,'position':pos,'team':'CAR' if bye else 'ARI','on_bye':bye,'projection':{'median_fantasy_points':pts}}

def test_young_bye_not_dropped_for_cousins():
    roster=[p('Brissett','QB',13),p('Young','QB',0,True),p('Walker','RB',10),p('Dicker','K',6)]
    out=recommend_waiver_moves(roster,[p('Cousins','QB',17)],['QB','RB','K'])
    assert all(m['drop']['name']!='Young' for m in out['moves'])

def test_non_bye_zero_can_be_replaced():
    roster=[p('Brissett','QB',13),p('Backup','QB',0),p('Walker','RB',10),p('Dicker','K',6)]
    out=recommend_waiver_moves(roster,[p('Cousins','QB',17)],['QB','RB','K'])
    assert out['moves'][0]['drop']['name']=='Backup'

def test_no_fake_slot_changes():
    before={'assignment':[{'slot_index':0,'slot':'RB','player_id':'a','name':'A'},{'slot_index':1,'slot':'FLEX','player_id':'b','name':'B'}]}
    after={'assignment':[{'slot_index':0,'slot':'RB','player_id':'b','name':'B'},{'slot_index':1,'slot':'FLEX','player_id':'a','name':'A'}]}
    assert _lineup_changes(before,after)==[]

def test_real_starter_change():
    before={'assignment':[{'slot_index':0,'slot':'QB','player_id':'a','name':'Brissett'}]}
    after={'assignment':[{'slot_index':0,'slot':'QB','player_id':'b','name':'Cousins'}]}
    assert _lineup_changes(before,after)==[{'slot':'QB','previous_starter':'Brissett','new_starter':'Cousins'}]
