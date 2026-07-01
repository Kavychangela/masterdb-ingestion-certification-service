
class RecommendationEngine:
    @staticmethod
    def generate(results):
        rec=[]
        if results['duplicates']['duplicate_rows']>0: rec.append('Remove duplicate records')
        if results['integrity']['violations']: rec.append('Fix integrity boundary violations')
        if results['completeness']['score']<100: rec.append('Handle missing values')
        return rec
