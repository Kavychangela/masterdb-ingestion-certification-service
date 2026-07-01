
class RiskEngine:
    @staticmethod
    def evaluate(results,rules):
        t=rules['risk_thresholds']; risks=[]
        if results['completeness']['score']<t['min_completeness_score']: risks.append('LOW_COMPLETENESS')
        if results['duplicates']['duplicate_percentage']>t['max_duplicate_percentage']: risks.append('HIGH_DUPLICATION')
        if results['schema']['score']<t['min_schema_score']: risks.append('SCHEMA_VIOLATION')
        if results['provenance']['score']<t['min_provenance_score']: risks.append('PROVENANCE_GAP')
        if results['metadata']['score']<t['min_metadata_score']: risks.append('METADATA_GAP')
        if results['integrity']['violations']: risks.append('INTEGRITY_BOUNDARY_VIOLATION')
        return risks
