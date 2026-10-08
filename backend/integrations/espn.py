import os
import re
import csv
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import unquote
import httpx
from .sleeper import SleeperClient

BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{league_id}"

class ESPNAPIError(RuntimeError):
    pass

# ESPN proTeamId -> canonical NFL abbreviation
PRO_TEAMS = {1:"ATL",2:"BUF",3:"CHI",4:"CIN",5:"CLE",6:"DAL",7:"DEN",8:"DET",9:"GB",10:"TEN",11:"IND",12:"KC",13:"LV",14:"LA",15:"MIA",16:"MIN",17:"NE",18:"NO",19:"NYG",20:"NYJ",21:"PHI",22:"ARI",23:"PIT",24:"LAC",25:"SF",26:"SEA",27:"TB",28:"WAS",29:"CAR",30:"JAC",33:"BAL",34:"HOU"}
POS = {1:"QB",2:"RB",3:"WR",4:"TE",5:"K",16:"DEF"}
# ESPN uses -16000 - proTeamId for team defenses (e.g. Rams = -16014).
# Sleeper commonly uses LAR while ESPN's proTeamId 14 is LA.
DEF_TEAM_ALIASES = {"LA": "LAR", "LAR": "LAR", "JAC": "JAX", "JAX": "JAX", "WSH": "WAS", "WAS": "WAS"}

def canonical_def_team(team):
    value = str(team or "").upper()
    return DEF_TEAM_ALIASES.get(value, value)

def espn_defense_team(player_id, pro_team_id=None, name=None):
    """Resolve an ESPN D/ST from its negative ID even if player metadata is absent."""
    try:
        number = int(player_id)
        if -16034 <= number <= -16001:
            team = PRO_TEAMS.get(-16000 - number)
            if team:
                return canonical_def_team(team)
    except (ValueError, TypeError):
        pass
    try:
        team = PRO_TEAMS.get(int(pro_team_id))
        if team:
            return canonical_def_team(team)
    except (ValueError, TypeError):
        pass
    # Never fuzzy-match a defense to the wrong NFL team.
    return None

LINEUP_SLOT = {0:"QB",1:"QB",2:"RB",3:"RB_WR",4:"WR",5:"WR_TE",6:"TE",7:"SUPER_FLEX",16:"DEF",17:"K",23:"FLEX"}

# Common ESPN FFL stat IDs. Unknown/custom scoring items are preserved in raw settings.
SCORING_IDS = {3:"pass_yd",4:"pass_td",20:"pass_int",24:"rush_yd",25:"rush_td",42:"rec_yd",43:"rec_td",53:"rec",72:"fum_lost"}

class ESPNClient:
    def __init__(self, season=2026, timeout=30, espn_s2=None, swid=None):
        self.season=int(season); self.timeout=timeout
        self.espn_s2=espn_s2 if espn_s2 is not None else os.getenv("ESPN_S2")
        self.swid=swid if swid is not None else os.getenv("ESPN_SWID") or os.getenv("SWID")
        self._cache={}
        self._sleeper=SleeperClient(timeout=timeout)

    def _get(self, league_id, views=(), week=None):
        key=(str(league_id),tuple(views),week,self.season)
        if key in self._cache:return self._cache[key]
        params=[]
        for view in views: params.append(("view",view))
        if week is not None: params.append(("scoringPeriodId",str(week)))
        cookies={}
        # Browser cookie exports may be percent-encoded. ESPN expects the cookie value,
        # not the literal export encoding. Decode once here so either form works.
        if self.espn_s2: cookies["espn_s2"] = unquote(self.espn_s2)
        if self.swid: cookies["SWID"] = self.swid
        url=BASE.format(season=self.season,league_id=league_id)
        try:
            r=httpx.get(url,params=params,cookies=cookies,headers={"Accept":"application/json","User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0.0.0 Safari/537.36"},timeout=self.timeout)
            if r.status_code in (401,403):
                if not (self.espn_s2 and self.swid):
                    raise ESPNAPIError("ESPN authentication required. Set ESPN_S2 and ESPN_SWID environment variables, then restart FME.")
                raise ESPNAPIError(f"ESPN rejected the authenticated league request (HTTP {r.status_code}). Credentials are loaded; this can also be caused by ESPN request filtering, league access, or an expired session.")
            r.raise_for_status(); data=r.json()
        except ESPNAPIError: raise
        except Exception as exc: raise ESPNAPIError(f"ESPN request failed for league {league_id}: {exc}") from exc
        self._cache[key]=data; return data

    def available_player_ids(self, league_id, week=None, limit=250):
        """Return ESPN player IDs currently marked FREEAGENT or WAIVERS by this league."""
        params=[("view","kona_player_info")]
        if week is not None: params.append(("scoringPeriodId",str(week)))
        cookies={}
        if self.espn_s2: cookies["espn_s2"]=unquote(self.espn_s2)
        if self.swid: cookies["SWID"]=self.swid
        filt={"players":{"filterStatus":{"value":["FREEAGENT","WAIVERS"]},"limit":int(limit),"sortPercOwned":{"sortPriority":1,"sortAsc":False}}}
        import json
        headers={"Accept":"application/json","User-Agent":"Mozilla/5.0","x-fantasy-filter":json.dumps(filt,separators=(",",":"))}
        url=BASE.format(season=self.season,league_id=league_id)
        try:
            r=httpx.get(url,params=params,cookies=cookies,headers=headers,timeout=self.timeout)
            r.raise_for_status(); data=r.json()
        except Exception as exc: raise ESPNAPIError(f"ESPN waiver request failed for league {league_id}: {exc}") from exc
        out=[]
        for x in data.get("players",[]) or []:
            pe=x.get("player") or (x.get("playerPoolEntry") or {}).get("player") or {}
            pid=x.get("id") or x.get("playerId") or pe.get("id")
            if pid is not None: out.append(str(pid))
        return out

    def league(self, league_id, week=None):
        return self._get(league_id,("mTeam","mRoster","mSettings","mMatchup","mMatchupScore"),week)

    def teams(self, league_id, week=None): return self.league(league_id,week).get("teams",[])

    def scoring_settings(self, league_id):
        data=self._get(league_id,("mSettings",))
        raw=((data.get("settings") or {}).get("scoringSettings") or {}).get("scoringItems") or []
        out={}
        for item in raw:
            key=SCORING_IDS.get(item.get("statId"))
            if key and item.get("points") is not None: out[key]=item.get("points")
        return out

    def lineup_settings(self, league_id):
        data=self._get(league_id,("mSettings",))
        counts=(((data.get("settings") or {}).get("rosterSettings") or {}).get("lineupSlotCounts") or {})
        # ESPN FFL: 20=bench, 21=IR. Every other configured slot is an active starter slot.
        active={str(k):int(v or 0) for k,v in counts.items() if int(k) not in (20,21) and int(v or 0)>0}
        slots=[]
        for slot_id,count in active.items():
            slots.extend([LINEUP_SLOT.get(int(slot_id), f"SLOT_{slot_id}")] * int(count))
        return {"active_slot_counts":active,"starter_slots":slots,"expected_starters":sum(active.values())}

    @staticmethod
    def _name(s): return re.sub(r"[^a-z0-9]","",str(s or "").lower())

    @classmethod
    def _name_variants(cls, s):
        raw=str(s or "").strip().lower()
        # Provider-neutral identity normalization: punctuation/spacing plus common
        # generational suffixes. Keep both forms so exact suffix matches still win.
        variants={cls._name(raw)}
        base=re.sub(r"(?:,?\s+)(jr\.?|sr\.?|ii|iii|iv|v)$", "", raw, flags=re.I).strip()
        if base:
            variants.add(cls._name(base))
        return {x for x in variants if x}

    def _nflverse_identity_index(self):
        # players.csv is the nflverse ID crosswalk and includes ESPN + GSIS IDs.
        # Use the local cache first so identity resolution does not depend on a
        # second live API call during an ESPN lineup request.
        path=Path(__file__).resolve().parents[2] / "data_cache" / "players.csv"
        by_espn={}
        if not path.exists(): return by_espn
        try:
            with path.open("r",encoding="utf-8-sig",newline="") as f:
                for r in csv.DictReader(f):
                    eid=str(r.get("espn_id") or "").strip()
                    gsis=str(r.get("gsis_id") or r.get("player_id") or "").strip()
                    if eid and gsis: by_espn[eid]=gsis
        except Exception:
            return {}
        return by_espn

    def _player_crosswalk(self):
        players=self._sleeper.get_players(); idx={}
        for sid,p in players.items():
            if not isinstance(p,dict):continue
            name=self._name(p.get("full_name") or (str(p.get("first_name") or "")+str(p.get("last_name") or "")))
            if name: idx.setdefault(name,[]).append((sid,p))
        return players,idx

    def normalized(self, league_id, team_id, week):
        data=self.league(league_id,week); teams=data.get("teams",[])
        try: tid=int(team_id)
        except Exception: raise ESPNAPIError("ESPN Team ID must be a number.")
        target=next((t for t in teams if int(t.get("id",-1))==tid),None)
        if not target: raise ESPNAPIError(f"ESPN team {team_id} was not found in league {league_id}.")
        sleeper_players,idx=self._player_crosswalk()
        espn_idx={}
        gsis_idx={}
        team_def_idx={}
        nflverse_espn=self._nflverse_identity_index()
        for sid,sp in sleeper_players.items():
            if not isinstance(sp,dict): continue
            eid=sp.get("espn_id") or sp.get("espn")
            if eid is not None: espn_idx[str(eid)]=(sid,sp)
            gsis=sp.get("gsis_id") or sp.get("gsis")
            if gsis: gsis_idx[str(gsis)]=(sid,sp)
            if str(sp.get("position") or "").upper() in {"DEF","DST"}:
                # Sleeper's D/ST ID is normally the team abbreviation, even when
                # its team field is missing or uses a different abbreviation.
                for value in (sp.get("team"), sid):
                    key=canonical_def_team(value)
                    if key in {canonical_def_team(t) for t in PRO_TEAMS.values()}:
                        team_def_idx[key]=(sid,sp)
        entries=((target.get("roster") or {}).get("entries") or [])
        roster_ids=[]; starter_ids=[]; unresolved=[]; roster_slots={}
        for e in entries:
            pool=e.get("playerPoolEntry") or {}; ep=pool.get("player") or {}
            name=ep.get("fullName") or ep.get("displayName")
            team=PRO_TEAMS.get(ep.get("proTeamId")); pos=POS.get(ep.get("defaultPositionId"))
            espn_pid=e.get("playerId") or pool.get("id") or ep.get("id")
            # Team-defense metadata is often missing from ESPN roster entries.
            # The lineup slot and negative player ID are sufficient to identify it.
            if int(e.get("lineupSlotId",20)) == 16 or (espn_pid is not None and str(espn_pid).startswith("-16")):
                inferred_team=espn_defense_team(espn_pid,ep.get("proTeamId"),name)
                if inferred_team:
                    team=inferred_team
                    pos="DEF"
            candidates=[]
            # Prefer the platform ID crosswalk. It avoids name changes/suffixes and duplicate names.
            if espn_pid is not None and str(espn_pid) in espn_idx:
                candidates=[espn_idx[str(espn_pid)]]
            # If Sleeper's ESPN-ID field is missing/stale, bridge ESPN -> nflverse
            # GSIS -> Sleeper. This is the stable universal path for any player
            # represented in nflverse's ID map.
            if not candidates and espn_pid is not None:
                gsis=nflverse_espn.get(str(espn_pid))
                if gsis and gsis in gsis_idx:
                    candidates=[gsis_idx[gsis]]
            # D/ST names differ between platforms; team+position is the stable identity.
            if not candidates and pos=="DEF" and canonical_def_team(team) in team_def_idx:
                candidates=[team_def_idx[canonical_def_team(team)]]
            # Exact normalized names, including suffix-insensitive variants.
            if not candidates:
                for nv in self._name_variants(name):
                    candidates.extend(idx.get(nv,[]))
                # Also compare suffix-insensitive variants from Sleeper because the
                # legacy index intentionally preserves exact names.
                if not candidates:
                    wanted=self._name_variants(name)
                    for sid2,sp2 in sleeper_players.items():
                        if not isinstance(sp2,dict): continue
                        sn=sp2.get("full_name") or (str(sp2.get("first_name") or "")+" "+str(sp2.get("last_name") or ""))
                        if wanted & self._name_variants(sn): candidates.append((sid2,sp2))
                if team: candidates=[c for c in candidates if str(c[1].get("team") or "").upper()==team] or candidates
                if pos: candidates=[c for c in candidates if str(c[1].get("position") or "").upper() in ({"DEF","DST"} if pos=="DEF" else {pos})] or candidates
            # Conservative fuzzy fallback: only within matching team + position and
            # only accept a unique, very-high-confidence name match.
            if not candidates and name and team and pos:
                target=min(self._name_variants(name), key=len, default="")
                scored=[]
                for sid2,sp2 in sleeper_players.items():
                    if not isinstance(sp2,dict): continue
                    if str(sp2.get("team") or "").upper()!=team: continue
                    spp=str(sp2.get("position") or "").upper()
                    if spp not in ({"DEF","DST"} if pos=="DEF" else {pos}): continue
                    sn=sp2.get("full_name") or (str(sp2.get("first_name") or "")+" "+str(sp2.get("last_name") or ""))
                    variants=self._name_variants(sn)
                    score=max((SequenceMatcher(None,target,v).ratio() for v in variants),default=0)
                    if score>=0.94: scored.append((score,sid2,sp2))
                scored.sort(reverse=True,key=lambda x:x[0])
                if scored and (len(scored)==1 or scored[0][0]-scored[1][0]>=0.03):
                    candidates=[(scored[0][1],scored[0][2])]
            if not candidates:
                unresolved.append({"name":name or str(espn_pid),"espn_player_id":espn_pid,"lineup_slot_id":e.get("lineupSlotId"),"starter":int(e.get("lineupSlotId",20)) not in (20,21)})
                continue
            sid=candidates[0][0]; roster_ids.append(sid)
            slot_id=int(e.get("lineupSlotId",20)); roster_slots[str(sid)]=slot_id
            if slot_id not in (20,21): starter_ids.append(sid)
        if not starter_ids: raise ESPNAPIError("ESPN roster loaded but no active starters could be resolved for this week.")
        lineup=self.lineup_settings(league_id)
        unresolved_starters=[x for x in unresolved if x.get("starter")]
        # Validate against OCCUPIED active roster entries, not the league's configured
        # maximum starter slots. ESPN permits intentionally empty starter slots (for
        # example, a benched QB leaving QB vacant). An empty configured slot has no
        # roster entry and therefore is not a crosswalk failure.
        occupied_active_entries=sum(1 for e in entries if int(e.get("lineupSlotId",20)) not in (20,21))
        if len(starter_ids) != occupied_active_entries:
            raise ESPNAPIError(
                f"ESPN lineup crosswalk incomplete: resolved {len(starter_ids)} of "
                f"{occupied_active_entries} occupied starter slots. Unresolved starters: {unresolved_starters}"
            )
        lineup["occupied_starters"]=occupied_active_entries
        lineup["open_starter_slots"]=max(0,int(lineup.get("expected_starters") or 0)-occupied_active_entries)
        sched=data.get("schedule") or []
        matchup=next((m for m in sched if int((m.get("home") or {}).get("teamId",-1))==tid or int((m.get("away") or {}).get("teamId",-1))==tid),{})
        home=matchup.get("home") or {}; away=matchup.get("away") or {}
        oppid=(away.get("teamId") if int(home.get("teamId",-1))==tid else home.get("teamId"))
        owners=target.get("owners") or []
        display=target.get("name") or " ".join(x for x in [target.get("location"),target.get("nickname")] if x) or f"ESPN Team {tid}"
        return {"players":sleeper_players,"starters":starter_ids,"roster":roster_ids,"team_id":tid,"opponent_team_id":oppid,"matchup_id":matchup.get("id"),"display_name":display,"owner_id":owners[0] if owners else str(tid),"unresolved":unresolved,"scoring_settings":self.scoring_settings(league_id),"lineup_settings":lineup,"roster_slots":roster_slots}
