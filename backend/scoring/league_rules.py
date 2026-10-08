"""League scoring coverage and stat-backed coefficient evaluation.

Only events explicitly projected by FME are applied. Other configured nonzero
rules are disclosed, never silently represented as fully modeled.
"""
from __future__ import annotations

from math import isfinite

# Every key in this table is backed by a corresponding predicted aggregate event.
SUPPORTED = {
    'pass_yd': 'passing_yards', 'pass_td': 'passing_tds',
    'pass_int': 'interceptions', 'int': 'interceptions',
    'pass_cmp': 'completions', 'pass_att': 'pass_attempts',
    'pass_inc': 'incompletions', 'rush_att': 'carries',
    'rush_yd': 'rushing_yards', 'rush_td': 'rushing_tds',
    'rec_yd': 'receiving_yards', 'rec_td': 'receiving_tds',
    'rec': 'receptions', 'fum_lost': 'fumbles_lost',
    'pass_2pt': 'passing_two_point_conversions',
    'rush_2pt': 'rushing_two_point_conversions',
    'rec_2pt': 'receiving_two_point_conversions',
    'two_pt': 'two_point_conversions', 'two_point': 'two_point_conversions',
    'fgm': 'field_goals', 'xpm': 'extra_points',
    'fgmiss': 'missed_field_goals', 'xpmiss': 'missed_extra_points',
    'sack': 'sacks', 'def_sack': 'sacks',
    'def_int': 'interceptions', 'def_st_fum_rec': 'fumble_recoveries',
    'def_fumble_rec': 'fumble_recoveries', 'def_td': 'def_tds',
}
# Canonical aliases must be selected once; cannot score 'int' and 'pass_int' twice.
ALIASES = {'def_sack': 'sack', 'def_fumble_rec': 'def_st_fum_rec',
           'two_point': 'two_pt'}
# Defaults are retained for unspecified standard scoring fields; if platform defines
# custom subcategory scoring that supersedes an aggregate, audit it separately.
DEFAULTS = {'pass_yd': .04, 'pass_td': 4, 'pass_int': -2,
            'rush_yd': .1, 'rush_td': 6, 'rec_yd': .1, 'rec_td': 6,
            'rec': 1, 'fum_lost': -2, 'two_pt': 2,
            'fgm': 3, 'xpm': 1, 'sack': 1, 'def_int': 2,
            'def_st_fum_rec': 2, 'def_td': 6}
# Distinguish unsupported *configured* scoring from an unknown key silently ignored.
METADATA = {'_espn_unmapped_stat_ids', '_espn_scoring_item_count'}


def coefficient(settings, key, default=0):
    value = (settings or {}).get(key, default)
    try:
        result = float(value)
        return result if isfinite(result) else default
    except (ValueError, TypeError):
        return default


def coverage(settings, platform=None):
    settings = settings or {}
    # The current predictor has no independent model for these event types.
    unprojected = {'fum_lost','pass_2pt','rush_2pt','rec_2pt','two_pt','two_point'}
    applied = sorted(k for k, v in settings.items() if k in SUPPORTED and k not in unprojected and _nonzero(v))
    unsupported = sorted(k for k, v in settings.items()
                         if (k not in SUPPORTED or k in unprojected) and k not in METADATA and _nonzero(v))
    unmapped = settings.get('_espn_unmapped_stat_ids', [])
    if isinstance(unmapped, list):
        unsupported.extend('espn_stat_id:' + str(i) for i in unmapped)
    if not settings:
        unsupported.append('league_scoring_settings_unavailable')
    return {'platform': platform, 'fully_modeled': not unsupported,
            'applied_configured_rules': applied, 'unmodeled_configured_rules': sorted(set(unsupported)),
            'warning': ('League contains scoring rules requiring additional projected statistics; '
                        'fantasy-point projections do not account for those rules.' if unsupported else None)}


def _nonzero(v):
    try:
        return float(v) != 0 and isfinite(float(v))
    except (TypeError, ValueError):
        return False


def score(settings, stats, pos=None):
    s = settings or {}
    pos = str(pos or '').upper()
    # Passing, rushing, receiving and fumbles may be performed by any player.
    keys = (['pass_yd','pass_td','pass_int','pass_cmp','pass_att','pass_inc','rush_att',
             'rush_yd','rush_td','rec_yd','rec_td','rec','fum_lost']
            if pos not in {'K','DEF'} else [])
    # 2-point events must not be double-counted if generic and typed stats coexist.
    typed = ('passing_two_point_conversions','rushing_two_point_conversions','receiving_two_point_conversions')
    if pos not in {'K','DEF'} and any(k in stats for k in typed):
        keys.extend(['pass_2pt','rush_2pt','rec_2pt'])
    elif pos not in {'K','DEF'}:
        keys.append('two_pt')
    if pos == 'K': keys.extend(['fgm','xpm','fgmiss','xpmiss'])
    if pos == 'DEF': keys.extend(['sack','def_int','def_st_fum_rec','def_td'])
    total = 0.0
    for key in keys:
        stat_key = SUPPORTED[key]
        if key == 'def_int' and 'def_int' not in s and 'int' in s:
            coeff = coefficient(s,'int',DEFAULTS[key])
        elif key == 'sack' and 'sack' not in s and 'def_sack' in s:
            coeff = coefficient(s,'def_sack',DEFAULTS[key])
        elif key == 'def_st_fum_rec' and 'def_st_fum_rec' not in s and 'def_fumble_rec' in s:
            coeff = coefficient(s,'def_fumble_rec',DEFAULTS[key])
        elif key == 'two_pt' and 'two_pt' not in s and 'two_point' in s:
            coeff = coefficient(s,'two_point',DEFAULTS[key])
        else:
            coeff = coefficient(s, key, DEFAULTS.get(key, coefficient(s,'two_pt',2) if key.endswith('_2pt') else 0))
        if key == 'fgmiss':
            event_count = max(0, float(stats.get('field_goal_attempts', 0) or 0) - float(stats.get('field_goals', 0) or 0))
        elif key == 'xpmiss':
            event_count = max(0, float(stats.get('extra_point_attempts', 0) or 0) - float(stats.get('extra_points', 0) or 0))
        elif key == 'pass_inc':
            event_count = max(0, float(stats.get('pass_attempts', 0) or 0) - float(stats.get('completions', 0) or 0))
        else:
            event_count = float(stats.get(stat_key, 0) or 0)
        total += event_count * coeff
    return total
