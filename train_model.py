"""Reproduce the synthetic demonstration models. Not a real-world validation."""
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.model_selection import train_test_split

rng = np.random.default_rng(2026)
X = rng.uniform(.15, 1, (4000, 7))
features = ['acad','att','lms','plc','skl','eng','fb']
coefficients = {'academic': [-4.5,-3,-1.4,-.3,-.5,-.6,-.5],
                'placement': [-1,-.5,-.7,-4,-3,-1,-.4]}
result = {'training_source':'Synthetic educational demonstration; no real outcomes used',
          'features':features,'sample_count':len(X),'feature_means':X.mean(axis=0).tolist(),'models':{}}
for name, coeff in coefficients.items():
    probabilities = 1/(1+np.exp(-(6 + X @ np.array(coeff))))
    y = rng.binomial(1, probabilities)
    train, test = train_test_split(np.arange(len(X)),test_size=.25,random_state=2026,stratify=y)
    model = LogisticRegression(C=2,max_iter=500).fit(X[train],y[train])
    pred=model.predict_proba(X[test])[:,1]
    result['models'][name]={'coefficients':model.coef_[0].tolist(),'intercept':float(model.intercept_[0]),
                           'synthetic_test_auc':round(roc_auc_score(y[test],pred),4),
                           'synthetic_test_accuracy':round(accuracy_score(y[test],pred>=.5),4)}
p=Path(__file__).parent/'models';p.mkdir(exist_ok=True)
(p/'risk_model.json').write_text(json.dumps(result,indent=2))
print('Saved model trained on 3,000 synthetic rows and evaluated on 1,000 held-out synthetic rows.')
