from abc import ABC


class Metadata(ABC):
    isolate_id: str or None
    metadata_fields = list()  # Set in subclasses

    def __init__(self, metadata: dict):
        for field in self.metadata_fields:
            setattr(self, field, metadata[field])
        self.isolate_id = metadata.get('isolate_id')
    
    @classmethod
    def get_field_list(cls):
        return cls.metadata_fields


class TBRMetadata(Metadata):
    metadata_fields = [
        'age',
        'gender',
        'kma',
        'region',
        'travel',
        'travel_country',
        'primary_isolate',
        # 'date_received',
        # 'date_received_kma',
        # 'date_sample',
    ]


class LIMSMetadata(Metadata):
    metadata_fields = [
        'product_type',
        'product',
        'origin_country',
        'cvr_number',
        'chr_number',
        'aut_number',
        'animal_species',
        # Could all the amr fields be concatenated to one field where the values could be unpacked by the frontend?
        # 'amr_ami',
        # 'amr_amp',
        # 'amr_azi',
        # 'amr_chl',
        # 'amr_cip',
        # 'amr_col',
        # 'amr_etp',
        # 'amr_f/c',
        # 'amr_fep',
        # 'amr_fot',
        # 'amr_fox',
        # 'amr_gen',
        # 'amr_imi',
        # 'amr_mero',
        # 'amr_nal',
        # 'amr_sul',
        # 'amr_t/c',
        # 'amr_taz',
        # 'amr_tet',
        # 'amr_tgc',
        # 'amr_tmp',
        # 'amr_trm',
        # 'animal_species',
        # 'date_analysis_sofi', Manual data?
        # 'date_sample', Manual data?
        # 'project_number', Manual data?
        # 'project_title', Manual data?
        # 'resfinder_version',
        # 'sample_info',
        #  'sequence_id', Not related to metadata
        # 'serotype_final', Manual data?
        # 'st_final', Manual data?
        # 'subspecies', Manual data?
    ]



class Sequence():
    sample_doc: dict = {
        "categories": {
            "species_detection": {
                "summary": dict()
            },
            "sample_info": {
                "summary": dict(),
                "filenames": list()
            },
            "paired_reads": {
                "summary": {
                    "data": list()
                },
            },
            "cgmlst": {
                "name": "cgmlst",
                "component": dict(),
                "summary": dict(),
                "report": {
                    "data": dict()
                    },
            }
        }
    }

    field_mapping: dict = {
        'owner': ['categories', 'sample_info', 'summary', 'institution'],
        'sequence_id':['sample_info', 'summary', 'sample_name'],
        'sample_id': ['name'],
        'species': ['species_detection', 'summary', 'detected_species'],
        'allele_profile': ['cgmlst', 'report', 'data', 'alleles'],
        'sequence_type': ['cgmlst', 'report', 'data', 'sequence_type'],
        }
    
    metadata: TBRMetadata or LIMSMetadata or None

    def as_dict(self):
        return self.sample_doc

    @classmethod
    def from_bifrost_sample(cls, sample_doc:dict):
        try:
            assert 'name' in sample_doc
        except AssertionError:
            raise ValueError("name not found")
        try:
            assert 'sample_name' in sample_doc['categories']['sample_info']['summary']
        except (AssertionError, KeyError):
            raise ValueError("sample_name not found")
        try:
            assert 'institution' in sample_doc['categories']['sample_info']['summary']
        except (AssertionError, KeyError):
            raise ValueError("institution not found")
        instance = cls()
        instance.sample_doc = sample_doc
        return instance

    @property
    def sequence_id(self):
        try:
            return self.sample_doc['categories']['sample_info']['summary']['sample_name']
        except KeyError:
            return None
    
    @sequence_id.setter
    def sequence_id(self, sequence_id: str):
        self.sample_doc['categories']['sample_info']['summary']['sample_name'] = sequence_id
    
    @property
    def isolate_id(self):
        try:
            return self.sample_doc['name']
        except KeyError:
            return None
    
    @isolate_id.setter
    def isolate_id(self, isolate_id: str):
        self.sample_doc['name'] = isolate_id
    
    @property
    def owner(self):
        try:
            return self.sample_doc['categories']['sample_info']['summary']['institution']
        except KeyError:
            return None
    
    @owner.setter
    def owner(self, owner: str):
        self.sample_doc['categories']['sample_info']['summary']['institution'] = owner
    
    @property
    def species(self):
        try:
            return self.sample_doc['categories']['species_detection']['summary']['detected_species']
        except KeyError:
            return None

    @species.setter
    def species(self, species: str):
        self.sample_doc['categories']['species_detection']['summary']['detected_species'] = species
    
    @property
    def allele_profile(self):
        try:
            return self.sample_doc['categories']['cgmlst']['report']['data']['alleles']
        except KeyError:
            return None

    @allele_profile.setter
    def allele_profile(self, allele_profile: dict):
        self.sample_doc['categories']['cgmlst']['report']['data']['alleles'] = allele_profile
    
    @property
    def sequence_type(self):
        try:
            return self.sample_doc['categories']['cgmlst']['report']['data']['sequence_type']
        except KeyError:
            return None
    
    @sequence_type.setter
    def sequence_type(self, sequence_type: int):
        self.sample_doc['categories']['cgmlst']['report']['data']['sequence_type'] = sequence_type
