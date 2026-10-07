class IdentityResolver:
    def __init__(self, nfl_players=None):
        self.rows=nfl_players or []
        self.by_gsis={str(r.get("gsis_id")):r for r in self.rows if r.get("gsis_id")}
        self.by_pfr={str(r.get("pfr_id")):r for r in self.rows if r.get("pfr_id")}
    def resolve(self,sleeper_player):
        for key,idx in [("gsis_id",self.by_gsis),("pfr_id",self.by_pfr)]:
            v=sleeper_player.get(key)
            if v and str(v) in idx:return idx[str(v)]
        return {}
