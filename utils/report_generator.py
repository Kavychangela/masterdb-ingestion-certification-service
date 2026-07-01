
import json, os
class ReportGenerator:
    @staticmethod
    def save(report,path):
        os.makedirs(os.path.dirname(path),exist_ok=True)
        with open(path,'w',encoding='utf-8') as f:
            json.dump(report,f,indent=4)
