#Developed by: Nikos Kargas 

from gnuradio import gr
from gnuradio import uhd
from gnuradio import blocks
from gnuradio import filter
from gnuradio import analog
from gnuradio import digital
from gnuradio import qtgui
from gnuradio.filter import firdes
import rfid

DEBUG = False

class reader_top_block(gr.top_block):

  # Configure usrp source
  def u_source(self):
    self.source = uhd.usrp_source(
    device_addr=self.usrp_address_source,
    stream_args=uhd.stream_args(
    cpu_format="fc32",
    channels=range(1),
    ),
    )
    self.source.set_samp_rate(self.adc_rate)
    self.source.set_center_freq(self.rx_freq, 0)
    self.source.set_gain(self.rx_gain, 0)
    self.source.set_antenna("RX2", 0)
    self.source.set_auto_dc_offset(False) # Uncomment this line for SBX daughterboard

  # Configure usrp sink
  def u_sink(self):
    self.sink = uhd.usrp_sink(
    device_addr=self.usrp_address_sink,
    stream_args=uhd.stream_args(
    cpu_format="fc32",
    channels=range(1),
    ),
    )
    self.sink.set_samp_rate(self.dac_rate)
    self.sink.set_center_freq(self.tx_freq, 0)
    self.sink.set_gain(self.tx_gain, 0)
    self.sink.set_antenna("TX/RX", 0)
    
  def __init__(self):
    gr.top_block.__init__(self)


    rt = gr.enable_realtime_scheduling() 

    ######## Variables #########
    self.dac_rate = 10e6                 # DAC rate 
    self.adc_rate = 5e6#2000e6/50            # ADC rate (2MS/s complex samples) *
    self.decim    = 5                   # Decimation (downsampling factor)
    self.ampl     = 0.5                  # Output signal amplitude (signal power vary for different RFX900 cards)
    self.tx_freq  = 910e6                # Modulation frequency (can be set between 902-920)
    self.rx_freq  = 910e6
    self.rx_gain  = 25                 # RX Gain (gain at receiver)
    self.tx_gain  = 10                    # RFX900 no Tx gain option

    self.usrp_address_source = "addr=192.168.10.2,recv_frame_size=256"
    self.usrp_address_sink   = "addr=192.168.10.2,recv_frame_size=256"

    # Each FM0 symbol consists of ADC_RATE/BLF samples (2e6/40e3 = 50 samples)
    # 10 samples per symbol after matched filtering and decimation
    self.num_taps     = [1] * int(self.adc_rate/(40e3*self.decim)) # matched to half symbol period
    print("Half symbol length is ",int(self.adc_rate/(2*40e3*self.decim)))

    ######## File sinks for debugging (1 for each block) #########
    self.file_sink_source    = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/source", False)
    self.file_sink_gate      = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/gate", False)
    self.file_sink_decoder   = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/decoder", False)
    self.file_sink_reader    = blocks.file_sink(gr.sizeof_float*1,      "../misc/data/reader", False)
    self.file_sink           = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/file_sink", False)
    self.file_throttle       = blocks.file_sink(gr.sizeof_float*1,      "../misc/data/throttle", False) 
    self.file_amp            = blocks.file_sink(gr.sizeof_float*1,      "../misc/data/amp", False)
    self.file_sub            = blocks.file_sink(gr.sizeof_float*1,      "../misc/data/sub", False)
    self.file_multiply       = blocks.file_sink(gr.sizeof_float*1,      "../misc/data/multiply", False)
    self.file_highpass       = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/highpass", False)
    self.file_matched_filter = blocks.file_sink(gr.sizeof_gr_complex*1, "../misc/data/matchedfilter", False)

    ######## Blocks #########
    self.matched_filter = filter.fir_filter_ccc(self.decim, self.num_taps);
    self.gate           = rfid.gate(int(self.adc_rate/self.decim))
    self.tag_decoder    = rfid.tag_decoder(int(self.adc_rate/self.decim))
    self.reader         = rfid.reader(int(self.adc_rate/self.decim),int(1e6))#int(self.dac_rate))#
    #Amp Removed as can multiply by sinwave amplitude instead
    self.amp            = blocks.multiply_const_ff(self.ampl)

    #Various filter blocks to use as required
    #self.low_pass_filter = filter.fir_filter_ccf(1, firdes.low_pass(1, int(self.adc_rate/self.decim), 30000, 10000, firdes.WIN_HAMMING, 6.76))
    #self.band_pass_filter = filter.fir_filter_ccf(1, firdes.band_pass(1, self.adc_rate/self.decim, 0, 10000, 2000, firdes.WIN_HAMMING, 6.76))
    #self.band_reject_filter = filter.fir_filter_ccf(1, firdes.band_reject(1, self.adc_rate, 500, 1500, 100, firdes.WIN_HAMMING, 6.76))

    #Sinwave and multiply block for mixing
    self.analog_sig_source = analog.sig_source_f(self.dac_rate, analog.GR_COS_WAVE, 2000000, 0.8, 0.4)
    self.multiply = blocks.multiply_vff(1)

    #Upsample baseband before multiplying by the sinewave
    self.interp_fir_filter = filter.interp_fir_filter_fff(int(self.dac_rate/1e6), ([1]*50))
    self.interp_fir_filter.declare_sample_delay(20)

    self.to_complex      = blocks.float_to_complex() #Needed before UHD sink

    if (DEBUG == False) : # Real Time Execution

      # USRP blocks - source goes directly to file for offline analysis.
      self.u_source()
      self.u_sink()
      #Take source from a file to prevent underruns whilst experimenting
      self.asource  = blocks.file_source(gr.sizeof_gr_complex*1, "../misc/data/file_source_test",False)   
      

      ######## Connections #########

      # Source - HP filter - Matched filter - gate
      #self.connect(self.source,  (self.high_pass_filter, 0))
      #self.connect((self.high_pass_filter, 0),self.matched_filter)
      #self.connect(self.matched_filter, self.gate)

      # Source - Matched filter - lowpass filter - gate
      #self.connect(self.source,self.matched_filter)
      #self.connect(self.matched_filter,(self.low_pass_filter, 0))
      #self.connect((self.low_pass_filter, 0), self.gate)
      #self.connect(self.matched_filter, self.gate)

      # File source - matched_filter - gate
      self.connect(self.asource, self.matched_filter)
      self.connect(self.matched_filter, self.gate)

      # Source - matched filter - band reject filter - gate
      #self.connect(self.source,self.matched_filter)
      #self.connect(self.matched_filter,(self.band_reject_filter, 0))
      #self.connect((self.band_reject_filter, 0), self.gate)
      

      # Normal tag reader chain
      self.connect(self.gate, self.tag_decoder)
      self.connect((self.tag_decoder,0), self.reader)
      self.connect(self.reader,(self.interp_fir_filter, 0))
      
      # Optional Amp stage
      #self.connect(self.reader, self.amp)
      #self.connect(self.amp, self.to_complex)
      #self.connect(self.amp,(self.interp_fir_filter, 0))


      # Modulate with sine-wave
      self.connect((self.interp_fir_filter, 0),(self.multiply, 0))
      self.connect((self.analog_sig_source, 0), (self.multiply, 1)) 
      self.connect((self.multiply, 0), self.to_complex) 
      self.connect(self.to_complex, self.sink)
      #self.connect(self.to_complex, self.file_sink)



      # File connections
      self.connect(self.source, self.file_sink_source) # Log the real source
      #self.connect((self.low_pass_filter, 0),self.file_highpass)
      self.connect((self.matched_filter, 0),self.file_matched_filter)
      self.connect((self.multiply, 0), self.file_multiply)

    else :  # Offline Data
      self.file_source = blocks.file_source(gr.sizeof_gr_complex*1, "../misc/data/5MHz_separation",False)     ## instead of uhd.usrp_source
      self.file_sink   = blocks.file_sink(gr.sizeof_gr_complex*1,   "../misc/data/file_sink", False) ## instead of uhd.usrp_sink
 
      ######## Connections ######### 
      self.connect(self.file_source, self.matched_filter)
      self.connect(self.matched_filter, self.gate)
      self.connect(self.gate, self.tag_decoder)
      self.connect((self.tag_decoder,0), self.reader)
      self.connect(self.reader, self.amp)
      self.connect(self.amp, self.to_complex)
      self.connect(self.to_complex, self.file_sink)
    
    #File sinks for logging 
    #self.connect(self.source,self.file_sink_source)
    #self.connect(self.gate, self.file_sink_gate)
    self.connect((self.tag_decoder,1), self.file_sink_decoder) # (Do not comment this line)
    #self.connect(self.reader, self.file_sink_reader)

if __name__ == '__main__':
  import ctypes
  import sys
  if sys.platform.startswith('linux'):
    try:
      x11 = ctypes.cdll.LoadLibrary('libX11.so')
      x11.XInitThreads()
    except:
        print "Warning: failed to XInitThreads()"

  main_block = reader_top_block()
  main_block.start()

  while(1):
    inp = raw_input("'Q' to quit \n")
    if (inp == "q" or inp == "Q"):
      break

  main_block.reader.print_results()
  main_block.stop()
