from backend.engine.features import *

def test_safe_div_and_clamp():
    assert safe_div(10,2)==5
    assert safe_div(10,0)==0
    assert clamp(2,0,1)==1

def test_game_script():
    g={"home_team":"KC","away_team":"LV","total_line":"47.5","spread_line":"-4.5"}
    x=game_script(g,"LV")
    assert x["pass_factor"]>1
    assert x["rush_factor"]<1

def test_qb_correlation():
    x=qb_correlation(1.1,"WR")
    assert x["rho"]==0.35
    assert x["qb_effect"]>1

def test_simulation():
    x=simulate(15,3,n=500)
    assert x["p10"]<=x["p50"]<=x["p90"]

def test_all_layers_return_values():
    g={"home_team":"KC","away_team":"LV","total_line":"47.5","spread_line":"-4.5","wind":"8","roof":"dome","surface":"grass"}
    assert availability({})["availability"]==1
    assert replacement_factor(["1","2"],"1")==1
    assert offensive_line_factor([])>0
    assert defensive_front_factor([])>0
    assert trench_matchup(1,1)==1
    assert play_volume([],g,"LV")>0
    assert weather(g)["pass_factor"]>0
    assert surface(g)["indoor"]
    assert referee(g)["data_status"]=="unavailable"
    assert coaching(g,"LV")["coach"] is None
    assert red_zone([])["td_rate_proxy"]>0
    assert explosive([])["explosive_rate"]==0
    assert cutoff(2026,4)["historical_weeks_lt"]==3
