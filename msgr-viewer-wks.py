# to format jsons:
# (jq -n "[inputs | .messages] | add" *.json ) >> output_file

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sys
import time
import argparse

ms_day = 1000*60*60*24
ms_per_wk = ms_day

parser = argparse.ArgumentParser()
#-f JSON FILE -n PERSON'S NAME -o OUTPUT FILE
parser.add_argument("-f", "--jsonfile", help="JSON file")
parser.add_argument("-n", "--name", help="Person's name")
parser.add_argument("-o", "--output", help="Output file")

args = parser.parse_args()

filename = args.jsonfile


# In[22]:


plt.rcParams['figure.figsize'] = [15, 5]

with open(filename, 'r') as messagefile:
    data = messagefile.read()

obj = json.loads(data)

names = []
msgs = pd.DataFrame(columns=['name', 'time-ms', 'time-wk', 'year-mo', 'date'])
# for person in obj['participants']:
#     names.append(person['name'])

xlabels = []
    
for msg in obj:
    name = msg['sender_name']
    ms = float(msg['timestamp_ms'])
    t = int(ms/ms_per_wk)
    date = time.strftime('%Y-%m-%d', time.gmtime(ms/1000.0))
    ymo = time.strftime('%Y-%m', time.gmtime(ms/1000.0))
    
    msgs.loc[msgs.shape[0]] = [name] + [ms] + [t] + [ymo] + [date]
    
    xlabel = time.strftime('%Y-%m', time.gmtime(ms/1000.0))
    if xlabel not in xlabels:
        xlabels.append(xlabel)
        
    if (msgs.shape[0] % 1000 == 0):
        print(msgs.shape[0], "messages processed!")

msgs = msgs.sort_values(by='time-ms')

names = np.unique(msgs['name'])

# rearrange so I always get the same color (bc this is for me)
myindex = np.where(names == "Ananya Yammanuru")[0][0]
names[0], names[myindex] = names[myindex], names[0]

print("People in this conversation:", names)

t = np.unique(msgs['year-mo'])

ax = plt.figure().add_subplot(111)
for n in names:
    person = msgs[msgs['name'] == n].copy()
    #k = person['year-mo'].value_counts()
    k, nmsgs = np.unique(person['time-wk'], return_counts=True)
    #missing = np.setdiff1d(t, k)
    #for m in missing:
    #    k=np.array(list(k).append(m))
    #    nmsgs=np.array(list(nmsgs).append(0))
    ax.plot(k, nmsgs, linewidth=3, label=n, marker='o')
    #ax.plot(k, linewidth=3, label=n)

# the following is rlly dumb
# but index goes out of bounds if i do it the smart way
nlabels = len(ax.xaxis.get_ticklabels())
for label in ax.xaxis.get_ticklabels()[::2]:
    label.set_visible(False)
for label in ax.xaxis.get_ticklabels()[::3]:
    label.set_visible(False)
for label in ax.xaxis.get_ticklabels()[::5]:
    label.set_visible(False)
    
plt.xlabel("Date")
ax.legend()
plt.ylabel("Number of Messages")
plt.title("Messages with " + args.name)
    
if args.output is not None:
    print("Saving in:", args.output)
    plt.savefig(args.output)


# In[ ]:




