
class DuplicateValidator:
    @staticmethod
    def validate(df):
        d=int(df.duplicated().sum())
        p=round((d/len(df))*100,2) if len(df) else 0
        return {'score':max(0,100-p),'duplicate_rows':d,'duplicate_percentage':p}
