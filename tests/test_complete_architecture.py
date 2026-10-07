from backend.engines.complete_architecture import CompleteArchitecture

def test_all_24_layers(): assert len(CompleteArchitecture.LAYERS)==24

def test_build_has_24_layer_records():
 a=CompleteArchitecture(); o=a.build({'player_id':'x','position':'WR','team':'DET'},{'targets':8,'receptions':5,'receiving_yards':70},{'team_scoring_impact':1,'pass_volume':1},{'plays':65,'pass_rate':.6},{'coverage':1},1,{'season':2026,'week':4,'total_line':48,'spread_line':-3}, {'coverage':1})
 assert o['layer_count']==24 and len(o['layers'])==24 and o['versioning']['model_version']=='1.2.0'
