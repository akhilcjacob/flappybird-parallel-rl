import json
import os
from multiprocessing import Queue, Lock
import time
from Plotting_Service import plotting_service
from multiprocessing import Manager
import multiprocessing

class Q_Table_Processor:
    def __init__(self, agents, file_save_rate=20):
        self.agents = agents
        self.total_n = sum(range(0, agents))
        self.master_q = {}
        self.output_file_loc = "./models/master.json"
        # self.manager = Manager()
        self._import_q_table()
        self.best_run = 0
        self.best_score = 0
        self.update = multiprocessing.Value('i',0)
        self.file_save_rate = file_save_rate
        # self.q = []
        self.q = Queue()
        self.run_server_on = True
        self.lock = Lock()
        self.plotter = plotting_service()
        self.hist = []
        self.max_states=0
        self.lock2 = Lock()


    def _import_q_table(self):
        if os.path.exists(self.output_file_loc):
            with open(self.output_file_loc) as json_file:
                print("Importing previous datafile")
                # self.master_q = self.manager.dict(json.load(json_file))
                self.master_q = json.load(json_file)
        else:
            print("Initializing new datafile")
            self.master_q = {'0_0_0': [0, 0]}

    def _export_q_table(self):
        f = open(self.output_file_loc, "w")
        f.write(json.dumps(self.master_q))
        f.close()

    def kill_server(self):
        self.run_server_on = False

    def run_server(self):
        try:
            while self.run_server_on:
                new_table, distance, score = self.q.get()
                # print(self.update.value,  'is the real update num')
                self.hist.append([new_table, distance, score])
                self.max_states =max([self.max_states,len(new_table),len(self.master_q)])
                self.plotter.add_row([self.update.value, distance, score, self.max_states])
                if self.update.value % self.file_save_rate:
                    self._export_q_table()
                    self.plotter.to_file()
                
                self.lock.acquire()
                new_tables = [h[0] for h in self.hist]
                new_tables.append(self.master_q)
                distances = [h[1] for h in self.hist]
                distances.append(self.best_run)
                scores = [h[2] for h in self.hist]
                scores.append(self.best_score)
                weights = [d**2 for d in distances]
                # weights = [w*((s+1)**2) for w, s in zip(weights, scores)]
                weights = [float(i)/max(weights) for i in weights]
                
                final_table = {}
                for tab in range(len(new_tables)):
                    table = new_tables[tab]
                    for k,v in table.items():
                        if k in final_table:
                            
                            final_table[k] = [
                                int((1-0.25)*final_table[k][0] + (0.25)*v[0]),
                                int((1-0.25)*final_table[k][1] + (0.25)*v[1])
                            ]
                        else:
                            final_table[k] = v
                        # else:
                        #     final_table[k] = [0,0]
                            # print(final_table[k])
                self.master_q = final_table.copy()
                with self.update.get_lock():
                    self.update.value += 1
                self.lock.release()

                if len(self.hist) < self.agents:
                    continue

                self.hist.remove(self.hist[0])
                # print(self.hist)


                # print(len(self.hist),self.agents)
                # if len(self.hist) > self.agents/2:
                #     # new_table, distance, score
                #     print("hserre")
                #     new_tables = [h[0] for h in self.hist]
                #     new_tables.append(self.master_q)
                #     distances = [h[1] for h in self.hist]
                #     distances.append(self.best_run)
                #     scores = [h[2] for h in self.hist]
                #     scores.append(self.best_score)
                #     weights = [d**4 for d in distances]

                #     # Normalize the weights
                   
                #     # self.master_q = self.merge_tables(self.master_q, new_table, distance, self.best_run)
                    
                #     if distance > self.best_run:
                #         self.best_run = max(distances)
                #         self.best_score = max(scores)
                #     self.hist = []

               
                # print(self.best_run)
                # self.update_line([self.update,score])

        except KeyboardInterrupt:
            print('Exiting Server')
            # for new_table, score in self.q.get():
                # print("recd new score")
                
                # self.master_q = self.merge_tables(self.master_q, new_table, score - self.best_run)
                # if score > self.best_run:
                #     self.best_run = score
                # self.update += 1

                # if self.update % self.file_save_rate:
                #     self._export_q_table()
                # self.q = []

    def process_table(self, q_table, distance, score):
        update_num = 0
        self.lock.acquire()
        self.q.put([q_table, distance, score])
        update_num = self.update.value
        self.lock.release()
        return update_num

    def get_table(self, prev_update):
        # with self.lock2:
        while prev_update == self.update.value: 
            # print('this is the update', self.update.value)
            time.sleep(0.01)
        with self.lock:
            return self.master_q
        # self.master_q = self.merge_tables(self.master_q, q_table, score > self.best_run)






    def merge_tables(self, primary_q, secondary_q, dist,best_run):
        better = dist-best_run > 0
        weights = [1, 1]
        primary_q = primary_q.copy()
        if better:
            weights = weights[::-1]
            # weights[1] *=diff
        # combined_q = {'0_0_0':[0,0]}
        for key, value in secondary_q.items():
            if key in primary_q:
                for action in [0, 1]:
                    previous_mem = weights[0]*primary_q[key][action]*best_run
                    new_memory = weights[1]*secondary_q[key][action]*dist
                    # prim[key] = [0,0]
                    
                    # if previous_mem + new_memory > 0:
                    primary_q[key][action] = previous_mem+new_memory
            else:
                primary_q[key] = value
        return primary_q