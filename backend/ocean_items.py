# ============================================================================
# SCRIPT 2: ocean_items.py - The Item Bank (single source of truth)
# ============================================================================
# The 50 scored items are the IPIP "Big-Five Factor Markers" (Goldberg, 1992),
# distributed by the International Personality Item Pool at https://ipip.ori.org
# and explicitly placed in the public domain.
#
# The item codes below (EXT1..EXT10, EST1..EST10, AGR1..AGR10, CSN1..CSN10,
# OPN1..OPN10) are the SAME codes used as column names in the training
# dataset (Open-Source Psychometrics Project, IPIP-FFM, 1,015,342 responses).
# Do not rename them: the trained weights are indexed by ITEM_ORDER below, so
# a rename silently reorders the model input.
#
# The five V items are this project's own cross-checks. They are never scored
# as traits; they drive the self-flattery correction only, and they are not
# part of the model input vector.
# ============================================================================

from typing import Dict, List

# Answer scale. Matches the training dataset: 1 = Disagree, 5 = Agree.
SCALE_MIN = 1
SCALE_MAX = 5
SCALE_LABELS = {
    1: 'Strongly disagree',
    2: 'Disagree',
    3: 'Neutral',
    4: 'Agree',
    5: 'Strongly agree',
}

TRAITS = {
    'O': {'code': 'OPN', 'name': 'Openness', 'blurb': 'Curiosity, imagination, and appetite for the unfamiliar.'},
    'C': {'code': 'CSN', 'name': 'Conscientiousness', 'blurb': 'Order, follow-through, and attention to detail.'},
    'E': {'code': 'EXT', 'name': 'Extraversion', 'blurb': 'Sociability, assertiveness, and energy around people.'},
    'A': {'code': 'AGR', 'name': 'Agreeableness', 'blurb': 'Warmth, empathy, and concern for other people.'},
    'N': {'code': 'EST', 'name': 'Neuroticism', 'blurb': 'Proneness to worry, tension, and shifting moods.'},
}

# Trait order used everywhere a five-vector appears.
TRAIT_ORDER: List[str] = ['O', 'C', 'E', 'A', 'N']

# ============================================================================
# THE 50 SCORED ITEMS
# ============================================================================
# 'reverse': True means a high answer indicates a LOW standing on the trait.
# Reverse keying follows the standard IPIP-50 scoring sheet. The EST items are
# worded toward neuroticism, so EST2 and EST4 ("relaxed", "seldom feel blue")
# are the reversed ones.

SCORED_ITEMS: List[Dict] = [
    # ---- Extraversion -----------------------------------------------------
    {'id': 'EXT1',  'trait': 'E', 'reverse': False, 'text': 'I am the life of the party.'},
    {'id': 'EXT2',  'trait': 'E', 'reverse': True,  'text': "I don't talk a lot."},
    {'id': 'EXT3',  'trait': 'E', 'reverse': False, 'text': 'I feel comfortable around people.'},
    {'id': 'EXT4',  'trait': 'E', 'reverse': True,  'text': 'I keep in the background.'},
    {'id': 'EXT5',  'trait': 'E', 'reverse': False, 'text': 'I start conversations.'},
    {'id': 'EXT6',  'trait': 'E', 'reverse': True,  'text': 'I have little to say.'},
    {'id': 'EXT7',  'trait': 'E', 'reverse': False, 'text': 'I talk to a lot of different people at parties.'},
    {'id': 'EXT8',  'trait': 'E', 'reverse': True,  'text': "I don't like to draw attention to myself."},
    {'id': 'EXT9',  'trait': 'E', 'reverse': False, 'text': "I don't mind being the centre of attention."},
    {'id': 'EXT10', 'trait': 'E', 'reverse': True,  'text': 'I am quiet around strangers.'},

    # ---- Neuroticism (dataset codes these EST, worded toward neuroticism) --
    {'id': 'EST1',  'trait': 'N', 'reverse': False, 'text': 'I get stressed out easily.'},
    {'id': 'EST2',  'trait': 'N', 'reverse': True,  'text': 'I am relaxed most of the time.'},
    {'id': 'EST3',  'trait': 'N', 'reverse': False, 'text': 'I worry about things.'},
    {'id': 'EST4',  'trait': 'N', 'reverse': True,  'text': 'I seldom feel blue.'},
    {'id': 'EST5',  'trait': 'N', 'reverse': False, 'text': 'I am easily disturbed.'},
    {'id': 'EST6',  'trait': 'N', 'reverse': False, 'text': 'I get upset easily.'},
    {'id': 'EST7',  'trait': 'N', 'reverse': False, 'text': 'I change my mood a lot.'},
    {'id': 'EST8',  'trait': 'N', 'reverse': False, 'text': 'I have frequent mood swings.'},
    {'id': 'EST9',  'trait': 'N', 'reverse': False, 'text': 'I get irritated easily.'},
    {'id': 'EST10', 'trait': 'N', 'reverse': False, 'text': 'I often feel blue.'},

    # ---- Agreeableness ----------------------------------------------------
    {'id': 'AGR1',  'trait': 'A', 'reverse': True,  'text': 'I feel little concern for others.'},
    {'id': 'AGR2',  'trait': 'A', 'reverse': False, 'text': 'I am interested in people.'},
    {'id': 'AGR3',  'trait': 'A', 'reverse': True,  'text': 'I insult people.'},
    {'id': 'AGR4',  'trait': 'A', 'reverse': False, 'text': "I sympathise with others' feelings."},
    {'id': 'AGR5',  'trait': 'A', 'reverse': True,  'text': "I am not interested in other people's problems."},
    {'id': 'AGR6',  'trait': 'A', 'reverse': False, 'text': 'I have a soft heart.'},
    {'id': 'AGR7',  'trait': 'A', 'reverse': True,  'text': 'I am not really interested in others.'},
    {'id': 'AGR8',  'trait': 'A', 'reverse': False, 'text': 'I take time out for others.'},
    {'id': 'AGR9',  'trait': 'A', 'reverse': False, 'text': "I feel others' emotions."},
    {'id': 'AGR10', 'trait': 'A', 'reverse': False, 'text': 'I make people feel at ease.'},

    # ---- Conscientiousness ------------------------------------------------
    {'id': 'CSN1',  'trait': 'C', 'reverse': False, 'text': 'I am always prepared.'},
    {'id': 'CSN2',  'trait': 'C', 'reverse': True,  'text': 'I leave my belongings around.'},
    {'id': 'CSN3',  'trait': 'C', 'reverse': False, 'text': 'I pay attention to details.'},
    {'id': 'CSN4',  'trait': 'C', 'reverse': True,  'text': 'I make a mess of things.'},
    {'id': 'CSN5',  'trait': 'C', 'reverse': False, 'text': 'I get chores done right away.'},
    {'id': 'CSN6',  'trait': 'C', 'reverse': True,  'text': 'I often forget to put things back in their proper place.'},
    {'id': 'CSN7',  'trait': 'C', 'reverse': False, 'text': 'I like order.'},
    {'id': 'CSN8',  'trait': 'C', 'reverse': True,  'text': 'I shirk my duties.'},
    {'id': 'CSN9',  'trait': 'C', 'reverse': False, 'text': 'I follow a schedule.'},
    {'id': 'CSN10', 'trait': 'C', 'reverse': False, 'text': 'I am exacting in my work.'},

    # ---- Openness ---------------------------------------------------------
    {'id': 'OPN1',  'trait': 'O', 'reverse': False, 'text': 'I have a rich vocabulary.'},
    {'id': 'OPN2',  'trait': 'O', 'reverse': True,  'text': 'I have difficulty understanding abstract ideas.'},
    {'id': 'OPN3',  'trait': 'O', 'reverse': False, 'text': 'I have a vivid imagination.'},
    {'id': 'OPN4',  'trait': 'O', 'reverse': True,  'text': 'I am not interested in abstract ideas.'},
    {'id': 'OPN5',  'trait': 'O', 'reverse': False, 'text': 'I have excellent ideas.'},
    {'id': 'OPN6',  'trait': 'O', 'reverse': True,  'text': 'I do not have a good imagination.'},
    {'id': 'OPN7',  'trait': 'O', 'reverse': False, 'text': 'I am quick to understand things.'},
    {'id': 'OPN8',  'trait': 'O', 'reverse': False, 'text': 'I use difficult words.'},
    {'id': 'OPN9',  'trait': 'O', 'reverse': False, 'text': 'I spend time reflecting on things.'},
    {'id': 'OPN10', 'trait': 'O', 'reverse': False, 'text': 'I am full of ideas.'},
]

# ============================================================================
# THE 5 CROSS-CHECKS
# ============================================================================
# These probe how the respondent answers rather than what they are like.
# 'expects_low' marks the two items where a *high* answer is the candid one,
# so an implausibly low answer is what counts against the profile.

VALIDITY_ITEMS: List[Dict] = [
    {'id': 'V1', 'trait': 'V', 'expects_low': False,
     'text': 'I find it easy to admit when I have made a mistake or been wrong about something.'},
    {'id': 'V2', 'trait': 'V', 'expects_low': False,
     'text': 'I am genuinely humble, rather than appearing humble to win social approval.'},
    {'id': 'V3', 'trait': 'V', 'expects_low': False,
     'text': 'My behaviour and my values are much the same with close friends, at work, and with strangers.'},
    {'id': 'V4', 'trait': 'V', 'expects_low': True,
     'text': 'I sometimes cannot work out my own reasons for doing something, even after thinking it over.'},
    {'id': 'V5', 'trait': 'V', 'expects_low': True,
     'text': 'I can recall specific times I acted selfishly, even though I tell people generosity matters to me.'},
]

ALL_ITEMS: List[Dict] = SCORED_ITEMS + VALIDITY_ITEMS

# Canonical model input order. The trained weights are indexed by this list.
ITEM_ORDER: List[str] = [item['id'] for item in SCORED_ITEMS]
VALIDITY_ORDER: List[str] = [item['id'] for item in VALIDITY_ITEMS]
ALL_ITEM_IDS: List[str] = ITEM_ORDER + VALIDITY_ORDER

N_SCORED = len(ITEM_ORDER)          # 50
N_VALIDITY = len(VALIDITY_ORDER)    # 5
N_ITEMS = len(ALL_ITEM_IDS)         # 55

# Lookups built once at import.
ITEM_BY_ID: Dict[str, Dict] = {item['id']: item for item in ALL_ITEMS}
REVERSED_IDS = frozenset(item['id'] for item in SCORED_ITEMS if item['reverse'])
TRAIT_ITEM_IDS: Dict[str, List[str]] = {
    trait: [item['id'] for item in SCORED_ITEMS if item['trait'] == trait]
    for trait in TRAIT_ORDER
}


def reverse_score(value: float) -> float:
    """Flip an answer about the midpoint of the scale (1<->5, 2<->4)."""
    return (SCALE_MIN + SCALE_MAX) - value


def keyed_value(item_id: str, value: float) -> float:
    """Return the answer in trait-positive direction, reversing where keyed."""
    return reverse_score(value) if item_id in REVERSED_IDS else float(value)


def to_frontend_payload() -> Dict:
    """The item bank in the shape the questionnaire page needs."""
    return {
        'scale': {
            'min': SCALE_MIN,
            'max': SCALE_MAX,
            'labels': {str(k): v for k, v in SCALE_LABELS.items()},
        },
        'traits': {k: {'name': v['name'], 'blurb': v['blurb']} for k, v in TRAITS.items()},
        'trait_order': TRAIT_ORDER,
        'items': (
            [{'id': i['id'], 'trait': i['trait'], 'text': i['text'], 'validity': False}
             for i in SCORED_ITEMS]
            + [{'id': i['id'], 'trait': 'V', 'text': i['text'], 'validity': True}
               for i in VALIDITY_ITEMS]
        ),
        'counts': {'scored': N_SCORED, 'validity': N_VALIDITY, 'total': N_ITEMS},
    }


def validate_item_bank() -> None:
    """Fail loudly at import time if the bank has drifted out of shape."""
    assert N_SCORED == 50, f'expected 50 scored items, found {N_SCORED}'
    assert N_VALIDITY == 5, f'expected 5 validity items, found {N_VALIDITY}'
    assert len(set(ALL_ITEM_IDS)) == N_ITEMS, 'duplicate item id in the bank'
    for trait in TRAIT_ORDER:
        n = len(TRAIT_ITEM_IDS[trait])
        assert n == 10, f'trait {trait} has {n} items, expected 10'


validate_item_bank()
