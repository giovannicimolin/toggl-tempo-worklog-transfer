from collections import namedtuple


TIMELOG = namedtuple(
    'Timelog',
    field_names=[
        'ticket',
        'date',
        'time',
        'description',
        'ff_time',
        'dd_time'
    ]
)
