# to format jsons:
# (jq -n "[inputs | .messages] | add" *.json ) >> output_file

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sys
from datetime import datetime
import argparse
import pytz
import math

ms_day = 86400000
ms_per_wk = ms_day# * 7

# plt.rcParams['figure.figsize'] = [15, 5]
# nlabels = len(ax.xaxis.get_ticklabels())

def get_messages(filename):
    with open(filename, 'r') as messagefile:
        data = messagefile.read()

    obj = json.loads(data)
    return pd.io.json.json_normalize(obj)

def add_cols(msgs):
    # set NaNs to None
    def makenone(x):
        if isinstance(x, float) and math.isnan(x):
            return None
        return x
    msgs = msgs.apply(lambda x: x.apply(makenone))

    # ncharacters
    msgs["nchars"] = msgs["content"].apply(lambda x : 0 if x is None else len(x))

    # n words
    def nwords(x):
        if x is not None:
            return x.count(' ') + x.count('\n') + x.count('\t') \
                    - x.count('  ') - x.count('\n\n') - x.count('\t\t') \
                    + 1
        else:
            return 0
    msgs["nwords"] = msgs["content"].apply(nwords)

    # date
    def cst(x, fm):
        dt = datetime.fromtimestamp(x)
        final = dt.astimezone(pytz.timezone('US/Central'))
        return final.strftime(fm)
        
    msgs["year"]  = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%Y'))
    msgs["month"] = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%m'))
    msgs["day"]   = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%d'))

    # time
    msgs["hour"]   = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%H'))
    msgs["minute"] = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%M'))

    return msgs

def plot_hrs(names, msgs, ax):
    for n in names:
        person = msgs[msgs["sender_name"] == n].sort_values(by="hour")
        k, nmsgs = np.unique(person["hour"], return_counts=True)
        ax.plot(k, nmsgs, linewidth=2.5, label=n, marker='o')
    
    # visual pretty things
    ax.legend()

def get_names(msgs):
    names = np.unique(msgs['sender_name'])

    # rearrange so I always get the same color (bc this is for me)
    myindex = np.where(names == "Ananya Yammanuru")[0][0]
    names[0], names[myindex] = names[myindex], names[0]
    print("People in this conversation:", names)

    return names

def main(args):
    msgs = get_messages(args.jsonfile)
    msgs = add_cols(msgs)

    msgs = msgs.sort_values(by='timestamp_ms')
    
    names = get_names(msgs)

    f, ax = plt.subplots(nrows=1, ncols=1)
    plot_hrs(names, msgs, ax)

    plt.xlabel("Date")
    ax.legend()
    plt.ylabel("Number of Messages")
    plt.title("Messages with " + args.name)

    if args.output is not None:
        print("Saving in:", args.output)
        plt.savefig(args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    #-f JSON FILE -n PERSON'S NAME -o OUTPUT FILE
    parser.add_argument("-f", "--jsonfile", help="JSON file")
    parser.add_argument("-n", "--name", help="Person's name")
    parser.add_argument("-o", "--output", help="Output file")
    main(parser.parse_args())
