"""Reject incorrect or incomplete actual capabilities; preserve existing port budgets."""
import copy
import csv
from pathlib import Path
import tempfile
import unittest

from capabilities import compare_capabilities,observer_source_control,FIELDS,PORTS,HERE


def write(path,records,fields=None):
    with path.open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields or list(records[0]))
        writer.writeheader();writer.writerows(records)


class CapabilityControls(unittest.TestCase):
    def test_passive_observer_forwarding_and_getters_cannot_change(self):
        self.assertIn('passed',observer_source_control()['status'])
        body=(HERE/'NativeProbe.cpp').read_bytes()
        damaged=body.replace(b'    original(services,time,running,active,force);',b'    // original call removed',1)
        with self.assertRaisesRegex(ValueError,'forwarding'):observer_source_control(damaged)

    def fixture(self,root):
        state=dict(tick='0',object='Telescope',**{'class':'HST'},**{name:'1' for name in FIELDS})
        state.update(empty_mass='10886',size='7.52',thrusters='0',propellants='0')
        port=dict(tick='0',object='Telescope',index='0',x='0',y='0',z='1',dx='0',dy='0',dz='1',rx='0',ry='1',rz='0',docked='')
        for name in ('native','windows'):
            folder=root/name;folder.mkdir()
            write(folder/'stock-vessel-state.csv',[state])
            write(folder/'stock-vessel-docks.csv',[port])
            write(folder/'stock-vessel-attachments.csv',[],['tick','object','to_parent','index'])
        return state,port

    def check(self,root):
        return compare_capabilities(root/'native',root/'windows',{'Telescope':'HST'},dict(position_m=.01,rotation_rad=1e-8))

    def test_wrong_caps_duplicates_missing_and_nonfinite_values_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);state,port=self.fixture(root)
            self.assertEqual(self.check(root)['Telescope']['size'],'7.52')
            for change in (dict(thrusters='1'),dict(size='7.53'),dict(empty_mass='nan'),dict(csx='inf'),{'class':'Generic'}):
                with self.subTest(change=change),self.assertRaises(ValueError):
                    write(root/'native/stock-vessel-state.csv',[dict(state,**change)])
                    self.check(root)
            for records in ([],[state,state]):
                with self.subTest(records=len(records)),self.assertRaises(ValueError):
                    write(root/'native/stock-vessel-state.csv',records,list(state));self.check(root)

    def test_missing_port_identity_and_geometry_outside_existing_budget_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);state,port=self.fixture(root)
            write(root/'native/stock-vessel-docks.csv',[dict(port,x='0.009')]);self.check(root)
            for records in ([],[dict(port,x='0.011')],[dict(port,dy='0.00000002')],[dict(port,docked='Manufactured')],[port,port]):
                with self.subTest(records=records),self.assertRaises(ValueError):
                    write(root/'native/stock-vessel-docks.csv',records,list(port));self.check(root)
            partial={key:port[key] for key in ('tick','object','index')}
            write(root/'native/stock-vessel-docks.csv',[partial])
            with self.assertRaisesRegex(ValueError,'Incomplete'):self.check(root)


if __name__=='__main__':unittest.main()
