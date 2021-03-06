# This import registers the 3D projection, but is otherwise unused.
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 unused import

import matplotlib.pyplot as plt
import numpy as np
import csv


def correct_tx1(power):
    return float(power)*0.9791000266-24.98921646
def correct_tx2(power):
    return float(power)*0.9668768473-25.34882759
def total_power(p1,p2):
    return 10*np.log10((10**-3*10**(p1/10.0)+10**-3*10**(p2/10.0))/10**-3)

#print(10**-3*10**(5/10))
print(total_power(correct_tx1(5),correct_tx2(7)))

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

with open('dataoutput.csv') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    num_repeats=len(headers[4:])
    print("NUmber of repeats is",num_repeats)
    for row in reader:
        print(row)
        avg_rn16 = sum([int(a) for a in filter(None,  row[4:])])/len(filter(None, row[4:]))
        print("avg rn16 is ",avg_rn16)
        ax.scatter(total_power(correct_tx1(float(row[2])),correct_tx2(float(row[3]))),
                   abs(float(row[1])-float(row[0])),avg_rn16, c='r', marker='o')
        pass

ax.set_xlabel('Power at tag')
ax.set_ylabel('Frequency Separation')
ax.set_zlabel('Number of RN16 reads')

plt.show()
