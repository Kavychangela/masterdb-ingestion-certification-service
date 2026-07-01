
class ClassificationEngine:
    @staticmethod
    def classify(score,rules):
        t=rules['classification_thresholds']
        if score>=t['trusted']: return 'Trusted'
        if score>=t['reliable']: return 'Reliable'
        if score>=t['review_required']: return 'Review Required'
        return 'High Risk'
