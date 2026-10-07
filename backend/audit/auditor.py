from statistics import mean
class PredictionAuditor:
    def compare(self,predictions,actuals):
        rows=[]
        for p in predictions:
            a=actuals.get(str(p.get("player_id")))
            if not a: continue
            med=p.get("fantasy_points",{}).get("median")
            if med is None: continue
            err=med-a.get("fantasy_points",0)
            rows.append({"player_id":p["player_id"],"predicted":med,"actual":a.get("fantasy_points",0),"error":err,"absolute_error":abs(err)})
        return {"n":len(rows),"mae":round(mean(r["absolute_error"] for r in rows),3) if rows else None,"bias":round(mean(r["error"] for r in rows),3) if rows else None,"rows":rows}
