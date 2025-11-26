# Libraries

import h5py
from collections import namedtuple


# Helper classes

Channel_Info = namedtuple('ChannelInfo', ['digitisation', 'parange', 'offset', 'sampling_rate', 'raw_signal'])

class OsBp_FAST5():
    '''
    Reader class for FAST5 file from osmium-tagged oligo translocation experiments
    '''
    def __init__(self, filename):
        '''
        :param filename: String
        '''
        self.filename = filename
        self.handle = h5py.File(filename)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.handle:
            self.handle.close()
        self.filename = None
    
    def get_channel_raw(self, channel_id):
        '''
        Extract raw channel data in pA
        
        :param read_id: Int
        :return: <Channel_Info>
        '''
        raw_obj = self.handle['Raw']
        channel_name = 'Channel_' + str(channel_id)
        if channel_name not in raw_obj:
            raise KeyError('Channel "{}" not in: {}'.format(channel_name, self.filename))
        channel_obj = raw_obj[channel_name]

        # Channel information
        
        _meta_info = channel_obj['Meta'].attrs
        digi = _meta_info['digitisation']
        parange = _meta_info['range']
        offset = _meta_info['offset']
        samprate= _meta_info['sample_rate']
        
        # Raw signal
        
        raw_signal = channel_obj['Signal'][()]
        
        # Bundle the waveform with the metadata needed for downstream pA conversion.
        return Channel_Info(
            raw_signal=raw_signal,
            digitisation=digi,
            parange=parange,
            offset=offset,
            sampling_rate=samprate
        )
