"""
ASAM MDF version 4 file format module
"""

import time
from functools import reduce
from numpy import (interp, linspace, dtype, amin, amax, array_equal,
                   array, searchsorted, clip, union1d, float64)
from numexpr import evaluate
from numpy.core.records import fromstring, fromarrays

import os

from .v4blocks import (Channel, ChannelGroup, ChannelConversion, DataBlock,
                       FileIdentificationBlock, HeaderBlock, DataList,
                       DataGroup, FileHistory, SourceInformation, TextBlock)
from .v4constants import *
from .utils import MdfException, get_fmt, fmt_to_datatype, pair
from .signal import Signal


__all__ = ['MDF4', ]


class MDF4(object):
    """If the *name* exist it will be loaded otherwise an empty file will be created that can be later saved to disk

    Parameters
    ----------
    name : string
        mdf file name
    load_measured_data : bool
        load data option; default *True*

        * if *True* the data group binary data block will be loaded in RAM
        * if *False* the channel data is read from disk on request

    compression : bool
        compression option for data group binary data block; default *False*
    version : string
        mdf file version ('4.00', '4.10', '4.11'); default '4.00'

    Attributes
    ----------
    name : string
        mdf file name
    groups : list
        list of data groups
    header : HeaderBlock
        mdf file header
    file_history : list
        list of (FileHistory, TextBlock) pairs
    identification : FileIdentificationBlock
        mdf file start block
    load_measured_data : bool
        load measured data option
    compression : bool
        measured data compression option
    version : int
        mdf version
    channels_db : dict
        used for fast channel access by name; for each name key the value is a (group index, channel index) tuple
    masters_db : dict
        used for fast master channel access; for each group index key the value is the master channel index

    """
    def __init__(self, name=None, load_measured_data=True, compression=False, version='4.00'):
        self.groups = []
        self.header = None
        self.identification = None
        self.file_history = []
        self.name = name
        self.load_measured_data = load_measured_data
        self.channels_db = {}
        self.masters_db = {}
        self.compression = compression

        if name and os.path.isfile(name):
            with open(self.name, 'rb') as file_stream:
                self._read(file_stream)
        else:
            self.load_measured_data = True

            self.header = HeaderBlock()
            self.identification = FileIdentificationBlock(version=version)
            self.version = version

    def _read(self, file_stream):
        dg_cntr = 0

        self.identification = FileIdentificationBlock(file_stream=file_stream)
        self.version = self.identification['version_str'].decode('utf-8').strip(' ').strip('\x00')
        self.header = HeaderBlock(address=0x40, file_stream=file_stream)

        fh_addr = self.header['file_history_addr']
        while fh_addr:
            fh = FileHistory(address=fh_addr, file_stream=file_stream)
            try:
                fh_text = TextBlock(address=fh['comment_addr'], file_stream=file_stream)
            except:
                print(self.name)
                raise
            self.file_history.append((fh, fh_text))
            fh_addr = fh['next_fh_addr']

        # go to first date group and read each data group sequentially
        dg_addr = self.header['first_dg_addr']
        while dg_addr:
            self.groups.append({})
            grp = self.groups[-1]
            grp['channels'] = []
            grp['channel_conversions'] = []
            grp['channel_sources'] = []
            # channel_group is lsit to allow uniform handling of all texts in save method
            grp['texts'] = {'channels': [], 'sources': [], 'conversions': [], 'conversion_tab': [], 'channel_group': []}
            grp['data_group'] = DataGroup(address=dg_addr, file_stream=file_stream)
            # go to first channel group of the current data group
            cg_addr = grp['data_group']['first_cg_addr']

            # read each channel group sequentially
            channel_group = grp['channel_group'] = ChannelGroup(address=cg_addr, file_stream=file_stream)
            # read acquisition name and comment for current channel group
            channel_group_texts = {}
            grp['texts']['channel_group'].append(channel_group_texts)

            for key in ('acq_name_addr', 'comment_addr'):
                address = channel_group[key]
                if address:
                    channel_group_texts[key] = TextBlock(address=address, file_stream=file_stream)

            # go to first channel of the current channel group
            ch_addr = channel_group['first_ch_addr']
            ch_cntr = 0
            channels = grp['channels']
            while ch_addr:
                # read channel block and create channel object
                channel = Channel(address=ch_addr, file_stream=file_stream)
                channels.append(channel)

                # read conversion block and create channel conversion object
                address = channel['conversion_addr']
                if address:
                    conv = ChannelConversion(address=address, file_stream=file_stream)
                else:
                    conv = None
                grp['channel_conversions'].append(conv)

                conv_tabx_texts = {}
                grp['texts']['conversion_tab'].append(conv_tabx_texts)
                if conv and conv['conversion_type'] in (CONVERSION_TYPE_TABX, CONVERSION_TYPE_RTABX, CONVERSION_TYPE_TTAB):
                    for i in range(conv['links_nr'] - 5):
                        address = conv['text_{}'.format(i)]
                        if address:
                            conv_tabx_texts['text_{}'.format(i)] = TextBlock(address=address, file_stream=file_stream)
                    address = conv.get('default_addr', 0)
                    if address:
                        file_stream.seek(address, SEEK_START)
                        blk_id = file_stream.read(4)
                        if blk_id == b'##TX':
                            conv_tabx_texts['default_addr'] = TextBlock(address=address, file_stream=file_stream)
                        elif blk_id == b'##CC':
                            conv_tabx_texts['default_addr'] = ChannelConversion(address=address, file_stream=file_stream)
                            conv_tabx_texts['default_addr'].text_str = str(time.clock())

                            conv['unit_addr'] = conv_tabx_texts['default_addr']['unit_addr']
                            conv_tabx_texts['default_addr']['unit_addr'] = 0
                elif conv and conv['conversion_type'] == CONVERSION_TYPE_TRANS:
                    for i in range((conv['links_nr'] - 4 - 1 ) //2):
                        for key in ('input_{}_addr'.format(i), 'output_{}_addr'.format(i)):
                            address = conv[key]
                            if address:
                                conv_tabx_texts[key] = TextBlock(address=address, file_stream=file_stream)
                    address = conv['default_addr']
                    if address:
                        conv_tabx_texts['default_addr'] = TextBlock(address=address, file_stream=file_stream)

                # read source block and create source infromation object
                source_texts = {}
                address = channel['source_addr']
                if address:
                    source = SourceInformation(address=address, file_stream=file_stream)
                    grp['channel_sources'].append(source)
                    grp['texts']['sources'].append(source_texts)
                    # read text fields for channel sources
                    for key in ('name_addr', 'path_addr', 'comment_addr'):
                        address = source[key]
                        if address:
                            source_texts[key] = TextBlock(address=address, file_stream=file_stream)
                else:
                    grp['channel_sources'].append(None)
                    grp['texts']['sources'].append(source_texts)

                # read text fields for channel conversions
                conv_texts = {}
                grp['texts']['conversions'].append(conv_texts)
                for key in ('name_addr', 'unit_addr', 'comment_addr', 'formula_addr'):
                    if conv is not None:
                        address = conv.get(key, 0)
                        if address:
                            conv_texts[key] = TextBlock(address=address, file_stream=file_stream)

                # read text fields for channel
                channel_texts = {}
                grp['texts']['channels'].append(channel_texts)
                for key in ('name_addr', 'comment_addr'):
                    address = channel[key]
                    if address:
                        channel_texts[key] = TextBlock(address=address, file_stream=file_stream)

                # update channel object name and block_size attributes
                channel.name = channel_texts['name_addr'].text_str
                self.channels_db[channel.name] = (dg_cntr, ch_cntr)

                if channel['channel_type'] in (CHANNEL_TYPE_MASTER, CHANNEL_TYPE_VIRTUAL_MASTER):
                    self.masters_db[dg_cntr] = ch_cntr

                # go to next channel of the current channel group
                ch_addr = channel['next_ch_addr']
                ch_cntr += 1

            if self.load_measured_data:
                # go to the first data block of the current data group
                dat_addr = grp['data_group']['data_block_addr']
                file_stream.seek(dat_addr, SEEK_START)
                id_string = file_stream.read(4)
                if id_string == b'##DT':
                    grp['data_block'] = DataBlock(address=dat_addr, file_stream=file_stream, compression=self.compression)
                elif id_string == b'##DL':
                    data = bytearray()
                    next_dl_addr = dat_addr
                    while next_dl_addr:
                        dl = DataList(address=next_dl_addr, file_stream=file_stream)
                        for i in range(dl['links_nr'] - 1):
                            addr = dl['data_block_addr{}'.format(i)]
                            data.extend(DataBlock(file_stream=file_stream, address=addr)['data'])
                        next_dl_addr = dl['next_dl_addr']
                    kargs={'data': data, 'block_len': len(data) + COMMON_SIZE, 'compression': self.compression}
                    grp['data_block'] = DataBlock(**kargs)
                else:
                    grp['data_block'] = None

            # go to next data group
            dg_addr = grp['data_group']['next_dg_addr']
            dg_cntr += 1

        # save measurement comment information
        for gp in self.groups:
            if 'Comment' in [ch.name for ch in gp['channels']]:
                if not gp['channels'][-1]['data_block_addr'] == 0:
                    file_stream.seek(gp['channels'][-1]['data_block_addr'] + 8, SEEK_START)
                    size = unpack('<Q', file_stream.read(8))[0]
                    file_stream.seek(8, SEEK_REL)
                    comment = file_stream.read(size - COMMON_SIZE)
                    comment = comment[4:]
                    gp['channels'][-1]['data_block_addr'] = 0
                    gp['channels'][-1]['channel_type'] = CHANNEL_TYPE_VALUE
                    gp['channels'][-1]['bit_count'] = 8 * len(comment)
                    gp['channel_group']['samples_byte_nr'] = 8 + len(comment)
                    ba = bytearray(gp['data_block']['data'][:8])
                    ba += bytearray(comment)
                    gp['data_block']['data'] = bytes(ba)
                    gp['data_block']['block_len'] = len(ba) + COMMON_SIZE

    def append(self, signals, source_info='Python'):
        """Appends a new data group.

        Parameters
        ----------
        signals : list
            list on *Signal* objects
        acquisition_info : str
            acquisition information; default 'Python'

        Examples
        --------
        >>> # case 1 conversion type None
        >>> s1 = np.array([1, 2, 3, 4, 5])
        >>> s2 = np.array([-1, -2, -3, -4, -5])
        >>> s3 = np.array([0.1, 0.04, 0.09, 0.16, 0.25])
        >>> t = np.array([0.001, 0.002, 0.003, 0.004, 0.005])
        >>> names = ['Positive', 'Negative', 'Float']
        >>> units = ['+', '-', '.f']
        >>> info = {}
        >>> s1 = Signal(samples=s1, timstamps=t, unit='+', name='Positive')
        >>> s2 = Signal(samples=s2, timstamps=t, unit='-', name='Negative')
        >>> s3 = Signal(samples=s3, timstamps=t, unit='flts', name='Floats')
        >>> mdf = MDF4('new.mf4')
        >>> mdf.append([s1, s2, s3], 'created by asammdf v1.1.0')
        >>> # case 2: VTAB conversions from channels inside another file
        >>> mdf1 = MDF4('in.mf4')
        >>> ch1 = mdf1.get("Channel1_VTAB")
        >>> ch2 = mdf1.get("Channel2_VTABR")
        >>> sigs = [ch1, ch2]
        >>> mdf2 = MDF4('out.mf4')
        >>> mdf2.append(sigs, 'created by asammdf v1.1.0')

        """
        signals_nr = len(signals)
        dg_cntr = len(self.groups)
        self.groups.append({})
        gp = self.groups[-1]

        t_ = signals[0].timestamps
        for s in signals[1:]:
            if not array_equal(s.timestamps, t_):
                different = True
                break
        else:
            different = False

        if different:
            times = [s.timestamps for s in signals]
            t = reduce(union1d, times).flatten().astype(float64)
            signals = [s.interp(t) for s in signals]
            times = None
        else:
            t = t_

        cycles_nr = len(t)

        t_type, t_size = fmt_to_datatype(t.dtype, version=4)

        gp['channels'] = gp_channels = []
        gp['channel_conversions'] = gp_conv = []
        gp['channel_sources'] = gp_source = []
        gp['texts'] = gp_texts = {'channels': [], 'sources': [], 'conversions': [], 'conversion_tab': [], 'channel_group': []}

        #time channel texts
        for key, item in gp['texts'].items():
            item.append({})
        gp_texts['channels'][-1]['name_addr'] = TextBlock.from_text('t')
        gp_texts['conversions'][-1]['unit_addr'] = TextBlock.from_text('s')

        gp_texts['sources'][-1]['name_addr'] = TextBlock.from_text(source_info)
        gp_texts['sources'][-1]['path_addr'] = TextBlock.from_text(source_info)
        gp_texts['channel_group'][-1]['acq_name_addr'] = TextBlock.from_text(source_info)
        gp_texts['channel_group'][-1]['comment_addr'] = TextBlock.from_text(source_info)

        #channels texts
        for s in signals:
            for key, item in gp['texts'].items():
                item.append({})
            gp_texts['channels'][-1]['name_addr'] = TextBlock.from_text(s.name)
            if s.unit:
                gp_texts['conversions'][-1]['unit_addr'] = TextBlock.from_text(s.unit)
            gp_texts['sources'][-1]['name_addr'] = TextBlock.from_text(source_info)
            gp_texts['sources'][-1]['path_addr'] = TextBlock.from_text(source_info)

        #conversion for time channel
        kargs = {'conversion_type': CONVERSION_TYPE_NON,
                 'min_phy_value': t[0] if cycles_nr else 0,
                 'max_phy_value': t[-1] if cycles_nr else 0}
        gp_conv.append(ChannelConversion(**kargs))
        gp_texts['conversion_tab'].append({})

        #conversions for channels
        if cycles_nr:
            min_max = [(amin(s.samples), amax(s.samples)) for s in signals]
        else:
            min_max = [(0, 0) for s in signals]

        for idx, s in enumerate(signals):
            conv = s.conversion
            conv_texts_tab = gp_texts['conversion_tab'][idx+1]
            if conv:
                conv_type = conv['type']
                if conv_type == CONVERSION_TYPE_TABX:
                    kargs = {}
                    kargs['conversion_type'] = CONVERSION_TYPE_TABX
                    raw = conv['raw']
                    phys = conv['phys']
                    for i, (r_, p_) in enumerate(zip(raw, phys)):
                        kargs['text_{}'.format(i)] = 0
                        kargs['val_{}'.format(i)] = r_
                        conv_texts_tab['text_{}'.format(i)] = TextBlock.from_text(p_)
                    if conv.get('default', b''):
                        conv_texts_tab['default_addr'] = TextBlock.from_text(conv['default'])
                    kargs['default_addr'] = 0
                    kargs['links_nr'] = len(raw) + 5
                elif conv_type == CONVERSION_TYPE_RTABX:
                    kargs = {}
                    kargs['conversion_type'] = CONVERSION_TYPE_RTABX
                    lower = conv['lower']
                    upper = conv['upper']
                    texts = conv['phys']
                    kargs['ref_param_nr'] = len(upper)
                    kargs['default_addr'] = conv.get('default', 0)
                    kargs['links_nr'] = len(lower) + 5

                    for i, (u_, l_, t_) in enumerate(zip(upper, lower, texts)):
                        kargs['lower_{}'.format(i)] = l_
                        kargs['upper_{}'.format(i)] = u_
                        kargs['text_{}'.format(i)] = 0
                        conv_texts_tab['text_{}'.format(i)] = TextBlock.from_text(t_)
                    if conv.get('default', b''):
                        conv_texts_tab['default_addr'] = TextBlock.from_text(conv['default'])
                    kargs['default_addr'] = 0

                else:
                     kargs = {'conversion_type': CONVERSION_TYPE_NON,
                              'min_phy_value': min_max[idx][0],
                              'max_phy_value': min_max[idx][1]}
                gp_conv.append(ChannelConversion(**kargs))
            else:
                kargs = {'conversion_type': CONVERSION_TYPE_NON,
                         'min_phy_value': min_max[idx][0],
                         'max_phy_value': min_max[idx][1]}
                gp_conv.append(ChannelConversion(**kargs))


        #source for channels
        for i in range(signals_nr + 1):
            gp_source.append(SourceInformation())

        #time channel
        kargs = {'channel_type': CHANNEL_TYPE_MASTER,
                 'data_type': t_type,
                 'sync_type': 1,
                 'byte_offset': 0,
                 'bit_count': t_size,
                 'min_raw_value': t[0] if cycles_nr else 0,
                 'max_raw_value' : t[-1]if cycles_nr else 0,
                 'lower_limit' : t[0]if cycles_nr else 0,
                 'upper_limit' : t[-1]if cycles_nr else 0}
        ch = Channel(**kargs)
        ch.name = 't'
        gp_channels.append(ch)
        self.masters_db[dg_cntr] = 0

        #channels
        sig_dtypes = [sig.samples.dtype for sig in signals]
        sig_formats = [fmt_to_datatype(typ, version=4) for typ in sig_dtypes]
        offset = t_size // 8
        ch_cntr = 1
        for (sigmin, sigmax), (sig_type, sig_size), name in zip(min_max, sig_formats, [sig.name for sig in signals]):
            byte_size = max(sig_size // 8, 1)
            kargs = {'channel_type': CHANNEL_TYPE_VALUE,
                     'bit_count': sig_size,
                     'byte_offset': offset,
                     'bit_offset' : 0,
                     'data_type': sig_type,
                     'min_raw_value': sigmin,
                     'max_raw_value' : sigmax,
                     'lower_limit' : sigmin,
                     'upper_limit' : sigmax}
            ch = Channel(**kargs)
            ch.name = name
            gp_channels.append(ch)
            offset += byte_size
            self.channels_db[name] = (dg_cntr, ch_cntr)
            ch_cntr += 1

        #channel group
        kargs = {'cycles_nr': len(t),
                 'samples_byte_nr': offset}
        gp['channel_group'] = ChannelGroup(**kargs)

        #data block
        types = [('t', t.dtype),]
        types.extend([('sig{}'.format(i), typ) for i, typ in enumerate(sig_dtypes)])
        arrays = [t, ]
        arrays.extend([sig.samples for sig in signals])

        samples = fromarrays(arrays, dtype=types)
        block = samples.tostring()

        kargs = {'data': block,
                 'block_len': 24 + len(block),
                 'compression' : self.compression}
        gp['data_block'] = DataBlock(**kargs)

        #data group
        gp['data_group'] = DataGroup(**{})

    def get(self, name=None, *, group=None, index=None, raster=None):
        """Gets channel samples.
        Channel can be specified in two ways:

        * using the first positional argument *name*
        * using the group number (keyword argument *group*) and the channel number (keyword argument *index*). Use *info* method for group and channel numbers



        If the *raster* keyword argument is not *None* the output is interpolated accordingly

        Parameters
        ----------
        name : string
            name of channel
        group : int
            0-based group index
        index : int
            0-based channel index
        raster : float
            time raster in seconds

        Returns
        -------
        vals, t, unit, conversion : (numpy.array, numpy.array, string, dict | None)
            The conversion is *None* exept for the VTAB and VTABR conversions. The conversion keys are:

            * for VTAB conversion:

                * raw - numpy.array for X-axis
                * phys - numpy.array of strings for Y-axis
                * type - conversion type = CONVERSION_TYPE_TABX

            * for VTABR conversion:

                * lower - numpy.array for lower range
                * upper - numpy.array for upper range
                * phys - numpy.array of strings for Y-axis
                * type - conversion type = COONVERSION_TYPE_VTABR

            The conversion information can be used by the *append* method for the *info* argument

        Raises
        ------
        MdfError :

        * if the channel name is not found
        * if the group index is out of range
        * if the channel index is out of range

        """
        if name is None:
            if group is None or index is None:
                raise MdfException('Invalid arguments for "get" methos: must give "name" or, "group" and "index"')
            else:
                gp_nr, ch_nr = group, index
                if gp_nr > len(self.groups) - 1:
                    raise MdfException('Group index out of range')
                if index > len(self.groups[gp_nr]['channels']) - 1:
                    raise MdfException('Channel index out of range')
        else:
            if not name in self.channels_db:
                raise MdfException('Channel "{}" not found'.format(name))
            else:
                gp_nr, ch_nr = self.channels_db[name]

        gp = self.groups[gp_nr]
        channel = gp['channels'][ch_nr]

        conversion = gp['channel_conversions'][ch_nr]

        unit = gp['texts']['conversions'][ch_nr].get('unit_addr', None)
        if unit:
            unit = unit.text_str
        else:
            unit = ''

        time_idx = self.masters_db[gp_nr]
        time_ch = gp['channels'][time_idx]
        time_conv = gp['channel_conversions'][time_idx]

        group = gp

        time_size = time_ch['bit_count'] // 8
        t_fmt = get_fmt(time_ch['data_type'], time_size, version=4)
        t_byte_offset, bit_offset = time_ch['byte_offset'], time_ch['bit_offset']
        bits = time_ch['bit_count']
        if bits % 8:
            t_size = bits // 8 + 1
        else:
            t_size = bits // 8

        bits = channel['bit_count']
        size = bits + bit_offset
        if size % 8:
            size = bits // 8 + 1
        else:
            size = bits // 8
        block_size = gp['channel_group']['samples_byte_nr']
        byte_offset, bit_offset = channel['byte_offset'], channel['bit_offset']
#        print(channel, gp_nr, ch_nr, size)
        ch_fmt = get_fmt(channel['data_type'], size, version=4)

        if not self.load_measured_data:
            with open(self.name, 'rb') as file_stream:
                # go to the first data block of the current data group
                dat_addr = group['data_group']['data_block_addr']
                read_size = group['channel_group']['samples_byte_nr'] * group['channel_group']['cycles_nr']
                data = DataBlock(file_stream=file_stream, address=dat_addr, size=read_size)['data']
        else:
            try:
                data = group['data_block']['data']
            except KeyError:
                return Signal(samples=array([]),
                              timestamps=array([]),
                              unit=unit,
                              name=channel.name,
                              conversion=None)

        if time_idx == ch_nr:
            if time_ch['channel_type'] == CHANNEL_TYPE_MASTER:
                types = dtype( [('res1', 'a{}'.format(t_byte_offset)),
                                ('t', t_fmt),
                                ('res2', 'a{}'.format(block_size - byte_offset - size))] )
                values = fromstring(data, types)
        else:

            if time_ch['channel_type'] == CHANNEL_TYPE_MASTER:
                if t_byte_offset < byte_offset:
                    types = dtype( [('res1', 'a{}'.format(t_byte_offset)),
                                    ('t', t_fmt),
                                    ('res2', 'a{}'.format(byte_offset - time_size - t_byte_offset)),
                                    ('vals', ch_fmt),
                                    ('res3', 'a{}'.format(block_size - byte_offset - size))] )
                else:
                    types = dtype( [('res1', 'a{}'.format(byte_offset)),
                                    ('vals', ch_fmt),
                                    ('res2', 'a{}'.format(t_byte_offset - size - byte_offset)),
                                    ('t', t_fmt),
                                    ('res3', 'a{}'.format(block_size - t_byte_offset - t_size))] )
            elif time_ch['channel_type'] == CHANNEL_TYPE_VIRTUAL_MASTER:
                types = dtype( [('res1', 'a{}'.format(byte_offset)),
                                ('vals', ch_fmt),
                                ('res3', 'a{}'.format(block_size - byte_offset - size))] )
#            print(channel.name, types, hex(2**bits - 1), bit_offset)
            values = fromstring(data, types)

        if time_ch['channel_type'] == CHANNEL_TYPE_MASTER:
            # get timestamps
            time_conv_type = CONVERSION_TYPE_NON if time_conv is None else time_conv['conversion_type']
            if time_conv_type == CONVERSION_TYPE_LIN:
                time_a = time_conv['a']
                time_b = time_conv['b']
                t = values['t'] * time_a
                if time_b:
                    t += time_b
            elif time_conv_type == CONVERSION_TYPE_NON:
                t = values['t']
        elif time_ch['channel_type'] == CHANNEL_TYPE_VIRTUAL_MASTER:
            time_a = time_conv['a']
            time_b = time_conv['b']
            cycles = len(data) // block_size
            t = array([t * time_a + time_b for t in range(cycles)], dtype=float64)

        if time_idx == ch_nr:
            res = Signal(samples=t,
                         timestamps=t[:],
                         unit=unit,
                         name=time_ch.name,
                         conversion=None)
        else:

            # get channel values
            conversion_type = CONVERSION_TYPE_NON if conversion is None else conversion['conversion_type']
            vals = values['vals']
            if bit_offset:
                vals = vals >> bit_offset
            if bits % 8:
                vals = vals & (2**bits - 1)

            if conversion_type == CONVERSION_TYPE_NON:
                pass

            elif conversion_type == CONVERSION_TYPE_LIN:
                a = conversion['a']
                b = conversion['b']
                if (a, b) == (1, 0):
                    if not vals.dtype == ch_fmt:
                        vals = vals.astype(ch_fmt)
                else:
                    vals = vals * a
                    if b:
                        vals.setflags(write=True)
                        vals += b

            elif conversion_type == CONVERSION_TYPE_RAT:
                P1 = conversion['P1']
                P2 = conversion['P2']
                P3 = conversion['P3']
                P4 = conversion['P4']
                P5 = conversion['P5']
                P6 = conversion['P6']
                X = values['vals']
                vals = (P1 * X**2 + P2 * X + P3) / (P4 * X**2 + P5 * X + P6)

            elif conversion_type == CONVERSION_TYPE_ALG:
                formula = gp['texts']['conversions'][ch_nr]['formula_addr'].text_str
                X = values['vals']
                vals = evaluate(formula)

            elif conversion_type in (CONVERSION_TYPE_TABI, CONVERSION_TYPE_TAB):
                nr = conversion['val_param_nr'] // 2
                raw = array([conversion['raw_{}'.format(i)] for i in range(nr)])
                phys = array([conversion['phys_{}'.format(i)] for i in range(nr)])
                if conversion_type == CONVERSION_TYPE_TABI:
                    vals = interp(values['vals'], raw, phys)
                else:
                    idx = searchsorted(raw, values['vals'])
                    idx = clip(idx, 0, len(raw) - 1)
                    vals = phys[idx]

            elif conversion_type ==  CONVERSION_TYPE_RTAB:
                nr = (conversion['val_param_nr'] - 1) // 3
                lower = array([conversion['lower_{}'.format(i)] for i in range(nr)])
                upper = array([conversion['upper_{}'.format(i)] for i in range(nr)])
                phys = array([conversion['phys_{}'.format(i)] for i in range(nr)])
                default = conversion['default']
                vals = values['vals']

                res = []
                for v in vals:
                    for l, u, p in zip(lower, upper, phys):
                        if l <= v <= u:
                            res.append(p)
                            break
                    else:
                        res.append(default)
                vals = array(res).astype(ch_fmt)

            elif conversion_type == CONVERSION_TYPE_TABX:
                nr = conversion['val_param_nr']
                raw = array([conversion['val_{}'.format(i)] for i in range(nr)])
                phys = array([gp['texts']['conversion_tab'][ch_nr]['text_{}'.format(i)]['text'] for i in range(nr)])
                default = gp['texts']['conversion_tab'][ch_nr].get('default_addr', {}).get('text', b'')
                vals = values['vals']
                info = {'raw': raw, 'phys': phys, 'default': default, 'type': CONVERSION_TYPE_TABX}

            elif conversion_type == CONVERSION_TYPE_RTABX:
                nr = conversion['val_param_nr'] // 2

                phys = array([gp['texts']['conversion_tab'][ch_nr]['text_{}'.format(i)]['text'] for i in range(nr)])
                lower = array([conversion['lower_{}'.format(i)] for i in range(nr)])
                upper = array([conversion['upper_{}'.format(i)] for i in range(nr)])
                default = gp['texts']['conversion_tab'][ch_nr].get('default_addr', {}).get('text', b'')
                vals = values['vals']
                info = {'lower': lower, 'upper': upper, 'phys': phys, 'type': CONVERSION_TYPE_RTABX}

            elif conversion == CONVERSION_TYPE_TTAB:
                nr = conversion['val_param_nr'] - 1

                raw = array([gp['texts']['conversion_tab'][ch_nr]['text_{}'.format(i)]['text'] for i in range(nr)])
                phys = array([conversion['val_{}'.format(i)] for i in range(nr)])
                default = conversion['val_default']
                vals = values['vals']
                info = {'lower': lower, 'upper': upper, 'phys': phys, 'type': CONVERSION_TYPE_TTAB}

            elif conversion == CONVERSION_TYPE_TRANS:
                nr = (conversion['ref_param_nr'] - 1 ) // 2
                in_ = array([gp['texts']['conversion_tab'][ch_nr]['input_{}'.format(i)]['text'] for i in range(nr)])
                out_ = array([gp['texts']['conversion_tab'][ch_nr]['output_{}'.format(i)]['text'] for i in range(nr)])
                default = gp['texts']['conversion_tab'][ch_nr]['default_addr']['text']
                vals = values['vals']

                res = []
                for v in vals:
                    for i, o in zip(in_, out_):
                        if v == i:
                            res.append(o)
                            break
                    else:
                        res.append(default)
                vals = array(res)
                info = {'input': in_, 'output': out_, 'default': default, 'type': CONVERSION_TYPE_TRANS}


            if conversion_type in (CONVERSION_TYPE_TABX, CONVERSION_TYPE_RTABX, CONVERSION_TYPE_TTAB, CONVERSION_TYPE_TRANS):
                conversion = info
            else:
                conversion = None
            res = Signal(samples=vals,
                         timestamps=t,
                         unit=unit,
                         name=channel.name,
                         conversion=conversion)

        if raster:
            tx = linspace(0, t[-1], int(t[-1] / raster))
            res = res.interp(tx)
        return res

    def info(self):
        """get MDF information as a dict

        Examples
        --------
        >>> mdf = MDF4('test.mdf')
        >>> mdf.info()


        """
        info = {}
        info['version'] = self.identification['version_str'].strip(b'\x00').decode('utf-8')
        info['groups'] = len(self.groups)
        for i, gp in enumerate(self.groups):
            inf = {}
            info['group {}'.format(i)] = inf
            inf['cycles'] = gp['channel_group']['cycles_nr']
            inf['channels count'] = len(gp['channels'])
            for j, ch in enumerate(gp['channels']):
                inf['channel {}'.format(j)] = (ch.name, ch['channel_type'])

        return info

    def remove(self, *, group=None, name=None):
        """Remove data group. Use *group* or *name* keyword arguments to identify the group's index. *group* has priority

        Parameters
        ----------
        name : string
            name of the channel inside the data group to be removed
        group : int
            data group index to be removed

        Examples
        --------
        >>> mdf = MDF4('test.mdf')
        >>> mdf.remove(group=3)
        >>> mdf.remove(name='VehicleSpeed')

        """
        if group:
            if 0 <= group <= len(self.groups):
                idx = group
            else:
                print('Group index "{}" not in valid range[0..{}]'.format(group, len(self.groups)))
                return
        elif name:
            if name in self.channels_db:
                idx = self.channels_db[name][1]
            else:
                print('Channel name "{}" not found in the measurement'.format(name))
                return
        else:
            print('Must specify a valid group or name argument')
            return
        self.groups.pop(idx)

    def save(self, dst=None):
        """Save MDF to *dst*. If *dst* is *None* the original file is overwritten

        """
        if self.name is None and dst is None:
            print('New MDF created without a name and no destination file name specified for save')
            return
        dst = dst if dst else self.name

        if not self.file_history:
            comment = 'created'
        else:
            comment = 'updated'

        self.file_history.append([FileHistory(), TextBlock.from_text('<FHcomment>\n<TX>{}</TX>\n<tool_id>PythonMDFEditor</tool_id>\n<tool_vendor></tool_vendor>\n<tool_version>1.0</tool_version>\n</FHcomment>'.format(comment), meta=True)])

        with open(dst, 'wb') as dst:
            defined_texts = {}

            address = IDENTIFICATION_BLOCK_SIZE + HEADER_BLOCK_SIZE
            dst.write(b'\x00' * address)
            for i, (fh, fh_text) in enumerate(self.file_history):
                fh_text.address = address
                address += dst.write(bytes(fh_text))

                fh['comment_addr'] = fh_text.address

            for i, (fh, fh_text) in enumerate(self.file_history):
                fh.address = address
                address += FH_BLOCK_SIZE

            for i, (fh, fh_text) in enumerate(self.file_history[:-1]):
                fh['next_fh_addr'] = self.file_history[i+1][0].address
            self.file_history[-1][0]['next_fh_addr'] = 0
            for fh, _ in self.file_history:
                dst.write(bytes(fh))

            for i, gp in enumerate(self.groups):
                for _, item_list in gp['texts'].items():
                    for dict_ in item_list:
                        for key in dict_:
                            #text blocks can be shared
                            if dict_[key].text_str in defined_texts:
                                dict_[key].address = defined_texts[dict_[key].text_str]
                            else:
                                defined_texts[dict_[key].text_str] = address
                                dict_[key].address = address
                                address += dst.write(bytes(dict_[key]))

                for j, conv in enumerate(gp['channel_conversions']):
                    if conv:
                        conv.address = address

                        for key in ('name_addr', 'unit_addr', 'comment_addr', 'formula_addr'):
                            if key in gp['texts']['conversions'][j]:
                                conv[key] = gp['texts']['conversions'][j][key].address
                            else:
                                conv[key] = 0
                        conv['inv_conv_addr'] = 0

                        if conv['conversion_type'] in (CONVERSION_TYPE_TABX,
                                                       CONVERSION_TYPE_RTABX,
                                                       CONVERSION_TYPE_TTAB,
                                                       CONVERSION_TYPE_TRANS):
                            for key in gp['texts']['conversion_tab'][j]:
                                conv[key] = gp['texts']['conversion_tab'][j][key].address

                        address += dst.write(bytes(conv))

                for j, source in enumerate(gp['channel_sources']):
                    if source:
                        source.address = address

                        for key in ('name_addr', 'path_addr', 'comment_addr'):
                            if key in gp['texts']['sources'][j]:
                                source[key] = gp['texts']['sources'][j][key].address
                            else:
                                source[key] = 0

                        address += dst.write(bytes(source))

                for j, channel in enumerate(gp['channels']):
                    channel.address = address
                    address += CN_BLOCK_SIZE

                    for key in ('name_addr', 'comment_addr'):
                        if key in gp['texts']['channels'][j]:
                            channel[key] = gp['texts']['channels'][j][key].address
                        else:
                            channel[key] = 0
                    channel['conversion_addr'] = 0 if not gp['channel_conversions'][j] else gp['channel_conversions'][j].address
                    channel['source_addr'] = gp['channel_sources'][j].address if gp['channel_sources'][j] else 0
                    channel['component_addr'] = 0
                    channel['data_block_addr'] = 0
                    channel['unit_addr'] = 0

                for channel, next_channel in pair(gp['channels']):
                    channel['next_ch_addr'] = next_channel.address
                    dst.write(bytes(channel))
                next_channel['next_ch_addr'] = 0
                dst.write(bytes(next_channel))

                gp['channel_group'].address = address
                gp['channel_group']['first_ch_addr'] = gp['channels'][0].address
                gp['channel_group']['next_cg_addr'] = 0
                for key in ('acq_name_addr', 'comment_addr'):
                    if key in gp['texts']['channel_group'][0]:
                        gp['channel_group'][key] = gp['texts']['channel_group'][0][key].address
                gp['channel_group']['acq_source_addr'] = 0
                address += dst.write(bytes(gp['channel_group']))

                #print(len(self.groups), self.groups.index(gp))

                if gp['data_block']:
                    block = gp['data_block']

                    block.address = address
                    address += block['block_len']
                    align = address % 8
                    if align:
                        add = 8 - align
                        address += add
                    else:
                        add = 0
                    dst.write(bytes(block) + b'\x00' * add)

            for gp in self.groups:
                gp['data_group'].address = address
                address += DG_BLOCK_SIZE

                gp['data_group']['first_cg_addr'] = gp['channel_group'].address
                gp['data_group']['comment_addr'] = 0
                if gp['data_block']:
                    gp['data_group']['data_block_addr'] = gp['data_block'].address
                else:
                    gp['data_group']['data_block_addr'] = 0

            for i, dg in enumerate(self.groups[:-1]):
                dg['data_group']['next_dg_addr'] = self.groups[i+1]['data_group'].address
            self.groups[-1]['data_group']['next_dg_addr'] = 0

            for dg in (dg_['data_group'] for dg_ in self.groups):
                dst.write(bytes(dg))

            if self.groups:
                self.header['first_dg_addr'] = self.groups[0]['data_group'].address
            else:
                self.header['first_dg_addr'] = 0
            self.header['file_history_addr'] = self.file_history[0][0].address
            dst.seek(0, SEEK_START)
            dst.write(bytes(self.identification))
            dst.write(bytes(self.header))


if __name__ == '__main__':
    pass