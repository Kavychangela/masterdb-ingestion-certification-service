
class ProvenanceValidator:
    @staticmethod
    def validate(meta):
        fields=['source','owner','license','version','lineage','transformation_log']
        miss=[f for f in fields if not meta.get(f)]
        return {'score':round(((len(fields)-len(miss))/len(fields))*100,2),'missing_fields':miss}
