from __future__ import print_function
import scipy
from scipy.signal import argrelextrema
import matplotlib.pyplot as plt
import numpy as np
from os import getcwd

# relative_path_to_file = '../data/Corilateme/source'
relative_path_to_file = '../misc/data/matched_filter'

Verbose=False

adc_rate = (2 * 10 ** 6)
decim = 5  # decimation of matched filter
samp_rate =  adc_rate/ decim  # Samples per second
if Verbose:
    print("Sample rate is %i = %i/%i = ADC Rate/Decim"% (samp_rate,adc_rate,decim))

half_symbol_length = int(round(12.5 * 10 ** -6 * samp_rate))
if Verbose:
    print("Half symbol length is %i"% half_symbol_length)

# Reduce computation by specifying a range to look at
first_sample = 0
last_sample = 20000
#verbose = False #Unused. Can be helpful for debugging rn16s



##### This is a terrible way of counting RN16s.
##### Based on the fact the tag signal is of similar amplitude and opposite phase to the reader
##### IN THIS PARTICULAR SETUP.
##### Likely will not work for many other setups. Only used since correlation of multisine data is hard.

def count_rn16s_filter(numpyarray,plot=False):
    """Find the preamble of RN16 using cross-correlation"""
    # TODO downsample for speed, if reliable enough.

    peak_locations = argrelextrema(numpyarray, np.greater)[0]
    #Filter the peaks >30. Noise generally around 24. True signal generally around 42.
    peak_locations = peak_locations[numpyarray[peak_locations] > 0.8]


    #Remove peaks that are too close together.
    #Subtract list from one offset by 1 to give distances between the peaks.
    distance_between_peaks = peak_locations[1:]-peak_locations[:-1]
    #Find where distance <60. Returns [False,False,True,..]
    to_remove = distance_between_peaks<1500
    #Add a "Do not remove" to last peak. 
    #Needed since distance between peaks list is one shorter than filtered_peak_locations list.
    to_remove= np.append(to_remove,[False])
    #np.where(to_remove) #Which samples will be removed. Good for debug.
    #Delete peaks that are too close toegther.
    filtered_peak_locations = np.delete(peak_locations, np.where(to_remove))

    if plot:
        #Find y points for plotting
        y =  [numpyarray[x] for x in filtered_peak_locations]
        plt.plot(filtered_peak_locations,y,'rs')

    print("Counted %i RN16s"%len(filtered_peak_locations),end='')
    return len(filtered_peak_locations)


def count(plot=False): #Use plot to allow calling from other (supervisor) functions
    # File operations
    f = scipy.fromfile(open(getcwd() + '/' + relative_path_to_file), dtype=scipy.float32)
    if Verbose:    
        print("Number of datapoints is: %i"% f.size)

    #f = f[first_sample:last_sample]
    abs_f = abs(f[0::2] + 1j * f[1::2])
    try:
        abs_f = abs_f / np.amax(abs_f)
    except Exception as e:
        print("Error when normalising: \"%s\" "%e)
        return 0        
    # Matched filter to reduce hf noise
    abs_f = scipy.signal.correlate(abs_f, np.ones(decim), mode='same') / decim


    #Remove dc
    to_remove = abs_f < 0.25
    abs_f = np.delete(abs_f, np.where(to_remove))

    mean = np.mean(abs_f)
    if mean<0.7:
        print("Mean value is %0.4f <0.7 so reads present: "%mean,end='')
        count_rn16 = count_rn16s_filter(abs_f,plot)
    else:
        print("Mean value is %0.4f >0.7 so no reads present"%mean,end='')
        return 0

    if plot:
#        plt.plot(abs_f)
        plt.plot(abs_f)   
        plt.show()
    return count_rn16

if __name__=='__main__':
    count(plot=True)
