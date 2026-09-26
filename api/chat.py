import json
from pathlib import Path

from django.conf import settings

METRICS_PATH = Path(settings.BASE_DIR).parent / 'asset' / 'metrics.json'

GRADE_LABELS = ['Normal', 'Doubtful', 'Mild', 'Moderate', 'Severe']

EXAMPLE_QUESTIONS = [
    'What does this result mean?',
    'How accurate is this model?',
    'How does the model work?',
    'Where does the training data come from?',
]

INTENTS = [
    ('kellgren', ['kellgren', 'kl scale', 'grading system', 'lawrence']),
    ('advice', [
        'should i do', 'treatment', 'see a doctor', 'diagnose', 'diagnosis',
        'hurts', 'hurt', 'my knee', 'should i take', 'surgery', 'medication',
        'exercise', 'painkiller',
    ]),
    ('grade1', ['grade 1', 'doubtful', 'unreliable', 'why unreliable']),
    ('accuracy', ['accurate', 'accuracy', 'reliable', 'reliability', 'trust']),
    ('architecture', ['how does it work', 'architecture', 'mobilenet', 'how it works', 'how the model']),
    ('dataset', ['dataset', 'data from', 'data source', 'where does the data']),
    ('result', ['result', 'explain', 'grade', 'mean', 'means']),
]

_metrics = None


def get_metrics():
    global _metrics
    if _metrics is None:
        with open(METRICS_PATH) as f:
            _metrics = json.load(f)
    return _metrics


def _score(message, keywords):
    return sum(1 for kw in keywords if kw in message)


def match_intent(message):
    message = message.lower()
    best_intent, best_score = 'fallback', 0
    for name, keywords in INTENTS:
        score = _score(message, keywords)
        if score > best_score:
            best_intent, best_score = name, score
    return best_intent


def _result_reply(consultation):
    if consultation is None or consultation.grade is None:
        return (
            "I don't have a graded X-ray for this conversation yet. Upload an X-ray in the "
            "composer and I can explain that result once it's ready."
        )
    grade = consultation.grade
    label = GRADE_LABELS[grade]
    oa = 'osteoarthritis was detected' if grade >= 2 else 'no significant osteoarthritis was detected'
    text = (
        f"This X-ray was graded Kellgren-Lawrence Grade {grade} ({label}), with "
        f"{consultation.confidence:.0%} confidence and an expected grade of "
        f"{consultation.expected_grade:.1f}. Based on that, {oa}."
    )
    if grade in (1, 2):
        grade1_f1 = get_metrics()['per_class']['Doubtful']['f1-score']
        text += (
            f" Note: Grades 1-2 are the hardest for this model to separate (Grade 1 F1 is only "
            f"{grade1_f1:.2f}), so treat this specific grade cautiously."
        )
    return text


def _accuracy_reply():
    m = get_metrics()
    h = m['headline']
    dep = m['deployment']
    return (
        f"The full 4-model ensemble reaches {h['accuracy']*100:.1f}% 5-class accuracy, "
        f"macro-F1 {h['macro_f1']:.3f}, and Quadratic Weighted Kappa (QWK) {h['qwk']:.3f}. "
        f"This app runs {dep['model']} alone, which reaches QWK {dep['qwk']:.3f} and binary "
        f"(healthy vs osteoarthritis) accuracy {dep['acc_binary']*100:.1f}%. QWK is the metric "
        "that matters most here because this is an ordinal scale — mistaking Grade 2 for "
        "Grade 3 is a smaller error than mistaking Grade 2 for Grade 0, and QWK is the only "
        "metric that accounts for that distinction."
    )


def _grade1_reply():
    m = get_metrics()
    pc = m['per_class']['Doubtful']
    return (
        f"Grade 1 (Doubtful) is the model's weakest class: F1 is only {pc['f1-score']:.2f}. "
        "In this dataset, repeat gradings of 21 knees by human experts disagreed with each "
        "other at this boundary, and the Grade 1 and Grade 2 score distributions overlap "
        "almost entirely. The limitation is in the underlying labels, not just the model."
    )


def _kellgren_reply():
    m = get_metrics()
    lines = [f"Grade {g}: {desc}" for g, desc in m['kl_definitions'].items()]
    return "The Kellgren-Lawrence scale grades knee osteoarthritis 0-4:\n" + "\n".join(lines)


def _advice_reply():
    return (
        "I can't give medical advice, exercises, medication or treatment recommendations — "
        "this is a research prototype, not a medical device, and it can't diagnose you. "
        "Please see a licensed clinician for any of that."
    )


def _architecture_reply():
    m = get_metrics()
    dep = m['deployment']
    ds = m['dataset']
    ensemble_qwk = m['headline']['qwk']
    return (
        f"This app runs {dep['model']} ({dep['params']} parameters, {dep['size_mb']}MB), "
        f"trained on {ds['total']:,} X-rays from {ds['patients']:,} patients with a "
        f"patient-level train/val/test split ({ds['split']}). The full 4-model ensemble "
        f"(DenseNet201, EfficientNetV2S, MobileNetV2, Xception) reaches QWK {ensemble_qwk:.3f}; "
        f"this deployment trades {ensemble_qwk - dep['qwk']:.3f} kappa for a much smaller, "
        f"faster model — {dep['note']}"
    )


def _dataset_reply():
    m = get_metrics()
    return f"The training data source is: {m['dataset']['source']}."


def _fallback_reply():
    examples = "\n".join(f"- {q}" for q in EXAMPLE_QUESTIONS)
    return (
        "I can answer questions about a graded X-ray result, this model's real accuracy, the "
        "Kellgren-Lawrence grading scale, how the model works, and where the training data "
        "comes from. For example:\n" + examples
    )


def reply(message, consultation=None):
    intent = match_intent(message)
    builders = {
        'result': lambda: _result_reply(consultation),
        'accuracy': _accuracy_reply,
        'grade1': _grade1_reply,
        'kellgren': _kellgren_reply,
        'advice': _advice_reply,
        'architecture': _architecture_reply,
        'dataset': _dataset_reply,
        'fallback': _fallback_reply,
    }
    return {'reply': builders[intent](), 'intent': intent}
