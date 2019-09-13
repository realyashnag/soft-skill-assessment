import pandas as pd

class Compare:
    PROGRAM_KU = {
        'LEGEND'            : 'Knowledge Units associated with Tasks',
        'TOTAL_KU'          : 10,
        'TASK_LABELS'       : ['A', 'B', 'C', 'D'],
        'TASK_KU'           : [2, 1, 3 , 1],
        'KU_PER_TASK'       : [['A', 2],
                               ['B', 1],
                               ['C', 3],
                               ['D', 1]],
    }

    KU_DISTRIBUTION = {
        'LEGEND'            : 'Knowledge Units',
        'TOTAL_KU'          : 10,
        'TASKS_UNIQUE_KU'   : 6,
    }


    def __init__(self, main_sheet=None, reference_sheet=None):
        if (main_sheet is None or reference_sheet is None):
            raise ("Main Sheet or Reference Sheet is not passed.")

        tasks_ku = self.getTaskKUs(main_sheet)
        total_ku = self.getTotalKUs(reference_sheet)
        self.updateVariables(tasks_ku, total_ku)


    def updateVariables(self, tasks_ku, total_ku):
        # PROGRAM_KU
        TOTAL_KU        = total_ku.shape[0]
        TASK_LABELS     = [x for x in tasks_ku]
        TASK_KU         = [tasks_ku[x].shape[0] for x in tasks_ku]
        KU_PER_TASK     = [[TASK_LABELS[i], TASK_KU[i]] for i in range(len(TASK_LABELS))]

        self.PROGRAM_KU['TOTAL_KU'] = TOTAL_KU
        self.PROGRAM_KU['TASK_LABELS'] = TASK_LABELS
        self.PROGRAM_KU['TASK_KU'] = TASK_KU
        self.PROGRAM_KU['KU_PER_TASK'] = KU_PER_TASK

        # KU_DISTRIBUTION
        TOTAL_KU        = total_ku.shape[0]
        TASKS_UNIQUE_KU = pd.concat([tasks_ku[i][['Knowledge Area (KA)', 'Knowledge Unit (KU)']] for i in tasks_ku], axis=0).drop_duplicates().shape[0]

        self.KU_DISTRIBUTION['TOTAL_KU']    = TOTAL_KU
        self.KU_DISTRIBUTION['TASKS_UNIQUE_KU'] = TASKS_UNIQUE_KU


    def getTaskKUs(self, df):
        common = df[df['Task'] == 'common'].drop_duplicates(subset=['Knowledge Area (KA)', 'KA Subset', 'Knowledge Unit (KU)'])
        tasks = {}

        # Clean Data
        for x in df['Task'].unique():
            if (x != 'common' and x.strip() != ''):
                task = df[df['Task'] == str(x)].drop_duplicates(subset=['Knowledge Area (KA)', 'KA Subset', 'Knowledge Unit (KU)']).dropna(subset=['Knowledge Area (KA)', 'KA Subset', 'Knowledge Unit (KU)'])

                com = common.copy()
                com['Task'] = x
                if not df.empty:
                    task = pd.concat([task, com], axis=0)
                    tasks.update({x: task})
                else:
                    tasks.update({x: com})
        return tasks


    def getTotalKUs(self, df):
        stop = df[df['KA'] == 'Non-Programming / Illustration KUs'].index[0]    # After these, there are Non-Programming / Illustrative KUs Only
        total_ku = df.iloc[0:stop,:].dropna().drop_duplicates(subset=['KU', 'Learning Outcome'])
        return total_ku
