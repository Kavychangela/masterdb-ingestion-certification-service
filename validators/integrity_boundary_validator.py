
class IntegrityBoundaryValidator:
    @staticmethod
    def validate(df,rules):
        violations=[]
        for col,lim in rules.get('integrity_boundaries',{}).items():
            if col in df.columns:
                cnt=int(((df[col] < lim['min']) | (df[col] > lim['max'])).sum())
                if cnt: violations.append({'column':col,'violations':cnt})
        return {'score':max(0,100-len(violations)*20),'violations':violations}
