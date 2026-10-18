"""Exercise Dev-export normalization against copies of the native solution."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'solution/unpacked'
spec = importlib.util.spec_from_file_location('prepare_dev_export', ROOT/'scripts/prepare-dev-export.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareDevExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'unpacked'
        shutil.copytree(SOURCE, self.folder)

    def test_unchanged_portable_source_is_byte_identical(self):
        module.prepare(self.folder, SOURCE)
        for path in SOURCE.rglob('*'):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (self.folder/path.relative_to(SOURCE)).read_bytes(), str(path.relative_to(SOURCE)))

    def test_clears_installation_values_but_preserves_flow_edit(self):
        path = next((self.folder/'Workflows').glob('*.json'))
        flow = json.loads(path.read_text(encoding='utf-8-sig'))
        definition = flow['properties']['definition']
        definition['description'] = 'Updated in Dev'
        for parameter in definition['parameters'].values():
            if 'schemaName' in parameter.get('metadata', {}):
                parameter['defaultValue'] = 'test@example.com'
        ref = next(iter(flow['properties']['connectionReferences'].values()))
        ref['connection']['connectionId'] = 'tenant-owned-connection'
        ref['connectionName'] = 'tenant-owned-connection'
        path.write_text(json.dumps(flow), encoding='utf-8')
        metadata_path = path.with_name(path.name+'.data.xml')
        tree = ET.parse(metadata_path)
        tree.find('StateCode').text = '1'
        tree.find('StatusCode').text = '2'
        tree.write(metadata_path)
        definition_path = next((self.folder/'environmentvariabledefinitions').glob('*/environmentvariabledefinition.xml'))
        tree = ET.parse(definition_path)
        ET.SubElement(tree.getroot(), 'defaultvalue').text = 'test@example.com'
        tree.write(definition_path)
        values = definition_path.parent/'environmentvariablevalues'
        values.mkdir()
        (values/'test.xml').write_text('<environmentvariablevalue><value>test@example.com</value></environmentvariablevalue>')
        custom = self.folder/'Other/Customizations.xml'
        tree = ET.parse(custom)
        ET.SubElement(tree.find('connectionreferences')[0], 'connectionid').text = 'tenant-owned-connection'
        tree.write(custom)
        module.prepare(self.folder, SOURCE)
        result = json.loads(path.read_text())
        self.assertEqual(result['properties']['definition']['description'], 'Updated in Dev')
        self.assertNotIn('tenant-owned-connection', path.read_text())
        self.assertNotIn('test@example.com', path.read_text())
        self.assertIsNone(ET.parse(definition_path).find('defaultvalue'))
        self.assertFalse(values.exists())
        self.assertIsNone(ET.parse(custom).find('.//connectionid'))
        self.assertEqual(ET.parse(metadata_path).findtext('StateCode'), '0')

    def test_rejects_hard_coded_recipient_without_disclosing_it(self):
        path = next((self.folder/'Workflows').glob('*.json'))
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        data['properties']['definition']['description'] = 'private@example.com'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError) as error:
            module.prepare(self.folder, SOURCE)
        self.assertNotIn('private@example.com', str(error.exception))

    def test_rejects_missing_portable_configuration(self):
        shutil.rmtree(next((self.folder/'environmentvariabledefinitions').iterdir()))
        with self.assertRaisesRegex(ValueError, 'missing portable configuration'):
            module.prepare(self.folder, SOURCE)

    def test_rejects_different_solution_and_missing_dependencies(self):
        path = self.folder/'Other/Solution.xml'
        tree = ET.parse(path)
        tree.find('SolutionManifest/UniqueName').text = 'OtherSolution'
        tree.write(path)
        with self.assertRaisesRegex(ValueError, 'different solution'):
            module.prepare(self.folder, SOURCE)
        shutil.copy2(SOURCE/'Other/Solution.xml', path)
        tree = ET.parse(path)
        ET.SubElement(tree.find('SolutionManifest/MissingDependencies'), 'MissingDependency')
        tree.write(path)
        with self.assertRaisesRegex(ValueError, 'missing solution dependencies'):
            module.prepare(self.folder, SOURCE)

    def test_guard_prevents_replacing_arbitrary_directory(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected source destination'):
            module.replace_source(self.folder, Path(self.temp.name)/'elsewhere')

    def test_keeps_form_fill_opt_out(self):
        module.prepare(self.folder, SOURCE)
        path = next((self.folder/'aiskillconfigs').glob('*/aiskillconfig.xml'))
        self.assertEqual(ET.parse(path).findtext('aiskill'), 'FormFillFieldOptOut')

    def test_workflow_is_manual_main_only_and_does_not_publish_raw_export(self):
        # BaseLoader avoids YAML 1.1 treating the Actions key "on" as a boolean.
        workflow = yaml.load((ROOT/'.github/workflows/pull-from-dev.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['on']), {'workflow_dispatch'})
        job = workflow['jobs']['pull']
        self.assertEqual(job['if'], "github.ref == 'refs/heads/main'")
        self.assertEqual(job['concurrency']['group'], 'meeting-concierge-${{ inputs.environment }}')
        steps = job['steps']
        names = [step.get('name') for step in steps]
        self.assertLess(names.index('Check exported changes and package'), names.index('Open review pull request'))
        for step in steps:
            if 'actions/upload-artifact@' in step.get('uses', ''):
                self.assertNotIn('live-export', step['with']['path'])
                self.assertNotIn('unpacked', step['with']['path'])
        commands = '\n'.join(step.get('run', '') for step in steps)
        self.assertNotIn('pac solution import', commands)
        self.assertNotIn('pac solution publish', commands)
        self.assertNotIn('gh pr merge', commands)
        self.assertIn('DEV_EXPORT_ENABLED', commands)


if __name__ == '__main__':
    unittest.main(verbosity=2)
