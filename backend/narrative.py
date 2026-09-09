# ============================================================================
# SCRIPT 6: narrative.py - Written Interpretations, no third-party API
# ============================================================================
# Replaces the previous Gemini dependency. Two backends, both free:
#
#   'template'  (default) A deterministic generator. Pure Python, no model, no
#               network, no key, no rate limit, no per-request cost. It runs
#               anywhere the API runs and produces the same prose for the same
#               profile every time, which also makes it testable.
#
#   'llm'       (opt-in) A local open-weights instruct model through
#               llama-cpp-python, e.g. Qwen2.5-0.5B-Instruct or
#               SmolLM2-360M-Instruct in GGUF form, both Apache-2.0. Nothing
#               leaves the host. Enable with NARRATIVE_BACKEND=llm and point
#               LLM_MODEL_PATH at the .gguf file. Any failure, including a
#               missing model or missing library, falls back to 'template'
#               rather than failing the request.
#
# Set NARRATIVE_BACKEND in the environment. Default is 'template'.
# ============================================================================

import hashlib
import logging
import os
from typing import Dict, List, Optional

from ocean_items import TRAITS, TRAIT_ORDER

logger = logging.getLogger(__name__)

# Score bands on the 0-100 scale position.
BANDS = ((20.0, 'very_low'), (40.0, 'low'), (60.0, 'moderate'), (80.0, 'high'))


def band_of(score: float) -> str:
    for threshold, name in BANDS:
        if score < threshold:
            return name
    return 'very_high'


# Two phrasings per trait per band, chosen by a hash of the profile so the same
# answers always produce the same page while different answers vary.
TRAIT_LINES: Dict[str, Dict[str, List[str]]] = {
    'O': {
        'very_low': ["You prefer the settled and the concrete, and you have little patience for abstraction for its own sake.",
                     "Novelty holds little pull for you; you would rather work with what is known and proven."],
        'low': ["You lean practical over speculative, and you tend to want an idea to earn its keep before you adopt it.",
                "Abstract discussion interests you only when it leads somewhere you can use."],
        'moderate': ["You can follow an idea where it leads without losing your footing in the practical.",
                     "You are open to the unfamiliar without being pulled around by it."],
        'high': ["You reach for the unfamiliar readily and enjoy an idea before knowing what it is for.",
                 "Curiosity is a live part of how you work, not an occasional visitor."],
        'very_high': ["Ideas are where you live. You are drawn to the untested and the strange almost by reflex.",
                      "You have an unusually strong appetite for the new, which is a real advantage and an occasional cost in focus."],
    },
    'C': {
        'very_low': ["Structure sits lightly on you. Plans and schedules are things you work around rather than through.",
                     "You resist being organised by a system, and follow-through depends heavily on interest."],
        'low': ["You are flexible about order and deadlines, and you work best when the structure is loose.",
                "Routine is not your natural mode; you would rather stay adaptable than tidy."],
        'moderate': ["You keep enough order to be reliable without letting method become the point.",
                     "You can hold to a plan and abandon one, which is a more useful combination than it sounds."],
        'high': ["You finish what you start and you notice the details other people leave behind.",
                 "Order is not an effort for you so much as a preference you act on consistently."],
        'very_high': ["You are exacting, prepared, and hard to catch out. That reliability is your most visible trait.",
                      "Method matters to you a great deal, and you hold yourself to it even when nobody checks."],
    },
    'E': {
        'very_low': ["You conserve social energy carefully and are most yourself with few people or none.",
                     "Company costs you something, and you are deliberate about when you spend it."],
        'low': ["You are comfortable in the background and rarely feel the need to fill a silence.",
                "You prefer smaller rooms and fewer conversations, and you are unhurried about entering either."],
        'moderate': ["You can hold a room or sit out of one, and neither costs you much.",
                     "You move between company and solitude without either feeling like a retreat."],
        'high': ["You start conversations easily and gain energy from the people in the room.",
                 "You are comfortable being noticed, and you tend to be the one who opens things up."],
        'very_high': ["You are the current in a room rather than something carried by it.",
                      "Sociability is close to a default state for you, and solitude is the thing you have to schedule."],
    },
    'A': {
        'very_low': ["You are blunt and hard to move by appeals to feeling, which makes you useful and occasionally difficult.",
                     "You put the argument ahead of the atmosphere, and you rarely soften a position to keep the peace."],
        'low': ["You are more sceptical than accommodating, and you do not take other people's framing at face value.",
                "You will say the unwelcome thing, and you are not especially troubled when it lands badly."],
        'moderate': ["You can be warm and you can be firm, and you choose between them rather than defaulting.",
                     "You take other people seriously without losing your own position in the process."],
        'high': ["You read other people's feelings quickly and you act on what you read.",
                 "Warmth is a genuine part of how you operate, not a manner you put on."],
        'very_high': ["Concern for other people runs through almost everything you do, sometimes ahead of your own position.",
                      "You are unusually attuned to how others feel, and you carry more of that weight than most people notice."],
    },
    'N': {
        'very_low': ["You are steady under pressure to a degree most people are not, and setbacks move you less than they move others.",
                     "Very little rattles you, and you recover from what does without much visible cost."],
        'low': ["You keep an even keel, and stress tends to pass through you rather than settle.",
                "You are not easily thrown, and you rarely carry a bad hour into the next one."],
        'moderate': ["You feel pressure without being run by it, which is the ordinary and workable case.",
                     "Difficult periods reach you, and they do not take you over."],
        'high': ["You feel things sharply, and worry is a familiar companion rather than an occasional visitor.",
                 "Stress lands hard and stays a while, which is exhausting and also makes you attentive."],
        'very_high': ["Your emotional weather is vivid and changes quickly, and it takes real effort to hold steady in it.",
                      "You register strain early and strongly. That is costly, and it is also information other people miss."],
    },
}

LAMBDA_LINES = {
    'light': ("Your cross-check answers sit comfortably alongside your trait answers, so these numbers "
              "are close to what you gave us. The correction barely moved them."),
    'moderate': ("There is some tension between your cross-check answers and your trait answers, so the "
                 "correction has shifted the numbers a little. The originals are shown alongside."),
    'substantial': ("Your answers describe someone more consistent than people usually are, so the correction "
                    "is doing real work here. Read the adjusted numbers as one reading and the originals as another."),
}


class NarrativeGenerator:
    """Produces the written reading that accompanies a result."""

    def __init__(self, backend: Optional[str] = None, model_path: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.backend = (backend or os.getenv('NARRATIVE_BACKEND', 'template')).lower()
        self.model_path = model_path or os.getenv('LLM_MODEL_PATH', '')
        self._llm = None
        if self.backend == 'llm':
            self._init_llm()
        self.logger.info(f'[NARRATIVE] ✓ Backend: {self.active_backend}')

    @property
    def active_backend(self) -> str:
        return 'llm' if self._llm is not None else 'template'

    def _init_llm(self) -> None:
        if not self.model_path or not os.path.exists(self.model_path):
            self.logger.warning(
                f'[NARRATIVE] ⚠ NARRATIVE_BACKEND=llm but no model at "{self.model_path}". '
                'Falling back to the template backend.'
            )
            return
        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=1024,
                n_threads=int(os.getenv('LLM_THREADS', '2')),
                verbose=False,
            )
            self.logger.info(f'[NARRATIVE] ✓ Local model loaded from {self.model_path}')
        except Exception as exc:
            self.logger.warning(f'[NARRATIVE] ⚠ Could not load local model ({exc}). Using templates.')
            self._llm = None

    # ------------------------------------------------------------------

    def generate(self, context: Dict) -> Dict:
        """context: type_name, confidence, lambda, lambda_band, corrected/raw scores."""
        if self._llm is not None:
            text = self._generate_llm(context)
            if text:
                return {'interpretation': text, 'backend': 'llm', 'model': os.path.basename(self.model_path)}
            self.logger.warning('[NARRATIVE] ⚠ Local model returned nothing. Using templates.')
        return {'interpretation': self._generate_template(context),
                'backend': 'template', 'model': None}

    # ------------------------------------------------------------------
    # Template backend
    # ------------------------------------------------------------------

    def _generate_template(self, context: Dict) -> str:
        scores: Dict[str, float] = context['corrected_trait_scores']
        seed = self._seed(scores)
        mean = sum(scores.values()) / len(scores)

        # The two traits furthest from this profile's own centre carry the read.
        ranked = sorted(TRAIT_ORDER, key=lambda t: abs(scores[t] - mean), reverse=True)
        standout, second = ranked[0], ranked[1]
        settled = [t for t in ranked[2:] if abs(scores[t] - mean) < 10.0]

        paragraphs = []

        opening = context.get('type_name')
        if opening and context.get('weights_loaded'):
            confidence = context.get('confidence')
            pct = f' The fit is {round(confidence * 100)}% clearer than the next nearest pattern.' if confidence else ''
            paragraphs.append(
                f"Your profile sits closest to {opening}.{pct} What separates it from the others is "
                f"{TRAITS[standout]['name'].lower()}, with {TRAITS[second]['name'].lower()} close behind."
            )
        else:
            paragraphs.append(
                f"The two traits that shape your profile most are {TRAITS[standout]['name'].lower()} "
                f"and {TRAITS[second]['name'].lower()}."
            )

        paragraphs.append(' '.join([
            self._line(standout, scores[standout], seed),
            self._line(second, scores[second], seed + 1),
        ]))

        if settled:
            names = [TRAITS[t]['name'].lower() for t in settled]
            joined = names[0] if len(names) == 1 else ', '.join(names[:-1]) + f' and {names[-1]}'
            paragraphs.append(
                f"On {joined} you sit near the middle. That is the common case, and it usually means "
                f"context decides more than disposition does."
            )
        else:
            paragraphs.append(
                'None of your five traits sit near the middle, which makes this a more pronounced '
                'profile than most and a more distinctive one.'
            )

        percentiles = context.get('percentiles')
        if percentiles:
            highest = max(TRAIT_ORDER, key=lambda t: percentiles[t])
            lowest = min(TRAIT_ORDER, key=lambda t: percentiles[t])
            paragraphs.append(
                f"Against the reference sample, your {TRAITS[highest]['name'].lower()} is higher than "
                f"{percentiles[highest]:.0f}% of respondents and your {TRAITS[lowest]['name'].lower()} "
                f"is higher than {percentiles[lowest]:.0f}%."
            )

        paragraphs.append(LAMBDA_LINES.get(context.get('lambda_band', 'moderate'),
                                           LAMBDA_LINES['moderate']))
        paragraphs.append(
            'This is a research prototype, not a clinical instrument. Treat it as a prompt for '
            'reflection rather than a finding about you.'
        )
        return '\n\n'.join(paragraphs)

    def _line(self, trait: str, score: float, seed: int) -> str:
        options = TRAIT_LINES[trait][band_of(score)]
        return options[seed % len(options)]

    @staticmethod
    def _seed(scores: Dict[str, float]) -> int:
        key = '|'.join(f'{t}:{scores[t]:.1f}' for t in TRAIT_ORDER)
        return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)

    # ------------------------------------------------------------------
    # Local model backend
    # ------------------------------------------------------------------

    def _generate_llm(self, context: Dict) -> Optional[str]:
        try:
            scores = context['corrected_trait_scores']
            profile = ', '.join(
                f"{TRAITS[t]['name']} {scores[t]:.0f} out of 100" for t in TRAIT_ORDER)
            prompt = (
                '<|im_start|>system\nYou write short, plain, non-flattering personality readings. '
                'Never diagnose. Never predict the future. Three short paragraphs, no lists, no headings.'
                '<|im_end|>\n<|im_start|>user\n'
                f'Write a reading for this Big Five profile: {profile}. '
                f"The self-flattery correction applied to these scores was {context.get('lambda_band', 'moderate')}. "
                'Say what the two most distinctive traits mean day to day, then note what the correction '
                'implies about reading the numbers.<|im_end|>\n<|im_start|>assistant\n'
            )
            out = self._llm(prompt, max_tokens=380, temperature=0.7, top_p=0.9,
                            stop=['<|im_end|>', '<|im_start|>'])
            text = out['choices'][0]['text'].strip()
            return text or None
        except Exception as exc:
            self.logger.error(f'[NARRATIVE] ✗ Local model failed: {exc}', exc_info=True)
            return None


narrative_generator = None
