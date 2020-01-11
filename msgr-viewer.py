# to format jsons:
# (jq -n "[inputs | .messages] | add" *.json ) >> output_file

import json
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sys
import datetime as dt
import argparse
import pytz
import math

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

    msgs["nmsgs"] = msgs["content"].apply(lambda x : 1)

    # ncharacters
    if "content" in msgs.columns.values:
        msgs["nchars"] = msgs["content"].apply(lambda x : 0 if x is None else len(x))

    # n words
    def nwords(x):
        if x is not None:
            return x.count(' ') + x.count('\n') + x.count('\t') \
                    - x.count('  ') - x.count('\n\n') - x.count('\t\t') \
                    + 1
        else:
            return 0
    if "content" in msgs.columns.values:
        msgs["nwords"] = msgs["content"].apply(nwords)

    # date
    def cst(x, fm):
        date = dt.datetime.fromtimestamp(x)
        final = date.astimezone(pytz.timezone('US/Central'))
        return final.strftime(fm)
        
    msgs["timestamp_ms"] = msgs["timestamp_ms"].astype(float)
    msgs["year"]  = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%Y'))
    msgs["month"] = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%m'))
    msgs["day"]   = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%d'))

    # time
    msgs["hour"]   = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%H'))
    msgs["minute"] = msgs["timestamp_ms"].apply(lambda x : cst(x/1000.0, '%M'))

    # week id
    def weekid(x):
        today = dt.datetime.fromtimestamp(x/1000.0).date()
        epoch = dt.date(1980, 1, 6)
        epochMonday = epoch - dt.timedelta(epoch.weekday())
        todayMonday = today - dt.timedelta(today.weekday())
        return (todayMonday - epochMonday).days / 7
    msgs["weekid"] = msgs["timestamp_ms"].apply(weekid).astype(int)
    msgs["weekid"] -= np.min(msgs["weekid"])

    # month id and date id
    msgs["monthid"] = msgs["year"].astype(str) + msgs["month"].astype(str)
    msgs["dateid"] = msgs["monthid"].astype(str) + msgs["day"].astype(str)

    return msgs

def xticks(x):
    maxlen = len(str(x[-1]))
    if maxlen < 3: 
        nmax = 25
    elif maxlen < 5:
        nmax = 15
    elif maxlen < 6:
        nmax = 10
    else:
        nmax = 5
        
    if len(x) < nmax:
        return x
    else:
        spacing = int((len(x)/nmax)+.5)
        return x[::spacing]

# I'm sure pandas has a way of dealing with this but idk what it is so here
def add_full(full, x, y):
    for i in range(len(full)):
        if full[i] not in x:
            x=np.insert(x, i, full[i])
            y=np.insert(y, i, 0)

    return x, y

def plot_graph(names, msgs, ax, timediff, colname):
    full_data = np.unique(msgs[timediff])

    grouped = msgs.groupby([timediff, "sender_name"], as_index=False)[colname].sum()

    for n in names:
        person = grouped[grouped["sender_name"] == n]
        k, nmsgs = np.array(person[timediff]), np.array(person[colname])
        _, nmsgs = add_full(full_data, k, nmsgs)
        ax.plot(full_data, nmsgs, linewidth=2.5, label=n, marker='o')
    
    # visual pretty things
    ax.legend()   
    ax.set_xticks(xticks(full_data))

def plot_percent(names, msgs, ax, timediff, colname):
    full_data = np.unique(msgs[timediff])
    nwords = []

    grouped = msgs.groupby([timediff, "sender_name"], as_index=False)[colname].sum()

    for n in names:
        person = grouped[grouped["sender_name"] == n]
        k, nwrd = np.array(person[timediff]), np.array(person[colname])
        _, nwrd = add_full(full_data, k, nwrd)
        nwords.append(nwrd)

    nwords = np.array(nwords)
    totals = nwords.sum(axis=0)
    nwords = np.divide(nwords, totals)

    for i in range(len(names)):
        ax.bar(full_data, nwords[i:, :].sum(axis=0), label=names[i])

    ax.set_xticks(xticks(full_data))

def plot_difference(names, msgs, ax, timediff, colname):
    full_data = np.unique(msgs[timediff])
    ncompare = []

    grouped = msgs.groupby([timediff, "sender_name"], as_index=False)[colname].sum()

    for name in names:
        person = grouped[grouped["sender_name"] == name]
        k, n = np.array(person[timediff]), np.array(person[colname])
        _, n = add_full(full_data, k, n)
        ncompare.append(n)

    difference = np.divide(ncompare[0]-ncompare[1], (ncompare[0]+ncompare[1])/2) * 100
    df = pd.DataFrame(np.vstack((difference, difference < 0)).T, columns=["vals", "colors"])
    ax.bar(full_data, np.abs(df["vals"]), color=df.colors.map({True:(255/255., 125/255., 46/255.), False:(40/255., 116/255., 176/255.)}))
    ax.set_xticks(xticks(full_data))

def get_names(msgs):
    names = np.unique(msgs['sender_name'])

    # rearrange so I always get the same color (bc this is for me)
    myindex = np.where(names == "Ananya Yammanuru")[0][0]
    names[0], names[myindex] = names[myindex], names[0]
    print("People in this conversation:", names)

    return names

def plot_line(names, msgs, ax, colnum, datacol, axisstr, small=False):
    plot_graph(names, msgs, ax[0, colnum], "hour", datacol)
    ax[0, colnum].set_title(axisstr + " by hour")
    ax[0, colnum].set_xlabel("Hour")
    ax[0, colnum].set_ylabel(axisstr)
    
    plot_graph(names, msgs, ax[1, colnum], "weekid", datacol)
    ax[1, colnum].set_title(axisstr + " by week")
    ax[1, colnum].set_xlabel("Week")
    ax[1, colnum].set_ylabel(axisstr)
    
    if not small:
        plot_graph(names, msgs, ax[2, colnum], "monthid", datacol)
        ax[2, colnum].set_title(axisstr + " by month")
        ax[2, colnum].set_xlabel("Month")
        ax[2, colnum].set_ylabel(axisstr)
    else:
        plot_graph(names, msgs, ax[2, colnum], "dateid", datacol)
        ax[2, colnum].set_title(axisstr + " by day")
        ax[2, colnum].set_xlabel("day")
        ax[2, colnum].set_ylabel(axisstr)
    

def plot_stacked_bar(names, msgs, ax, colnum, datacol, axisstr, small=False):
    plot_percent(names, msgs, ax[0, colnum], "hour", datacol)
    ax[0, colnum].set_xlabel("Hour")
    ax[0, colnum].set_title(axisstr + " by hour")
    ax[0, colnum].set_ylabel(axisstr)

    plot_percent(names, msgs, ax[1, colnum], "weekid", datacol)
    ax[1, colnum].set_xlabel("Week")
    ax[1, colnum].set_title(axisstr + " by week")
    ax[1, colnum].set_ylabel(axisstr)

    if not small:
        plot_percent(names, msgs, ax[2, colnum], "monthid", datacol)
        ax[2, colnum].set_xlabel("Month")
        ax[2, colnum].set_title(axisstr + " by month")
        ax[2, colnum].set_ylabel(axisstr)
    else:
        plot_percent(names, msgs, ax[2, colnum], "dateid", datacol)
        ax[2, colnum].set_xlabel("Day")
        ax[2, colnum].set_title(axisstr + " by day")
        ax[2, colnum].set_ylabel(axisstr)

def plot_diff_graphs(names, msgs, ax, colnum, datacol, axisstr, small=False):
    yaxis = axisstr.split()[0]

    plot_difference(names, msgs, ax[0, colnum], "hour", datacol)
    ax[0, colnum].set_xlabel("Hour")
    ax[0, colnum].set_title(axisstr + " by hour")
    ax[0, colnum].set_ylabel(yaxis)

    plot_difference(names, msgs, ax[1, colnum], "weekid", datacol)
    ax[1, colnum].set_xlabel("Week")
    ax[1, colnum].set_title(axisstr + " by week")
    ax[1, colnum].set_ylabel(yaxis)

    if not small:
        plot_difference(names, msgs, ax[2, colnum], "monthid", datacol)
        ax[2, colnum].set_xlabel("Month")
        ax[2, colnum].set_title(axisstr + " by month")
        ax[2, colnum].set_ylabel(yaxis)
    else:
        plot_difference(names, msgs, ax[2, colnum], "dateid", datacol)
        ax[2, colnum].set_xlabel("Day")
        ax[2, colnum].set_title(axisstr + " by day")
        ax[2, colnum].set_ylabel(yaxis)
    

def main(args):
    msgs = get_messages(args.jsonfile)
    msgs = add_cols(msgs)

    msgs = msgs.sort_values(by='timestamp_ms')
    
    names = get_names(msgs)
    small = True if len(np.unique(msgs['monthid'])) < 12 else False

    f, ax = plt.subplots(nrows=3, ncols=4, figsize=(40, 20))

    plot_line(names, msgs, ax, 0, "nmsgs", "Number of messages", small)
    plot_line(names, msgs, ax, 3, "nwords", "Number of words", small)

    if len(names) == 2:
        plot_diff_graphs(names, msgs, ax, 1, "nmsgs", "Percent difference of messages", small)
        plot_diff_graphs(names, msgs, ax, 2, "nwords", "Percent difference of words", small)
    else:
        plot_stacked_bar(names, msgs, ax, 1, "nmsgs", "Percent of messages", small)
        plot_stacked_bar(names, msgs, ax, 2, "nwords", "Percent of words", small)
        
    # save
    if args.output is not None:
        print("Saving in:", args.output)
        plt.savefig(args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # -f JSON FILE -n PERSON'S NAME -o OUTPUT FILE
    parser.add_argument("-f", "--jsonfile", help="JSON file")
    parser.add_argument("-n", "--name", help="Person's name")
    parser.add_argument("-o", "--output", help="Output file")
    main(parser.parse_args())
