from .optimizer import optimize_lineup, normalize_slot


def _median(p):
    try: return float((p.get('projection') or {}).get('median_fantasy_points') or 0.0)
    except Exception: return 0.0


def _pid(p):
    return str(p.get('player_id'))


def _assigned_ids(opt):
    return {str(x.get('player_id')) for x in (opt.get('assignment') or []) if x.get('player_id') is not None}


def _best_drop_without_reopt(current, opt_with_add, add, slots):
    """Return a current-roster player that is not needed by the optimized lineup.

    If a player is absent from the optimal assignment after the add, removing that player
    leaves that exact assignment feasible and therefore preserves the optimum. This lets us
    prove the swap value without re-running the optimizer for every add/drop pair.
    """
    used=_assigned_ids(opt_with_add)
    bench=[p for p in current if _pid(p) not in used and _safe_drop(p, add, current, slots)]
    if not bench:
        return None
    # A bye-week zero is *not* a zero player valuation. Protect bye players
    # whenever a non-bye eligible drop exists, even within the same position.
    def key(p):
        intel=p.get('waiver_role_intel') or {}
        return (bool(p.get('on_bye')), _median(p), float(intel.get('opportunity_multiplier') or 1.0))
    return min(bench,key=key)


def _position(p):
    pos=str(p.get('position') or '').upper()
    return 'DEF' if pos in {'DEF','DST'} else pos


def _safe_drop(drop, add, roster, slots):
    """Conservative roster safeguards; unknown future value must not be treated as zero."""
    ap, dp = _position(add), _position(drop)
    # Never discard a bye-week player for a marginal current-week streamer.
    # With no defensible ROS projection, preserve that asset rather than
    # assuming its zero weekly points represent its future worth.
    if drop.get('on_bye') and dp in {'QB','RB','WR','TE'}:
        return False
    counts={pos:sum(_position(x)==pos for x in roster) for pos in {'QB','RB','WR','TE','K','DEF'}}
    if ap in {'QB','K','DEF'} and counts.get(ap,0) >= (2 if ap=='QB' else 1):
        # A streamer's projected gain alone is not grounds to add redundant QB/K/DEF.
        if ap != dp: return False
    if dp in {'RB','WR','TE'} and ap != dp and counts.get(dp,0) <= 2:
        return False
    # A missing projection, or an injury-related zero, is not evidence of zero ROS value.
    quality=drop.get('data_quality') or {}
    if _median(drop)<=0 and dp in {'QB','RB','WR','TE'} and ap!=dp:
        return False
    if quality.get('projection_status') in {'unavailable','pending'} and ap!=dp:
        return False
    return True


def _lineup_changes(before, after):
    """Only report entrants and exits, not players exchanging equivalent slots."""
    old={str(x.get('player_id')):x for x in before.get('assignment',[]) if x.get('player_id') is not None}
    new={str(x.get('player_id')):x for x in after.get('assignment',[]) if x.get('player_id') is not None}
    leaving=[x for pid,x in old.items() if pid not in new]
    entering=[x for pid,x in new.items() if pid not in old]
    changes=[]
    for i in range(max(len(leaving),len(entering))):
        prev=leaving[i] if i<len(leaving) else {}
        nxt=entering[i] if i<len(entering) else {}
        changes.append({'slot':nxt.get('slot') or prev.get('slot'),
                        'previous_starter':prev.get('name'),
                        'new_starter':nxt.get('name')})
    return changes


def recommend_waiver_moves(roster, candidates, slots, max_moves=12, min_gain=0.01, progress=None, cancelled=None):
    """Fast exact-current-week waiver advisor.

    Every supplied candidate is considered, but each candidate normally requires ONE lineup
    optimization rather than one optimization per pickup/drop pair.  For normal fantasy
    rosters (starter slots + bench), the drop is chosen from players unused by the optimized
    post-add lineup, which mathematically preserves that lineup and its score.  A rare no-bench
    fallback performs exact pair evaluation.
    """
    current=list(roster or [])
    available=list(candidates or [])
    # Preserve repeated FLEX slots and the independent QB-eligible Superflex slot.
    slots=[normalize_slot(s) for s in (slots or [])]
    flex_audit={"standard_flex":slots.count("FLEX"),"superflex":slots.count("SUPER_FLEX"),"configured_slots":slots}

    moves=[]
    baseline=optimize_lineup(current, slots)
    baseline_points=float(baseline.get('median_points') or 0.0)
    evaluated=0
    for move_idx in range(max(0,int(max_moves))):
        if cancelled and cancelled(): break
        best=None
        total=max(1,len(available))
        for idx,add in enumerate(available,1):
            if cancelled and cancelled(): break
            if any(_pid(x)==_pid(add) for x in current): continue
            # One exact optimization for this pickup. No add x drop Cartesian product.
            opt=optimize_lineup(current+[add],slots)
            evaluated += 1
            # A waiver candidate must actually enter the optimized starting lineup.
            # Adding a bench-only player never qualifies as a weekly upgrade.
            if _pid(add) not in _assigned_ids(opt):
                if progress and (idx==1 or idx%5==0 or idx==total): progress(idx,total,move_idx)
                continue
            drop=_best_drop_without_reopt(current,opt,add,slots)
            if drop is not None:
                new_points=float(opt.get('median_points') or 0.0)
                gain=new_points-baseline_points
                cand=(gain,_median(add)-_median(drop),add,drop,opt)
                if gain>=min_gain and (best is None or cand[:2]>best[:2]): best=cand
            else:
                # Roster has no bench/unassigned player. Rare exact fallback.
                for d in current:
                    if not _safe_drop(d,add,current,slots): continue
                    trial=[x for x in current if _pid(x)!=_pid(d)]+[add]
                    o=optimize_lineup(trial,slots)
                    if o.get('filled_slots',0)<baseline.get('filled_slots',0): continue
                    if _pid(add) not in _assigned_ids(o): continue
                    gain=float(o.get('median_points') or 0.0)-baseline_points
                    cand=(gain,_median(add)-_median(d),add,d,o)
                    if gain>=min_gain and (best is None or cand[:2]>best[:2]): best=cand
            if progress and (idx==1 or idx%5==0 or idx==total): progress(idx,total,move_idx)
        if best is None: break
        gain,raw_gain,add,drop,opt=best
        prior_starters=_assigned_ids(baseline)
        next_starters=_assigned_ids(opt)
        replaced=[x for x in baseline.get('assignment',[]) if str(x.get('player_id')) not in next_starters]
        # The pickup can fill an open starter slot instead of replacing a starter.
        if _pid(add) not in next_starters:
            break
        pickup_assignment=next((x for x in opt.get('assignment',[]) if str(x.get('player_id'))==_pid(add)),{})
        moves.append({'pickup':_brief(add),'drop':_brief(drop),'projected_team_points_before':round(baseline_points,2),'projected_team_points_after':round(float(opt.get('median_points') or 0.0),2),'team_points_gain':round(gain,2),'player_median_difference':round(raw_gain,2),'lineup_changes':_lineup_changes(baseline,opt),'starter_replaced':[{'player_id':x.get('player_id'),'name':x.get('name'),'position':x.get('position')} for x in replaced],'pickup_starting_slot':pickup_assignment.get('slot'),'drop_was_starter':_pid(drop) in prior_starters,'gain_basis':'optimized_starting_lineup_only','recommendation_type':'current_week_only','rest_of_season_assessed':False,'bye_protection_applied':True,'warning':'Future-week projections are not yet available; do not interpret this as a rest-of-season upgrade.'})
        current=[x for x in current if _pid(x)!=_pid(drop)]+[add]
        available=[x for x in available if _pid(x)!=_pid(add)]
        baseline=opt; baseline_points=float(opt.get('median_points') or 0.0)
    return {'moves':moves,'move_count':len(moves),'final_optimal_team_points':round(baseline_points,2),'evaluated_candidates':len(candidates or []),'lineup_optimizations':evaluated,'evaluation_mode':'starter_entry_required_bye_protected','rest_of_season_assessed':False,'lineup_slot_audit':flex_audit}


def _brief(p):
    return {'player_id':p.get('player_id'),'name':p.get('name') or p.get('full_name'),'position':p.get('position'),'team':p.get('team'),'median_fantasy_points':round(_median(p),2),'low':(p.get('projection') or {}).get('low'),'high':(p.get('projection') or {}).get('high'),'waiver_role_intel':p.get('waiver_role_intel') or {},'on_bye':bool(p.get('on_bye'))}
