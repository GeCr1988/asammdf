.. raw:: html

    <style> .red {color:red} </style>
    <style> .blue {color:blue} </style>
    <style> .green {color:green} </style>
    <style> .cyan {color:cyan} </style>
    <style> .magenta {color:magenta} </style>
    <style> .orange {color:orange} </style>
    <style> .brown {color:brown} </style>
    
.. role:: red
.. role:: blue
.. role:: green
.. role:: cyan
.. role:: magenta
.. role:: orange
.. role:: brown

.. _benchmarks:

Intro
-----

The benchmarks were done using two test files (for mdf version 3 and 4) of around 170MB. 
The files contain 183 data groups and a total of 36424 channels.

*asamdf 2.1.0* was compared against *mdfreader 0.2.5*. 
*mdfreader* seems to be the most used Python package to handle MDF files, and it also supports both version 3 and 4 of the standard.

The three benchmark cathegories are file open, file save and extracting the data for all channels inside the file(36424 calls).
For each cathegory two aspect were noted: elapsed time and peak RAM usage.

Dependencies
------------
You will need the following packages to be able to run the benchmark script

* psutil
* mdfreader

x64 Python results
------------------
The test environment used for 64 bit tests had:

* Python 3.6.1 (v3.6.1:69c0db5, Mar 21 2017, 18:41:36) [MSC v.1900 64 bit (AMD64)]
* Windows-7-6.1.7601-SP1
* Intel64 Family 6 Model 94 Stepping 3, GenuineIntel (i7-6820Q)
* 16GB installed RAM

The notations used in the results have the following meaning:

* nodata = MDF object created with load_measured_data=False (raw channel data no loaded into RAM)
* compression = MDF object created with compression=True (raw channel data loaded into RAM and compressed)
* noconvert = MDF object created with convertAfterRead=False

Raw data
^^^^^^^^

================================================== ========= ========
Open file                                          Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                      801      352
asammdf 2.1.0 compression mdfv3                          946      278
asammdf 2.1.0 nodata mdfv3                               490      172
mdfreader 0.2.5 mdfv3                                   2962      525
mdfreader 0.2.5 no convert mdfv3                        2740      392
asammdf 2.1.0 mdfv4                                     1674      440
asammdf 2.1.0 compression mdfv4                         1916      343
asammdf 2.1.0 nodata mdfv4                              1360      245
mdfreader 0.2.5 mdfv4                                  31915      737
mdfreader 0.2.5 noconvert mdfv4                        31425      607
================================================== ========= ========


================================================== ========= ========
Save file                                          Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                      575      353
asammdf 2.1.0 compression mdfv3                          705      276
mdfreader 0.2.5 mdfv3                                  21591     1985
asammdf 2.1.0 mdfv4                                      913      447
asammdf 2.1.0 compression mdfv4                         1160      352
mdfreader 0.2.5 mdfv4                                  18666     2782
================================================== ========= ========


================================================== ========= ========
Get all channels (36424 calls)                     Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                     2835      363
asammdf 2.1.0 compression mdfv3                        18188      287
asammdf 2.1.0 nodata mdfv3                             11926      188
mdfreader 0.2.5 mdfv3                                     29      525
asammdf 2.1.0 mdfv4                                     2338      450
asammdf 2.1.0 compression mdfv4                        15566      355
asammdf 2.1.0 nodata mdfv4                             12598      260
mdfreader 0.2.5 mdfv4                                     39      737
================================================== ========= ========

Graphical results
^^^^^^^^^^^^^^^^^

.. plot::

    import matplotlib.pyplot as plt
    import numpy as np

    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'mdfreader 0.2.5 no convert mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4', 'mdfreader 0.2.5 noconvert mdfv4']
    time = np.array([801, 946, 490, 2962, 2740, 1674, 1916, 1360, 31915, 31425])
    ram =  np.array([352, 278, 172, 525, 392, 440, 343, 245, 737, 607])

    y_pos = list(range(len(cat)))

    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)

    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]

    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Open test file - time')
    ax.xaxis.grid() 

    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'mdfreader 0.2.5 no convert mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4', 'mdfreader 0.2.5 noconvert mdfv4']
    time = np.array([801, 946, 490, 2962, 2740, 1674, 1916, 1360, 31915, 31425])
    ram =  np.array([352, 278, 172, 525, 392, 440, 343, 245, 737, 607])
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAM [MB]')
    ax.set_title('Open test file - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
   
    plt.show()
    
.. plot::

    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [575, 705, 21591, 913, 1160, 18666] )
    ram = np.array( [353, 276, 1985, 447, 352, 2782] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Save test file - time')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [575, 705, 21591, 913, 1160, 18666] )
    ram = np.array( [353, 276, 1985, 447, 352, 2782] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAM [MB]')
    ax.set_title('Save test file - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)

    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [2835, 18188, 11926, 29, 2338, 15566, 12598, 39] )
    ram = np.array( [363, 287, 188, 525, 450, 355, 260, 737] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Get all channels (36424 calls) - time')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)

    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [2835, 18188, 11926, 29, 2338, 15566, 12598, 39] )
    ram = np.array( [363, 287, 188, 525, 450, 355, 260, 737] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAm [MB]')
    ax.set_title('Get all channels (36424 calls) - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)

    plt.show()
    

x86 Python results
------------------
The test environment used for 32 bit tests had:

* Python 3.6.1 (v3.6.1:69c0db5, Mar 21 2017, 17:54:52) [MSC v.1900 32 bit (Intel)]
* Windows-7-6.1.7601-SP1
* Intel64 Family 6 Model 94 Stepping 3, GenuineIntel (i7-6820Q)
* 16GB installed RAM

The notations used in the results have the following meaning:

* nodata = MDF object created with load_measured_data=False (raw channel data no loaded into RAM)
* compression = MDF object created with compression=True (raw channel data loaded into RAM and compressed)
* noconvert = MDF object created with convertAfterRead=False

Raw data
^^^^^^^^

================================================== ========= ========
Open file                                          Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                     1031      284
asammdf 2.1.0 compression mdfv3                         1259      192
asammdf 2.1.0 nodata mdfv3                               584      114
mdfreader 0.2.5 mdfv3                                   3809      455
mdfreader 0.2.5 no convert mdfv3                        3498      321
asammdf 2.1.0 mdfv4                                     2109      341
asammdf 2.1.0 compression mdfv4                         2405      239
asammdf 2.1.0 nodata mdfv4                              1686      159
mdfreader 0.2.5 mdfv4                                  44400      578
mdfreader 0.2.5 noconvert mdfv4                        43867      449
================================================== ========= ========


================================================== ========= ========
Save file                                          Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                      713      286
asammdf 2.1.0 compression mdfv3                          926      194
mdfreader 0.2.5 mdfv3                                  19862     1226
asammdf 2.1.0 mdfv4                                     1109      347
asammdf 2.1.0 compression mdfv4                         1267      246
mdfreader 0.2.5 mdfv4                                  17518     1656
================================================== ========= ========


================================================== ========= ========
Get all channels (36424 calls)                     Time [ms] RAM [MB]
================================================== ========= ========
asammdf 2.1.0 mdfv3                                     3943      295
asammdf 2.1.0 compression mdfv3                        29682      203
asammdf 2.1.0 nodata mdfv3                             23215      129
mdfreader 0.2.5 mdfv3                                     38      455
asammdf 2.1.0 mdfv4                                     3227      351
asammdf 2.1.0 compression mdfv4                        26070      250
asammdf 2.1.0 nodata mdfv4                             21619      171
mdfreader 0.2.5 mdfv4                                     51      578
================================================== ========= ========


Graphical results
^^^^^^^^^^^^^^^^^

.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'mdfreader 0.2.5 no convert mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4', 'mdfreader 0.2.5 noconvert mdfv4']
    time = np.array( [1031, 1259, 584, 3809, 3498, 2109, 2405, 1686, 44400, 43867] )
    ram = np.array( [284, 192, 114, 455, 321, 341, 239, 159, 578, 449] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Open test file - time')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.show()

.. plot::   

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'mdfreader 0.2.5 no convert mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4', 'mdfreader 0.2.5 noconvert mdfv4']
    time = np.array( [1031, 1259, 584, 3809, 3498, 2109, 2405, 1686, 44400, 43867] )
    ram = np.array( [284, 192, 114, 455, 321, 341, 239, 159, 578, 449] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAM [MB]')
    ax.set_title('Open test file - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.show()

.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [713, 926, 19862, 1109, 1267, 17518] )
    ram = np.array( [286, 194, 1226, 347, 246, 1656] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Save test file - time')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)

    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [713, 926, 19862, 1109, 1267, 17518] )
    ram = np.array( [286, 194, 1226, 347, 246, 1656] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAM [MB]')
    ax.set_title('Save test file - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.savefig('x86_save.png', dpi=300)
    
    plt.show()

.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [3943, 29682, 23215, 38, 3227, 26070, 21619, 51] )
    ram = np.array( [295, 203, 129, 455, 351, 250, 171, 578] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, time[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, time[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Time [ms]')
    ax.set_title('Get all channels (36424 calls) - time')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.show()
    
.. plot::

    import matplotlib.pyplot as plt
    import numpy as np
    
    cat = ['asammdf 2.1.0 mdfv3', 'asammdf 2.1.0 compression mdfv3', 'asammdf 2.1.0 nodata mdfv3', 'mdfreader 0.2.5 mdfv3', 'asammdf 2.1.0 mdfv4', 'asammdf 2.1.0 compression mdfv4', 'asammdf 2.1.0 nodata mdfv4', 'mdfreader 0.2.5 mdfv4']
    time = np.array( [3943, 29682, 23215, 38, 3227, 26070, 21619, 51] )
    ram = np.array( [295, 203, 129, 455, 351, 250, 171, 578] )
    
    y_pos = list(range(len(cat)))
    
    fig, ax = plt.subplots()
    fig.set_size_inches(9, 4.5)
    
    asam_pos = [i for i, c in enumerate(cat) if c.startswith('asam')]
    mdfreader_pos = [i for i, c in enumerate(cat) if c.startswith('mdfreader')]
    
    ax.barh(asam_pos, ram[asam_pos], color='green', ecolor='green')
    ax.barh(mdfreader_pos, ram[mdfreader_pos], color='blue', ecolor='black')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('RAM [MB]')
    ax.set_title('Get all channels (36424 calls) - RAM usage')
    ax.xaxis.grid() 
    
    fig.subplots_adjust(bottom=0.15, top=0.9, left=0.4, right=0.9)
    
    plt.show()