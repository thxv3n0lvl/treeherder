import json
import itertools
from datadiff import diff

from sampledata import SampleData
from treeherder.model.derived.refdata import RefDataManager

def do_job_ingestion(jm, refdata, job_data, sample_resultset, verify_data=True):
    """
    Ingest ``job_data`` which will be JSON job blobs.

    ``verify_data`` - whether or not to run the ingested jobs
                      through the verifier.
    """
    jm.store_result_set_data(sample_resultset)

    max_index = len(sample_resultset) - 1
    resultset_index = 0

    # Structures to test if we stored everything
    job_guids_ref = {}
    build_platforms_ref = set()
    machine_platforms_ref = set()

    machines_ref = set()
    options_ref = set()
    job_types_ref = set()
    products_ref = set()
    result_sets_ref = set()
    log_urls_ref = set()
    artifacts_ref = {}

    blobs = []
    for index, blob in enumerate(job_data):

        if resultset_index > max_index:
            resultset_index = 0

        # Modify job structure to sync with the resultset sample data
        if 'sources' in blob:
            del blob['sources']

        blob['revision_hash'] = sample_resultset[resultset_index]['revision_hash']

        blobs.append(blob)

        resultset_index += 1

        # Build data structures to confirm everything is stored
        # as expected
        if verify_data:

            job_guid = blob['job']['job_guid']

            job = blob['job']

            job_guids_ref[ job_guid ] = {
                job.get('who', 'unknown'),
                job.get('reason', 'unknown'),
                job.get('result', 'unknown'),
                job.get('state', 'unknown'),
                long( job.get('submit_timestamp') ) or None,
                long( job.get('start_timestamp') ) or None,
                long( job.get('end_timestamp') ) or None
                }

            build_platforms_ref.add(
                RefDataManager.get_platform_key(
                    job.get('build_platform', {}).get('os_name', 'unkown'),
                    job.get('build_platform', {}).get('platform', 'unkown'),
                    job.get('build_platform', {}).get('architecture', 'unknown')
                    ) )

            machine_platforms_ref.add(
                RefDataManager.get_platform_key(
                    job.get('machine_platform', {}).get('os_name', 'unkown'),
                    job.get('machine_platform', {}).get('platform', 'unkown'),
                    job.get('machine_platform', {}).get('architecture', 'unknown')
                    ) )

            machines_ref.add(job.get('machine', 'unknown'))

            options_ref = options_ref.union( job.get('option_collection', []).keys() )

            job_types_ref.add(job.get('name', 'unknown'))
            products_ref.add(job.get('product_name', 'unknown'))
            result_sets_ref.add(blob['revision_hash'])

            log_url_list = job.get('log_references', [])
            for log_data in log_url_list:
                log_urls_ref.add( log_data['url'] )

            artifact_name = job.get('artifact', {}).get('name')
            if artifact_name:
                artifacts_ref[artifact_name] = job.get('artifact')

    #Store the modified json blobs
    jm.store_job_data(blobs)

    # Process the job objects in chunks of size == process_objects_limit
    process_objects_limit = 1000
    chunks = grouper(job_data, process_objects_limit)
    for c in chunks:
        jm.process_objects(process_objects_limit, raise_errors=True)

    if verify_data:
        # Confirms stored data matches whats in the reference data structs
        verify_build_platforms(refdata, build_platforms_ref)
        verify_machine_platforms(refdata, machine_platforms_ref)
        verify_machines(refdata, machines_ref)
        verify_options(refdata, options_ref)
        verify_job_types(refdata, job_types_ref)
        verify_products(refdata, products_ref)
        verify_result_sets(jm, result_sets_ref)
        verify_log_urls(jm, log_urls_ref)
        verify_artifacts(jm, artifacts_ref)

    # Default verification confirms we loaded all of the objects
    complete_count = jm.get_os_dhub().execute(
        proc="objectstore_test.counts.complete")[0]["complete_count"]
    loading_count = jm.get_os_dhub().execute(
        proc="objectstore_test.counts.loading")[0]["loading_count"]

    assert complete_count == len(job_data)
    assert loading_count == 0

def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return itertools.izip_longest(*args, fillvalue=fillvalue)

def verify_build_platforms(refdata, build_platforms_ref):

    build_platforms = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_build_platforms',
        )
    build_platforms_set = set()
    for build_platform in build_platforms:
        build_platforms_set.add(
            RefDataManager.get_platform_key(
                build_platform.get('os_name'),
                build_platform.get('platform'),
                build_platform.get('architecture')
                ) )

    assert build_platforms_ref.issubset(build_platforms_set)

def verify_machine_platforms(refdata, machine_platforms_ref):

    machine_platforms = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_machine_platforms',
        )
    machine_platforms_set = set()
    for machine_platform in machine_platforms:
        machine_platforms_set.add(
            RefDataManager.get_platform_key(
                machine_platform.get('os_name'),
                machine_platform.get('platform'),
                machine_platform.get('architecture')
                ) )

    assert machine_platforms_ref.issubset(machine_platforms_set)

def verify_machines(refdata, machines_ref):

    machines = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_machines',
        key_column='name',
        return_type='set'
        )

    assert machines_ref.issubset(machines)

def verify_options(refdata, options_ref):

    options = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_options',
        key_column='name',
        return_type='set'
        )

    assert options_ref.issubset(options)

def verify_job_types(refdata, job_types_ref):

    job_types = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_job_types',
        key_column='name',
        return_type='set'
        )

    assert job_types_ref.issubset(job_types)

def verify_products(refdata, products_ref):

    products = refdata.dhub.execute(
        proc='test_refdata.selects.test_all_products',
        key_column='name',
        return_type='set'
        )

    assert products_ref.issubset(products)

def verify_result_sets(jm, result_sets_ref):

    revision_hashes = jm.get_jobs_dhub().execute(
        proc='jobs.selects.get_all_result_set_revision_hashes',
        key_column='revision_hash',
        return_type='set'
        )

    assert result_sets_ref.issubset(revision_hashes)

def verify_log_urls(jm, log_urls_ref):

    log_urls = jm.get_jobs_dhub().execute(
        proc='jobs.selects.get_all_log_urls',
        key_column='url',
        return_type='set'
        )

    assert log_urls_ref.issubset(log_urls)

def verify_artifacts(jm, artifacts_ref):

    artifacts = jm.get_jobs_dhub().execute(
        proc='jobs.selects.get_all_artifacts',
        key_column='name',
        return_type='dict'
        )

    for key in artifacts.keys():
        assert artifacts[key]['name'] == artifacts_ref[key]['name']
        assert artifacts[key]['type'] == artifacts_ref[key]['type']
        assert json.loads(artifacts[key]['blob']) == artifacts_ref[key]['blob']


def load_exp(filename):
    """
    Load in an expected result json and return as an obj.

    If the file doesn't exist, it will be created, but the test will
    fail, due to no content.  This is to make it easier during test
    development.
    """
    path = SampleData().get_log_path(filename)
    exp_str = open(path, "a+").read()
    try:
        return json.loads(exp_str)
    except ValueError:
        # if it's not parse-able, return an empty dict
        return {}


class SourceDictBuilder(object):
    """Given a ``job_id``, rebuild the dictionary the source came from."""

    def __init__(self, jm, job_guid):
        self.jm = jm
        self.job_guid = job_guid
        job_data = self.jm.get_jobs_dhub().execute(
            proc="jobs_test.selects.row_by_guid",
            placeholders=[self.job_guid],
            return_type="iter"
        ).next()
        self.job_id = job_data['id']

    def as_dict(self):

        source = self.jm.get_jobs_dhub().execute(
            proc="jobs_test.selects.job_source",
            placeholders=[self.job_id],
            return_type="iter"
        ).next()

        source["repository"] = self._get_repository(
            source["repository_id"])
        del(source["repository_id"])

        return unicode_keys(source)

    def _get_repository(self, obj_id):
        obj = self.jm.refdata_model.get_row_by_id(
            "repository",
            obj_id,
        ).get_column_data("name")
        return obj


class JobDictBuilder(object):
    """Given a ``job_id``, rebuild the dictionary the job came from."""

    def __init__(self, jm, job_guid):
        self.jm = jm
        self.job_guid = job_guid
        job_data = self.jm.get_jobs_dhub().execute(
            proc="jobs_test.selects.row_by_guid",
            placeholders=[self.job_guid],
            return_type="iter"
        ).next()
        self.job_id = job_data['id']

    def as_dict(self):
        job = self.jm.get_job(self.job_id)

        job["artifact"] = self._get_artifact()
        job["log_references"] = self._get_logs()

        job["option_collection"] = self._get_option_collection(
            job["option_collection_hash"])
        del(job["option_collection_hash"])

        job["machine_platform"] = self._get_machine_platform(
            job["machine_platform_id"])
        del(job["machine_platform_id"])

        job["build_platform"] = self._get_build_platform(
            job["build_platform_id"])
        del(job["build_platform_id"])

        job["machine"] = self._get_machine(
            job["machine_id"])
        del(job["machine_id"])
        del(job["machine_name"])

        job["product_name"] = self._get_product(
            job["product_id"])
        del(job["product_id"])

        job["name"] = self._get_name(
            job["job_type_id"])
        del(job["job_type_id"])

        del(job["id"])
        del(job["active_status"])
        del(job["result_set_id"])

        if not job["job_coalesced_to_guid"]:
            del(job["job_coalesced_to_guid"])

        return unicode_keys(job)

    def _get_option_collection(self, option_collection_hash):
        """
        Needs to work with hash.  Get row by id won't work anymore.
        probably need to a new getter where it gets the option id
        but the hash means there's possibly more than one option.
        maybe I need mauro to make a splitter get method?
        """
        option_iter = self.jm.refdata_model.get_option_names(
            option_collection_hash)
        options = {}
        for name_dict in option_iter:
            options[name_dict["name"]] = True

        return options

    def _get_machine_platform(self, obj_id):
        obj = self.jm.refdata_model.get_row_by_id(
            "machine_platform",
            obj_id,
        ).next()
        del(obj["active_status"])
        del(obj["id"])
        return unicode_keys(obj)

    def _get_build_platform(self, obj_id):
        obj = self.jm.refdata_model.get_row_by_id(
            "build_platform",
            obj_id,
        ).next()
        del(obj["active_status"])
        del(obj["id"])
        return unicode_keys(obj)

    def _get_machine(self, obj_id):
        obj = self.jm.refdata_model.get_row_by_id(
            "machine",
            obj_id,
        ).get_column_data("name")
        return obj

    def _get_product(self, obj_id):
        obj = self.jm.refdata_model.get_row_by_id(
            "product",
            obj_id,
        ).get_column_data("name")
        return obj

    def _get_name(self, obj_id):
        job_type = self.jm.refdata_model.get_row_by_id(
            "job_type",
            obj_id,
        ).next()
        return job_type['name']

    def _get_logs(self):
        logs = self.jm.get_jobs_dhub().execute(
            proc="jobs_test.selects.job_log_urls",
            placeholders=[self.job_id],
            key_column="id",
            return_type='dict',
        )

        log_values = []
        for log in logs.values():
            del(log["active_status"])
            del(log["id"])
            del(log["job_id"])
            log_values.append(unicode_keys(log))

        return log_values

    def _get_artifact(self):
        artifact = self.jm.get_jobs_dhub().execute(
            proc="jobs_test.selects.job_artifact",
            placeholders=[self.job_id],
            key_column="id",
            return_type='dict',
        )
        if not len(artifact):
            artifact = {}
        else:
            artifact = artifact[self.job_id]
            del(artifact["active_status"])
            del(artifact["id"])
            del(artifact["job_id"])

        return unicode_keys(artifact)


def unicode_keys(d):
    return dict([(unicode(k), v) for k, v in d.items()])


def clean_source_blob_dict(src):
    """Fix a few fields so they're easier to compare"""
    src["commit_timestamp"] = long(src["commit_timestamp"])
    src["push_timestamp"] = long(src["push_timestamp"])
    return src


def clean_job_blob_dict(job):
    """Fix a few fields so they're easier to compare"""
    job["start_timestamp"] = long(job["start_timestamp"])
    job["submit_timestamp"] = long(job["submit_timestamp"])
    job["end_timestamp"] = long(job["end_timestamp"])
    job["result"] = unicode(job["result"])

    # move artifact logs to log_references area for comparison
    try:
        artlog = job["artifact"]["log_urls"]
        job["log_references"].extend(artlog)
        del(job["artifact"]["log_urls"])
    except KeyError:
        pass  # no problem

    # @@@ we don't keep track of VM'ness?
    try:
        del(job["machine_platform"]["vm"])
    except KeyError:
        pass  # no problem
    try:
        del(job["build_platform"]["vm"])
    except KeyError:
        pass  # no problem

    return job
