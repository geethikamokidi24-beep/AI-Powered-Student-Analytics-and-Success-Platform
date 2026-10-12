"""Portable inference for the bundled logistic regression demonstration models."""
import json
import math
from pathlib import Path

MODEL = json.loads((Path(__file__).parent / 'models' / 'risk_model.json').read_text())
ACTIONS = {
 'acad': 'Plan subject-specific tutoring and a backlog review with an academic mentor.',
 'att': 'Discuss attendance barriers and agree on a weekly attendance improvement plan.',
 'lms': 'Schedule regular LMS study sessions and catch up on incomplete assignments.',
 'eng': 'Choose one club, project or hackathon aligned with the student interests.',
 'plc': 'Practice aptitude, coding and mock interviews with the placement team.',
 'skl': 'Set a four-week technical and communication skill development goal.',
 'fb': 'Arrange a confidential check-in to understand feedback and support needs.'
}

def predict(indices):
    keys = MODEL['features']
    recs = [ACTIONS[k] for k in sorted(indices, key=indices.get) if indices[k] < 65][:3]
    if not recs:
        recs = ['Maintain progress and set an optional advanced learning or career goal.']
    if any(k not in indices for k in keys):
        return {'academic': None, 'placement': None, 'drivers': [],
                'recommendations': ['Complete missing records before interpreting AI estimates.'] + recs}
    x = [indices[k] / 100 for k in keys]
    estimates, contributions = {}, [0.] * len(keys)
    for name, model in MODEL['models'].items():
        z = model['intercept'] + sum(w*v for w,v in zip(model['coefficients'],x))
        estimates[name] = round(100 / (1 + math.exp(-max(-40, min(40,z)))), 1)
        # Positive log-odds contribution relative to the synthetic training mean.
        for i, (w,v,mean) in enumerate(zip(model['coefficients'],x,MODEL['feature_means'])):
            contributions[i] += max(0, w*(v-mean))
    drivers = [keys[i] for i in sorted(range(len(keys)),key=lambda i:-contributions[i]) if contributions[i] > 0][:3]
    return dict(estimates, drivers=drivers, recommendations=recs)
