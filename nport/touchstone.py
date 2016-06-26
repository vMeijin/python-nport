import os
import re
from datetime import datetime

import numpy as np

import nport
from nport import parameter

REAL_IMAG = 'RI'
MAG_ANGLE = 'MA'
DB_ANGLE = 'DB'

keys = {
    REAL_IMAG: ('real', 'imag'),
    MAG_ANGLE: ('mag', 'deg'),
    DB_ANGLE: ('db20', 'deg')
}

formats = {
    REAL_IMAG: (parameter.real, parameter.imag),
    MAG_ANGLE: (parameter.mag, parameter.deg),
    DB_ANGLE: (parameter.db20, parameter.deg)
}


class ParseError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "{0}: {1}".format(__class__, self.message)


def read(file_path, verbose=False):
    """
    Load the contents of a Touchstone file into an NPort
    
    :returns: NPort holding data contained in the Touchstone file
    :rtype: :class:`nport.NPort`
    
    """
    re_filename = re.compile(r"\.s(?P<ports>\d+)+p", re.I)
    m = re_filename.search(file_path)
    ports = int(m.group('ports'))
    if verbose:
        print(("File '%s'" % file_path))
        print(("  Number of ports (based on file extension) = %d" % \
               ports))
    file_path = os.path.abspath(file_path)
    file = open(file_path, 'r')
    (frequnit, type, format, z0) = _parse_option_line(file, verbose)
    freqs = []
    matrices = []
    try:
        while True:
            freq, matrix = _parse_next_sample(file, ports, format)
            freqs.append(freq)
            matrices.append(matrix)
    except EOFError:
        pass
    finally:
        file.close()
    return nport.NPort(np.asarray(freqs) * frequnit, matrices, type, z0)


_re_comment = re.compile(r"^\s*!")
_re_options = re.compile(r"^\s*#")
_re_empty = re.compile(r"^\s*$")


def _parse_option_line(file, verbose=False):
    """Parse and interpret the option line in the touchstone file"""
    prefix = {
        '': 1,
        'K': 1e3,
        'M': 1e6,
        'G': 1e9
    }

    # defaults
    frequnit = 1e9
    type = nport.SCATTERING
    format = MAG_ANGLE
    z0 = 50

    # format of the options line (order is unimportant)
    # <frequency unit> <parameter> <format> R <n>
    line = file.readline()
    while not line.startswith('#'):
        line = file.readline()

    options = line[1:].upper().split()

    i = 0
    while i < len(options):
        option = options[i]
        if option in ('GHZ', 'MHZ', 'KHZ', 'HZ'):
            frequnit = prefix[option[:-2]]
        elif option in ('DB', 'MA', 'RI'):
            format = option
        elif option in ('S', 'Y', 'Z', 'H', 'G'):
            parameter = option
        elif option == 'R':
            i += 1
            z0 = float(options[i])
        else:
            raise ParseError('unrecognized option: {0}'.format(option))
        i += 1

    if verbose:
        print(("  Frequency unit: %g Hz" % frequnit))
        print(("  Parameter:      %s" % type))
        print(("  Format:         %s" % format))
        print(("  Reference R:    %g" % z0))

    # only S-parameters are supported for now
    if type != nport.SCATTERING:
        raise NotImplementedError

    return (frequnit, type, format, z0)


def _get_next_line_data(file):
    """
    Returns the data on the next line of the input file as an array 
    of floats, skipping comment, option and empty lines.
    
    """
    line = '!'
    while _re_comment.search(line) or \
            _re_options.search(line) or \
            _re_empty.search(line):
        line = file.readline()
        if not line:  # end of data
            raise EOFError
    data = []
    line = line.split('!')[0]
    for number in line.split():
        data.append(float(number))
    return data


def _parse_next_sample(file, ports, format):
    """Parse the parameters for the next frequency point"""
    data = _get_next_line_data(file)
    # data lines always contain an even number of values (2 values
    #  per parameter), *unless* a frequency value is included in
    #  front
    assert len(data) % 2 == 1
    freq = data[0]
    data = data[1:]
    count = 0

    port1 = port2 = 1
    matrix = np.array([[None for i in range(ports)]
                       for j in range(ports)], dtype=complex)

    while True:
        for i in range(len(data) // 2):
            index = 2 * i
            args = {}
            args[keys[format][0]] = data[index]
            args[keys[format][1]] = data[index + 1]
            try:
                if ports == 2:
                    matrix[port1 - 1, port2 - 1] = parameter.parameter(**args)
                else:
                    matrix[port2 - 1, port1 - 1] = parameter.parameter(**args)
            except IndexError:
                raise Exception("more ports than reported in the file "
                                "extension")

            port1 += 1
            if port1 > ports:
                port2 += 1
                port1 = 1

        count += len(data) / 2
        if port2 > ports:
            break
        data = _get_next_line_data(file)
        if len(data) % 2 != 0:
            raise Exception("less ports than reported in the file extension")

    assert count == ports ** 2
    return (freq, matrix)


def write(instance, file_path, format=REAL_IMAG):
    """Write the n-port data held in `instance` to a Touchstone file at
    file_path.
    
    :param instance: n-port data
    :type instance: :class:`nport.NPort`
    :param file_path: filename to write to (without extension)
    :type file_path: str
    :param format: specifies the parameter format ('MA', 'RI' or 'DB')
    :type format: str
  
    """
    if not isinstance(instance, nport.NPort) or instance.type is not nport.S:
        raise ValueError("Only S-type NPorts are supported currently")
    try:
        first, second = formats[format]
    except KeyError:
        raise ValueError("unknown format specified")
    file_path = file_path + ".s%dp" % instance.ports
    file = open(file_path, 'wb')
    creationtime = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    file.write("! Created by the Python nport module\n")
    file.write("! Creation time: %s\n" % creationtime)
    file.write("# Hz %s %s R %g\n" % (instance.type, format, instance.z0))
    flatten_order = 'F' if instance.ports == 2 else 'C'
    threeport = (instance.ports == 3)

    for i, freq in enumerate(instance.freqs):
        sample = "\t%g\t" % freq
        parameters = instance[i].flatten(flatten_order)
        for i, element in enumerate(parameters):
            if i != 0 and \
                    ((threeport and i % 3 == 0) or (not threeport and i % 4 == 0)):
                sample += "\n\t\t"
            sample += " %g %g" % (first(element), second(element))
        file.write(sample + "\n")
