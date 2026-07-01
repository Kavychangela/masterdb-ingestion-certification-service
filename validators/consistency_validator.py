
class ConsistencyValidator:
    @staticmethod
    def validate(df):
        issues=[]
        for c in df.columns:
            if df[c].isnull().all(): issues.append(c)
        return {'score':max(0,100-len(issues)*10),'issues':issues}
