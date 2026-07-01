
class SchemaValidator:
    @staticmethod
    def validate(df,schema):
        score=100; details=[]
        for c,t in schema['columns'].items():
            if c not in df.columns:
                score-=20; details.append({'column':c,'status':'MISSING'}); continue
            actual=str(df[c].dtype)
            status='PASS' if SchemaValidator._matches_dtype(actual,t) else 'TYPE_MISMATCH'
            if status!='PASS': score-=10
            details.append({'column':c,'expected':t,'actual':actual,'status':status})
        return {'score':max(score,0),'details':details}

    @staticmethod
    def _matches_dtype(actual, expected):
        string_types={'object','str','string'}
        if actual in string_types and expected in string_types:
            return True
        return actual==expected
