import os
import json
import yaml

class checkpoint():

    def get_checkpoint(self):
        with open('sp_workplacesearch.config.yaml', 'r') as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)

        start_time = data['start_time']
        end_time = data['end_time']

        checkpoint_path = "/path/to/file"
        if os.path.exists(checkpoint_path) and os.path.getsize(checkpoint_path) > 0:
            with open('checkpoint.json', 'r') as f:
                checkpoint = json.loads(f)
        else:
            checkpoint = {start_time: data['start_time'],end_time: data['end_time']}

        start_time= checkpoint['start_time']
        end_time = checkpoint['end_time']

        if start_time and not end_time:
            query="?$filter=Created ge datetime {start_time}"
        elif not start_time and end_time:
            query="?$filter=Created le datetime {end_time}"
        elif start_time and end_time:
            query="?$filter= (Created ge datetime {start_time}) and (Created le datetime {end_time})"
        else:
            query = "?"
        
        return query

    def set_checkpoint(self,current):
        with open('checkpoint.json', 'w') as fp:
                json.dump(current, fp,indent=4)