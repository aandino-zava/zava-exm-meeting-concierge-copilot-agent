"""Turn a staged Dev export into portable source; never contacts a tenant."""
import argparse
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def write_xml(path, tree):
    ET.indent(tree, space='  ')
    tree.write(path, encoding='utf-8', xml_declaration=True)


def prepare(exported, baseline):
    """Normalize only installation values and flow state, preserving Dev logic."""
    manifest = ET.parse(exported/'Other/Solution.xml')
    expected = ET.parse(baseline/'Other/Solution.xml')
    if manifest.findtext('SolutionManifest/UniqueName') != expected.findtext('SolutionManifest/UniqueName'):
        raise ValueError('Dev export is a different solution.')
    if manifest.findtext('SolutionManifest/Managed') != '0':
        raise ValueError('Dev must contain the unmanaged solution.')
    dependencies = manifest.find('SolutionManifest/MissingDependencies')
    if dependencies is not None and len(dependencies):
        raise ValueError('Add or resolve missing solution dependencies in Dev before exporting.')

    required = {p.parent.name for p in (baseline/'environmentvariabledefinitions').glob('*/environmentvariabledefinition.xml')}
    definitions = list((exported/'environmentvariabledefinitions').glob('*/environmentvariabledefinition.xml'))
    present = {p.parent.name for p in definitions}
    if not required.issubset(present):
        raise ValueError('Dev is missing portable configuration definitions. Reconcile Dev with the current configurable package first; do not overwrite unsaved Dev work.')
    for path in definitions:
        tree = ET.parse(path)
        # Neither current values nor defaults belong in the portable package.
        for parent in tree.iter():
            for child in list(parent):
                if child.tag.lower() in {'defaultvalue', 'environmentvariablevalues', 'environmentvariablevalue'}:
                    parent.remove(child)
        write_xml(path, tree)
    for path in sorted(exported.rglob('*'), reverse=True):
        if 'environmentvariablevalues' in [part.lower() for part in path.relative_to(exported).parts]:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()

    customizations = exported/'Other/Customizations.xml'
    tree = ET.parse(customizations)
    for parent in tree.iter():
        for child in list(parent):
            if child.tag.lower() in {'environmentvariablevalues', 'environmentvariablevalue'}:
                parent.remove(child)
    for ref in tree.findall('connectionreferences/connectionreference'):
        for child in list(ref):
            if child.tag.lower() == 'connectionid':
                ref.remove(child)
    write_xml(customizations, tree)

    used = set()
    for path in (exported/'Workflows').glob('*.json'):
        flow = json.loads(path.read_text(encoding='utf-8-sig'))
        properties = flow['properties']
        for parameter in properties['definition'].get('parameters', {}).values():
            schema = parameter.get('metadata', {}).get('schemaName')
            if schema:
                used.add(schema)
                parameter['defaultValue'] = ''
        for ref in properties.get('connectionReferences', {}).values():
            for item in [ref, ref.get('connection', {})]:
                for key in ['connectionId', 'connectionName', 'id']:
                    item.pop(key, None)
            connection = ref.get('connection', {})
            for key in list(connection):
                if key != 'connectionReferenceLogicalName':
                    del connection[key]
        properties.pop('connectionReferencesRuntime', None)
        if 'state' in properties:
            properties['state'] = 'Stopped'
        path.write_text(json.dumps(flow, indent=2)+'\n', encoding='utf-8')
        metadata_path = path.with_name(path.name+'.data.xml')
        metadata = ET.parse(metadata_path)
        for tag, value in [('StateCode', '0'), ('StatusCode', '1')]:
            node = metadata.find(tag)
            if node is None:
                raise ValueError('An exported flow is missing state metadata.')
            node.text = value
        write_xml(metadata_path, metadata)
    if not required.issubset(used):
        raise ValueError('Dev flows must use the portable calendar settings. Hard-coded lab flows need reconciliation first.')

    # Do not expose source tenant values in a PR or build artifact. Unknown literals
    # require a deliberate configuration change rather than blind replacement.
    forbidden = re.compile(r'[\w.+%-]+@[\w.-]+\.[A-Za-z]{2,}|https?://[^\s\"<>]+\.crm\d*\.dynamics\.com|[\w.-]+\.onmicrosoft\.com', re.I)
    for path in exported.rglob('*'):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            continue
        if forbidden.search(text):
            raise ValueError('Export still contains an email address or tenant URL. Move that value into configuration in Dev before retrying. No source values were printed.')

    # Retain existing byte formatting when only whitespace or XML formatting changed.
    for path in exported.rglob('*'):
        old = baseline/path.relative_to(exported)
        if not path.is_file() or not old.is_file():
            continue
        if path.suffix == '.json':
            same = json.loads(path.read_text(encoding='utf-8-sig')) == json.loads(old.read_text(encoding='utf-8-sig'))
        elif path.suffix == '.xml':
            def canonical(file):
                element = ET.parse(file).getroot()
                for node in element.iter():
                    if node.text is not None:
                        node.text = node.text.strip() or None
                    node.tail = None
                return ET.tostring(element)
            same = canonical(path) == canonical(old)
        else:
            same = path.read_bytes() == old.read_bytes()
        if same:
            path.write_bytes(old.read_bytes())


def replace_source(exported, destination):
    # Only this known checkout directory can be replaced, never a caller's path.
    if destination.resolve() != (ROOT/'solution/unpacked').resolve():
        raise ValueError('Unexpected source destination.')
    if exported.resolve() == destination.resolve() or destination.resolve() in exported.resolve().parents:
        raise ValueError('Stage the export outside solution/unpacked.')
    shutil.rmtree(destination)
    shutil.copytree(exported, destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    baseline = ROOT/'solution/unpacked'
    prepare(args.folder, baseline)
    if args.apply:
        replace_source(args.folder, baseline)
    print('Dev export prepared without installation values; packaged flows are off. Dev was not modified.')
