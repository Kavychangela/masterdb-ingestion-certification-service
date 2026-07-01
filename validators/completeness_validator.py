
class CompletenessValidator:
    @staticmethod
    def validate(df):
        total=df.size
        missing=int(df.isnull().sum().sum())
        score=round(((total-missing)/total)*100,2) if total else 0
        return {'score':score,'missing_cells':missing}
