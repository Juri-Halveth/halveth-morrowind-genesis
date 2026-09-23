from pathlib import Path
import struct
import tempfile
import unittest
from scripts.survey_universe import survey,scan


def record(tag,parts):
    data=b''.join(struct.pack('<4sI',key,len(value))+value for key,value in parts)
    return struct.pack('<4sIII',tag,len(data),0,0)+data


class UniverseSurveyTests(unittest.TestCase):
    def test_complete_bytes_case_insensitive_overrides_and_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/'a.esm';b=root/'b.esp'
            a.write_bytes(record(b'TES3',[])+record(b'WEAP',[(b'NAME',b'Sword\0'),(b'FNAM',b'Old')])+
                          record(b'BOOK',[(b'NAME',b'book\0'),(b'TEXT',b'Text')]))
            b.write_bytes(record(b'TES3',[])+record(b'WEAP',[(b'NAME',b'sword\0'),(b'FNAM',b'New')])+
                          record(b'BOOK',[(b'NAME',b'BOOK\0'),(b'DELE',b'\0'*4)]))
            before=[a.read_bytes(),b.read_bytes()]
            result=survey([a,b],root/'result')
            self.assertEqual(result['sourceBytesCovered'],sum(map(len,before)))
            self.assertEqual(result['recordsWalked'],6)
            self.assertEqual(result['effectiveRecordCounts'],{'WEAP':1})
            self.assertEqual(result['semanticIdentityFallbacks'],0)
            self.assertEqual(before,[a.read_bytes(),b.read_bytes()])
            with self.assertRaises(FileExistsError): survey([a],root/'result')

    def test_partial_record_cannot_count_as_full_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'bad.esm';path.write_bytes(record(b'TES3',[])+b'BOOK')
            with self.assertRaises(ValueError): list(scan(path))

    def test_exterior_cells_have_distinct_grid_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'cells.esm'
            p.write_bytes(record(b'TES3',[])+b''.join(record(b'CELL',[(b'NAME',b'Wilderness\0'),
                (b'DATA',struct.pack('<Iii',0,x,0))]) for x in (1,2)))
            self.assertEqual(survey([p],root/'out')['effectiveRecordCounts']['CELL'],2)

if __name__=='__main__': unittest.main()
