from backend.engine.predictor import sleeper_starter_slot_map


def test_slot_alignment_is_by_matchup_starter_id_not_roster_order():
    slots = ['QB', 'RB', 'RB', 'WR', 'WR', 'TE', 'FLEX', 'FLEX', 'SUPER_FLEX', 'K', 'DEF', 'BN']
    starter_ids = ['goff', 'jeanty', 'williams', 'pickens', 'flowers', 'laporta', 'boston', 'nacua', 'brissett', 'mevis', 'BAL']
    # A roster might arrive in this completely different order; map must not depend on it.
    roster_ids = ['laporta', 'mevis', 'jeanty', 'boston', 'goff', 'brissett', 'pickens', 'williams', 'nacua', 'flowers', 'BAL']
    mapping = sleeper_starter_slot_map(starter_ids, slots)
    assert len(mapping) == 11
    assert mapping['laporta']['starting_slot'] == 'TE'
    assert mapping['mevis']['starting_slot'] == 'K'
    assert mapping['goff']['starting_slot'] == 'QB'
    assert mapping['brissett']['starting_slot'] == 'SUPER_FLEX'
    assert mapping['flowers']['starting_slot'] == 'WR'
    assert [mapping[p]['starting_slot'] for p in roster_ids][:2] == ['TE', 'K']


def test_empty_slots_do_not_shift_others():
    assert sleeper_starter_slot_map(['0','rb1','qb2'], ['QB','RB','SUPER_FLEX']) == {
        'rb1': {'starting_slot':'RB','starting_slot_index':1},
        'qb2': {'starting_slot':'SUPER_FLEX','starting_slot_index':2}}


def test_mismatched_counts_fail_closed():
    assert sleeper_starter_slot_map(['qb','rb'], ['QB','RB','WR']) == {}
    assert sleeper_starter_slot_map(['qb','qb'], ['QB','SUPER_FLEX']) == {}
