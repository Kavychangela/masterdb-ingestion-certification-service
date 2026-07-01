
class ScoringEngine:
    @staticmethod
    def calculate(results,rules):
        total=0
        for k,w in rules['weights'].items():
            if k in results: total += results[k]['score']*w
        return round(total/100,2)
