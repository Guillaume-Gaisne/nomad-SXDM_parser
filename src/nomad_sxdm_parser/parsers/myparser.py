from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

import os
import h5py
import numpy as np

from nomad.config import config
from nomad.datamodel.results import Material, Results
from nomad.parsing.parser import MatchingParser

import nomad_sxdm_parser.schema_packages.mypackage as sxdm

configuration = config.get_plugin_entry_point(
    'nomad_sxdm_parser.parsers:myparser'
)


class MyParser(MatchingParser):

    def extract_string(self, dataset):
        return dataset[()].decode('UTF-8')

    def parse_instrument(self):
        instrument = self.entry.m_create(sxdm.Instrument)
        monochromator = instrument.m_create(sxdm.Monochromator)
        monochromator.energy = self.extract_string(
            self.instrument['monochromator/energy']
        )

        sec_source = instrument.m_create(sxdm.Source)
        source = self.instrument['SOURCE']
        sec_source.name = self.extract_string(source['name'])
        sec_source.probe = self.extract_string(source['probe'])
        sec_source.type = self.extract_string(source['type'])

###############################################################################
    def parse_data(self):
        data = self.entry.m_create(sxdm.Data)

        data.energy = self.extract_string(self.data_section['energy'])
        data.sxdm_scan_type = self.extract_string(self.data_section['sdxm_scan_type'])

        sample_x = self.data_section['sample_x'][()]
        sample_y = self.data_section['sample_y'][()]
        dim_x = sample_x.shape[0]
        dim_y = sample_y.shape[0]

        data.dim_x = dim_x
        data.dim_y = dim_y
        data.sample_x = np.around(sample_x, 1)
        data.sample_y = np.around(sample_y, 1)
        data.dataset = self.data_section['data'][()]

###############################################################################
    def parse_sample(self):
        sample = self.entry.m_create(sxdm.Sample)
        sample.rotation_angle = self.sample['rotation_angle'][()]


###############################################################################
###############################################################################
    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:

        self.filepath = mainfile
        self.maindir = os.path.dirname(self.filepath)
        self.mainfile = os.path.basename(self.filepath)

        try:
            self.data = h5py.File(self.filepath)
        except Exception:
            self.logger.error('Error opening h5 file.')
            self.data = None
            return

        self.entry = sxdm.Entry()

        sec_entry = self.data['ENTRY']

        archive.data = self.entry

        self.entry.definition = self.extract_string(sec_entry['definition'])
        self.entry.start_time = self.extract_string(sec_entry['start_time'])
        self.entry.end_time = self.extract_string(sec_entry['end_time'])
        self.entry.title = self.extract_string(sec_entry['title'])

        self.data_section = sec_entry.get('DATA')
        self.instrument = sec_entry.get('INSTRUMENT')
        self.sample = sec_entry.get('SAMPLE')

        self.parse_data()
        self.parse_instrument()
        self.parse_sample()

        archive.results = Results(material=Material(elements=['Ga', 'N']))